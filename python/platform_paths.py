import os
import shutil
import sys


def _expand(path):
    return os.path.expanduser(os.path.expandvars(path))


def app_data_dir():
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share"
        )
    return os.path.join(base, "fdm-realdebrid")


def fdm_candidates():
    if sys.platform == "win32":
        return [
            _expand(r"C:\Program Files\Softdeluxe\Free Download Manager\fdm.exe"),
            _expand(
                r"%LOCALAPPDATA%\Programs\Softdeluxe\Free Download Manager\fdm.exe"
            ),
        ]

    candidates = []
    fdm_on_path = shutil.which("fdm")
    if fdm_on_path:
        candidates.append(fdm_on_path)
    candidates.extend(
        [
            "/opt/freedownloadmanager/fdm",
            _expand("~/.local/opt/freedownloadmanager/fdm"),
        ]
    )
    return candidates


def fdm_addon_candidates(repo_root=None):
    if repo_root is None:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        installed = os.path.join(
            base,
            "Softdeluxe",
            "Free Download Manager",
            "plugins",
            "fdm-realdebrid",
        )
    else:
        share = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share"
        )
        installed = os.path.join(
            share,
            "Softdeluxe",
            "Free Download Manager",
            "plugins",
            "fdm-realdebrid",
        )

    return [installed, repo_root]


def find_fdm():
    for path in fdm_candidates():
        if os.path.isfile(path):
            return path
    return None


def find_addon_root(repo_root=None):
    for path in fdm_addon_candidates(repo_root):
        parse_py = os.path.join(path, "python", "parse.py")
        if os.path.isfile(parse_py):
            return path
    return None


def detached_popen_kwargs():
    if sys.platform == "win32":
        return {
            "creationflags": 0x08000000 | 0x00000008,  # CREATE_NO_WINDOW | DETACHED
        }
    return {"start_new_session": True}
