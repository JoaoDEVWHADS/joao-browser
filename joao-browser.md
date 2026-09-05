# João Browser for Windows x64

## Accepted scope
Work directly on `main`; create a separate local commit for each coherent change.
Remove browser-integrated AI only, without modifying AI elements on websites.
Remember rejection of the initial default-browser offer. Brand the product João
Browser. Enable native ad blocking, including YouTube. Provide a GitHub release
workflow producing a self-contained portable ZIP, online installer and offline
installer.

## Implementation status
- [x] Browser AI: immutable product policy disables integrated entry points and
  services, including existing profiles. See docs/joao_browser/integrated_ai.md.
- [x] Default browser: persist rejection and migrate previous dismissals without
  disabling the manual default-browser setting.
- [x] Branding: João Browser strings, Windows product/install identity and UTF-8
  version resources. Installers support the current user only.
- [x] Native ad blocking: enabled-by-default all-site subresource filtering,
  bundled EasyList, cosmetic rules and YouTube player-response intervention.
  First HTTP(S) navigation waits for bundled rules to publish.
- [x] Distribution code: Windows x64 release workflow, adjacent portable storage,
  offline installer packaging and a checksum-verifying online installer.
- [x] Local integration review and executable Python/JavaScript/script checks.
- [ ] Full Windows build and execution of added C++ tests.
- [ ] Actual portable browser smoke test and clean-VM online/offline installation,
  upgrade/uninstall, default-prompt and AI UI regression checks.
- [ ] Live YouTube playback validation, signed in and signed out.
- [ ] Remote release build/publication (no push or execution requested).

## Validation evidence
Local checks passed: six package tests, five filter-resource tests, one actual
HTTP fixture lifecycle test, JavaScript behavioral fixtures, PowerShell parser
checks, actionlint, GN formatting and git whitespace checks. Earlier branding
validation generated 84 locale PAKs with GRIT; ten version utility tests passed.
These checks do not establish that the Windows browser compiles or runs.
The workflow now builds/runs portable profile and native rule matcher tests,
then tests first-navigation blocking against a local server with an unfiltered
control and verifies profile storage after moving the portable directory.

The Windows job requires a dedicated self-hosted runner; see
tools/joao_browser/README.md for exact prerequisites and release instructions.
Native ad filtering is an initial implementation using Chromium's engine, not
the full Brave engine. Unsupported rule operators and service-worker requests
remain outside its coverage. YouTube server-side ads or changed response formats
may evade filtering. The bundled list updates with browser releases, without a
runtime subscription updater. Details: components/joao_adblock/README.md.
Portable profile/cache/crash/temp storage is adjacent to the executable; Windows
account-bound encrypted credentials do not become transferable between machines.

## Local commits
- `e74c590f5a962`: accepted implementation plan.
- `66db941c40e12`: Windows release workflow and installer/ZIP packaging.
- `37568031085dc`: native adjacent portable storage.
- `47cbcf4bfcb66`: permanent default-browser refusal.
- `0825370635967`: UTF-8 Windows version resources.
- `55dd16f428f13`: João Browser branding.
- `555bc98efe709`: browser-integrated AI product policy.
- `08801ec360677`: native/portable release validation gates.
- `16e879a0bd198`: native filters, YouTube intervention and startup readiness.

## Coordination
One coordinator and at most three simultaneous workers (runtime limit), no
recursive delegation. Separate path ownership; shared files are edited only
after coordination. Workers request a commit window; coordinator serializes
commits on `main`. Browser AI, ad blocking and release infrastructure start first;
default-browser and branding each receive a dedicated worker as slots free.
Workers report evidence and blockers after bounded investigation, avoiding
repeated failed operations. No push or remote workflow execution is included.

## Environment
Chromium 155.0.8044.0 source checkout on Linux. Dependency sync, Windows toolchain,
build output and Windows runtime are not present at the start of the work.
