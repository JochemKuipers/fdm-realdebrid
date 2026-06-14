import json
import os
import time

DEFAULT_TTL_SEC = 4 * 60 * 60


def _cache_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "fdm-realdebrid")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


def _cache_path():
    return os.path.join(_cache_dir(), "parse-cache.json")


def _load_cache():
    path = _cache_path()
    if not os.path.isfile(path):
        return {}

    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(data):
    path = _cache_path()
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
    except OSError:
        pass


def _purge_expired(cache, ttl_sec):
    now = time.time()
    expired_keys = [
        key
        for key, entry in cache.items()
        if not isinstance(entry, dict) or (now - entry.get("savedAt", 0)) > ttl_sec
    ]
    for key in expired_keys:
        cache.pop(key, None)


def get_cached(url, ttl_sec=DEFAULT_TTL_SEC):
    try:
        cache = _load_cache()
        entry = cache.get(url)
        if not isinstance(entry, dict):
            return None

        if (time.time() - entry.get("savedAt", 0)) > ttl_sec:
            cache.pop(url, None)
            _save_cache(cache)
            return None

        result = entry.get("result")
        return result if isinstance(result, dict) else None
    except OSError:
        return None


def set_cached(url, result, ttl_sec=DEFAULT_TTL_SEC):
    try:
        cache = _load_cache()
        _purge_expired(cache, ttl_sec)
        cache[url] = {
            "savedAt": time.time(),
            "result": result,
        }
        _save_cache(cache)
    except OSError:
        pass
