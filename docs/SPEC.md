# Clip finder: share a clip to Nuvio, resume at that moment

Goal: Mo shares a TikTok or Instagram clip of a show or movie to Nuvio from the iOS share sheet.
Nuvio works out the show, the episode and the moment, then plays the episode from there.

User: Mo, on iPhone, through his own TestFlight build of this fork.

## Decisions (Mo, 2026-11-15)
- Entry point is the iOS share sheet: share the **link**, pick Nuvio.
- The app never uses Claude or any paid AI. All recognition runs on the phone (Apple Speech and
  Apple Vision). A Claude plan cannot power an app; only a pay-per-use API key could, and we
  don't want one.
- Playback uses Nuvio's normal stream list, then jumps to the matched time.
- iPhone only. A little background music must not break it.

## Features
1. The user can pick Nuvio in the share sheet for a TikTok or Instagram link.
   Check: Nuvio opens on the Clip finder screen showing that link.
2. The user can also send Nuvio a saved video file (Photos, Files) as a backup route.
   Check: sharing a saved clip opens the same screen.
3. The user sees progress in plain words (Reading link, Listening, Searching episodes).
   Check: each stage appears and none hangs longer than 60 s without a message.
4. The user sees up to 3 candidates (show, season, episode, time, confidence).
   Check: for each of Mo's 3 test clips the right episode is the top candidate.
5. The user can tap a candidate, pick a stream as usual, and playback starts about 10 s before
   the matched moment. Check: on the 3 test clips the scene is on screen within 20 s of starting.
6. The user can choose "from clip start" or "after the clip" (default: after the clip).
   Check: both start points differ by the clip's length.
7. If the show can't be guessed, the user can type the show name and the rest stays automatic.
   Check: a clip with an empty caption still reaches the right episode after typing the show.
8. If nothing matches, the user is told why (no speech found, no subtitles found, no match) and
   nothing plays. Check: a music-only clip ends with "no speech found".
9. Works for movies as well as series. Check: one movie test clip finds its moment.

## Out of scope (v1)
- Android, iPad layout, desktop.
- Clips with no speech and no on-screen captions.
- Languages other than English. Arabic comes right after v1 (milestone 8).
- Any Claude or cloud AI call from the app. Any account login to TikTok or Instagram.
- Saving or re-sharing the clip. Audio is analysed in memory and dropped.

## Assumptions and open questions
- A1. A subtitle add-on is installed. Mo has OpenSubtitles v3 (confirmed 2026-11-15).
- A2. Reading the clip's audio straight from the link is possible but fragile and, on paper,
  against the platforms' terms (automated reading). Mo approved "link first" on 2026-11-15.
  If it breaks, features 1 to 9 still work through the saved video file.
- A3. Subtitle timing differs between releases by a few seconds, sometimes more. That is why
  playback starts 10 s early and the check in feature 5 is 20 s, not exact.
- A4. Clips are often sped up, cut or mirrored. The matcher ignores order and speed; mirrored
  burned-in captions are not read.
- A5. Opening the app from a share extension is not an official Apple feature. Fallback: the
  extension posts a notification that opens Nuvio when tapped.
- Test clips: 3 TikToks from Mo (links kept out of this public repo). Answers so far: South
  Park S14E02; Suits (episode unknown); Love Is Blind: Habibi (Arabic). OPEN: a movie clip.
