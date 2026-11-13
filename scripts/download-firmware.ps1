<#
.SYNOPSIS
    Re-fetch official NETGEAR GS105Ev2 firmware and the NDT utility into downloads/.
.DESCRIPTION
    Mirrors the pattern used by the sibling mfc9330cdw project's
    scripts/download-all.ps1: pull known-good URLs, verify they land as real
    archives, and print SHA-256 so it can be cross-checked against
    downloads/firmware/HASHES.md and downloads/utilities/HASHES.md.
#>

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$firmwareDir = Join-Path $root 'downloads\firmware'
$utilDir = Join-Path $root 'downloads\utilities'
New-Item -ItemType Directory -Force -Path $firmwareDir, $utilDir | Out-Null

$targets = @(
    @{ Url = 'https://www.downloads.netgear.com/files/GDC/GS105EV2/GS105Ev2_V1.6.0.25.zip'; Out = Join-Path $firmwareDir 'GS105Ev2_V1.6.0.25.zip' },
    @{ Url = 'https://www.downloads.netgear.com/files/GDC/GS105EV2/GS105Ev2_V1.6.0.4.zip'; Out = Join-Path $firmwareDir 'GS105Ev2_V1.6.0.4.zip' },
    @{ Url = 'https://www.downloads.netgear.com/files/GDC/NDT/NETGEAR_Discovery_Tool_Windows-V2.0.4.zip'; Out = Join-Path $utilDir 'NETGEAR_Discovery_Tool_Windows-V2.0.4.zip' }
)

foreach ($t in $targets) {
    Write-Host "Fetching $($t.Url)"
    Invoke-WebRequest -Uri $t.Url -OutFile $t.Out -UseBasicParsing
    $hash = Get-FileHash $t.Out -Algorithm SHA256
    Write-Host ("  {0}  {1}" -f $hash.Hash, (Split-Path -Leaf $t.Out))
}

Write-Host "`nCross-check the hashes above against downloads/firmware/HASHES.md and downloads/utilities/HASHES.md."
