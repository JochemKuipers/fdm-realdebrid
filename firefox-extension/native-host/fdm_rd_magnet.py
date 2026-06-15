import json
import os
import struct
import subprocess
import sys

host_dir = os.path.dirname(os.path.abspath(__file__))
repo_python = os.path.abspath(os.path.join(host_dir, "..", "..", "python"))
for path in (host_dir, repo_python):
    if path not in sys.path:
        sys.path.insert(0, path)

from platform_paths import detached_popen_kwargs, find_fdm


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


def extract_url(message):
    if isinstance(message, str):
        return message.strip()
    if isinstance(message, dict):
        for key in ("url", "magnet", "link"):
            value = message.get(key)
            if value:
                return str(value).strip()
    return ""


def spawn_worker(magnet_url):
    host_dir = os.path.dirname(os.path.abspath(__file__))
    worker_py = os.path.join(host_dir, "fdm_rd_magnet_worker.py")
    if not os.path.isfile(worker_py):
        raise FileNotFoundError(f"Missing worker script: {worker_py}")

    subprocess.Popen(
        [sys.executable, worker_py, magnet_url],
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **detached_popen_kwargs(),
    )


def main():
    try:
        message = read_message()
        url = extract_url(message)
    except Exception as error:
        send_message({"success": False, "error": str(error)})
        return

    if not url.lower().startswith("magnet:"):
        send_message({"success": False, "error": "Not a magnet link"})
        return

    if not find_fdm():
        send_message({"success": False, "error": "Could not find fdm"})
        return

    try:
        spawn_worker(url)
        send_message(
            {
                "success": True,
                "queued": True,
                "message": "Real-Debrid is processing the magnet. FDM will receive downloads when ready.",
            }
        )
    except Exception as error:
        send_message({"success": False, "error": str(error)})


if __name__ == "__main__":
    main()
