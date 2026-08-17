# Real-Debrid Magnets for FDM (Firefox)

Companion Firefox extension that captures **magnet links**, shows configuration and live Real-Debrid progress in the toolbar popup, and sends finished HTTPS downloads to Free Download Manager.

## How it works

```text
Click magnet link in Firefox  (or paste a magnet in FDM)
  -> job is written to jobs.json
  -> worker talks to Real-Debrid (instant check, add or reuse, poll)
  -> popup: pick files, watch progress
  -> unrestricted HTTPS links are sent to FDM with fdm -fs
  -> FDM downloads via Real-Debrid (not the built-in torrent client)
```

Magnet URLs cannot go straight to `fdm` because FDM routes those to its built-in BitTorrent handler.

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

- Open the **toolbar popup** — that is the UI. It shows what is configured (native host, FDM, add-on, token set, poll/wait) and every waybill in flight.
- **Click any magnet link** on a web page — it is queued instead of opening your default torrent client
- **Right-click a magnet link** → **Send magnet to FDM (Real-Debrid)**
- Turn **Capture** off in the popup if magnet links should use the browser default
- When a waybill says **pick files**, check the cargo lines and click **Send to FDM**. Cached files are stamped. If you pick nothing for 60 seconds, all files are selected.

The toolbar badge is the live count (`N`) or `!` when a file pick is waiting.

## Troubleshooting

| Problem                                               | Fix                                                                                                    |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Popup says native host missing                        | Re-run the install script, then **fully restart Firefox**                                              |
| "Could not find fdm"                                  | Install FDM or edit `fdm_candidates` in `python/platform_paths.py`                                     |
| FDM uses built-in torrent instead of Real-Debrid      | Re-run the install script so the updated native host is installed                                      |
| Token / add-on rows are red                           | Install the FDM add-on and set `apiToken` in its `config.json`                                         |
| Extension disappears after restart                    | Temporary add-ons unload on restart — reload via `about:debugging`                                     |

## Files

- `popup.html` / `popup.css` / `popup.js` — toolbar dock (config + waybills)
- `manifest.json` — Firefox extension manifest
- `content.js` — intercepts magnet link clicks
- `background.js` — enqueue + badge
- `native-host/fdm_rd_magnet.py` — native messaging router (`enqueue`, `status`, `selectFiles`)
- `scripts/install-native-host.sh` — registers the native host with Firefox (Linux / macOS)
- `scripts/install-native-host.ps1` — registers the native host with Firefox (Windows)
