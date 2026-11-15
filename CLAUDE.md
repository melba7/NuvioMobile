# Mo's Nuvio fork
Upstream Nuvio iOS release + patch files in `fork/`, built on GitHub and sent to TestFlight.
Current work: Clip finder (share a TikTok/Instagram clip, resume the episode at that moment).

## Commands
- Work tree: `fork/dev-tree.sh` (makes `../nuvio-work`); save changes: `fork/dev-tree.sh save`.
- Check: `fork/check.sh` (patches apply + deep link and clipfinder tests). Runs in the work tree:
  `./gradlew :composeApp:testAndroidHostTest --tests '<package>.*'`. Needs the Android SDK and
  Google Maven, so it only runs on GitHub ("Fork check" on pull requests), not in the cloud workspace.
- Mac build + TestFlight: happens by itself when `fork/` changes on `cmp-rewrite`. About 70 min.

## Always / never
- Never open or grep `fork/*.patch` (12k+ lines). Edit in the work tree, then save.
- Never edit upstream code in this repo outside `fork/`, `docs/`, `.claude/`, `.github/`,
  `CLAUDE.md`, `FORK.md`. It does not ship.
- New feature code goes in `features/clipfinder/` (Kotlin) and `iosApp/iosApp/ClipFinder/`,
  `iosApp/ShareExtension/` (Swift). Touch existing upstream files as little as possible.
- Logic goes in shared Kotlin with tests. Swift only for what needs Apple frameworks.
- Work on a branch and open a pull request. Merge to `cmp-rewrite` once per milestone, because
  every merge that touches `fork/` costs a 70 min Mac build.
- No Claude, no API keys, no cloud AI in the app. Never type, print or commit secrets.
- Test subtitles and transcripts are made up. Never commit real show subtitles or clips.
- tiktok.com and instagram.com are blocked in the cloud workspace: use saved sample
  responses for tests; live checks happen on the phone.
- Mo wants short, plain answers.

## Docs (open only the part you need)
- docs/SPEC.md: what Clip finder must do, with pass/fail checks.
- docs/ARCHITECTURE.md: how the fork ships, existing code to reuse, data flow, glossary.
- docs/PLAN.md: milestones. docs/LESSONS.md: past mistakes. FORK.md: TestFlight setup.

## Fork notes
- Original: NuvioMedia/NuvioMobile. Branch here: `cmp-rewrite`.
- Changed by Mo's fork: everything in `fork/`, `.github/workflows/`, `FORK.md`, `docs/`.
- Patches, in order: nuvio-public-gcm, nuvio-downloads, nuvio-downloads-2,
  nuvio-downloads-3, nuvio-share-resume (always last).

## WORKFLOW (tech-lead v3)
When I say "next":
1. Open docs/PLAN.md. If there's a Handoff note, resume it; otherwise take the next unchecked milestone. Only that one. If it's too big for one session, split it in PLAN.md and take the first part.
2. Search first. Read only the files and doc sections it needs.
3. State the plan and your assumptions in 3-5 lines. If it touches 3+ files, changes how data is stored, or the request can be read two ways, wait for my OK; otherwise go.
4. Build the simplest thing that works. Follow existing patterns. No extra features, nothing built "for later". Every changed line must trace to the milestone: remove only what your change made unused, and note other problems under "Later". Handle errors and bad input where data comes in (user input, network, files). Keep files under about 300 lines. Add a dependency only with a one-line reason, and check its current docs before using an API you're unsure of.
5. Test first: write a test for the milestone's main behavior, see it fail, then write the least code that passes. For purely visual changes, check a screenshot instead. Run the check command and fix causes, not symptoms. Never weaken, skip or delete a test to make it pass. No placeholders, TODOs or fake data in work marked done.
6. If it touches data, accounts, payments, or deletes anything: have a subagent review the diff against "done when" before committing. Fix correctness issues only.
7. Tick it, update the status line, log changed decisions in ARCHITECTURE.md. If something went wrong, took two tries, or I corrected you, add a one-line lesson to docs/LESSONS.md (or to CLAUDE.md if it applies to every session). Commit.
8. Reply in at most 6 lines: what changed in plain English, proof (command + last few lines of output), how I try it myself, what's next. Tell me to /clear.
9. If 5+ milestones are done since the last cleanup, suggest I say "cleanup".

When I say "next N" (a number): do N milestones in a row, each in a fresh subagent told to read CLAUDE.md and follow the steps above for one milestone. Give me one line per milestone. Stop early on a failed check, a question for me, or anything on the ask-before list.
When I say "add: [idea]": ask up to 5 questions with suggested answers (check the code before asking me), update SPEC.md, add milestones to PLAN.md. Don't build until I say "next".
When I say "bug: [what happened]": search docs/LESSONS.md, reproduce it, write a test that fails because of it, find the root cause with evidence before changing code (no guess-fixes), fix it, run the check command, add a lesson, commit. If it needs more than one session, make it a milestone.
When I say "cleanup": read .claude/skills/cleanup/SKILL.md and follow it.
When I say "status": answer in at most 5 lines from PLAN.md only (done count, next 3 milestones, anything waiting on me).

Always:
- Never say something is done unless the check command ran and passed in this session.
- Same fix failed twice, or the conversation is getting long: write a 3-line Handoff note at the top of PLAN.md (where you stopped, next step, open question), commit, and tell me to /clear and say "next".
- New idea mid-milestone: park it under "Later" and keep going.
- Ask before anything that's hard to undo or costs money: bulk deletes, changing the database structure, force-push or reset, deploying or publishing, paid services.
- Never commit secrets. Keys go in .env (gitignored). Never print them.
- In a fork: never reformat or remove original-project code; keep changes minimal so upstream updates merge cleanly.
