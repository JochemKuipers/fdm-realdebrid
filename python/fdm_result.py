import os

VIDEO_EXTENSIONS = {
    "mp4",
    "mkv",
    "avi",
    "mov",
    "webm",
    "flv",
    "wmv",
    "m4v",
    "mpg",
    "mpeg",
    "3gp",
}

AUDIO_EXTENSIONS = {
    "mp3",
    "flac",
    "wav",
    "m4a",
    "aac",
    "ogg",
    "opus",
    "wma",
}


def extension_from_filename(filename):
    _, ext = os.path.splitext(filename or "")
    return ext.lstrip(".").lower() or "bin"


def build_format(download_url, filename, filesize=0):
    ext = extension_from_filename(filename)
    protocol = "https" if download_url.startswith("https://") else "http"
    fmt = {
        "url": download_url,
        "ext": ext,
        "protocol": protocol,
    }

    if filesize and int(filesize) > 0:
        fmt["filesize"] = int(filesize)

    if ext in VIDEO_EXTENSIONS:
        fmt["video_ext"] = ext
        fmt["vcodec"] = "unknown"
    elif ext in AUDIO_EXTENSIONS:
        fmt["audio_ext"] = ext
        fmt["acodec"] = "unknown"

    return fmt


def single_media(title, webpage_url, download_url, filename, filesize=0, media_id=None):
    result = {
        "title": title or filename or "Download",
        "webpage_url": webpage_url,
        "formats": [build_format(download_url, filename, 0)],
    }
    if media_id:
        result["id"] = str(media_id)
    return result


def playlist(title, webpage_url, entries):
    return {
        "_type": "playlist",
        "title": title or "Real-Debrid folder",
        "webpage_url": webpage_url,
        "entries": entries,
    }


def playlist_entry(url, title):
    return {
        "_type": "url",
        "url": url,
        "title": title or url,
    }


def folder_playlist(webpage_url, items, title=None):
    entries = []
    for item in items:
        link = item.get("link") or item.get("url")
        if not link:
            continue
        filename = item.get("filename") or item.get("path") or link
        entries.append(playlist_entry(link, filename))

    if not entries:
        raise ValueError("No links found in folder")

    return playlist(title or "Real-Debrid folder", webpage_url, entries)


def container_playlist(webpage_url, links, title=None):
    entries = []
    for link in links:
        if isinstance(link, dict):
            url = link.get("link") or link.get("url")
            name = link.get("filename") or url
        else:
            url = link
            name = link
        if url:
            entries.append(playlist_entry(url, name))

    if not entries:
        raise ValueError("No links found in container file")

    return playlist(title or "Real-Debrid container", webpage_url, entries)


def torrent_playlist(webpage_url, unrestricted_items, title):
    if len(unrestricted_items) == 1:
        item = unrestricted_items[0]
        return single_media(
            title=title or item.get("filename") or "Download",
            webpage_url=webpage_url,
            download_url=item["download"],
            filename=item.get("filename") or "download",
            filesize=item.get("filesize", 0),
        )

    entries = []
    for item in unrestricted_items:
        entries.append(
            playlist_entry(
                item["download"],
                item.get("filename") or item["download"],
            )
        )

    return playlist(title or "Real-Debrid torrent", webpage_url, entries)
