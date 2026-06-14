$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$extensionRoot = Split-Path -Parent $root
$nativeHostDir = Join-Path $extensionRoot "native-host"
$cmdPath = Join-Path $nativeHostDir "fdm_rd_magnet.cmd"
$installDir = Join-Path $env:LOCALAPPDATA "fdm-realdebrid\native-host"
$manifestDir = Join-Path $env:APPDATA "Mozilla\NativeMessagingHosts"
$manifestPath = Join-Path $manifestDir "com.fdmrealdebrid.magnet.json"
$registryKey = "HKCU:\Software\Mozilla\NativeMessagingHosts\com.fdmrealdebrid.magnet"
$registryKeyWow = "HKCU:\Software\WOW6432Node\Mozilla\NativeMessagingHosts\com.fdmrealdebrid.magnet"

if (-not (Test-Path $cmdPath)) {
    throw "Missing native host launcher: $cmdPath"
}

New-Item -ItemType Directory -Path $installDir -Force | Out-Null
Copy-Item (Join-Path $nativeHostDir "fdm_rd_magnet.py") (Join-Path $installDir "fdm_rd_magnet.py") -Force
Copy-Item (Join-Path $nativeHostDir "fdm_rd_magnet_worker.py") (Join-Path $installDir "fdm_rd_magnet_worker.py") -Force
Copy-Item $cmdPath (Join-Path $installDir "fdm_rd_magnet.cmd") -Force

$hostPath = Join-Path $installDir "fdm_rd_magnet.cmd"
$hostPathJson = ($hostPath -replace "\\", "/")

New-Item -ItemType Directory -Path $manifestDir -Force | Out-Null

$manifest = @{
    name = "com.fdmrealdebrid.magnet"
    description = "Send magnet links to Free Download Manager for Real-Debrid"
    path = $hostPathJson
    type = "stdio"
    allowed_extensions = @("fdm-realdebrid-magnets@jochem.local")
}

$json = $manifest | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText($manifestPath, $json, (New-Object System.Text.UTF8Encoding $false))

New-Item -Path $registryKey -Force | Out-Null
Set-ItemProperty -Path $registryKey -Name "(Default)" -Value $manifestPath

New-Item -Path $registryKeyWow -Force | Out-Null
Set-ItemProperty -Path $registryKeyWow -Name "(Default)" -Value $manifestPath

Write-Host "Installed native host manifest:"
Write-Host "  $manifestPath"
Write-Host "Registered registry keys:"
Write-Host "  $registryKey"
Write-Host "  $registryKeyWow"
Write-Host "Host launcher:"
Write-Host "  $hostPath"
Write-Host ""
Write-Host "Restart Firefox completely, then click a magnet link."
