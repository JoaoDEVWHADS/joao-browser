# João Browser native ad filtering

Windows builds enable Chromium's native indexed subresource filter on all sites,
including ordinary sites not classified by Safe Browsing. Network filtering uses
Chromium's EasyList parser, resource type/first-party rules and rule exceptions.
The EasyList authors (https://easylist.to/) maintain the included snapshot.
EasyList is distributed under CC BY-SA 3.0 (see LICENSE.easylist). The original
snapshot and reproducible conversion source are included in this repository.

Cosmetic CSS runs in a browser isolated world and supports domain inclusions,
exclusions and selector exceptions. Only compiled CSS data is injected; there
is no downloaded JavaScript. A separate browser-owned YouTube intervention
removes player advertising fields from initial player responses and JSON
responses, preserving ordinary video data. It does not alter page AI features.

## Updating

Before tagging a release, run `python3 components/joao_adblock/update_rules.py`,
review the diff and commit both easylist.txt and snapshot.json. The HTTPS source,
maximum download size and format are validated. GN embeds that committed
snapshot; the installed browser indexes it off the UI thread and caches it in
its user-data directory. Browser releases update the rules. There is no automatic
runtime subscription updater in this version. Google's limited Better Ads
component cannot overwrite João's list.

## Validation and limits

Run `python3 components/joao_adblock/resources_test.py` and
`node components/joao_adblock/script_test.cjs`. The native target
`//components/joao_adblock:joao_adblock_unittests` exercises Chromium's actual
parser and indexed matcher when build dependencies are available.

This is a native initial implementation, not the full Brave Shields engine.
Chromium does not support all modern uBO/ABP operators: unsupported network rules
are dropped and counted in the browser log; redirect replacements, procedural
cosmetic filters and arbitrary filter-list scriptlets are not implemented.
Cosmetic and YouTube interventions honor the native per-document activation,
including per-site network allow settings and document exceptions.
Rules are installed asynchronously on a new user-data directory. Protected
HTTP(S) navigation waits for ruleset publication; initialization failure or the
30-second deadline cancels the navigation instead of silently allowing ads.
Subsequent sessions reuse the indexed ruleset.
Subresource filtering does not cover every request class, e.g. service worker
network requests. YouTube server-side ads and new response formats may evade
this intervention. Script fixture tests are not live YouTube playback tests.
A Windows build and signed-in/signed-out playback regression remain required.
