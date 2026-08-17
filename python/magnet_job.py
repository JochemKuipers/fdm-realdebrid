import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import uuid

from config_loader import load_config, public_config
from fdm_result import torrent_playlist
from platform_paths import app_data_dir, detached_popen_kwargs, find_addon_root, find_fdm
from rd_client import RealDebridClient, RealDebridError

SELECTION_WAIT_SEC = 60
MAX_JOBS = 20
TORRENT_FAIL_STATUSES = {"magnet_error", "error", "virus", "dead"}
TORRENT_WAIT_STATUSES = {
    "magnet_conversion",
    "waiting_files_selection",
    "queued",
    "downloading",
    "compressing",
    "uploading",
}
QUEUED_MESSAGE = (
    "Queued on Real-Debrid. Open the Firefox toolbar popup to pick files and watch progress."
)


class QueuedJob(Exception):
    def __init__(self, job_id, message=QUEUED_MESSAGE):
        super().__init__(message)
        self.job_id = job_id


def magnet_hash(url):
    if not str(url).lower().startswith("magnet:"):
        raise ValueError("Not a magnet link")

    query = url.split("?", 1)[1] if "?" in url else ""
    xts = urllib.parse.parse_qs(query, keep_blank_values=True).get("xt") or []
    for xt in xts:
        if xt.lower().startswith("urn:btih:"):
            return btih_to_hex(xt[9:])

    match = re.search(r"xt=urn:btih:([a-zA-Z0-9]+)", url, re.I)
    if match:
        return btih_to_hex(match.group(1))

    if re.search(r"xt=urn:btmh:", url, re.I):
        raise ValueError("Magnet is BitTorrent v2 only — Real-Debrid needs a v1 (btih) hash")
    raise ValueError("Magnet has no valid BitTorrent v1 hash (xt=urn:btih)")


def btih_to_hex(value):
    value = (value or "").strip()
    lowered = value.lower()
    if len(lowered) == 40 and all(char in "0123456789abcdef" for char in lowered):
        return lowered

    compact = value.replace("=", "").upper()
    if len(compact) == 32:
        raw = base64.b32decode(compact)
        if len(raw) == 20:
            return raw.hex()

    raise ValueError("Magnet has no valid BitTorrent v1 hash (xt=urn:btih)")


def normalize_magnet(url):
    return "magnet:?xt=urn:btih:" + magnet_hash(url)


def jobs_path():
    override = os.environ.get("FDM_RD_JOBS")
    if override:
        return override
    return os.path.join(app_data_dir(), "jobs.json")


def _empty_store():
    return {"jobs": []}


def load_store():
    path = jobs_path()
    if not os.path.isfile(path):
        return _empty_store()
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict) and isinstance(data.get("jobs"), list):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return _empty_store()


def save_store(store):
    path = jobs_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(store, handle)
    os.replace(tmp, path)


def get_job(job_id):
    for job in load_store().get("jobs", []):
        if job.get("id") == job_id:
            return job
    return None


def upsert_job(job):
    store = load_store()
    jobs = [item for item in store.get("jobs", []) if item.get("id") != job["id"]]
    job["updatedAt"] = time.time()
    jobs.insert(0, job)
    store["jobs"] = jobs[:MAX_JOBS]
    save_store(store)
    return job


def update_job(job_id, **fields):
    job = get_job(job_id)
    if not job:
        raise KeyError(job_id)
    job.update(fields)
    return upsert_job(job)


def set_selection(job_id, files):
    if files == "all" or files == ["all"]:
        selected = ["all"]
    else:
        selected = [str(item) for item in files if str(item).strip()]
    if not selected:
        raise ValueError("Select at least one file")
    job = get_job(job_id)
    if not job:
        raise KeyError(job_id)
    if job.get("status") not in ("needs_selection", "waiting_files_selection"):
        raise ValueError("This waybill is not waiting for a file pick")
    return update_job(job_id, selected=selected)


