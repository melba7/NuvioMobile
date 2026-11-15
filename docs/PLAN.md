Done: 2 | Last cleanup: none | Mac builds used: 0 of about 5

Waiting on Mo: 1 movie clip with its name and rough time.
Approved by Mo 2026-11-15: reading audio from the link (SPEC A2).

Rules for every milestone: edit only in the work tree, never open the `.patch` files, save
with `fork/dev-tree.sh save`. Milestones 1 and 2 need no Mac build. Each later milestone ends
with exactly one merge to `cmp-rewrite` (one Mac build). Suggested model: Sonnet; use Fable
for milestone 4 or after a check fails twice.

- [x] **1. Dev loop and fast check** (no Mac build)
  - Build: `fork/dev-tree.sh` (clone NuvioMedia/NuvioMobile at `fork/UPSTREAM_TAG` into
    `../nuvio-work`, apply the patches in `PATCHES` order, commit as baseline;
    `fork/dev-tree.sh save` writes the diff since baseline to `fork/nuvio-share-resume.patch`).
    Add that patch to `PATCHES` in `fork/build_from_source.py` and to whatever list
    `fork/check_upstream.py` uses. `fork/check.sh`: patches apply cleanly + clipfinder unit
    tests, printing only failures and a one-line summary. `.github/workflows/fork-check.yml`
    runs `fork/check.sh` on Linux for pull requests. First real code: `AppDeepLink.Clip(url)`
    for `nuvio://clip?url=...` in `AppUrlBridge.kt`, with tests in `AppUrlBridgeTest.kt`.
  - Settle: which Gradle test task runs commonTest on Linux without a Mac (try the desktop
    or Android host test target); write the answer into CLAUDE.md.
  - Done when: "Fork check" is green on the pull request and takes under 15 min.
  - Try it: GitHub, Actions tab, "Fork check" shows a green tick.
  - Files: fork/dev-tree.sh, fork/check.sh, fork/build_from_source.py, fork/check_upstream.py,
    .github/workflows/fork-check.yml, CLAUDE.md, work tree AppUrlBridge.kt + its test.

- [x] **2. The matcher** (no Mac build)
  - Build in `features/clipfinder/`: `ClipText.normalize` (lowercase, strip punctuation and
    filler), `ClipMatcher.match(lines, episodes)` using word triples: index each episode's
    cues, count distinct triple hits inside a sliding window (clip length x 2), rank by hits
    and by margin over the runner-up, return `ClipCandidate`s. Order and speed must not
    matter. Reject when fewer than 4 distinct hits or margin is thin.
  - Tests (made-up subtitles, never real show text): exact lines; 30% wrong words; half the
    lines missing (music); lines out of order (edited clip); two similar episodes; wrong
    show rejected; movie (one long file); empty transcript.
  - Done when: all those tests pass in the fast check.
  - Try it: Actions tab, open "Fork check", the test list shows the cases above.
  - Files: clipfinder/ClipText.kt, ClipMatcher.kt, ClipModels.kt, tests beside them.

