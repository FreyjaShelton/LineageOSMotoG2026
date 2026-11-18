# Copy a finished release folder from the build laptop to this PC and check its checksums.
#
#   .\scripts\fetch-release.ps1                 # the newest folder in the laptop's ~/lineage/release/
#   .\scripts\fetch-release.ps1 utah-20261118   # a named one
#   .\scripts\fetch-release.ps1 -List           # just list what is there
#
# Needs the "laptop" shortcut in ~/.ssh/config (key ~/.ssh/id_laptop). Copies to
# D:\LineageOS\release\<name>\ (override with -Dest). Re-running resumes nothing: it
# re-copies the folder, then verifies every file against SHA256SUMS.
param(
    [string]$Name,
    [string]$Dest = "D:\LineageOS\release",
    [switch]$List
)
$ErrorActionPreference = "Stop"
$remote = "laptop"

$names = (ssh $remote "ls -t ~/lineage/release") -split "`n" | Where-Object { $_ }
if ($List) { $names; return }
if (-not $Name) { $Name = $names[0] }
if ($names -notcontains $Name) { throw "No release folder '$Name' on the laptop. Have: $($names -join ', ')" }

$target = Join-Path $Dest $Name
if (Test-Path $target) { throw "$target already exists; move or delete it first." }
New-Item -ItemType Directory -Force $Dest | Out-Null
Write-Host "Copying $Name from the laptop to $target ..."
scp -r "${remote}:lineage/release/$Name" $Dest
if ($LASTEXITCODE -ne 0) { throw "scp failed" }

$sums = Join-Path $target "SHA256SUMS"
if (-not (Test-Path $sums)) { Write-Warning "No SHA256SUMS in the folder; copy not verified."; return }
$bad = 0
foreach ($line in Get-Content $sums) {
    if ($line -notmatch '^([0-9a-f]{64})\s+\*?(.+)$') { continue }
    $want, $file = $Matches[1], $Matches[2]
    if ($file -eq "SHA256SUMS") { continue }
    $path = Join-Path $target $file
    if (-not (Test-Path $path)) { Write-Host "MISSING  $file"; $bad++; continue }
    $got = (Get-FileHash $path -Algorithm SHA256).Hash.ToLower()
    if ($got -eq $want) { Write-Host "ok       $file" } else { Write-Host "MISMATCH $file"; $bad++ }
}
if ($bad) { throw "$bad file(s) failed the checksum check." }
Write-Host "All files match SHA256SUMS. Release is in $target"
