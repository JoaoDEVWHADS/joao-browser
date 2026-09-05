# Joao Browser Windows releases

Every push to `main` starts the release workflow. An Ubuntu job commits a UTC
`YYYYMMDDHHMMSS` version to `version.txt` and tags that exact source before the
Windows job builds and publishes three artifacts:

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
  `JoaoDEVWHADS/joao-browser`, checks its compiled-in SHA-256 and length, and executes
  it only after successful verification. It does not extract untrusted ZIPs or
  resolve a moving `latest` URL. Both installers install the same browser.

Both installers support per-user installation only. `--system-level` is
unsupported; this release does not install machine-wide services.

`release-manifest.json` records source/tool revisions and artifact sizes/hashes.
`SHA256SUMS.txt` covers the artifacts and manifest. Release assets must not be
replaced: an older online installer will intentionally reject changed bytes.
Request a new timestamped build for a rebuild. Signing binaries is not configured;
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

Push changes to `main`; a lightweight Ubuntu job creates the version commit and
`joao-vYYYYMMDDHHMMSS` tag automatically. It then explicitly dispatches a new
workflow run at that tag with `GITHUB_TOKEN`. All release runs share a concurrency
group with cancellation enabled: the newest execution interrupts the previous
one. The dispatched build run never stamps another version, so the automatic
commit starts a new build without causing an infinite commit/build cycle.
Manual workflow dispatch without a release tag starts the versioning phase too.

The Windows build checks out the exact stamped commit, builds and validates it,
then uploads assets into a draft and publishes only after validation passes.
Existing releases are never overwritten. Repository rules must allow Actions to
update `main`, create tags and dispatch workflows; failures are reported by the
version job. The Windows runner prerequisite still applies; version stamping
alone is not a successful browser build. Pushes with several commits produce one
initial workflow run, followed by the automatically dispatched build run.

`version.txt` is the public release/update identity. Updates are offered only
from published GitHub releases, never from an unbuilt version on `main`.
At build time, `build_version.py` maps the timestamp to Windows' four 16-bit
version fields: engine major, days since 2020-01-01, minutes since midnight,
seconds. This lets the native installer recognize newer timestamp builds while
preserving the Chromium engine major. `chrome/VERSION` changes only in the build
checkout after dependency sync; the committed upstream version remains intact.
The manifest records the timestamp as `version` and the generated four-part
version as `chromium_version`. Portable archives retain the adjacent user profile.

For a local Windows build, clone this repository into `<checkout>\src` and run:

```powershell
$commit = (git -C C:\joao\src rev-parse HEAD).Trim()
$version = (Get-Content C:\joao\src\version.txt -Raw).Trim()
& C:\joao\src\tools\joao_browser\build.ps1 -Tag "joao-v$version" -Commit $commit
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
`UserDataDir.*Portable*` filter, all `joao_adblock_unittests` and
`joao_updater_unittests` before packaging.
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

## Browser update checks

On Windows, the About page checks published releases from
`JoaoDEVWHADS/joao-browser` and displays the embedded UTC release version.
A newer release offers the offline installer for an installed browser, or the
portable ZIP for a portable browser. Installation/application is explicit; the
checker does not replace a running browser automatically. See
[the updater implementation notes](../../docs/joao_browser/updater.md).
