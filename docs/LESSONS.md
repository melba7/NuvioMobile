# Lessons (one line each)
- Gradle cannot run in the cloud workspace (Google Maven blocked, no Android SDK): run `fork/check.sh` through the "Fork check" workflow on a pull request instead of retrying locally.
- Ktor `Url("https://")` parses with a non-blank host: check the text after `://` yourself when validating links.
- Review of milestone 2: start times need clustering (the earliest hit anywhere moves the start to a repeated phrase) and "confident" needs an absolute bar (share of the clip's triples, hits in the main cluster), not only a margin over the runner-up.
- A hit must be vouched for by a different triple from a different cue, or one repeated line validates itself.
- Without Kotlin or Gradle here, port the matcher to a throwaway Python script to check test numbers before pushing; one CI run costs 7 min.
- Compilations need every substantial cluster (4+ hits, 3+ cues), not a share-of-hits cut: a cut drops real segments and collapses confidence.
