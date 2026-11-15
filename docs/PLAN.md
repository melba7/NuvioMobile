Done: 2 | Last cleanup: none | Mac builds used: 0 of about 5 (PR #1 merged; milestone 3 built on branch clip-finder-share, awaiting the Mac build and phone check)
Milestone 3 is a draft pull request; merging it to cmp-rewrite starts the Mac build, so merge only after the branch test build passes on the phone.

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
  - Built in `features/clipfinder/`: `ClipText.normalize` (lowercase, Unicode letters and digits;
    drops [music]/(laughs), speaker labels, leading dashes/notes; joins "2 00 8"). `ClipMatcher.match`
    counts distinct word triples shared with each episode. A hit needs a different hit from a
    different cue within 45 s; hits form time clusters (gap 60 s); clusters with at least 25% of
    the hits form the span. Confident = 4+ hits in the main cluster, 15%+ of the clip's triples,
    and 2x the runner-up. Order and speed do not matter.
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
    tapping it opens Clip finder with the link; a saved video shared from the Files app ("Open in Nuvio") does the same (Photos needs an App Group; later).
  - Try it: open a TikTok, Share, Nuvio.
  - Files: iosApp.xcodeproj/project.pbxproj, iosApp/ShareExtension/*, iosApp/iosApp/Info.plist,
    clipfinder/ClipFinderScreen.kt, MainAppContent.kt, fork/nuvio_testflight.py.
  - Wait for OK before starting (touches 3+ files and signing).

### Milestone 3 implementation notes (written 2026-11-15)
Checked against the work tree (upstream 0.6.12-beta + patches). Paths are inside `../nuvio-work` unless they
start with `fork/` or `docs/`. Copy the code below exactly: Swift and Xcode files only compile in the Mac build.

Facts found (do not re-search):
- The project uses Xcode 16 synchronized folders (`PBXFileSystemSynchronizedRootGroup`): every file in a
  target's folder is compiled by itself. Swift files need NO pbxproj entry; only the new target does.
- CI runs `xcodebuild -scheme iosApp -configuration Release build` with signing off
  (`scripts/build-ios-ipa.sh`), zips `Nuvio.app`, then `fork/nuvio_testflight.py` renames bundle IDs and signs.
  The scheme only names `iosApp`; the extension is built because `iosApp` depends on it.
- Extension targets set `APPLICATION_EXTENSION_API_ONLY = YES`, so `UIApplication.open` cannot be named in
  extension code. The Swift below calls it through the Objective-C runtime instead.
- `OrientationLockAppDelegate` already opens `userInfo["deeplink"]` when a notification is tapped. The
  fallback notification uses that key, so the main app needs no Swift change at all.
- Opening the app: primary = walk the responder chain to `UIApplication`, call
  `openURL:options:completionHandler:`. Fallback (refused, not found, or no answer in 2 s) = local notification.
- No App Group, no capabilities: the App Store Connect key registers the bundle ID and profile by itself.

Steps
1. Kotlin test first. Add to `composeApp/src/commonTest/kotlin/com/nuvio/app/core/deeplink/AppUrlBridgeTest.kt`:
   ```kotlin
   @Test
   fun `parses a shared video file`() {
       val file = "file:///private/var/mobile/Containers/Shared/AppGroup/ABC/File%20Provider%20Storage/My%20clip.MOV"
       assertEquals(AppDeepLink.ClipFile(file), parseAppDeepLink(file))
       assertNull(parseAppDeepLink("file:///"))
       assertNull(parseAppDeepLink("file:///private/var/folder/"))
       assertNull(parseAppDeepLink("file://host/share/clip.mp4"))
       assertNull(parseAppDeepLink("file:///" + "a".repeat(2048) + ".mp4"))
   }
   ```
   New `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipFinderScreenTest.kt` (package
   `com.nuvio.app.features.clipfinder`, imports `kotlin.test.Test`, `kotlin.test.assertEquals`):
   ```kotlin
   class ClipFinderScreenTest {
       @Test
       fun `shows a link as it is and a file by its name`() {
           assertEquals("https://vm.tiktok.com/ZM8abc/", clipSourceLabel("https://vm.tiktok.com/ZM8abc/"))
           assertEquals("My clip.MOV", clipSourceLabel("file:///private/var/x/My%20clip.MOV"))
       }
       @Test
       fun `stage names are the three planned steps`() =
           assertEquals(listOf("Reading link", "Listening", "Searching episodes"), CLIP_FINDER_STAGES)
   }
   ```
2. `core/deeplink/AppUrlBridge.kt` (the parser takes the file URL directly; iOSApp.swift stays untouched):
   - in `sealed interface AppDeepLink`, after `Clip`: `data class ClipFile(val fileUrl: String) : AppDeepLink`
   - first line of `parseAppDeepLink`: `clipFileDeepLink(url)?.let { return it }`
   - after `clipDeepLink`:
   ```kotlin
   private fun clipFileDeepLink(url: String): AppDeepLink.ClipFile? {
       if (!url.startsWith("file:///", ignoreCase = true) || url.length > CLIP_URL_MAX_LENGTH) return null
       val name = url.substringBefore('?').substringBefore('#').substringAfterLast('/')
       return if (name.isBlank()) null else AppDeepLink.ClipFile(url)
   }
   ```
3. New `composeApp/src/commonMain/kotlin/com/nuvio/app/navigation/ClipFinderRoute.kt` (own file, same package
   as the sealed `AppRoute`, so `Routes.kt` is not touched):
   ```kotlin
   package com.nuvio.app.navigation

   import kotlinx.serialization.Serializable

   /** [source] is the shared web link, or the file:// address of a shared video. */
   @Serializable
   data class ClipFinderRoute(val source: String, override val title: String = "") : AppRoute
   ```
   `AppNavigationSupport.kt`: after the `PartyRoute` line add
   `subclass(ClipFinderRoute::class, ClipFinderRoute.serializer())`.
4. New `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderScreen.kt`. English text is
   hard-coded on purpose (no edits to upstream's 27 string files). No `stickyHeader`, plain `item`s:
   ```kotlin
   package com.nuvio.app.features.clipfinder

   import androidx.compose.material3.MaterialTheme
   import androidx.compose.material3.Text
   import androidx.compose.runtime.Composable
   import com.nuvio.app.core.ui.NuvioScreen
   import com.nuvio.app.core.ui.NuvioScreenHeader
   import com.nuvio.app.core.ui.NuvioSectionLabel
   import com.nuvio.app.core.ui.NuvioSurfaceCard
   import com.nuvio.app.core.ui.nuvio
   import io.ktor.http.decodeURLPart

   internal const val CLIP_FINDER_TITLE = "Clip finder"
   internal val CLIP_FINDER_STAGES = listOf("Reading link", "Listening", "Searching episodes")

   private fun isClipFile(source: String) = source.startsWith("file://", ignoreCase = true)

   /** The text shown for a shared clip: a web link as it is, a shared video by its file name. */
   internal fun clipSourceLabel(source: String): String {
       if (!isClipFile(source)) return source
       val name = source.substringBefore('?').substringBefore('#').substringAfterLast('/')
       return runCatching { name.decodeURLPart() }.getOrDefault(name)
   }

   @Composable
   fun ClipFinderScreen(source: String, onBack: () -> Unit) {
       val colors = MaterialTheme.nuvio.colors
       NuvioScreen {
           item { NuvioScreenHeader(title = CLIP_FINDER_TITLE, onBack = onBack) }
           item {
               NuvioSurfaceCard {
                   NuvioSectionLabel(if (isClipFile(source)) "Shared video" else "Shared link")
                   Text(clipSourceLabel(source), style = MaterialTheme.typography.bodyMedium, color = colors.textPrimary)
               }
           }
           item {
               NuvioSurfaceCard {
                   NuvioSectionLabel("Steps (coming in the next update)")
                   CLIP_FINDER_STAGES.forEachIndexed { index, stage ->
                       Text("${index + 1}. $stage", style = MaterialTheme.typography.bodyMedium, color = colors.textMuted)
                   }
               }
           }
       }
   }
   ```
5. `MainAppContent.kt` (three small edits):
   - imports, next to the other `features` imports: `import com.nuvio.app.features.clipfinder.CLIP_FINDER_TITLE`
     and `import com.nuvio.app.features.clipfinder.ClipFinderScreen` (`navigation.*` is already imported).
   - replace the line `is AppDeepLink.Clip -> AppDeepLinkRepository.markConsumed(deepLink)` with
   ```kotlin
                       is AppDeepLink.Clip, is AppDeepLink.ClipFile -> {
                           appGateController?.appReady?.first { it }
                           activateTab(AppScreenTab.Home)
                           val source = if (deepLink is AppDeepLink.ClipFile) deepLink.fileUrl else (deepLink as AppDeepLink.Clip).url
                           navController.navigate(ClipFinderRoute(source = source, title = CLIP_FINDER_TITLE)) {
                               launchSingleTop = true
                           }
                           AppDeepLinkRepository.markConsumed(deepLink)
                       }
   ```
   - directly before `entry<PartyRoute> { route ->` add (same helper Party uses; it supplies the back action):
   ```kotlin
                   entry<ClipFinderRoute> { route ->
                       SettingsDestination(route, navController) { onBack ->
                           ClipFinderScreen(source = route.source, onBack = onBack)
                       }
                   }
   ```
6. `iosApp/iosApp/Info.plist`: add before the final `</dict>` (tabs like the rest of the file). In-place = no copy
   of the video is stored. Note for milestone 5: reading such a file needs
   `startAccessingSecurityScopedResource()` on the `URL` object given to `.onOpenURL`, not on a rebuilt string.
   ```xml
   	<key>CFBundleDocumentTypes</key>
   	<array><dict>
   		<key>CFBundleTypeName</key><string>Video</string>
   		<key>CFBundleTypeRole</key><string>Viewer</string>
   		<key>LSHandlerRank</key><string>Alternate</string>
   		<key>LSItemContentTypes</key>
   		<array><string>public.movie</string><string>public.mpeg-4</string><string>com.apple.quicktime-movie</string></array>
   	</dict></array>
   	<key>LSSupportsOpeningDocumentsInPlace</key><true/>
   ```
7. `iosApp/ShareExtension/Info.plist`: `cp iosApp/DownloadsWidgetExtension/Info.plist iosApp/ShareExtension/Info.plist`,
   then change `<string>Downloads</string>` to `<string>Nuvio</string>` and replace the whole `NSExtension` dict with:
   ```xml
   	<key>NSExtension</key>
   	<dict>
   		<key>NSExtensionAttributes</key>
   		<dict><key>NSExtensionActivationRule</key><dict>
   			<key>NSExtensionActivationSupportsWebURLWithMaxCount</key><integer>1</integer>
   			<key>NSExtensionActivationSupportsText</key><true/>
   		</dict></dict>
   		<key>NSExtensionPointIdentifier</key><string>com.apple.share-services</string>
   		<key>NSExtensionPrincipalClass</key><string>ShareViewController</string>
   	</dict>
   ```
   No storyboard. The class name works unprefixed because of `@objc(ShareViewController)` below.
8. `iosApp/ShareExtension/ShareViewController.swift` (the only other file in that folder; exact text):
   ```swift
   import UIKit
   import UserNotifications

   private typealias OpenURLFunction = @convention(c) (AnyObject, Selector, NSURL, NSDictionary, AnyObject?) -> Void

   private final class SharedText: @unchecked Sendable {
       private let lock = NSLock()
       private var values: [String] = []
       func add(_ value: String) { lock.lock(); values.append(value); lock.unlock() }
       func all() -> [String] { lock.lock(); defer { lock.unlock() }; return values }
   }

   @objc(ShareViewController)
   final class ShareViewController: UIViewController {
       private var started = false
       private var openAnswered = false
       private var target: URL?

       override func viewDidLoad() {
           super.viewDidLoad()
           view.backgroundColor = .clear
       }

       override func viewDidAppear(_ animated: Bool) {
           super.viewDidAppear(animated)
           guard !started else { return }
           started = true
           collectText { [weak self] texts in
               guard let self = self else { return }
               guard let link = texts.compactMap({ ShareViewController.firstWebLink(in: $0) }).first,
                     let url = ShareViewController.clipURL(for: link) else {
                   self.finish(message: "Nuvio found no link in what you shared.")
                   return
               }
               self.target = url
               self.openNuvio(url)
           }
       }

       private func collectText(_ done: @escaping ([String]) -> Void) {
           let found = SharedText()
           let group = DispatchGroup()
           for item in (extensionContext?.inputItems ?? []).compactMap({ $0 as? NSExtensionItem }) {
               if let text = item.attributedContentText?.string { found.add(text) }
               for provider in item.attachments ?? [] {
                   for type in ["public.url", "public.plain-text"] where provider.hasItemConformingToTypeIdentifier(type) {
                       group.enter()
                       provider.loadItem(forTypeIdentifier: type, options: nil) { value, _ in
                           if let url = value as? URL { found.add(url.absoluteString) }
                           else if let text = value as? String { found.add(text) }
                           group.leave()
                       }
                   }
               }
           }
           group.notify(queue: .main) { done(found.all()) }
       }

       private static func firstWebLink(in text: String) -> String? {
           guard let detector = try? NSDataDetector(types: NSTextCheckingResult.CheckingType.link.rawValue) else { return nil }
           let matches = detector.matches(in: text, options: [], range: NSRange(location: 0, length: (text as NSString).length))
           for match in matches {
               if let url = match.url, let scheme = url.scheme?.lowercased(), scheme == "http" || scheme == "https" {
                   return url.absoluteString
               }
           }
           return nil
       }

       private static func clipURL(for link: String) -> URL? {
           var allowed = CharacterSet.alphanumerics
           allowed.insert(charactersIn: "-._~")
           guard let encoded = link.addingPercentEncoding(withAllowedCharacters: allowed) else { return nil }
           return URL(string: "nuvio://clip?url=" + encoded)
       }

       private func openNuvio(_ url: URL) {
           let selector = NSSelectorFromString("openURL:options:completionHandler:")
           var responder: UIResponder? = self
           while let current = responder {
               if let appClass = NSClassFromString("UIApplication"), current.isKind(of: appClass),
                  current.responds(to: selector), let implementation = current.method(for: selector) {
                   let callback: @convention(block) (Bool) -> Void = { [weak self] opened in
                       DispatchQueue.main.async { self?.openEnded(opened) }
                   }
                   let function = unsafeBitCast(implementation, to: OpenURLFunction.self)
                   function(current, selector, url as NSURL, NSDictionary(), unsafeBitCast(callback, to: AnyObject.self))
                   perform(#selector(openTimedOut), with: nil, afterDelay: 2)
                   return
               }
               responder = current.next
           }
           openEnded(false)
       }

       @objc private func openTimedOut() { openEnded(false) }

       private func openEnded(_ opened: Bool) {
           guard !openAnswered else { return }
           openAnswered = true
           if opened { finish(message: nil); return }
           UNUserNotificationCenter.current().requestAuthorization(options: [.alert]) { granted, _ in
               DispatchQueue.main.async { self.postNotification(allowed: granted) }
           }
       }

       private func postNotification(allowed: Bool) {
           let failure = "Nuvio could not be opened. Open Nuvio, allow its notifications in Settings, then share again."
           guard allowed, let target = target else { finish(message: failure); return }
           let content = UNMutableNotificationContent()
           content.title = "Nuvio"
           content.body = "Tap to find this clip."
           content.userInfo = ["deeplink": target.absoluteString]
           let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 1, repeats: false)
           let request = UNNotificationRequest(identifier: "nuvio-clip", content: content, trigger: trigger)
           UNUserNotificationCenter.current().add(request) { error in
               let message: String? = error == nil ? nil : failure
               DispatchQueue.main.async { self.finish(message: message) }
           }
       }

       private func finish(message: String?) {
           guard let message = message else {
               extensionContext?.completeRequest(returningItems: nil, completionHandler: nil)
               return
           }
           let alert = UIAlertController(title: "Nuvio", message: message, preferredStyle: .alert)
           alert.addAction(UIAlertAction(title: "OK", style: .default) { [weak self] _ in self?.finish(message: nil) })
           present(alert, animated: true)
       }
   }
   ```
9. Add the target to `iosApp/iosApp.xcodeproj/project.pbxproj` with this script (tested on this exact file: 13 new
   objects, only added lines). It copies every DownloadsWidgetExtension object under a new ID (`...A4xx` becomes
   `...A5xx`, name becomes ShareExtension) and adds the new product to the existing "Embed App Extensions" phase,
   so target, phases, proxy, dependency, configs (bundle IDs `com.nuvio.media.ShareExtension` /
   `com.nuvio.app.ShareExtension`, iOS 16.1, `INFOPLIST_FILE = ShareExtension/Info.plist`) match the widget.
   Save it outside the repo as `/tmp/add_share_target.py`, run once: `python3 /tmp/add_share_target.py <pbxproj>`.
   ```python
   import re, sys
   path = sys.argv[1]
   OLD, NEW, EMBED = "0A1B2C3D4E5F60718293A4", "0A1B2C3D4E5F60718293A5", "0A1B2C3D4E5F60718293A4BC"
   src = open(path, encoding="utf-8").read()
   assert NEW not in src and "ShareExtension" not in src, "already added"
   clone = lambda s: s.replace(OLD, NEW).replace("DownloadsWidgetExtension", "ShareExtension")
   out, block, own, attr = [], None, False, None
   for line in src.split("\n"):
       if block is None:
           m = re.match(r"\t\t([0-9A-F]{24}) ", line)
           if m and line.endswith("{"):            # a multi-line object starts
               block, own = [line], m.group(1).startswith(OLD) and m.group(1) != EMBED
           elif m and m.group(1).startswith(OLD):  # a one-line widget object
               out += [line, clone(line)]
           else:
               out.append(line)
           continue
       if attr is not None:                        # the widget's 3-line TargetAttributes entry
           attr.append(line)
           if line.strip() == "};":
               block += attr + [clone(l) for l in attr]
               attr = None
           continue
       if not own and re.match(r"\t{3,}%s[0-9A-F]{2} = \{$" % OLD, line):
           attr = [line]
           continue
       block.append(line)
       if not own and EMBED not in line and re.match(r"\t{3,}%s[0-9A-F]{2} /\* .* \*/,$" % OLD, line):
           block.append(clone(line))               # a shared object's reference to a widget object
       if line == "\t\t};":
           out += block + ([clone(l) for l in block] if own else [])
           block = None
   assert block is None and attr is None
   open(path, "w", encoding="utf-8").write("\n".join(out))
   ```
10. `fork/nuvio_testflight.py` (the API key registers the ID and profile unattended, as for the widget):
    - after `WIDGET_SUFFIX = ...`: `SHARE_SUFFIX = ".ShareExtension"`
    - after `widget_id = ...`: `share_id = bundle_id + SHARE_SUFFIX`
    - after `widget_bid = ...`: `share_bid = ensure_bundle_id(asc, share_id, "Nuvio Share Extension")`
    - after the `widget_prof = make_profile(...)` statement:
      `share_prof = make_profile(asc, "Nuvio TestFlight Share", share_bid, cert["cert_id"], os.path.join(prof_dir, "share.mobileprovision"))`
    - after `widget_ents = ...`: `share_ents = os.path.join(prof_dir, "share.entitlements")`
    - after `entitlements_from_profile(widget_prof, widget_id, widget_ents)`:
      `entitlements_from_profile(share_prof, share_id, share_ents)`
    - in `sign_and_package`, between the widget `if` and the `else`:
      `elif os.path.basename(ext) == "ShareExtension.appex":` / `ext_profiles[ext] = (share_prof, share_ents)`;
      change the die text to end `this script only knows the downloads widget and the share extension.`
    `prepare_bundle` needs no change (it renames to `<app id>.ShareExtension` already).
    `fork/build_from_source.py`: add below `verify_no_private_gcm` and call it right after that call in `main`:
    ```python
    def verify_share_extension(ipa):
        with zipfile.ZipFile(ipa) as z:
            names = z.namelist()
        if not any(re.fullmatch(r"Payload/[^/]+\.app/PlugIns/ShareExtension\.appex/Info\.plist", n) for n in names):
            die("the build has no ShareExtension.appex; check the ShareExtension target in project.pbxproj.")
    ```
11. Pre-flight before pushing (all must pass; run from the repo root):
    ```bash
    W=../nuvio-work
    python3 - $W/iosApp/iosApp/Info.plist $W/iosApp/ShareExtension/Info.plist $W/iosApp/DownloadsWidgetExtension/Info.plist <<'PY'
    import plistlib, sys
    app, share, widget = (plistlib.load(open(p, "rb")) for p in sys.argv[1:])
    assert app["CFBundleDocumentTypes"][0]["LSItemContentTypes"][0] == "public.movie" and app["LSSupportsOpeningDocumentsInPlace"] is True
    assert "nuvio" in app["CFBundleURLTypes"][0]["CFBundleURLSchemes"]
    ext = share["NSExtension"]
    assert ext["NSExtensionPointIdentifier"] == "com.apple.share-services" and ext["NSExtensionPrincipalClass"] == "ShareViewController"
    assert ext["NSExtensionAttributes"]["NSExtensionActivationRule"] == {"NSExtensionActivationSupportsWebURLWithMaxCount": 1, "NSExtensionActivationSupportsText": True}
    assert share["CFBundleDisplayName"] == "Nuvio" and {k: v for k, v in share.items() if k not in ("NSExtension", "CFBundleDisplayName")} == {k: v for k, v in widget.items() if k not in ("NSExtension", "CFBundleDisplayName")}
    print("plists OK")
    PY
    python3 - $W/iosApp/iosApp.xcodeproj/project.pbxproj <<'PY'
    import re, sys
    s = open(sys.argv[1], encoding="utf-8").read()
    defs = re.findall(r"^\t\t([0-9A-F]{24}) (?:/\* .*? \*/ )?= \{", s, re.M)
    assert len(defs) == len(set(defs)), "an object is defined twice"
    missing = set(re.findall(r"\b[0-9A-F]{24}\b", s)) - set(defs)
    assert not missing, "referenced but not defined: %s" % missing
    assert s.count("{") == s.count("}") and s.count("(") == s.count(")"), "unbalanced brackets"
    assert len([d for d in defs if d.startswith("0A1B2C3D4E5F60718293A5")]) == 13, "expected 13 new objects"
    for needle, n in (("ShareExtension.appex in Embed App Extensions */,", 1), ("/* ShareExtension */,", 3),
                      ("/* ShareExtension.appex */,", 1), ("0A1B2C3D4E5F60718293A5C2 /* PBXTargetDependency */,", 1),
                      ("INFOPLIST_FILE = ShareExtension/Info.plist;", 2), ("0A1B2C3D4E5F60718293A5B8 = {", 1),
                      ("PRODUCT_BUNDLE_IDENTIFIER = com.nuvio.media.ShareExtension;", 1), ("/* Embed App Extensions */,", 1)):
        assert s.count(needle) == n, "%r: %d times, expected %d" % (needle, s.count(needle), n)
    print("pbxproj OK")
    PY
    git -C $W diff --stat fork-baseline -- iosApp/iosApp.xcodeproj | tail -1   # expect: 1 file changed, 137 insertions(+)
    ls $W/iosApp/ShareExtension                                       # exactly: Info.plist ShareViewController.swift
    git -C $W status --short iosApp/iosApp/iOSApp.swift                # prints nothing (untouched)
    python3 -m py_compile fork/nuvio_testflight.py fork/build_from_source.py && fork/dev-tree.sh save
    ```
    Then push the branch and open the pull request: "Fork check" compiles the Kotlin (screen, route, parser) and
    runs the new tests. Gradle cannot run in the cloud workspace, so that is the Kotlin proof.
12. Mac test build from the branch, before merging (uses 1 of the Mac builds, uploads to TestFlight; Mo is fine
    with that): after Fork check is green, `gh workflow run TestFlight --ref clip-finder-share`. The workflow
    checks out the ref it is started on (default branch is `cmp-rewrite`, so branch runs are allowed). Green and
    phone checks pass: merge. Skip a second build only if nothing under `fork/` changed since.

Deviations when built (2026-11-15)
- Step 3: `AppNavigationSupport.kt` is at `com/nuvio/app/`, not `navigation/`; the `subclass(ClipFinderRoute...)` line went there.
- Step 11: `fork/check.sh` stops at Gradle here (Google Maven blocked); it still showed the patches apply. Kotlin proof = "Fork check" on the PR.

What each check proves
- Fork check (Linux): patch applies, Kotlin compiles, parser + label tests. Nothing about Swift, plists, Xcode.
- Mac build only: pbxproj loads, ShareViewController.swift compiles, appex is embedded, signing, upload.
  Swift errors show within the first minutes of xcodebuild as `error:` lines near `ShareExtension` in
  `fork/state/build.log` (kept as the `build-log` artifact on failure).
- Phone only: share sheet lists Nuvio, the app opens, the notification fallback, saved videos.

ASSUMPTIONS (cannot be checked from here)
- A1 Responder chain still reaches `UIApplication` and iOS 26/27 honours the open. If not, no build error: the
  phone shows the "Nuvio / Tap to find this clip" notification about 2 s after sharing. Still passes "done when".
- A2 A notification posted by the extension counts as Nuvio's and its tap reaches the app delegate. If A1 and A2
  both fail the phone shows the "could not be opened" alert: next step is an App Group hand-off (needs Mo in
  Apple's developer portal), to be planned as its own milestone.
- A3 TikTok and Instagram share a URL or text only. If Nuvio is missing from one of their sheets, they add another
  attachment type: replace the activation dict with a predicate string matching any `public.url` or
  `public.plain-text` attachment.
- A4 Photos lists apps that declare movie document types. If not, the try-it path for saved videos is
  Files, long-press the video, Share, Nuvio.
- A5 The Swift compiles as written (Swift 5 mode, no strict concurrency). Every `self` use after a system
  callback sits inside `DispatchQueue.main.async` for that reason; do not "simplify" it.
- A6 App Store Connect accepts a share extension with no extra keys. A refusal shows as an ITMS line at the end
  of the "Build, sign and upload" step.
When done: add to docs/ARCHITECTURE.md decisions "Share extension opens the app through the responder chain,
notification as fallback" and "Shared video = file:// link parsed in Kotlin, opened in place".

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
  - Tune the 15% clip-share bar on Mo's real clips. In simulation, correct matches on noisy 6-min clips (45% wrong words) were confident only 72% of the time. Consider measuring share against matchable lines.
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