- [ ] **3. Share sheet to Clip finder screen** (Mac build 1)
  - Build: `iosApp/ShareExtension` target (accepts 1 web URL), declared the way
    DownloadsWidgetExtension is; it opens `nuvio://clip?url=`. If the open is refused, post a
    notification that opens Nuvio. Main app: document type for movie files, routed to the
    same place. Compose `ClipFinderScreen` showing the link or file name and the stage
    names, reached from `MainAppContent.kt` on `AppDeepLink.Clip`. Signing script: bundle
    ID + profile for the new extension next to the widget one.
  - Done when: TestFlight build installs; TikTok and Instagram share sheets list Nuvio;
    tapping it opens Clip finder with the link; sharing a saved video does the same.
  - Try it: open a TikTok, Share, Nuvio.
  - Files: iosApp.xcodeproj/project.pbxproj, iosApp/ShareExtension/*, iosApp/iosApp/Info.plist,
    clipfinder/ClipFinderScreen.kt, MainAppContent.kt, fork/nuvio_testflight.py.
  - Wait for OK before starting (touches 3+ files and signing).

- [ ] **4. Read the link** (Mac build 2; the riskiest step, one session only)
  - Build: `ClipLinkReader` (follow short links; caption from the TikTok page metadata, since
    oEmbed no longer has it; Instagram embed
    page) -> `ClipInfo`. Parsing is tested against saved sample responses in commonTest.
    `ClipAudio.swift`: load the platform's embed player off-screen, take the video's
    address from the page, read up to 6 min of audio into memory. Nothing written to disk.
  - Done when: for Mo's test links Clip finder shows the caption and "audio: N seconds".
  - If audio fails for a platform after this one session: stop, write it under Known
    problems, and make that platform ask for the saved video instead. Do not keep trying.
  - Try it: share each test link; read the caption and the seconds shown.
  - Files: clipfinder/ClipLinkReader.kt + tests + fixtures, iosApp/iosApp/ClipFinder/ClipAudio.swift.

- [ ] **5. Hear and read the clip** (Mac build 3)
  - Build: `ClipTranscriber.swift`: Apple Speech with on-device recognition required, for
    link audio and for a shared video file (audio pulled with AVFoundation). Normalise
    loudness, then recognise 30 s chunks and add each chunk's offset (one request on a long
    file only returns the last sentence; seen on the Mac 2026-11-15). Apple Vision
    text recognition on about 1 frame per second of a shared file for burned-in captions.
    Merge into `ClipLine`s and pass to Kotlin. Add the Info.plist permission text. Check
    Apple's current docs for the newest on-device speech API before coding.
  - Done when: Clip finder shows the recognised lines for the test clips, and a shared
    video file still works in airplane mode.
  - Try it: airplane mode on, share a saved clip to Nuvio, read the lines.
  - Files: iosApp/iosApp/ClipFinder/ClipTranscriber.swift, Info.plist, clipfinder bridge file.

- [ ] **6. Find it and play it** (Mac build 4)
  - Build: `ShowGuesser` (caption + hashtags -> search -> top 3; "S2E5" hints first),
    `EpisodeSubtitleSource` (episode list, add-on subtitles 6 at a time, disk cache capped
    at 50 MB, early stop), wired to `ClipMatcher`. Candidates list on Clip finder. Tap ->
    normal streams screen -> player with `initialPositionMs` = moment minus 10 s, as an
    explicit start time (do not write fake watch progress). "From clip start / after the
    clip" switch.
  - Tests: guesser on sample captions; subtitle source with a fake add-on (cache, early stop).
  - Done when: SPEC checks 4, 5, 6 and 9 pass on Mo's test clips.
  - Try it: share a test link, tap the top candidate, pick a stream.
  - Files: clipfinder/ShowGuesser.kt, EpisodeSubtitleSource.kt, ClipFinderScreen.kt,
    streams/player hand-off (StreamLaunchStore.kt or StreamsScreen.kt), tests.
  - Wait for OK before starting (touches 3+ files).

- [ ] **7. Fallbacks, tuning, ship** (Mac build 5)
  - Build: type-the-show fallback (SPEC 7), clear failure messages (SPEC 8), 60 s stage
    limit with a message, tune matcher thresholds on Mo's real clips, add a Clip finder
    section to FORK.md.
  - Done when: every SPEC check passes on the phone.
  - Try it: one clip of each kind: named show, no caption, music only, movie.
  - Files: clipfinder/*, FORK.md.

- [ ] **8. Arabic** (after v1 ships; Mo wants it). Speech locale picked from the show's
  language or a setting; Arabic subtitles from OpenSubtitles; Arabic text normalising
  (diacritics, letter forms). Test clip: Love Is Blind: Habibi (on Mo's Mac).

## Later (parked, not v1)
- "Listen" mode: Nuvio records ~10 s of any app's sound through iOS screen broadcast. Works
  for every app and never breaks when a site changes, but takes more taps.
- Apple's on-device model to guess the show from the lines when the caption says nothing.
- A list of past clips. Android. Other languages. Mirrored caption reading.
- Fold the three older patches and this one into fewer, smaller patches.
