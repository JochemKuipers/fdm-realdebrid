$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$dist = Join-Path $root "dist"
$fda = Join-Path $dist "fdm-realdebrid.fda"

if (-not (Test-Path $dist)) {
    New-Item -ItemType Directory -Path $dist | Out-Null
}

$items = @(
    "manifest.json",
    "icon.png",
    "msparser.js",
    "msbatchparser.js",
    "config.example.json",
    "python"
)

$staging = Join-Path $dist "staging"
if (Test-Path $staging) {
    Remove-Item -Recurse -Force $staging
}
New-Item -ItemType Directory -Path $staging | Out-Null

foreach ($item in $items) {
    $source = Join-Path $root $item
    if (-not (Test-Path $source)) {
        throw "Missing required file or directory: $item"
    }
    Copy-Item -Path $source -Destination (Join-Path $staging $item) -Recurse
}

if (Test-Path $fda) {
    Remove-Item -Force $fda
}

Compress-Archive -Path (Join-Path $staging "*") -DestinationPath (Join-Path $dist "fdm-realdebrid.zip") -Force
Rename-Item -Path (Join-Path $dist "fdm-realdebrid.zip") -NewName "fdm-realdebrid.fda"

Remove-Item -Recurse -Force $staging

Write-Host "Built $fda"
Write-Host "Copy config.example.json to config.json in the add-on folder after install, then add your API token."
