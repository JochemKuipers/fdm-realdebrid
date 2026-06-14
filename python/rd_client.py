import json
import uuid
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.real-debrid.com/rest/1.0"


class RealDebridError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def map_http_error(status_code, message):
    text = str(message or "").strip()
    if status_code == 401:
        return "Invalid Real-Debrid API token — edit config.json"
    if status_code == 403:
        return "Real-Debrid account locked or not premium"
    if status_code == 503:
        return "Host unavailable on Real-Debrid right now"
    if text:
        return text
    return f"Real-Debrid API error ({status_code})"


class RealDebridClient:
    def __init__(self, api_token):
        self.api_token = api_token

    def _request(
        self,
        method,
        path,
        data=None,
        headers=None,
        raw_body=None,
        auth=True,
        expect_json=True,
    ):
        url = API_BASE + path
        req_headers = {}
        if auth:
            req_headers["Authorization"] = f"Bearer {self.api_token}"

        if headers:
            req_headers.update(headers)

        body = None
        if raw_body is not None:
            body = raw_body
        elif data is not None:
            body = urllib.parse.urlencode(data).encode("utf-8")
            req_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

        request = urllib.request.Request(url, data=body, headers=req_headers, method=method)

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                content = response.read()
                if not expect_json or not content:
                    return None
                return json.loads(content.decode("utf-8"))
        except urllib.error.HTTPError as error:
            payload = error.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(payload)
                message = parsed.get("error", payload)
            except json.JSONDecodeError:
                message = payload or error.reason
            raise RealDebridError(map_http_error(error.code, message), error.code) from error
        except urllib.error.URLError as error:
            raise RealDebridError(f"Network error contacting Real-Debrid: {error.reason}") from error

    def get_user(self):
        return self._request("GET", "/user")

    def unrestrict_check(self, link, password=None):
        data = {"link": link}
        if password:
            data["password"] = password
        return self._request("POST", "/unrestrict/check", data=data, auth=False)

    def unrestrict_link(self, link, remote=0, password=None):
        data = {"link": link, "remote": str(remote)}
        if password:
            data["password"] = password
        return self._request("POST", "/unrestrict/link", data=data)

    def unrestrict_folder(self, link):
        return self._request("POST", "/unrestrict/folder", data={"link": link})

    def unrestrict_container_link(self, link):
        return self._request("POST", "/unrestrict/containerLink", data={"link": link})

    def add_magnet(self, magnet, host=None):
        data = {"magnet": magnet}
        if host:
            data["host"] = host
        return self._request("POST", "/torrents/addMagnet", data=data)

    def add_torrent_file(self, torrent_bytes, host=None):
        boundary = f"----FdMRdBoundary{uuid.uuid4().hex}"
        parts = []

        if host:
            parts.append(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="host"\r\n\r\n'
                f"{host}\r\n"
            )

        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="file.torrent"\r\n'
            f"Content-Type: application/x-bittorrent\r\n\r\n"
        )
        body = (
            "".join(parts).encode("utf-8")
            + torrent_bytes
            + f"\r\n--{boundary}--\r\n".encode("utf-8")
        )
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        return self._request(
            "PUT",
            "/torrents/addTorrent",
            raw_body=body,
            headers=headers,
        )

    def get_torrent_info(self, torrent_id):
        return self._request("GET", f"/torrents/info/{torrent_id}")

    def select_torrent_files(self, torrent_id, files="all"):
        return self._request(
            "POST",
            f"/torrents/selectFiles/{torrent_id}",
            data={"files": files},
            expect_json=False,
        )

    def delete_torrent(self, torrent_id):
        return self._request(
            "DELETE",
            f"/torrents/delete/{torrent_id}",
            expect_json=False,
        )

    @staticmethod
    def download_bytes(url, cookies=""):
        headers = {"User-Agent": "fdm-realdebrid/1.0"}
        if cookies:
            headers["Cookie"] = cookies.replace("\n", "; ")
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            payload = error.read().decode("utf-8", errors="replace")
            raise RealDebridError(
                payload or f"Failed to download torrent file ({error.code})",
                error.code,
            ) from error
        except urllib.error.URLError as error:
            raise RealDebridError(f"Failed to download torrent file: {error.reason}") from error
