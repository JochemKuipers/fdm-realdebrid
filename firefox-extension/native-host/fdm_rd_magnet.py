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
    from magnet_job import enqueue_url, set_selection, status_payload

    return enqueue_url, set_selection, status_payload


def handle(message):
    if not isinstance(message, dict):
        message = {"url": str(message)}

    cmd = (message.get("cmd") or "").strip()
    if not cmd and message.get("url"):
        cmd = "enqueue"

    try:
        enqueue_url, set_selection, status_payload = import_jobs()
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
        return status_payload()

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
