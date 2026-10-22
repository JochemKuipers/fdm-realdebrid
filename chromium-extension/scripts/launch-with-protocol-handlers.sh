#!/usr/bin/env bash
# Personal / unstable: Chromium 146+ extension protocol_handlers behind a flag.
# Without this flag the extension still works (click + context menu); magnet:
# protocol ownership stays inactive.
set -euo pipefail

FLAG="--enable-features=ExtensionProtocolHandlers"
EXTRA_ARGS=("$@")

pick_browser() {
  if [[ -n "${FDM_RD_BROWSER:-}" ]]; then
    command -v "$FDM_RD_BROWSER" >/dev/null 2>&1 || {
      echo "FDM_RD_BROWSER=$FDM_RD_BROWSER not found" >&2
      exit 1
    }
    echo "$FDM_RD_BROWSER"
    return
  fi
  local cand
  for cand in google-chrome-unstable google-chrome-beta google-chrome chromium-browser chromium vivaldi-stable vivaldi; do
    if command -v "$cand" >/dev/null 2>&1; then
      echo "$cand"
      return
    fi
  done
  echo "No Chrome / Chromium / Vivaldi binary found on PATH" >&2
  exit 1
}

browser="$(pick_browser)"
echo "Launching: $browser $FLAG ${EXTRA_ARGS[*]:-}"
exec "$browser" "$FLAG" "${EXTRA_ARGS[@]}"
