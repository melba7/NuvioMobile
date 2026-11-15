# Mo's Nuvio fork

This fork builds the official Nuvio iOS release named in `fork/UPSTREAM_TAG`, with four patches,
and uploads it to TestFlight:

- `fork/nuvio-public-gcm.patch`: replaces Nuvio's use of Apple's private AES-GCM functions, which
  makes Apple reject the upload (ITMS-90338), with an AES-GCM built on public CommonCrypto calls.
- `fork/nuvio-downloads.patch`: Netflix-style downloads (download button on every episode and
  movie, Download season, Smart Downloads, Wi-Fi only, background downloads, storage summary
  and Delete all).
- `fork/nuvio-downloads-2.patch`: change the source or quality of a download, a Download quality
  setting, many downloads at once, a Live Activity that starts with any download and keeps
  moving, downloads that continue with the app closed (background refresh), the download-mode
  stream list sorted by size, Pause all / Resume all.
- `fork/nuvio-downloads-3.patch`: uncached debrid streams (links that only play a "Downloading to
  Provider" placeholder video) are left out of the download source list and never auto-picked.

The rest of this branch is upstream's code and is not used by the build.

## How it runs

- **TestFlight** (`.github/workflows/testflight.yml`): on every push that changes `fork/`, and
  from the Actions tab. A GitHub Mac clones the tagged release, applies the patches, builds,
  signs with the App Store Connect API key and uploads. Builds land in TestFlight about 1-2
  hours after the push (build plus Apple's processing).
- **Upstream check** (`.github/workflows/upstream-check.yml`): every night. When Nuvio publishes
  a newer iOS release and the patches still apply, it moves `fork/UPSTREAM_TAG` and starts the
  TestFlight build. When they don't apply, it opens an issue (or, with Issues off, fails with
  the reason, which GitHub emails you).

## One-time setup

1. **Turn on Actions**: Actions tab, then "I understand my workflows, go ahead and enable them".
2. **Turn on Issues** (optional): Settings, General, Features, tick Issues.
3. **Add repository secrets** (Settings, Secrets and variables, Actions, New repository secret):
   - `ASC_KEY_ID`: the 10-character key ID (the same key the Mac script uses).
   - `ASC_ISSUER_ID`: the Issuer ID from App Store Connect, Users and Access, Integrations.
   - `ASC_KEY_P8`: the whole text of the `AuthKey_XXXXXXXXXX.p8` file. On the Mac:
     `cat ~/Downloads/Nuvio-TestFlight/state/AuthKey_*.p8 | pbcopy`, then paste.
   - `NUVIO_SIGNING` (recommended): the Mac script's distribution certificate, so cloud builds
     reuse it. On the Mac, after one successful run of the Mac script:
     `cd ~/Downloads/Nuvio-TestFlight/state && tar -cz dist.json dist.key dist.cer | base64 | pbcopy`,
     then paste. Without it each build makes a temporary certificate and revokes it at the end
     (Apple may email you about each revocation).
4. Actions tab, **TestFlight**, **Run workflow**.

If a build fails, the run's summary shows the last lines and the `build-log` artifact has the
full log.
