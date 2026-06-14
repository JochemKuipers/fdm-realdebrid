import json
import os

ADDON_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_PATH = os.path.join(ADDON_ROOT, "config.json")
EXAMPLE_CONFIG_PATH = os.path.join(ADDON_ROOT, "config.example.json")

DEFAULT_CONFIG = {
    "apiToken": "",
    "useRemoteTraffic": False,
    "selectAllTorrentFiles": True,
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
    config["selectAllTorrentFiles"] = bool(config.get("selectAllTorrentFiles", True))
    config["deleteTorrentAfter"] = bool(config.get("deleteTorrentAfter", False))
    config["torrentPollIntervalSec"] = max(1, int(config.get("torrentPollIntervalSec", 5)))
    config["torrentMaxWaitSec"] = max(30, int(config.get("torrentMaxWaitSec", 900)))
    return config
