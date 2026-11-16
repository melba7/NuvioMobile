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

## Decisions (Mo, 2026-11-16, after the first phone test)
- The caption is the weak point. Nuvio uses every clue it can get on the phone: hashtags, the poster's name,
  the sound title and keywords of the page, text on the video, what was heard, and shows of earlier clips.
- Not used: Continue Watching, the library, watch progress (what TikTok shows Mo is not what he watches).
- Apple's on-device language model may suggest titles (iPhone 15 Pro Max, iOS 26, Apple Intelligence on). It
  runs on the phone, needs no key, and its suggestions count only if the subtitles match. Still no cloud AI.
- Nuvio remembers, on the phone only, the shows of earlier confident matches (id, name, how often, when) and
  which poster they came from: at most 100 shows and 300 posters. Never the clip, its sound or its words.

## Decisions (Mo, 2026-11-16, after 7a worked)
- Many clips are cut from a YouTube video, often not from a show (interviews, podcasts). Nuvio also looks for the
  full YouTube video and opens it in the YouTube app at the clip's moment. No account and no API key of ours: the
  YouTube page's own public key is read each time. A video counts only if its captions match what was heard.
- Instagram reels whose page has no video address: Nuvio tries the post's other pages; if none works and the
  caption names a show, it offers that show's page.
- Speed: first measure (a timings line in Details), then do work while the clip is listened to.

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
7. If the show can't be guessed (or the guess is wrong), the user can type the show name and the rest stays
   automatic. Check: a clip with an empty caption still reaches the right episode after typing the show, and
   the "Listening" step does not run a second time.
8. If nothing matches, the user is told why (no speech found, no subtitles found, no match) and
   nothing plays. Check: a music-only clip ends with "no speech found".
9. Works for movies as well as series. Check: one movie test clip finds its moment.
10. The show is found without an exact name in the caption. Checks (unit tests, and the first on the phone):
    the caption "The best part of Modern family.❤️❤️#edit #movieedit #modernfamily #fyp #viral" gives "Modern
    Family"; "#modernfamily" alone, "#ModernFamily", "modernfamilyclips" and the handle "suits.clips" find
    "Modern Family" / "Suits" from a list of known titles; a hashtag glued to an emoji is still read.
11. A missing caption never stops the search. Check: a shared video file with no caption ends with a found
    episode, or with the type-the-show box and a reason; never with "no caption".
12. Other clues are used. Checks: a title written on the video ("Made Up Show S2E5") gives the show and puts
    that episode first; "previously on <show>" heard in the clip gives the show; a spoken "season two episode
    five" puts that episode first; the page's sound title or keywords naming the show give the show.
13. Nuvio learns from earlier clips. Check: after one confident match, a second clip by the same poster with
    an empty caption finds the show, and Details says "this poster before"; a later clip naming that show in a
    hashtag lists it as "shared before".
14. With several possible shows, the one whose people are named in the clip is searched first. Check (unit
    test): two shows fit the caption equally; the names heard are in one show's subtitles; that show is
    searched first and the other is only sampled.
15. Apple's on-device model is a helper, never a requirement. Checks: on a phone without it, Details says why
    and the search carries on; a title it names is only shown if the subtitles match.
16. Details shows why a guess failed. Check: after any run the Details card lists the text read on screen, how
    many titles were known, every search phrase with its number of results, and each guess with its clue.
17. The full YouTube video is found and opened at the moment. Checks: (unit) a made-up clip that is in no show but
    in a YouTube video's captions ends "Done" and opens that video; a video whose captions do not match is never
    shown; with a confident episode the YouTube card is shown below it and nothing opens by itself; (phone) a clip
    of a YouTube interview opens the YouTube app within 10 s of the clip's moment.
18. Instagram reels work without a login where the site allows it. Checks: (unit) the video address is found in the
    embed page and in the post page's scripts at any level of escaping, never a `blob:` address; the caption has
    no "N likes, N comments - handle on date:" and no quote marks, and the handle is the author; (phone) Details
    lists each Instagram page tried with its size and whether a video key was in it.
19. A clip that cannot be heard still leads somewhere. Checks: (unit) no video address, or no speech, with a
    caption naming a show: the message offers the show and a tap opens its page; a typed name then only finds the
    show and nothing is listened to.
20. Details shows where the time went. Check: every run ends with a `Timings` line (seconds per stage, work done
    beside, total) and, after a search, a `Match` line with the numbers behind "sure".
21. Work is done while the clip is listened to. Checks: (unit) when the page names a show at score 90+, its
    subtitle files are fetched during listening and none is fetched twice; YouTube is asked during listening;
    (phone) Details shows `Fetched while listening`.

## Out of scope (v1)
- Android, iPad layout, desktop.
- Clips with no speech and no on-screen captions.
- Languages other than English. Arabic comes right after v1 (milestone 8).
- Any Claude or cloud AI call from the app. Any account login to TikTok, Instagram or YouTube. An API key of
  our own for any site.
- Saving or re-sharing the clip. Audio is analysed in memory and dropped. (The small memory of show names
  and poster handles of feature 13 is not a clip.)
- Song or theme recognition (ShazamKit). A "forget what you learned" button.

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
- A6. Reading YouTube's pages and captions without its app, like A2, is on paper against the site's terms. Only
  pages and caption text are read; nothing is stored but Nuvio's own subtitle cache. YouTube may change or block
  the route at any time; the episode search does not depend on it.
- Test clips: 3 TikToks from Mo (links kept out of this public repo). Answers so far: South
  Park S14E02; Suits (episode unknown); Love Is Blind: Habibi (Arabic). OPEN: a movie clip.
