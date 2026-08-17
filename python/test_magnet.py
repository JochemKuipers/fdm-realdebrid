import json
import os
import tempfile

from config_loader import DEFAULT_CONFIG, sync_config_file
from fdm_result import named_download_url, safe_filename
from magnet_job import (
    add_or_reuse,
    magnet_hash,
    normalize_magnet,
    save_store,
    start_torrent_job,
    try_instant,
)
from rd_client import RealDebridError

HEX = "a" * 40
BASE32 = "MFRGGZDFMZTWQ2LK"  # 16 chars — need 32
# 20 zero bytes → base32
ZERO_HEX = "00" * 20


class FakeClient:
    def __init__(self, info, torrents=None, add_error=None, instant_error=None):
        self.info = info
        self.torrents = torrents or []
        self.add_error = add_error
        self.instant_error = instant_error
        self.add_calls = 0
        self.unrestrict_calls = 0

    def add_magnet(self, magnet):
        self.add_calls += 1
        if self.add_error:
            raise self.add_error
        return {"id": self.info["id"]}

    def list_torrents(self):
        return self.torrents

    def get_torrent_info(self, torrent_id):
        return dict(self.info)

    def instant_availability(self, torrent_hash):
        if self.instant_error:
            raise self.instant_error
        return {}

    def unrestrict_link(self, link, remote=0):
        self.unrestrict_calls += 1
        return {"download": "https://cdn.example/file.bin", "filename": "file.bin"}

    def delete_torrent(self, torrent_id):
        return None


def test_hash():
    assert magnet_hash("magnet:?xt=urn:btih:" + HEX) == HEX
    assert magnet_hash("magnet:?xt=urn:btih:" + HEX.upper() + "&dn=Name&tr=udp://x") == HEX
    zero32 = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    assert magnet_hash("magnet:?xt=urn:btih:" + zero32) == ZERO_HEX
    assert normalize_magnet("magnet:?xt=urn:btih:" + HEX + "&tr=1") == (
        "magnet:?xt=urn:btih:" + HEX
    )
    try:
        magnet_hash("magnet:?xt=urn:btmh:1220abcd")
        raise AssertionError("btmh-only should fail")
    except ValueError:
        pass
    try:
        magnet_hash("magnet:?dn=nohash")
        raise AssertionError("garbage should fail")
    except ValueError:
        pass


def test_error_33_reuses_and_fast_path():
    info = {
        "id": "T1",
        "status": "downloaded",
        "hash": HEX,
        "filename": "movie.mkv",
        "links": ["https://real-debrid.com/d/x"],
        "files": [{"id": 1, "path": "/movie.mkv", "bytes": 10}],
    }
    client = FakeClient(
        info,
        torrents=[{"id": "T1", "hash": HEX}],
        add_error=RealDebridError("Torrent already active", 400, 33),
        instant_error=RealDebridError("disabled", 404, 37),
    )
    reused = add_or_reuse(client, "magnet:?xt=urn:btih:" + HEX, HEX)
    assert reused["id"] == "T1"
    assert client.add_calls == 1

    result = start_torrent_job(
        client,
        {"useRemoteTraffic": 0, "deleteTorrentAfter": False},
        "magnet:?xt=urn:btih:" + HEX + "&dn=x",
        spawn=False,
    )
    assert result is not None
    assert result["formats"][0]["url"] == "https://cdn.example/file.bin"
    assert client.unrestrict_calls == 1


def test_enqueue_does_not_block():
    info = {
        "id": "T2",
        "status": "magnet_conversion",
        "hash": HEX,
        "filename": "pending",
        "links": [],
        "files": [],
        "progress": 0,
    }
    client = FakeClient(info, instant_error=RealDebridError("disabled", 404, 37))
    result = start_torrent_job(
        client,
        {"useRemoteTraffic": 0, "deleteTorrentAfter": False},
        "magnet:?xt=urn:btih:" + HEX,
        spawn=False,
    )
    assert result is None
    assert client.add_calls == 1


def test_instant_miss_still_adds():
    client = FakeClient(
        {
            "id": "T3",
            "status": "queued",
            "hash": HEX,
            "links": [],
            "files": [],
        },
        instant_error=RealDebridError("disabled", 404, 37),
    )
    assert try_instant(client, HEX) == set()
    result = start_torrent_job(
        client,
        {"useRemoteTraffic": 0, "deleteTorrentAfter": False},
        "magnet:?xt=urn:btih:" + HEX,
        spawn=False,
    )
    assert result is None
    assert client.add_calls == 1


def test_sync_config_keeps_token():
    handle, path = tempfile.mkstemp(suffix=".json")
    os.close(handle)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"apiToken": "keep-me"}, handle)
        merged = sync_config_file(path)
        assert merged["apiToken"] == "keep-me"
        for key in DEFAULT_CONFIG:
            assert key in merged
        with open(path, encoding="utf-8") as handle:
            saved = json.load(handle)
        assert saved["apiToken"] == "keep-me"
        assert os.path.isfile(path)
    finally:
        os.remove(path)


def test_save_store_strips_files():
    save_store(
        {
            "jobs": [
                {
                    "id": "fat",
                    "status": "downloading",
                    "files": [{"id": "1", "path": "/a"}] * 10,
                }
            ]
        }
    )
    with open(os.environ["FDM_RD_JOBS"], encoding="utf-8") as handle:
        stored = json.load(handle)
    assert stored["jobs"][0]["files"] == []
    assert stored["jobs"][0]["fileCount"] == 10


def test_named_download_url():
    url = (
        "https://x.download.real-debrid.com/d/ABC/"
        "Pokemon%20-%20Emerald%20Version%20%28USA%2C%20Europe%29.zip"
    )
    name = "Pokemon - Emerald Version (USA, Europe).zip"
    out = named_download_url(url, name)
    assert out.endswith("/" + name)
    assert "%20" not in out
    assert out.count(".zip") == 1
    assert safe_filename("Pokemon%20-%20Emerald%20Version%20%28USA%2C%20Europe%29.zip") == name
    encoded_only = named_download_url(url, "")
    assert encoded_only.endswith("/" + name)


if __name__ == "__main__":
    handle, path = tempfile.mkstemp(suffix=".json")
    os.close(handle)
    os.environ["FDM_RD_JOBS"] = path
    try:
        test_hash()
        test_error_33_reuses_and_fast_path()
        test_enqueue_does_not_block()
        test_instant_miss_still_adds()
        test_sync_config_keeps_token()
        test_save_store_strips_files()
        test_named_download_url()
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    print("ok")
