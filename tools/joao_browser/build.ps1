# Copyright 2026 The Joao Browser Authors
# Use of this source code is governed by a BSD-style license in LICENSE.
param(
    [Parameter(Mandatory = $true)][string]$Tag,
    [Parameter(Mandatory = $true)][string]$Commit,
    [string]$DepotToolsCommit = '81577f19a8497ba7e41afac322e8f03553a863ec'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed with exit code $LASTEXITCODE" }
}

if ($Tag -notmatch '^joao-v[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9]+)?$') {
    throw 'Invalid release tag.'
}
if (($Commit -notmatch '^[0-9a-f]{40}$') -or ($DepotToolsCommit -notmatch '^[0-9a-f]{40}$')) {
    throw 'Source revisions must be full commit hashes.'
}
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Windows x64 is required.' }
$source = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$checkout = Split-Path -Parent $source
if ((Split-Path -Leaf $source) -ne 'src') { throw 'Checkout must be located in a directory named src.' }
if ($source.Contains(' ')) { throw 'Chromium requires a source path without spaces.' }
$drive = Get-PSDrive -Name ([IO.Path]::GetPathRoot($source).Substring(0, 1))
if ($drive.Free -lt 150GB) { throw 'At least 150 GB free space is required before dependency sync.' }
$memory = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
if ($memory -lt 32GB) { throw 'Release runner needs at least 32 GB RAM (64 GB recommended).' }
$actualCommit = (& git -C $source rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $actualCommit -ne $Commit) { throw 'Checkout commit mismatch.' }
$depot = Join-Path $checkout 'depot_tools'
if (-not (Test-Path -LiteralPath $depot)) {
    Invoke-Checked git @('clone', 'https://chromium.googlesource.com/chromium/tools/depot_tools.git', $depot)
}
Invoke-Checked git @('-C', $depot, 'fetch', 'origin', $DepotToolsCommit)
Invoke-Checked git @('-C', $depot, 'checkout', '--detach', $DepotToolsCommit)
$env:DEPOT_TOOLS_UPDATE = '0'
$env:DEPOT_TOOLS_WIN_TOOLCHAIN = '0'
$env:PATH = "$depot;$env:PATH"
# Bootstrap depot_tools from cmd, as required by the Windows build instructions.
Invoke-Checked cmd.exe @('/d', '/c', 'gclient --version')
$gclient = @'
solutions = [{
  "name": "src",
  "url": "https://github.com/JoaoDEVWHADS/joao-browser.git",
  "managed": False,
  "custom_deps": {},
  "custom_vars": {},
}]
target_os = ["win"]
'@
Set-Content -LiteralPath (Join-Path $checkout '.gclient') -Value $gclient -Encoding ascii
Push-Location $checkout
try {
    Invoke-Checked gclient.bat @('sync', '--no-history', '--revision', "src@$Commit")
} finally { Pop-Location }
Push-Location $source
try {
    $build = Join-Path $source 'out/JoaoRelease'
    New-Item -ItemType Directory -Force -Path $build | Out-Null
    @'
is_debug = false
is_component_build = false
is_official_build = true
is_chrome_branded = false
target_cpu = "x64"
symbol_level = 0
blink_symbol_level = 0
v8_symbol_level = 0
use_remoteexec = false
chrome_pgo_phase = 0
generate_about_credits = true
'@ | Set-Content -LiteralPath (Join-Path $build 'args.gn') -Encoding ascii
    Invoke-Checked gn.bat @('gen', 'out/JoaoRelease', '--fail-on-unused-args')
    Invoke-Checked autoninja.bat @('-C', 'out/JoaoRelease', 'mini_installer',
        'install_static_unittests', 'joao_adblock_unittests')
    Invoke-Checked (Join-Path $build 'install_static_unittests.exe') @(
        '--gtest_filter=UserDataDir.*Portable*')
    Invoke-Checked (Join-Path $build 'joao_adblock_unittests.exe') @()
    $output = Join-Path $checkout "release-$Tag"
    Invoke-Checked python3.bat @('tools/joao_browser/package.py', '--build-dir', $build,
        '--output-dir', $output, '--tag', $Tag, '--commit', $Commit,
        '--depot-tools-commit', $DepotToolsCommit)
    & (Join-Path $PSScriptRoot 'smoke-test.ps1') -ReleaseDirectory $output
} finally { Pop-Location }
