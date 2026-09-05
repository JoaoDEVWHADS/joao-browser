# João Browser for Windows x64

## Accepted scope
Work directly on `main`; create a separate local commit for each coherent change.
Remove browser-integrated AI only, without modifying AI elements on websites.
Remember rejection of the initial default-browser offer. Brand the product João
Browser. Enable native ad blocking, including YouTube. Provide a GitHub release
workflow producing a self-contained portable ZIP, online installer and offline
installer.

## Tasks and verification
- [ ] Browser AI: disable integrated entry points and services; add regression
  coverage for the product policy and verify affected build references.
- [ ] Default browser: persist the first-run rejection and suppress subsequent
  prompts; cover accepted, rejected and existing-profile cases.
- [ ] Branding: update Windows product identity and visible strings; validate
  resource generation and installer identity consistency.
- [ ] Native ad blocking: integrate an enabled-by-default filtering engine and
  maintained rules; verify request filtering, exceptions and YouTube behavior.
- [ ] Distribution: build Windows x64, package portable profile storage, online
  and offline installers, and publish release assets; validate scripts and CI.
- [ ] Integration: review all changes, run available focused tests and static
  checks, record commits and explicitly distinguish Windows runtime/build checks
  from checks executable in the current Linux checkout.

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
