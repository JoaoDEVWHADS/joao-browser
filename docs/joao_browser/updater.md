# GitHub release update checks on Windows

The unbranded Windows About page uses the Joao Browser GitHub release checker,
not Google Update/Omaha. Opening About requests the latest published release
from `https://api.github.com/repos/JoaoDEVWHADS/joao-browser/releases/latest`.
Cookies and account credentials are omitted. The response is bounded to 1 MiB
and the request times out after 30 seconds; redirects to a different endpoint
are rejected.

The build embeds the root `version.txt` through a GN action. It must contain a
valid `YYYYMMDDHHMMSS` UTC timestamp; missing or invalid input fails the build.
The About page displays this public version alongside the native engine version.
Only newer `joao-vYYYYMMDDHHMMSS` releases are offered. Drafts, prereleases,
malformed dates, missing published metadata and missing/not-uploaded assets are
rejected. Asset URLs must exactly match the official repository, release tag,
Windows x64 filename and HTTPS download path.

A `joao_portable` marker selects the portable ZIP. Otherwise the checker selects
the full offline installer. The available-update state exposes a download link
and instructions in the About page (English and Brazilian Portuguese). Clicking
it uses the browser's normal download flow and protections.

## Applying an update

Installation is explicit, not automatic: close the browser and run the downloaded
installer. For portable installations, close the browser and replace program
files from the new ZIP while preserving `User Data`. The checker never starts an
installer or overwrites a running executable. It does not add a scheduled task,
background update service, silent updater or Omaha protocol shim.

GitHub rate limiting, network failures, a repository without a published release,
or incomplete release artifacts show a failed check, not a false up-to-date
status. Reopening About retries the check. Releases are trusted through HTTPS
and the repository's publishing permissions; the checker does not independently
verify release signatures or SHA256 metadata because it does not execute assets.

## Validation

`generate_joao_version_test.py` tests valid, malformed and missing timestamps.
`joao_updater_unittests` covers release parsing, installed/portable asset choice,
draft/prerelease rejection, invalid dates, cross-repository URL rejection,
incomplete uploads and equal/older version ordering. A settings WebUI regression
covers the download link, public version display and clearing the link when no
update is available.

In the source-only Linux checkout, Python tests/header generation, XML resource
parsing, C++/GN formatting, TypeScript syntax checks and diff checks were executed.
The Chromium C++ tests, WebUI browser test and real Windows GitHub/download flow
still require the synced Windows build environment; no runtime pass is claimed.
