# Copyright 2026 The Joao Browser Authors
# Use of this source code is governed by a BSD-style license in LICENSE.
param([Parameter(Mandatory = $true)][string]$ReleaseDirectory)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$manifest = Get-Content (Join-Path $ReleaseDirectory 'release-manifest.json') -Raw | ConvertFrom-Json
foreach ($entry in $manifest.artifacts.PSObject.Properties) {
    $file = Join-Path $ReleaseDirectory $entry.Name
    if ((Get-FileHash $file -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value.sha256) {
        throw "SHA256 mismatch: $file"
    }
    if ((Get-Item $file).Length -ne $entry.Value.size) { throw "Size mismatch: $file" }
}
$zip = @(Get-ChildItem -LiteralPath $ReleaseDirectory -Filter '*-portable.zip')
if ($zip.Count -ne 1) { throw 'Expected exactly one portable archive.' }
$temporary = Join-Path ([IO.Path]::GetTempPath()) ('JoaoSmoke-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporary | Out-Null

function Invoke-Portable {
    param([string]$Directory, [string]$Url, [string]$OutputName)
    $stdout = Join-Path $temporary "$OutputName.txt"
    $stderr = Join-Path $temporary "$OutputName.err"
    $browser = Join-Path $Directory 'chrome.exe'
    $process = Start-Process -FilePath $browser -PassThru -ArgumentList @(
        '--headless', '--no-first-run', '--disable-gpu', '--dump-dom', $Url
    ) -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if (-not $process.WaitForExit(120000)) {
        & taskkill.exe /PID $process.Id /T /F | Out-Null
        throw "Portable browser timed out: $Directory"
    }
    $process.Refresh()
    if ($process.ExitCode -ne 0) { throw "Portable browser failed: $Directory" }
    return (Get-Content -LiteralPath $stdout -Raw)
}

try {
    Expand-Archive -LiteralPath $zip[0].FullName -DestinationPath $temporary
    $browserDirectory = Join-Path $temporary 'JoaoBrowser'
    $html = Invoke-Portable $browserDirectory 'data:text/html,JOAO_SMOKE_OK' 'first'
    if ($html -notmatch 'JOAO_SMOKE_OK') { throw 'Browser did not render the test document.' }
    $preferences = Join-Path $browserDirectory 'User Data/Default/Preferences'
    if (-not (Test-Path -LiteralPath $preferences)) { throw 'Profile was not stored beside the executable.' }
    $moved = Join-Path $temporary 'Moved Joao Browser'
    Move-Item -LiteralPath $browserDirectory -Destination $moved
    $versionPage = Invoke-Portable $moved 'chrome://version' 'moved'
    $profile = Join-Path $moved 'User Data/Default'
    if ($versionPage.IndexOf($profile, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw 'Browser did not report the relocated portable profile.'
    }
    Write-Output 'Portable runtime, adjacent profile and relocation checks passed.'
} finally {
    Remove-Item -LiteralPath $temporary -Recurse -Force
}
