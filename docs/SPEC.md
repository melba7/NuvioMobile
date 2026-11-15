# Share-to-resume (Nuvio iPhone fork)

Goal: share a TikTok/Instagram clip to Nuvio from the iOS share sheet; Nuvio finds the show, episode and moment, and starts playback there.

## Decisions (Mo, 2026-11-15)
- Entry: Nuvio appears in the iOS share sheet; receives the link.
- No API key and no Claude usage in the app. Everything runs on the iPhone (Apple Vision OCR, Apple Speech) plus Nuvio's own metadata/subtitle sources. (Claude plan cannot be used by a third-party app.)
- Playback: Nuvio's normal stream list, seeking to the matched time.
- iPhone only. Clips with a little background music should still work (best effort).

## Features (each: pass/fail check)
1. The user can pick Nuvio in the share sheet on a TikTok/Instagram link. Check: Nuvio opens with the link.
2. The user sees up to 3 candidate shows/episodes with confidence. Check: a known test clip lists the right episode in the top 3.
3. The user taps a candidate and playback starts at the matched time (within ~5 s). Check: manual test on 3 known clips.
4. If nothing matches, the user can search manually and still set a start time.

## Out of scope (v1)
Silent or music-only clips; Android; downloading videos from the platforms by bypassing their rules.

## Open risks / assumptions
- A link alone gives caption, hashtags and thumbnail, not the video. Plan: caption/hashtags -> title guess; thumbnail OCR for burned-in subtitles; if still unsure, ask the user to share the saved video file, whose audio is transcribed on-device.
- Moment match = fuzzy-match the transcribed/OCR'd lines against the episode's subtitles (existing subtitle sources/autosync code, see docs/subtitle-autosync.md).
- Features ship as a patch (fork/nuvio-share-resume.patch) applied to the upstream tag; pushing it triggers TestFlight.