def cached_file_ids(payload, hash_hex):
    if not isinstance(payload, dict):
        return set()

    entry = (
        payload.get(hash_hex)
        or payload.get(hash_hex.lower())
        or payload.get(hash_hex.upper())
    )
    if entry is None and len(payload) == 1:
        entry = next(iter(payload.values()))
    if not isinstance(entry, dict):
        return set()

    ids = set()
    for variants in entry.values():
        if not isinstance(variants, list):
            continue
        for variant in variants:
            if isinstance(variant, dict):
                ids.update(str(key) for key in variant)
    return ids


def try_instant(client, hash_hex):
    try:
        payload = client.instant_availability(hash_hex)
    except RealDebridError as error:
        if error.status_code in (404, 503) or error.error_code in (7, 37):
            return set()
        raise
    return cached_file_ids(payload, hash_hex)


def add_or_reuse(client, magnet, hash_hex):
    try:
        return client.add_magnet(magnet)
    except RealDebridError as error:
        if error.error_code != 33:
            raise
        for torrent in client.list_torrents():
            if (torrent.get("hash") or "").lower() == hash_hex:
                return torrent
        raise RealDebridError("Torrent already active but not found in the Real-Debrid list")


def file_rows(info, cached_ids):
    rows = []
    for item in info.get("files") or []:
        file_id = str(item.get("id", ""))
        if not file_id:
            continue
        rows.append(
            {
                "id": file_id,
                "path": item.get("path") or file_id,
                "bytes": int(item.get("bytes") or 0),
                "cached": file_id in cached_ids,
            }
        )
    return rows


def unrestrict_links(client, config, info):
    links = info.get("links") or []
    if not links:
        raise RealDebridError("Torrent finished but Real-Debrid returned no links")

    unrestricted = []
    for link in links:
        result = client.unrestrict_link(link, remote=config["useRemoteTraffic"])
        if not result.get("download"):
            raise RealDebridError("Real-Debrid did not return a download link")
        unrestricted.append(result)

    if config["deleteTorrentAfter"]:
        try:
            client.delete_torrent(info["id"])
        except RealDebridError:
            pass

    title = info.get("filename") or info.get("original_filename") or "Real-Debrid torrent"
    webpage = info.get("magnet") or ""
    return torrent_playlist(webpage, unrestricted, title), [
        item["download"] for item in unrestricted
    ]


