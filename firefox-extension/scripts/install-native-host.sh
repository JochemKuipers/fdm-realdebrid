#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
repo_root="$(cd "$root/.." && pwd)"
native_host_dir="$root/native-host"
install_dir="${XDG_DATA_HOME:-$HOME/.local/share}/fdm-realdebrid/native-host"
manifest_dir="${XDG_CONFIG_HOME:-$HOME/.config}/mozilla/native-messaging-hosts"
manifest_path="$manifest_dir/com.fdmrealdebrid.magnet.json"
launcher="$install_dir/fdm_rd_magnet.sh"

if [[ ! -f "$native_host_dir/fdm_rd_magnet.py" ]]; then
    echo "Missing native host script: $native_host_dir/fdm_rd_magnet.py" >&2
    exit 1
fi

mkdir -p "$install_dir" "$manifest_dir"

cp "$native_host_dir/fdm_rd_magnet.py" "$install_dir/"
cp "$native_host_dir/fdm_rd_magnet_worker.py" "$install_dir/"
cp "$native_host_dir/fdm_rd_magnet.sh" "$install_dir/"
cp "$repo_root/python/platform_paths.py" "$install_dir/"
chmod +x "$install_dir/fdm_rd_magnet.sh"

cat >"$manifest_path" <<EOF
{
  "name": "com.fdmrealdebrid.magnet",
  "description": "Send magnet links to Free Download Manager for Real-Debrid",
  "path": "$launcher",
  "type": "stdio",
  "allowed_extensions": ["fdm-realdebrid-magnets@jochem.local"]
}
EOF

echo "Installed native host manifest:"
echo "  $manifest_path"
echo "Host launcher:"
echo "  $launcher"
echo ""
echo "Restart Firefox completely, then click a magnet link."
