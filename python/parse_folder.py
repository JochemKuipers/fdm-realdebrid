import sys

from parse import emit_error, emit_result, parse_url
from rd_client import RealDebridError


def main():
    if len(sys.argv) < 2:
        emit_error("Missing URL argument")

    url = sys.argv[1].strip()
    if not url:
        emit_error("URL argument is empty")

    try:
        emit_result(parse_url(url, mode="folder"))
    except RealDebridError as error:
        emit_error(str(error))
    except Exception as error:
        emit_error(str(error))


if __name__ == "__main__":
    main()
