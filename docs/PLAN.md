Done: 0 | Last cleanup: none

- [ ] 1. Skeleton: Share Extension appears in share sheet, opens Nuvio with the URL, shows it on a debug screen. Done when: CI build compiles and TestFlight build shows Nuvio in share sheet. Try: share a TikTok link.
- [ ] 2. Link metadata: fetch caption/hashtags/thumbnail from the link (public oEmbed); show them. Done when: shown for a TikTok and a reel.
- [ ] 3. Title guess: caption/hashtags -> candidate shows via Nuvio's existing metadata search; top 3 list.
- [ ] 4. Share a saved video file too; extract audio; on-device Speech transcript; OCR of burned-in captions from frames.
- [ ] 5. Moment match: fuzzy-match lines to episode subtitles (reuse subtitle sources); returns episode + timestamp + confidence; unit tests with sample lines.
- [ ] 6. Wire to playback: tap candidate -> stream list -> seek to the time.
- [ ] 7. Manual fallback + polish (background-music tolerance check on 3 real clips); ship via TestFlight.

## Later
- Link-only audio, other platforms.
