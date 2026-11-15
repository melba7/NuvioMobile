# Architecture (fork)
- Built from upstream tag in fork/UPSTREAM_TAG + patches in fork/ (see FORK.md). Repo source outside fork/ is not what ships.
- New work goes in fork/nuvio-share-resume.patch (applied after the downloads patches in fork/build_from_source.py PATCHES).
- iOS: Share Extension target in iosApp (receives URL, hands to app via app group / custom URL scheme) -> Swift matcher module (OCR, Speech, subtitle fuzzy match) -> Kotlin/Compose player seek.
- No check command locally (no Mac). Check = GitHub Actions TestFlight run (build compiles; upload when key accepted).

## Decisions log
- 2026-11-15: on-device matching, no API key.

## Known problems
- Full CI build takes ~70 min; patch must be developed against the checked-out upstream source (clone NuvioMedia/NuvioMobile at the tag).
