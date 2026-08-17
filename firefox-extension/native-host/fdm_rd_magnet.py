import json
import os
import struct
import sys

host_dir = os.path.dirname(os.path.abspath(__file__))
repo_python = os.path.abspath(os.path.join(host_dir, "..", "..", "python"))
for path in (host_dir, repo_python):
    if path not in sys.path:
        sys.path.insert(0, path)

from platform_paths import find_addon_root


def slim_status(payload):
    jobs = []
    for job in payload.get("jobs") or []:
        jobs.append(
            {
                "id": job.get("id"),
                "hash": job.get("hash") or "",
                "torrent_id": job.get("torrent_id") or "",
                "status": job.get("status") or "",
                "progress": int(job.get("progress") or 0),
                "filename": job.get("filename") or "",
                "fileCount": job.get("fileCount", len(job.get("files") or [])),
                "error": job.get("error") or "",
                "updatedAt": job.get("updatedAt") or 0,
            }
        )
    payload["jobs"] = jobs
    return payload


def files_from_job(get_job, job_id, offset, limit):
    job = get_job(job_id)
    if not job:
        raise KeyError(job_id)
    files = job.get("files") or []
    offset = max(0, int(offset))
    limit = max(1, min(int(limit), 1500))
    chunk = files[offset : offset + limit]
    return {
        "ok": True,
        "jobId": job_id,
        "files": chunk,
        "offset": offset,
        "total": len(files),
        "more": offset + len(chunk) < len(files),
    }


def read_message():
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        sys.exit(0)

    length = struct.unpack("=I", raw_length)[0]
    payload = sys.stdin.buffer.read(length)
    if not payload:
        return {}

    return json.loads(payload.decode("utf-8"))


def send_message(message):
    encoded = json.dumps(message).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("=I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def slim_status(payload):
    jobs = []
    for job in payload.get("jobs") or []:
        jobs.append(
            {
                "id": job.get("id"),
                "hash": job.get("hash") or "",
                "torrent_id": job.get("torrent_id") or "",
                "status": job.get("status") or "",
                "progress": int(job.get("progress") or 0),
                "filename": job.get("filename") or "",
                "fileCount": job.get("fileCount", len(job.get("files") or [])),
                "error": job.get("error") or "",
                "updatedAt": job.get("updatedAt") or 0,
            }
        )
    payload["jobs"] = jobs
    return payload


def files_from_job(get_job, job_id, offset, limit):
    job = get_job(job_id)
    if not job:
        raise KeyError(job_id)
    files = job.get("files") or []
    offset = max(0, int(offset))
    limit = max(1, min(int(limit), 1500))
    chunk = files[offset : offset + limit]
    return {
        "ok": True,
        "jobId": job_id,
        "files": chunk,
        "offset": offset,
        "total": len(files),
        "more": offset + len(chunk) < len(files),
    }


def addon_python():
    addon_root = find_addon_root()
    if not addon_root:
        raise RuntimeError(
            "Real-Debrid FDM add-on not found. Install fdm-realdebrid in FDM first."
        )
    path = os.path.join(addon_root, "python")
    if path not in sys.path:
        sys.path.insert(0, path)
    return path


def import_jobs():
    try:
        addon_python()
    except RuntimeError:
        pass
    from magnet_job import enqueue_url, get_job, set_selection, status_payload

    try:
        from magnet_job import job_files
    except ImportError:
        job_files = None

    return enqueue_url, get_job, job_files, set_selection, status_payload


def handle(message):
    if not isinstance(message, dict):
        message = {"url": str(message)}

    cmd = (message.get("cmd") or "").strip()
    if not cmd and message.get("url"):
        cmd = "enqueue"

    try:
        enqueue_url, get_job, job_files, set_selection, status_payload = import_jobs()
    except ImportError:
        if cmd == "status":
            from platform_paths import find_addon_root, find_fdm

            return {
                "ok": True,
                "config": {
                    "tokenSet": False,
                    "useRemoteTraffic": False,
                    "deleteTorrentAfter": False,
                    "torrentPollIntervalSec": 5,
                    "torrentMaxWaitSec": 900,
                    "fdmFound": bool(find_fdm()),
                    "addonFound": bool(find_addon_root()),
                    "error": "Real-Debrid FDM add-on not found. Install fdm-realdebrid in FDM first.",
                },
                "jobs": [],
            }
        raise RuntimeError(
            "Real-Debrid FDM add-on not found. Install fdm-realdebrid in FDM first."
        )

    if cmd == "status":
        return slim_status(status_payload())

    if cmd == "files":
        job_id = message.get("jobId") or message.get("id")
        if not job_id:
            raise ValueError("Missing jobId")
        offset = message.get("offset") or 0
        limit = message.get("limit") or 1500
        if job_files:
            return job_files(job_id, offset=offset, limit=limit)
        return files_from_job(get_job, job_id, offset, limit)

    if cmd == "selectFiles":
        job_id = message.get("jobId") or message.get("id")
        files = message.get("files")
        if not job_id:
            raise ValueError("Missing jobId")
        set_selection(job_id, files)
        return {"ok": True, "jobId": job_id}

    if cmd == "enqueue":
        url = str(
            message.get("url") or message.get("magnet") or message.get("link") or ""
        ).strip()
        if not url:
            raise ValueError("Missing magnet or torrent URL")
        return enqueue_url(url)

    raise ValueError("Unknown command")


def main():
    try:
        send_message(handle(read_message()))
    except Exception as error:
        send_message({"ok": False, "success": False, "error": str(error)})


if __name__ == "__main__":
    main()
