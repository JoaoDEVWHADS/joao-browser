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
$server = $null

function Invoke-Portable {
    param([string]$Directory, [string]$Url, [string]$OutputName,
        [string[]]$ExtraArguments = @())
    $stdout = Join-Path $temporary "$OutputName.txt"
    $stderr = Join-Path $temporary "$OutputName.err"
    $browser = Join-Path $Directory 'chrome.exe'
    $arguments = @('--headless', '--no-first-run', '--disable-gpu',
        '--disable-background-networking', '--no-proxy-server',
        '--host-resolver-rules="MAP ad.doubleclick.net 127.0.0.1"',
        '--dump-dom', $Url) + $ExtraArguments
    $process = Start-Process -FilePath $browser -PassThru -ArgumentList $arguments `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr
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
    if (Test-Path -LiteralPath (Join-Path $browserDirectory 'User Data')) {
        throw 'Portable archive unexpectedly contains an existing profile.'
    }
    $ready = Join-Path $temporary 'server-ready.json'
    $python = (& python3.bat -c 'import sys; print(sys.executable)').Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Cannot locate the fixture Python runtime.' }
    $fixture = Join-Path $PSScriptRoot 'smoke_server.py'
    $server = Start-Process -FilePath $python -PassThru -ArgumentList @(
        ('"' + $fixture + '"'), '--ready-file', ('"' + $ready + '"')
    ) -RedirectStandardOutput (Join-Path $temporary 'server.out') `
        -RedirectStandardError (Join-Path $temporary 'server.err')
    $deadline = [DateTime]::UtcNow.AddSeconds(15)
    while (-not (Test-Path -LiteralPath $ready)) {
        if ($server.HasExited -or [DateTime]::UtcNow -gt $deadline) {
            throw 'Local adblock fixture did not start.'
        }
        Start-Sleep -Milliseconds 100
    }
    $port = (Get-Content -LiteralPath $ready -Raw | ConvertFrom-Json).port
    $url = "http://127.0.0.1:$port/"
    # The first real network navigation must wait for a fresh ruleset to index.
    $html = Invoke-Portable $browserDirectory $url 'first'
    if ($html -notmatch 'data-joao-normal="executed"') {
        throw 'The normal fixture script did not execute.'
    }
    if ($html -match 'data-joao-ad="executed"') {
        throw 'Native ad blocking failed on the first portable navigation.'
    }
    # Prove the ad URL is reachable: DNS/proxy failures must not look like blocking.
    $control = Invoke-Portable $browserDirectory $url 'control' @(
        '--disable-features=JoaoNativeAdblock')
    if ($control -notmatch 'data-joao-ad="executed"') {
        throw 'Unfiltered control could not execute the ad fixture script.'
    }
    $preferences = Join-Path $browserDirectory 'User Data/Default/Preferences'
    if (-not (Test-Path -LiteralPath $preferences)) { throw 'Profile was not stored beside the executable.' }
    $moved = Join-Path $temporary 'Moved Joao Browser'
    Move-Item -LiteralPath $browserDirectory -Destination $moved
    $versionPage = Invoke-Portable $moved 'chrome://version' 'moved'
    $profile = Join-Path $moved 'User Data/Default'
    if ($versionPage.IndexOf($profile, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw 'Browser did not report the relocated portable profile.'
    }
    Write-Output 'Native adblock first navigation, portable profile and relocation checks passed.'
} finally {
    if ($null -ne $server) {
        if (-not $server.HasExited) { $server.Kill() }
        $server.WaitForExit()
        $server.Dispose()
    }
    Remove-Item -LiteralPath $temporary -Recurse -Force
}
