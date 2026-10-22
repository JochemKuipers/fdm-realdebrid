# Real-Debrid Magnets for FDM (Chrome / Chromium / Vivaldi)

Companion Chromium extension that captures **magnet links**, shows configuration and live Real-Debrid progress in the toolbar popup, and sends finished HTTPS downloads to Free Download Manager.

Chrome and Vivaldi cannot register as the browser/OS `magnet:` protocol handler. Capture works via **in-page clicks** and the **context menu**. Magnets opened outside a page (OS handler / address bar) will not reach this extension — paste them into FDM instead, or use the Firefox companion.

## How it works

```text
Click magnet link in the browser  (or paste a magnet in FDM)
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
- Chrome, Chromium, or Vivaldi

### 2. Install the native messaging host

Run once:

**Linux / macOS:**

```bash
./chromium-extension/scripts/install-native-host.sh
```

**Windows (PowerShell):**

```powershell
.\chromium-extension\scripts\install-native-host.ps1
```

This installs the launcher under `~/.local/share/fdm-realdebrid/native-host/` (Linux) or `%LOCALAPPDATA%\fdm-realdebrid\native-host\` (Windows) and registers it for Chrome, Chromium, and Vivaldi.

On **Windows**, registry entries under `HKCU\Software\Google\Chrome\NativeMessagingHosts\` (and Chromium / Vivaldi) are created automatically.

On **Linux**, manifests are written under `~/.config/google-chrome/NativeMessagingHosts/`, `~/.config/chromium/NativeMessagingHosts/`, and `~/.config/vivaldi/NativeMessagingHosts/`. On **macOS**, under the matching `Library/Application Support/.../NativeMessagingHosts/` paths.

The native host allowlist uses a fixed extension ID (`ijimlcmjkddnimablogpkmgopalomlfn`) derived from the `key` in `manifest.json`, so unpacked loads keep a stable ID.

### 3. Load the unpacked extension

1. Open `chrome://extensions` (Chrome / Chromium) or `vivaldi://extensions` (Vivaldi)
2. Enable **Developer mode**
3. Click **Load unpacked**
4. Select the `chromium-extension/` folder

### 4. Restart the browser

Restart Chrome / Chromium / Vivaldi after installing the native host so it picks up the manifest.

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
| Popup says native host missing                        | Re-run the install script, then **fully restart** the browser                                          |
| "Could not find fdm"                                  | Install FDM or edit `fdm_candidates` in `python/platform_paths.py`                                     |
| FDM uses built-in torrent instead of Real-Debrid      | Re-run the install script so the updated native host is installed                                      |
| Token / add-on rows are red                           | Install the FDM add-on and set `apiToken` in its `config.json`                                         |
| Magnet from OS / address bar ignored                  | Expected on Chromium — click the link on a page, use the context menu, or paste into FDM               |
| Extension ID does not match native host               | Load this folder as unpacked (do not strip the `key` from `manifest.json`)                             |

## Files

- `popup.html` / `popup.css` / `popup.js` — toolbar dock (config + waybills)
- `manifest.json` — Chromium MV3 manifest (`service_worker`, stable `key`)
- `content.js` — intercepts magnet link clicks
- `background.js` — enqueue + badge (`chrome.alarms`)
- `native-host/fdm_rd_magnet.py` — native messaging router (`enqueue`, `status`, `selectFiles`)
- `scripts/install-native-host.sh` — registers the native host for Chrome / Chromium / Vivaldi (Linux / macOS)
- `scripts/install-native-host.ps1` — same for Windows
