import os
import sys

host_dir = os.path.dirname(os.path.abspath(__file__))
repo_python = os.path.abspath(os.path.join(host_dir, "..", "..", "python"))
for path in (host_dir, repo_python):
    if path not in sys.path:
        sys.path.insert(0, path)

from platform_paths import find_addon_root


def main():
    if len(sys.argv) < 2:
        return 1

    addon_root = find_addon_root()
    if addon_root:
        addon_python = os.path.join(addon_root, "python")
        if addon_python not in sys.path:
            sys.path.insert(0, addon_python)

    from magnet_job import enqueue_url, run_job

    arg = sys.argv[1].strip()
    if arg.lower().startswith("magnet:") or arg.lower().startswith("http"):
        enqueue_url(arg)
        return 0
    run_job(arg)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(1)
