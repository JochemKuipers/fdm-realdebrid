import json
import os
import subprocess
import sys
from datetime import datetime

host_dir = os.path.dirname(os.path.abspath(__file__))
repo_python = os.path.abspath(os.path.join(host_dir, "..", "..", "python"))
for path in (host_dir, repo_python):
    if path not in sys.path:
        sys.path.insert(0, path)

from platform_paths import app_data_dir, find_addon_root, find_fdm

LOG_PATH = os.path.join(app_data_dir(), "native-host", "magnet-worker.log")


def log(message):
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(f"[{stamp}] {message}\n")
    except OSError:
        pass


def collect_download_urls(result):
    urls = []
    if result.get("_type") == "playlist":
        for entry in result.get("entries", []):
            url = entry.get("url")
            if url:
                urls.append(url)
    else:
        for fmt in result.get("formats", []):
            url = fmt.get("url")
            if url:
                urls.append(url)
    return urls


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


def process_magnet(magnet_url):
    repo_root = os.path.abspath(os.path.join(host_dir, "..", ".."))
    addon_root = find_addon_root(repo_root)
    if not addon_root:
        raise RuntimeError(
            "Real-Debrid FDM add-on not found. Install fdm-realdebrid in FDM first."
        )

    parse_py = os.path.join(addon_root, "python", "parse.py")
    completed = subprocess.run(
        [sys.executable, parse_py, magnet_url],
        capture_output=True,
        text=True,
        cwd=addon_root,
    )

    if completed.returncode != 0:
        error = (completed.stdout or completed.stderr or "Real-Debrid parser failed").strip()
        raise RuntimeError(error)

    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid parser output: {error}") from error

    urls = collect_download_urls(result)
    if not urls:
        raise RuntimeError("Real-Debrid returned no download URLs")

    send_to_fdm(urls)
    log(f"Added {len(urls)} download(s) to FDM for magnet")


def main():
    if len(sys.argv) < 2:
        log("Worker started without magnet URL")
        return 1

    magnet_url = sys.argv[1].strip()
    if not magnet_url.lower().startswith("magnet:"):
        log(f"Rejected non-magnet URL: {magnet_url}")
        return 1

    try:
        process_magnet(magnet_url)
        return 0
    except Exception as error:
        log(str(error))
        return 1


if __name__ == "__main__":
    sys.exit(main())
