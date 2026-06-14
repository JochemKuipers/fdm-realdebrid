import json
import os
import sys
import time
import urllib.parse

from config_loader import load_config
from fdm_result import (
    container_playlist,
    folder_playlist,
    single_media,
    torrent_playlist,
)
from result_cache import get_cached, set_cached
from rd_client import RealDebridClient, RealDebridError

CONTAINER_EXTENSIONS = (".dlc", ".ccf", ".ccfz", ".rsdf")
TORRENT_FAIL_STATUSES = {
    "magnet_error",
    "error",
    "virus",
    "dead",
}
TORRENT_WAIT_STATUSES = {
    "magnet_conversion",
    "queued",
    "downloading",
    "compressing",
    "uploading",
}


def emit_result(result):
    print(json.dumps(result, ensure_ascii=False))


def emit_error(message):
    print(message)
    sys.exit(1)


def is_magnet(url):
    return url.lower().startswith("magnet:")


def is_torrent_url(url):
    parsed = urllib.parse.urlparse(url)
    path = (parsed.path or "").lower()
    return path.endswith(".torrent")


def is_container_url(url):
    parsed = urllib.parse.urlparse(url)
    path = (parsed.path or "").lower()
    return path.endswith(CONTAINER_EXTENSIONS)


def is_rd_direct_url(url):
    parsed = urllib.parse.urlparse(url)
    hostname = (parsed.hostname or "").lower()
    return hostname.endswith("rdeb.io") or hostname.endswith("real-debrid.com")


def direct_download_result(url):
    filename = os.path.basename(urllib.parse.urlparse(url).path) or "download"
    return single_media(
        title=filename,
        webpage_url=url,
        download_url=url,
        filename=filename,
    )


def looks_like_folder_url(url):
    lowered = url.lower()
    markers = (
        "/folder/",
        "/folders/",
        "#f!",
        "folder=",
        "/dir/",
        "/collection/",
    )
    return any(marker in lowered for marker in markers)


def normalize_container_links(response):
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        links = response.get("links")
        if isinstance(links, list):
            return links
    return []


def wait_for_torrent(client, torrent_id, poll_interval, max_wait):
    deadline = time.time() + max_wait
    torrent_id = str(torrent_id)

    while time.time() < deadline:
        info = client.get_torrent_info(torrent_id)
        status = info.get("status")

        if status == "waiting_files_selection":
            return info
        if status == "downloaded":
            return info
        if status in TORRENT_FAIL_STATUSES:
            raise RealDebridError(f"Torrent failed on Real-Debrid ({status})")

        if status not in TORRENT_WAIT_STATUSES and status is not None:
            raise RealDebridError(f"Unexpected torrent status: {status}")

        time.sleep(poll_interval)

    raise RealDebridError(
        "Torrent still processing on Real-Debrid — try again later"
    )


def ensure_torrent_ready(client, config, torrent_info):
    torrent_id = torrent_info["id"]
    info = wait_for_torrent(
        client,
        torrent_id,
        config["torrentPollIntervalSec"],
        config["torrentMaxWaitSec"],
    )

    if info.get("status") == "waiting_files_selection":
        files = "all" if config["selectAllTorrentFiles"] else "all"
        client.select_torrent_files(torrent_id, files)
        info = wait_for_torrent(
            client,
            torrent_id,
            config["torrentPollIntervalSec"],
            config["torrentMaxWaitSec"],
        )

    links = info.get("links") or []
    if not links:
        raise RealDebridError("Torrent finished but Real-Debrid returned no links")

    return info


def unrestrict_all(client, config, links):
    remote = config["useRemoteTraffic"]
    unrestricted = []

    for link in links:
        result = client.unrestrict_link(link, remote=remote)
        download_url = result.get("download")
        if not download_url:
            raise RealDebridError("Real-Debrid did not return a download link")
        unrestricted.append(result)

    return unrestricted


def handle_hoster(client, config, url):
    cached = get_cached(url)
    if cached:
        return cached

    result = client.unrestrict_link(url, remote=config["useRemoteTraffic"])
    download_url = result.get("download")
    if not download_url:
        raise RealDebridError("Real-Debrid did not return a download link")

    fdm_result = single_media(
        title=result.get("filename") or url,
        webpage_url=download_url,
        download_url=download_url,
        filename=result.get("filename") or "download",
        media_id=result.get("id"),
    )
    set_cached(url, fdm_result)
    set_cached(download_url, fdm_result)
    return fdm_result


def handle_container(client, url):
    response = client.unrestrict_container_link(url)
    links = normalize_container_links(response)
    return container_playlist(url, links)


def handle_torrent(client, config, url, cookies=""):
    cached = get_cached(url)
    if cached:
        return cached

    if is_magnet(url):
        added = client.add_magnet(url)
    else:
        torrent_bytes = client.download_bytes(url, cookies)
        added = client.add_torrent_file(torrent_bytes)

    info = ensure_torrent_ready(client, config, added)
    unrestricted = unrestrict_all(client, config, info.get("links") or [])

    if config["deleteTorrentAfter"]:
        try:
            client.delete_torrent(info["id"])
        except RealDebridError:
            pass

    result = torrent_playlist(
        webpage_url=url,
        unrestricted_items=unrestricted,
        title=info.get("filename") or info.get("original_filename") or "Real-Debrid torrent",
    )
    set_cached(url, result)
    return result


def parse_url(url, mode="auto", cookies=""):
    if is_rd_direct_url(url):
        return direct_download_result(url)

    config = load_config()
    client = RealDebridClient(config["apiToken"])
    client.get_user()

    if mode == "folder" or (mode == "auto" and looks_like_folder_url(url)):
        try:
            items = client.unrestrict_folder(url)
            if items:
                return folder_playlist(url, items)
        except RealDebridError as error:
            if mode == "folder":
                raise
            if error.status_code not in (400, 404):
                raise

    if is_magnet(url) or is_torrent_url(url):
        return handle_torrent(client, config, url, cookies)

    if is_container_url(url):
        return handle_container(client, url)

    return handle_hoster(client, config, url)


def main():
    if len(sys.argv) < 2:
        emit_error("Missing URL argument")

    url = sys.argv[1].strip()
    cookies = sys.argv[2].strip() if len(sys.argv) > 2 else ""

    if not url:
        emit_error("URL argument is empty")

    try:
        emit_result(parse_url(url, mode="auto", cookies=cookies))
    except RealDebridError as error:
        emit_error(str(error))
    except Exception as error:
        emit_error(str(error))


if __name__ == "__main__":
    main()
