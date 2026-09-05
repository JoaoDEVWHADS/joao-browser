# Joao Browser Windows releases

The workflow builds the tagged source and publishes three artifacts:

- `JoaoBrowser-<tag>-windows-x64-portable.zip`: extract and run `chrome.exe`.
  The `joao_portable` marker enables native adjacent `User Data` storage, including
  cache and crash data. No installation or launcher arguments are required.
- `JoaoBrowser-<tag>-windows-x64-offline.exe`: Chromium's complete native
  `mini_installer.exe`, with Joao Browser branding. Installs for the current user;
  native setup handles shortcuts, registration, updates and uninstall through
  Windows Settings. It contains the entire browser; an internet connection is
  not required for installation.
- `JoaoBrowser-<tag>-windows-x64-online.exe`: small .NET Framework bootstrapper.
  It downloads that release's exact offline installer from
  `JoaoDEVWHADS/chromium`, checks its compiled-in SHA-256 and length, and executes
  it only after successful verification. It does not extract untrusted ZIPs or
  resolve a moving `latest` URL. Both installers install the same browser.

Installation is per-user only. The native installer rejects `--system-level`;
machine-wide installation is not supported by this build.

`release-manifest.json` records source/tool revisions and artifact sizes/hashes.
`SHA256SUMS.txt` covers the artifacts and manifest. Release assets must not be
replaced: an older online installer will intentionally reject changed bytes.
Use a new numbered tag for a rebuild. Signing binaries is not configured;
Windows may show an unknown-publisher prompt. Sign the offline payload before
packaging if signing is added, so its embedded bootstrapper digest stays correct.

## Runner preparation

This cannot be built on a standard GitHub-hosted Windows runner's disk budget.
Register a **dedicated Windows x64 self-hosted runner** with the custom label
`joao-browser-build`. Do not enable pull-request jobs on this machine. Required:

- Windows 10 or newer, Git for Windows, GitHub CLI (`gh`), Windows PowerShell 5.1
  and .NET Framework 4.8 (including `Framework64/v4.0.30319/csc.exe`).
- Visual Studio 2026 >=18.0.0, Desktop development with C++, ATL/MFC, Windows SDK
  10.0.28000.2270 and SDK Debugging Tools >=10.0.26100.3323, matching
  [this source tree's build instructions](../../docs/windows_build_instructions.md).
  Set `vs2026_install` if toolchain discovery requires it.
- 32 GB RAM minimum, 64 GB recommended, preferably 24 or more CPU cores, and
  150 GB free NTFS space **in addition to the source checkout**. Provision a
  400 GB or larger SSD for sources, dependencies, build and distribution staging.
- A short runner workspace path without spaces (for example `C:\actions`).
  Enable Windows/Git long paths as explained in the upstream build instructions.
- Network access to GitHub and Chromium's dependency/toolchain hosts.

The script pins depot_tools to `81577f19a8497ba7e41afac322e8f03553a863ec`, disables
its automatic update, and syncs the checkout's pinned DEPS at the exact tagged
commit. Update that pin deliberately when updating Chromium. The job allows
23 hours, below the
[24-hour GITHUB_TOKEN lifetime](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idtimeout-minutes).
A slow/cold machine that exceeds this needs more resources; successful publication
is not claimed until a complete Windows run passes.

## Releasing

Create a tag whose version matches `chrome/VERSION`: `joao-v155.0.8044.0`, or
`joao-v155.0.8044.0-1` for a numbered rebuild. Pushing that tag starts the workflow;
manual dispatch accepts an existing tag. The tagged commit must contain the
workflow and these tools. The workflow creates a draft only after build,
packaging and the portable runtime smoke test pass; uploads all five assets;
then publishes it. Upload failure leaves a draft for inspection. Existing
releases are never overwritten. No release is published merely by committing
these files locally.

For a local Windows build, clone this repository into `<checkout>\src` and run:

```powershell
$commit = (git -C C:\joao\src rev-parse HEAD).Trim()
& C:\joao\src\tools\joao_browser\build.ps1 -Tag joao-v155.0.8044.0 -Commit $commit
```

Packages appear in `<checkout>\release-<tag>`. This directory must initially be
empty. After an interrupted packaging run, inspect and remove only that generated
release directory before rerunning; build/dependency caches can be reused.

## Validation and portability limits

`python3 tools/joao_browser/package_test.py` exercises actual ZIP generation,
required runtime validation, x64 PE checks, filename collisions and traversal
rejection using synthetic files. These tests run on Linux; they are not a
Chromium build or installer runtime test.

The Windows pipeline builds and runs `install_static_unittests` with the
`UserDataDir.*Portable*` filter and all `joao_adblock_unittests` before packaging.
It then runs `smoke-test.ps1`: verify artifact digests/lengths, extract the ZIP,
and navigate the fresh portable profile to a local HTTP fixture. A normal script
must execute and a script from `ad.doubleclick.net` (mapped to loopback) must be
blocked. A second run with native ad blocking disabled must execute the same ad
script, ruling out an unreachable fixture as a false positive. The smoke test
also checks adjacent profile creation, moves the extracted folder (including a
path with spaces), and verifies `chrome://version` reports the moved profile.
It deliberately omits `--user-data-dir`, so missing native portable support fails
the test. It does not install into the build runner's account or test YouTube.

`python3 tools/joao_browser/smoke_server_test.py` exercises the fixture's actual
subprocess startup, ready-file protocol and HTTP responses on Linux or Windows.
This fixture test does not execute the browser.

Before public distribution, verify on a clean Windows x64 VM: online install,
network-disabled offline install, both upgrades, Windows Settings uninstall,
shortcuts, and portable first run/relocation. Test the online install against a
published matching test release; verify cancellation/network failures do not
install anything. The bootstrapper's Windows compilation and these installation
flows cannot be validated in a Linux-only checkout.

Close all browser processes before moving the portable folder. Profile storage
is local, but Windows DPAPI-protected passwords/cookies are still tied to the
Windows account/machine; copying the folder alone does not make those secrets
usable on another PC. Export/import passwords before migrating, and expect to
sign in again. The browser does not disable encryption to conceal this limit.
Windows itself can keep system-managed records of executed applications; a
portable application cannot promise to prevent OS-level logs/prefetch.
