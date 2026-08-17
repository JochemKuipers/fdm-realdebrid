import json
import os

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


def load_config():
    path = CONFIG_PATH if os.path.isfile(CONFIG_PATH) else EXAMPLE_CONFIG_PATH
    if not os.path.isfile(path):
        raise RuntimeError(
            "Missing config.json. Create "
            + CONFIG_PATH
            + " with your Real-Debrid API token."
        )

    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)

    config = dict(DEFAULT_CONFIG)
    config.update(data)

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
