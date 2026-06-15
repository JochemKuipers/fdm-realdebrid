# Real-Debrid Magnets for FDM (Firefox)

Companion Firefox extension that captures **magnet links** and sends them to Free Download Manager. FDM then hands the magnet to the **fdm-realdebrid** add-on for Real-Debrid processing.

## How it works

```text
Click magnet link in Firefox
  -> extension sends magnet to native host
  -> native host runs the Real-Debrid FDM add-on parser in the background
  -> when RD is ready, direct HTTPS links are sent to FDM with fdm -fs
  -> FDM downloads via Real-Debrid (not the built-in torrent client)
```

Magnet URLs cannot go straight to `fdm` because FDM routes those to its built-in BitTorrent handler. The native host unrestricts through Real-Debrid first, then passes the resulting download URLs to FDM.

## Setup

### 1. Prerequisites

- Free Download Manager with the **fdm-realdebrid** add-on installed and configured
- Python 3 on PATH (same as the FDM add-on)
- Firefox

### 2. Install the native messaging host

Run once:

**Linux / macOS:**

```bash
./firefox-extension/scripts/install-native-host.sh
```

**Windows (PowerShell):**

```powershell
.\firefox-extension\scripts\install-native-host.ps1
```

This installs the launcher under `~/.local/share/fdm-realdebrid/native-host/` (Linux) or `%LOCALAPPDATA%\fdm-realdebrid\native-host\` (Windows) and registers it with Firefox.

On **Windows**, Firefox also requires a registry entry under `HKCU\Software\Mozilla\NativeMessagingHosts\` — the install script creates this automatically.

On **Linux / macOS**, the manifest is written to `~/.config/mozilla/native-messaging-hosts/`.

### 3. Load the Firefox extension

1. Open `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on…**
3. Select `firefox-extension/manifest.json`

For a permanent install you would need to sign and publish the extension, or use Firefox Enterprise policies.

### 4. Restart Firefox

Restart Firefox after installing the native host so it picks up the manifest.

## Usage

- **Click any magnet link** on a web page — it is sent to FDM instead of your default torrent client
- **Right-click a magnet link** → **Send magnet to FDM (Real-Debrid)**
- **Toolbar button** toggles capture on/off (if disabled, magnet links behave normally)

When FDM receives the magnet, wait while Real-Debrid processes the torrent (this can take several minutes).

## Troubleshooting

| Problem                                               | Fix                                                                                                    |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| "No such native application com.fdmrealdebrid.magnet" | Re-run the install script, then **fully restart Firefox**                                              |
| "Could not find fdm"                                  | Install FDM or edit `FDM_CANDIDATES` in `python/platform_paths.py`                                     |
| FDM uses built-in torrent instead of Real-Debrid      | Re-run the install script so the updated native host is installed                                      |
| Worker failed silently                                | Check `~/.local/share/fdm-realdebrid/native-host/magnet-worker.log` (Linux) or `%LOCALAPPDATA%\fdm-realdebrid\native-host\magnet-worker.log` (Windows) |
| Extension disappears after restart                    | Temporary add-ons unload on restart — reload via `about:debugging`                                     |

## Files

- `manifest.json` — Firefox extension manifest
- `content.js` — intercepts magnet link clicks
- `background.js` — sends magnets to the native host
- `native-host/fdm_rd_magnet.py` — native messaging entry point
- `native-host/fdm_rd_magnet_worker.py` — unrestricts magnets and sends URLs to FDM
- `scripts/install-native-host.sh` — registers the native host with Firefox (Linux / macOS)
- `scripts/install-native-host.ps1` — registers the native host with Firefox (Windows)
