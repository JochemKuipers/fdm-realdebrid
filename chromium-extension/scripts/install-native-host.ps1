$ErrorActionPreference = "Stop"

# Stable extension ID from chromium-extension/manifest.json "key" field.
$ExtensionId = "ijimlcmjkddnimablogpkmgopalomlfn"
$AllowedOrigin = "chrome-extension://$ExtensionId/"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$extensionRoot = Split-Path -Parent $root
$nativeHostDir = Join-Path $extensionRoot "native-host"
$cmdPath = Join-Path $nativeHostDir "fdm_rd_magnet.cmd"
$installDir = Join-Path $env:LOCALAPPDATA "fdm-realdebrid\native-host"
$manifestPath = Join-Path $installDir "com.fdmrealdebrid.magnet.chromium.json"

$registryKeys = @(
    "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.fdmrealdebrid.magnet",
    "HKCU:\Software\Chromium\NativeMessagingHosts\com.fdmrealdebrid.magnet",
    "HKCU:\Software\Vivaldi\NativeMessagingHosts\com.fdmrealdebrid.magnet"
)

if (-not (Test-Path $cmdPath)) {
    throw "Missing native host launcher: $cmdPath"
}

New-Item -ItemType Directory -Path $installDir -Force | Out-Null
Copy-Item (Join-Path $nativeHostDir "fdm_rd_magnet.py") (Join-Path $installDir "fdm_rd_magnet.py") -Force
Copy-Item (Join-Path $nativeHostDir "fdm_rd_magnet_worker.py") (Join-Path $installDir "fdm_rd_magnet_worker.py") -Force
Copy-Item $cmdPath (Join-Path $installDir "fdm_rd_magnet.cmd") -Force
Copy-Item (Join-Path $extensionRoot "..\python\platform_paths.py") (Join-Path $installDir "platform_paths.py") -Force

$hostPath = Join-Path $installDir "fdm_rd_magnet.cmd"
$hostPathJson = ($hostPath -replace "\\", "/")

$manifest = @{
    name = "com.fdmrealdebrid.magnet"
    description = "Send magnet links to Free Download Manager for Real-Debrid"
    path = $hostPathJson
    type = "stdio"
    allowed_origins = @($AllowedOrigin)
}

$json = $manifest | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText($manifestPath, $json, (New-Object System.Text.UTF8Encoding $false))

foreach ($registryKey in $registryKeys) {
    New-Item -Path $registryKey -Force | Out-Null
    Set-ItemProperty -Path $registryKey -Name "(Default)" -Value $manifestPath
}

Write-Host "Installed native host manifest:"
Write-Host "  $manifestPath"
Write-Host "Registered registry keys:"
foreach ($registryKey in $registryKeys) {
    Write-Host "  $registryKey"
}
Write-Host "Host launcher:"
Write-Host "  $hostPath"
Write-Host "Extension origin:"
Write-Host "  $AllowedOrigin"
Write-Host ""
Write-Host "Restart Chrome / Chromium / Vivaldi completely, then load the unpacked extension."