def send_to_fdm(urls):
    fdm_path = find_fdm()
    if not fdm_path:
        raise RuntimeError("Could not find fdm")
    for url in urls:
        subprocess.Popen(
            [fdm_path, "-fs", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )


def new_job(url, torrent_id, hash_hex, filename, files, cached_ids):
    return {
        "id": uuid.uuid4().hex[:10],
        "magnet": url,
        "hash": hash_hex,
        "torrent_id": str(torrent_id),
        "status": "queued",
        "progress": 0,
        "filename": filename or hash_hex or "torrent",
        "files": files,
        "cachedIds": sorted(cached_ids),
        "selected": [],
        "error": "",
        "updatedAt": time.time(),
    }


def spawn_worker(job_id, addon_root=None):
    if addon_root is None:
        addon_root = find_addon_root()
    if not addon_root:
        raise RuntimeError("Real-Debrid FDM add-on not found")
    script = os.path.join(addon_root, "python", "magnet_job.py")
    subprocess.Popen(
        [sys.executable, script, job_id],
        cwd=addon_root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        **detached_popen_kwargs(),
    )


def start_torrent_job(client, config, url, cookies="", spawn=True):
    cached_ids = set()
    hash_hex = ""
    display_url = url

    if url.lower().startswith("magnet:"):
        hash_hex = magnet_hash(url)
        display_url = normalize_magnet(url)
        cached_ids = try_instant(client, hash_hex)
        added = add_or_reuse(client, display_url, hash_hex)
    else:
        added = client.add_torrent_file(client.download_bytes(url, cookies))

    torrent_id = added["id"]
    info = client.get_torrent_info(torrent_id)
    hash_hex = hash_hex or (info.get("hash") or "").lower()
    if hash_hex and not cached_ids:
        cached_ids = try_instant(client, hash_hex)

    filename = info.get("filename") or info.get("original_filename") or hash_hex
    files = file_rows(info, cached_ids)

    if info.get("status") == "downloaded" and info.get("links"):
        info = dict(info)
        info["magnet"] = display_url
        result, _urls = unrestrict_links(client, config, info)
        return result

    job = new_job(display_url, torrent_id, hash_hex, filename, files, cached_ids)
    job["status"] = info.get("status") or "queued"
    job["progress"] = int(info.get("progress") or 0)
    upsert_job(job)
    if spawn:
        spawn_worker(job["id"])
    return None


def urls_from_result(result):
    if result.get("_type") == "playlist":
        return [entry["url"] for entry in result.get("entries", []) if entry.get("url")]
    return [fmt["url"] for fmt in result.get("formats", []) if fmt.get("url")]


def enqueue_url(url, cookies="", spawn=True):
    config = load_config()
    client = RealDebridClient(config["apiToken"])
    client.get_user()
    result = start_torrent_job(client, config, url, cookies, spawn=spawn)
    if result is not None:
        hash_hex = magnet_hash(url) if url.lower().startswith("magnet:") else ""
        job = new_job(url, "", hash_hex, result.get("title") or "Download", [], set())
        job["status"] = "done"
        job["progress"] = 100
        upsert_job(job)
        send_to_fdm(urls_from_result(result))
        return {"ok": True, "jobId": job["id"], "fastPath": True}
    job = load_store()["jobs"][0]
    return {"ok": True, "jobId": job["id"], "fastPath": False}


def status_payload():
    config = public_config()
    config["fdmFound"] = bool(find_fdm())
    config["addonFound"] = bool(find_addon_root())
    return {"ok": True, "config": config, "jobs": load_store().get("jobs", [])}


def _wait(client, job_id, torrent_id, poll_interval, max_wait, done_statuses):
    deadline = time.time() + max_wait
    while time.time() < deadline:
        info = client.get_torrent_info(torrent_id)
        status = info.get("status")
        update_job(
            job_id,
            status=status or "queued",
            progress=int(info.get("progress") or 0),
            filename=info.get("filename") or info.get("original_filename") or "",
            files=file_rows(info, set(get_job(job_id).get("cachedIds") or [])),
        )
        if status in done_statuses:
            return info
        if status in TORRENT_FAIL_STATUSES:
            raise RealDebridError(f"Torrent failed on Real-Debrid ({status})")
        if status not in TORRENT_WAIT_STATUSES and status is not None:
            raise RealDebridError(f"Unexpected torrent status: {status}")
        time.sleep(poll_interval)
    raise RealDebridError("Torrent still processing on Real-Debrid — try again later")


def _wait_for_selection(job_id):
    deadline = time.time() + SELECTION_WAIT_SEC
    while time.time() < deadline:
        job = get_job(job_id)
        selected = job.get("selected") or []
        if selected:
            return selected
        time.sleep(0.5)
    return ["all"]


def run_job(job_id):
    job = get_job(job_id)
    if not job:
        raise KeyError(job_id)

    config = load_config()
    client = RealDebridClient(config["apiToken"])
    torrent_id = job["torrent_id"]
    poll = config["torrentPollIntervalSec"]
    max_wait = config["torrentMaxWaitSec"]

    info = _wait(
        client,
        job_id,
        torrent_id,
        poll,
        max_wait,
        {"waiting_files_selection", "downloaded"},
    )

    if info.get("status") != "downloaded":
        cached_ids = set(job.get("cachedIds") or [])
        update_job(
            job_id,
            status="needs_selection",
            files=file_rows(info, cached_ids),
            filename=info.get("filename") or job.get("filename") or "",
        )
        selected = _wait_for_selection(job_id)
        files_param = "all" if selected == ["all"] else ",".join(selected)
        client.select_torrent_files(torrent_id, files_param)
        info = _wait(client, job_id, torrent_id, poll, max_wait, {"downloaded"})

    info = dict(info)
    info["magnet"] = job.get("magnet") or ""
    _result, urls = unrestrict_links(client, config, info)
    send_to_fdm(urls)
    update_job(job_id, status="done", progress=100, error="")


def main():
    if len(sys.argv) < 2:
        print("Missing job id")
        return 1
    job_id = sys.argv[1].strip()
    try:
        run_job(job_id)
        return 0
    except Exception as error:
        try:
            update_job(job_id, status="error", error=str(error))
        except KeyError:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
