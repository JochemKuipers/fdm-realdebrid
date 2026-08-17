import json
import os
import sys

ADDON_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_PATH = os.path.join(ADDON_ROOT, "config.json")
EXAMPLE_CONFIG_PATH = os.path.join(ADDON_ROOT, "config.example.json")

DEFAULT_CONFIG = {
    "apiToken": "",
    "useRemoteTraffic": False,
    "deleteTorrentAfter": False,
    "torrentPollIntervalSec": 5,
    "torrentMaxWaitSec": 900,
}


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def sync_config_file(path):
    """Add missing keys in place. Never deletes the file or the token."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(path + " must be a JSON object")
    merged = dict(DEFAULT_CONFIG)
    merged.update(data)
    if any(key not in data for key in DEFAULT_CONFIG):
        _write_json(path, merged)
    return merged


def export_existing_config(dest):
    from platform_paths import fdm_addon_candidates

    exported = None
    for root in fdm_addon_candidates(ADDON_ROOT):
        path = os.path.join(root, "config.json")
        if os.path.isfile(path):
            merged = sync_config_file(path)
            if exported is None:
                exported = merged
    if exported is None:
        return False
    _write_json(dest, exported)
    return True


def load_config():
    if os.path.isfile(CONFIG_PATH):
        data = sync_config_file(CONFIG_PATH)
    elif os.path.isfile(EXAMPLE_CONFIG_PATH):
        with open(EXAMPLE_CONFIG_PATH, encoding="utf-8") as handle:
            data = json.load(handle)
        data = dict(DEFAULT_CONFIG, **data)
    else:
        raise RuntimeError(
            "Missing config.json. Create "
            + CONFIG_PATH
            + " with your Real-Debrid API token."
        )

    config = dict(data)

    token = (config.get("apiToken") or "").strip()
    if not token or token == "PASTE_YOUR_TOKEN_HERE":
        raise RuntimeError(
            "Real-Debrid API token is missing. Edit "
            + CONFIG_PATH
            + " and set apiToken from https://real-debrid.com/apitoken"
        )

    config["apiToken"] = token
    config["useRemoteTraffic"] = 1 if config.get("useRemoteTraffic") else 0
    config["deleteTorrentAfter"] = bool(config.get("deleteTorrentAfter", False))
    config["torrentPollIntervalSec"] = max(1, int(config.get("torrentPollIntervalSec", 5)))
    config["torrentMaxWaitSec"] = max(30, int(config.get("torrentMaxWaitSec", 900)))
    return config


def public_config():
    result = {
        "tokenSet": False,
        "useRemoteTraffic": False,
        "deleteTorrentAfter": False,
        "torrentPollIntervalSec": DEFAULT_CONFIG["torrentPollIntervalSec"],
        "torrentMaxWaitSec": DEFAULT_CONFIG["torrentMaxWaitSec"],
        "error": "",
    }
    try:
        config = load_config()
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        result["error"] = str(error)
        return result

    result["tokenSet"] = True
    result["useRemoteTraffic"] = bool(config["useRemoteTraffic"])
    result["deleteTorrentAfter"] = config["deleteTorrentAfter"]
    result["torrentPollIntervalSec"] = config["torrentPollIntervalSec"]
    result["torrentMaxWaitSec"] = config["torrentMaxWaitSec"]
    return result


if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else None
    if not dest:
        raise SystemExit("usage: config_loader.py <dest-config.json>")
    if export_existing_config(dest):
        print("Kept existing config.json (token preserved, missing keys filled)")
    else:
        print("No existing config.json — copy config.example.json after install")
