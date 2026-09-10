import json
import os
import ssl
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
API_URL = "https://api.real-debrid.com/rest/1.0/hosts/domains"

# Python 3.13+ VERIFY_X509_STRICT rejects RD certs missing Authority Key Identifier.
_SSL = ssl.create_default_context()
_SSL.verify_flags &= ~ssl.VERIFY_X509_STRICT


def main():
    with urllib.request.urlopen(API_URL, timeout=60, context=_SSL) as response:
        domains = json.loads(response.read().decode("utf-8"))

    if not isinstance(domains, list):
        raise RuntimeError("Unexpected Real-Debrid hosts response")

    json_path = os.path.join(ROOT, "rd-domains.json")
    js_path = os.path.join(ROOT, "rd-domains.js")

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(domains, handle, indent=2)

    with open(js_path, "w", encoding="utf-8") as handle:
        handle.write("var RD_EMBEDDED_DOMAINS = ")
        json.dump(domains, handle, separators=(",", ":"))
        handle.write(";\n")

    print(f"Updated {len(domains)} domains")


if __name__ == "__main__":
    main()
