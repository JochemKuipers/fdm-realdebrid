#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
dist="$root/dist"
fda="$dist/fdm-realdebrid.fda"
staging="$dist/staging"

items=(
    manifest.json
    icon.png
    rd-domains.js
    msparser.js
    msbatchparser.js
    config.example.json
    python
)

mkdir -p "$dist"

echo "Refreshing Real-Debrid host domains..."
python "$root/scripts/update-rd-domains.py"

rm -rf "$staging"
mkdir -p "$staging"

for item in "${items[@]}"; do
    source="$root/$item"
    if [[ ! -e "$source" ]]; then
        echo "Missing required file or directory: $item" >&2
        exit 1
    fi
    cp -r "$source" "$staging/$item"
done

python "$root/python/config_loader.py" "$staging/config.json"

rm -f "$fda"
(
    cd "$staging"
    zip -rq "$dist/fdm-realdebrid.zip" .
)
mv "$dist/fdm-realdebrid.zip" "$fda"
rm -rf "$staging"

echo "Built $fda"
