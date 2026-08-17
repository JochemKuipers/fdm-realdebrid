# FDM Real-Debrid Add-on

Free Download Manager add-on that uses [Real-Debrid](https://real-debrid.com/) to download from supported hosters, folders, magnets, torrent files, and container files (DLC/CCF).

## Requirements

- Free Download Manager 6.16 or newer
- Python 3 (FDM can install Python 3.8.10 when you install the add-on)
- Real-Debrid premium account
- API token from [real-debrid.com/apitoken](https://real-debrid.com/apitoken)

## Installation

1. Build the add-on package:

   **Linux / macOS:**

   ```bash
   ./scripts/build-fda.sh
   ```

   **Windows (PowerShell):**

   ```powershell
   .\scripts\build-fda.ps1
   ```

2. Install `dist/fdm-realdebrid.fda` in FDM:
   - Menu → Add-ons → Install add-on from file
   - Approve the **launchPython** permission

3. Configure the add-on:
   - Open the installed add-on folder (FDM add-ons directory)
   - Copy `config.example.json` to `config.json`
   - Set your `apiToken`

   Example:

   ```json
   {
     "apiToken": "YOUR_REAL_DEBRID_TOKEN",
     "useRemoteTraffic": false,
     "deleteTorrentAfter": false,
     "torrentPollIntervalSec": 5,
     "torrentMaxWaitSec": 900
   }
   ```

4. Restart FDM or reload add-ons if needed.

## Usage

Paste a URL into FDM's **Add Download** dialog:

| URL type     | Example                                                     |
| ------------ | ----------------------------------------------------------- |
| Hoster link  | `https://rapidgator.net/file/...`                           |
| Folder link  | Mega/Mediafire folder URLs                                  |
| Magnet       | `magnet:?xt=urn:btih:...` (paste into FDM **Add Download**) |
| Torrent file | `https://example.com/file.torrent`                          |
| Container    | `.dlc`, `.ccf`, `.ccfz`, `.rsdf` links                      |

The add-on unrestricts the link through Real-Debrid and returns a direct download URL for FDM.

**Magnet and torrent files:** FDM's add-download dialog returns immediately. Real-Debrid work continues in the background. Open the Firefox companion popup to pick files and watch progress. When Real-Debrid is done, HTTPS download URLs are sent to FDM with `fdm -fs` (never the raw magnet). If the torrent is already downloaded on your Real-Debrid account, FDM still fills the dialog as usual.

## Firefox browser extension

The add-on also works when downloads are captured from Firefox via the FDM extension.

1. Install the [Free Download Manager extension](https://addons.mozilla.org/firefox/addon/free-download-manager/) in Firefox.
2. In FDM, enable browser integration for Firefox.
3. In FDM → **Add-ons** → settings, enable **Allow add-ons to use web browser cookies** (recommended for hosters that need session cookies).
4. On a supported hoster page, click the normal download button — FDM should intercept the link and route it through Real-Debrid.

When the browser sends a direct file URL, FDM uses the add-on's `isPossiblySupportedSource` handler. The embedded host list in `rd-domains.js` makes that work immediately without waiting for a network fetch.

## Firefox magnet links

HTTP hoster links work through the official FDM Firefox extension. **Magnet links need the companion extension** in [`firefox-extension/`](firefox-extension/README.md):

1. Run the native host installer:

   **Linux / macOS:**

   ```bash
   ./firefox-extension/scripts/install-native-host.sh
   ```

   **Windows (PowerShell):**

   ```powershell
   .\firefox-extension\scripts\install-native-host.ps1
   ```
2. Load `firefox-extension/manifest.json` via `about:debugging`
3. Restart Firefox

Click a magnet (or paste one in FDM). The toolbar popup is the control surface: what is configured, which files to take, and live Real-Debrid progress. Finished files are unrestricted HTTPS URLs sent to FDM with `fdm -fs`.

## Manual test checklist

1. **Invalid token**
   - Set a bad token in `config.json`
   - Paste any supported hoster URL
   - Expected: `Invalid Real-Debrid API token — edit config.json`

2. **Hoster link**
   - Set a valid token
   - Paste a supported single-file hoster URL
   - Expected: FDM shows the filename and starts downloading via Real-Debrid CDN

3. **Folder link**
   - Paste a supported folder URL
   - Expected: FDM shows a playlist with one entry per file

4. **Magnet link**
   - Paste a small magnet link
   - Expected: FDM dialog returns immediately; the Firefox popup shows the waybill. Pick files (or wait 60s for all). Downloads appear in FDM when Real-Debrid finishes.

5. **Unavailable host**
   - Paste a link from a host that Real-Debrid marks offline
   - Expected: clear error such as `Host unavailable on Real-Debrid right now`

## Development layout

```
manifest.json
msparser.js
msbatchparser.js
config.example.json
python/
  config_loader.py
  rd_client.py
  fdm_result.py
  parse.py
  parse_folder.py
  magnet_job.py
  test_magnet.py
scripts/build-fda.sh
scripts/build-fda.ps1
```

## Limitations

- No automatic hoster-link detection on web pages (paste URLs manually, or use FDM's official browser extension)
- No in-app settings UI for the FDM add-on (`config.json` only; the Firefox popup shows the current values)
- Magnet URLs only work if FDM routes them to add-ons
- HLS/M3U8 streams are not supported

## License

MIT
