# Architecture (Mo's fork, Clip finder)

## How this fork ships
- The shipped app = upstream release named in `fork/UPSTREAM_TAG` + the patch files in `fork/`,
  applied in the order listed in `PATCHES` in `fork/build_from_source.py`.
- Code outside `fork/`, `docs/`, `.claude/` and `.github/` is upstream's and is NOT what ships.
- Pushing a change under `fork/` to `cmp-rewrite` starts the TestFlight workflow (about 70 min
  on a GitHub Mac, then Apple's processing). See FORK.md.
- Clip finder lives in its own patch: `fork/nuvio-share-resume.patch`, applied last.

## Stack
Kotlin Multiplatform + Compose (shared app code), Swift (iOS shell and extensions), Python
(build and signing scripts), GitHub Actions.

## Folder map (paths inside the work tree, i.e. upstream + patches)
- `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/` : new. Matcher, show
  guesser, subtitle source, link reader, Clip finder screen. No iOS-only code here.
- `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/` : new. Unit tests.
- `iosApp/ShareExtension/` : new target. Receives the link, forwards it to the app.
- `iosApp/iosApp/ClipFinder/` : new. Swift for audio capture, speech-to-text, OCR.
- `fork/` : patches, build scripts, `dev-tree.sh`, `check.sh` (both made in milestone 1).

## Existing code to reuse (found 2026-11-15, do not re-search)
- Deep links: `core/deeplink/AppUrlBridge.kt` (`AppDeepLink`, `parseAppDeepLink`, scheme
  `nuvio://`), consumed in `MainAppContent.kt` (`is AppDeepLink.Meta`). Swift entry:
  `iosApp/iosApp/iOSApp.swift` `.onOpenURL` -> `AppUrlBridgeKt.handleAppUrl`.
- Subtitles: `features/player/AddonSubtitleLoader.kt` (`loadAddonSubtitles(type, videoId)`),
  `features/player/PlayerSubtitleCueParser.kt` (SRT, VTT, ASS, TTML -> cues with times).
- Search: `features/search/SearchRepository.kt`. Episode lists: `features/details`.
- Player start time: `features/player/PlayerScreenArgs.kt` `initialPositionMs`. Stream
  launch: `features/streams/StreamLaunchStore.kt`, `StreamsScreen.kt`.
- Extension precedent: `iosApp/DownloadsWidgetExtension` (how a second target is declared).
- Signing: `fork/nuvio_testflight.py` registers bundle IDs and profiles per target and stops on
  any extension it doesn't know (`sign_and_package`). A new extension needs an entry there.

## Data flow
1. Share extension gets the link -> opens `nuvio://clip?url=<encoded link>` (no shared storage,
   so no App Group to set up). Saved video files arrive through "Open in Nuvio" (document
   type on the main app), also no extension storage.
2. `ClipLinkReader` (Kotlin): caption, hashtags, author, thumbnail from the platform's public
   page metadata (TikTok's public oEmbed no longer returns caption or author, checked
   2026-11-15). Short links are followed first.
3. `ClipAudio` (Swift): audio for up to 6 min (clips are often 5-6 min), from the link's embed player or from the shared
   file. Held in memory only.
4. `ClipTranscriber` (Swift): normalise loudness, split into 30 s chunks, Apple Speech
   (on-device only) per chunk with time offsets added -> lines with clip times. Apple
   Vision reads burned-in captions from about 1 frame per second. Both lists go to Kotlin.
5. `ShowGuesser` (Kotlin): caption words and hashtags -> Nuvio search -> up to 3 shows. A
   "S2E5"-style hint in the caption is tried first.
6. `EpisodeSubtitleSource` (Kotlin): for a show, fetches one subtitle per episode through the
   installed subtitle add-ons, 6 at a time, cached on disk (cap 50 MB), stops early on a
   decisive match.
7. `ClipMatcher` (Kotlin, pure): finds where the transcript's word triples cluster in an
   episode's cues. Returns episode, start, end, confidence. A guessed show is only accepted
   if its subtitles actually match, so wrong guesses fall away by themselves.
8. Clip finder screen lists candidates -> normal streams screen -> player with
   `initialPositionMs` = matched time minus 10 s.

## Data model (in memory unless noted)
- `ClipRequest(link | fileUrl)`; `ClipInfo(caption, hashtags, author, thumbnailUrl)`
- `ClipLine(text, startMs, endMs, source = speech | ocr)`
- `ClipCandidate(metaId, type, season, episode, startMs, endMs, confidence)`
- Disk: subtitle cache only (`clipfinder-subs/<metaId>/<videoId>.txt`). No clip is ever stored.

## Decisions log
- 2026-11-15 | On-device recognition, no API key, no Claude at runtime | Mo's usage and privacy.
- 2026-11-15 | Own patch file, applied last | keeps the feature isolated; upstream bumps easier.
- 2026-11-15 | Link passed by URL scheme, not an App Group | App Groups can't be created by the
  signing script's API key; this avoids manual Apple portal setup.
- 2026-11-15 | Matching logic in shared Kotlin with tests | tests run on Linux in about 10 min
  instead of a 70 min Mac build.
- 2026-11-15 | English first; Arabic is the first milestone after v1 | Mo. Keep the matcher
  language-neutral (Unicode-aware normalising, no English-only word lists baked in).
- 2026-11-15 | Start 10 s early | subtitle timing differs between releases.
- 2026-11-15 | Read clip audio from the link first, saved video as backup | Mo's choice; one tap.

## Known problems
- Mac test 2026-11-15 (3 real clips): one Speech request on a long file returns only the last
  utterance; 30 s chunks fixed it. A clip at -33 dB needed loudness normalisation. Background
  music cost some words but left plenty to match. Arabic clip: en-US found nothing.
- No Mac in the cloud: Swift code can only be compiled by the TestFlight workflow (70 min).
- tiktok.com and instagram.com are blocked from the cloud workspace; link reading is tested
  with saved sample responses, and live on the phone.
- The patch files are huge (12k+ lines). Never open them; work in the work tree.

## Glossary
- Clip: the TikTok/Instagram video Mo shares. Clip finder: this feature and its screen.
- Line: a piece of recognised speech or caption text with its time in the clip.
- Cue: one subtitle entry with its time in the episode.
- Candidate: a possible answer (episode + moment + confidence). Moment: the matched time.
- Work tree: upstream at the tag with all patches applied; where code is edited.
- Fast check: `fork/check.sh` and the "Fork check" workflow. Mac build: the TestFlight workflow.
