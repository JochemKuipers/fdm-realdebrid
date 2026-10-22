#!/usr/bin/env bash
set -euo pipefail

# Stable extension ID from chromium-extension/manifest.json "key" field.
EXTENSION_ID="ijimlcmjkddnimablogpkmgopalomlfn"
ALLOWED_ORIGIN="chrome-extension://${EXTENSION_ID}/"

root="$(cd "$(dirname "$0")/.." && pwd)"
repo_root="$(cd "$root/.." && pwd)"
native_host_dir="$root/native-host"
install_dir="${XDG_DATA_HOME:-$HOME/.local/share}/fdm-realdebrid/native-host"
launcher="$install_dir/fdm_rd_magnet.sh"

if [[ "$(uname -s)" == "Darwin" ]]; then
  manifest_dirs=(
    "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
    "$HOME/Library/Application Support/Chromium/NativeMessagingHosts"
    "$HOME/Library/Application Support/Vivaldi/NativeMessagingHosts"
  )
else
  config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
  manifest_dirs=(
    "$config_home/google-chrome/NativeMessagingHosts"
    "$config_home/chromium/NativeMessagingHosts"
    "$config_home/vivaldi/NativeMessagingHosts"
  )
fi

if [[ ! -f "$native_host_dir/fdm_rd_magnet.py" ]]; then
  echo "Missing native host script: $native_host_dir/fdm_rd_magnet.py" >&2
  exit 1
fi

mkdir -p "$install_dir"

cp "$native_host_dir/fdm_rd_magnet.py" "$install_dir/"
cp "$native_host_dir/fdm_rd_magnet_worker.py" "$install_dir/"
cp "$native_host_dir/fdm_rd_magnet.sh" "$install_dir/"
cp "$repo_root/python/platform_paths.py" "$install_dir/"
chmod +x "$install_dir/fdm_rd_magnet.sh"

manifest_body=$(cat <<EOF
{
  "name": "com.fdmrealdebrid.magnet",
  "description": "Send magnet links to Free Download Manager for Real-Debrid",
  "path": "$launcher",
  "type": "stdio",
  "allowed_origins": ["$ALLOWED_ORIGIN"]
}
EOF
)

echo "Installed native host launcher:"
echo "  $launcher"
echo ""
echo "Registered Chromium native messaging manifests:"

for manifest_dir in "${manifest_dirs[@]}"; do
  mkdir -p "$manifest_dir"
  manifest_path="$manifest_dir/com.fdmrealdebrid.magnet.json"
  printf '%s\n' "$manifest_body" >"$manifest_path"
  echo "  $manifest_path"
done

echo ""
echo "Extension origin: $ALLOWED_ORIGIN"
echo "Restart Chrome / Chromium / Vivaldi completely, then load the unpacked extension."
