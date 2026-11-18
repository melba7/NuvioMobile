Done: 7 | Last cleanup: none | Mac builds used: 4 of about 6 (7c-7d on TestFlight from branch clip-finder-share, draft PR #3; Mo's phone check pending)
Next: Mo's phone check of 7c-7d, then 7e (build 5; see "Milestone 7e implementation notes", after milestone 8), then 7b (build 6). Merge to cmp-rewrite after 7b.
Phone test 2026-11-16 (Mac build 3): 7a works. Mo then asked for the YouTube video, more speed and accuracy, and an Instagram fix (reel: "Video address found: no").

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

- [x] **3. Share sheet to Clip finder screen** (Mac build 1; verified on Mo's phone 2026-11-15)
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

- [x] **4. Read the link** (Mac build 2; the riskiest step, one session only)
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

- [x] **5. Hear and read the clip** (Mac build 3)
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

- [x] **6. Find it and play it** (Mac build 4)
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

### Milestones 4-6 implementation notes (written 2026-11-15)
Milestones 4, 5 and 6 are built together and tested with ONE Mac build. Checked against the work tree (upstream
0.6.12-beta + patches, milestone 3 applied). Paths are inside `../nuvio-work` unless they start with `fork/` or
`docs/`. Where these notes differ from the milestone text above, the notes win.

Not checked here: nothing below was compiled (no Swift, Kotlin or Gradle in the cloud workspace). The Swift was only
syntax-parsed (tree-sitter). Kotlin errors show in "Fork check" (8 min). Swift errors only show in the Mac build.

#### A. Decisions
1. Getting the clip (milestone 4): an off-screen `WKWebView` with its normal user agent (nothing faked) loads the
   shared link; short links redirect by themselves. A small page script returns the page's own data as text: meta
   tags, the `<video>` element addresses, and every JSON script tag (`__UNIVERSAL_DATA_FOR_REHYDRATION__`,
   `SIGI_STATE`, `__NEXT_DATA__`, `application/json`). Kotlin (`ClipPageParser`, tested) finds the caption, author
   and video addresses in it without relying on one exact shape. Swift then downloads the first address that works
   with `URLSession`, sending the web view's cookies for that host, the page as referer and the web view's own
   User-Agent, into a temporary file that is deleted right after the sound is read.
   - Not used: oEmbed (no caption any more), a Ktor page fetch (no cookies, wrong client), `WKDownload` (API
     details could not be checked without a compiler), any third-party service, any other browser's user agent.
   - Deviation from the old plan text: the video goes to a temporary file, not memory (a 6 min clip is 30-60 MB).
     Only the sound is held in memory (16 kHz mono, about 12 MB for 6 min).
   - Instagram runs through the same code (reel page, same script, `video_versions` / `video_url` keys). It is
     best-effort in this build: Instagram often shows a login wall. TikTok is the target.
   - Shared video file (`AppDeepLink.ClipFile`): same pipeline from "Listening" on; no page, so no caption yet.
2. Listening (milestone 5): `AVAssetReader` + `AVAssetReaderAudioMixOutput` to 16-bit mono 16 kHz in memory;
   one gain for the whole clip (target -20 dB, at most 40 times, clipped); 30 s parts every 28 s (2 s overlap),
   each written as a small WAV file and given to `SFSpeechURLRecognitionRequest` (on-device only, en-US), one
   part at a time. Partial results are on, and a finished sentence is kept when the recogniser starts over after
   a pause (that restart is why one long request only gave the last sentence). 45 s limit per part, 300 s in
   total, cancellable. No `async/await`, no `@MainActor`: callbacks hopped to the main queue, like the upstream
   coordinators. Left out of this build: Apple Vision caption reading and the new iOS 26 SpeechAnalyzer (Later).
3. Glue (milestone 6): all logic in shared Kotlin under `features/clipfinder/`, tested with fakes.
   - Bridge: the codebase's pattern is a Kotlin interface implemented in Swift and registered at app start
     (`NuvioPlayerBridge` / `NuvioPlayerBridgeFactory.registerFactory`). Same here, but the interface lives in
     commonMain (`ClipFinderNative.kt`) because it needs no iOS types: no `iosMain` code, no `expect/actual`,
     and "Fork check" compiles all of it.
   - Subtitle cache: there is no file abstraction in commonMain to reuse (`SubtitleCacheProvider` does nothing
     on iOS). The cache is two methods on the same bridge; Swift keeps files in `Caches/clipfinder-subs`,
     trimmed to 40 MB when above 50 MB.
   - Show guess: `ShowGuesser` builds up to 6 search phrases from the caption; search = `fetchCatalogPage(...,
     search = q)` on every search catalog of the switched-on add-ons (not `SearchRepository`, which drives the
     search screen's state). Results with IMDb ids (`tt...`) are preferred: OpenSubtitles only knows those.
   - Episodes: `MetaDetailsRepository.fetch(type, id).videos`; a movie is one entry.
   - Subtitles: `addonSubtitleRequests` + `loadAddonSubtitles` (the player's own path), first English result,
     second one if the first fails; text via `httpGetTextWithHeaders`; parsed by `PlayerSubtitleCueParser`.
     6 episodes at a time; after each batch `ClipMatcher.match(lines, best so far + batch)`; stops when the top
     candidate is `confident` with 8+ hits; 120 s per show, 240 s in total; hinted episode and season first.
   - Start time: `StreamLaunch.resumePositionMs` is NOT enough: `resolveStreamResumeState` lets stored watch
     progress win, and a finished episode starts from 0. So `StreamLaunch` gets `clipStartMs`, and
     `StreamDestination` uses it in the two stream-tap lambdas. No watch progress is written by Clip finder.
   - "From clip start / After the clip" switch: included (two chips, one tested function). Default in this build
     is "From clip start" (moment minus 10 s) so the first phone test proves the match. SPEC 6 says the default
     is "after the clip": flip `afterClip` to `true` in `ClipFinderScreen` in milestone 7 if Mo still wants that.
   - Typing the show name (SPEC 7) stays in milestone 7. A clip without a caption stops with a clear message.

#### B. The contract between Swift and Kotlin (do not change one side alone)
Kotlin file `ClipFinderNative.kt` (full text in section H). Swift sees it through `import ComposeApp`:
```
protocol ClipFinderNative   func readPage(link: String, listener: ClipNativeListener)
                            func listen(mediaUrls: [String], pageUrl: String, listener: ClipNativeListener)
                            func cancel()
                            func cacheRead(key: String) -> String?
                            func cacheWrite(key: String, text: String)
protocol ClipNativeListener func onNote(label: String, value: String)      // diagnostic line
                            func onPage(pageJson: String)                  // ends readPage
                            func onLine(text: String, startMs: Int64, endMs: Int64)
                            func onDone()                                  // ends listen
                            func onFailed(stage: String, message: String)  // ends either; stage = "Reading link" or "Listening"
ClipFinderBridge.shared.register(impl:)                                    // called once from iOSApp.init
```
- Every listener call is made on the main thread. Exactly one ending call per `readPage` / `listen`.
- `listen` gets either one `file://` address or the page's video addresses, best first.
- Notes Swift sends (label: example value): `Page loaded: yes, after 3 s` | `Download: HTTP 200, 12.3 MB` or
  `Download: address 1: the video server refused the download (HTTP 403)` | `Speech: on this iPhone, English (US)`
  | `Audio: 312 s` | `Loudness: -33 dB, made 4.5 times louder` | `Listening: part 4 of 12`.
  Notes Kotlin adds: `Caption`, `Author`, `Video address found: yes (3) / no`, `Lines heard`, `Show guesses`,
  `Search`, `Subtitles: 41 of 60 episodes`, `Candidates`. The label `Audio` also moves the screen to "Listening".
- Page JSON made by the Swift page script and read by `ClipPageParser`:
  `{"url": final address, "title": "...", "metas": {"og:description": "..."}, "videos": ["https://..."], "scripts": ["<text of each JSON script tag>"]}`.

#### C. Files (all new unless marked "edit")
| Step | Owner | File | What |
|---|---|---|---|
| 4 | worker 1 | `K/ClipFinderNative.kt` | the contract |
| 4 | worker 1 | `K/ClipPageParser.kt`, `T/ClipPageParserTest.kt` | page JSON -> caption, author, video addresses |
| 4 | worker 1 | `S/ClipPageReader.swift`, `S/ClipMediaFetcher.swift` | web view, download to a temporary file |
| 5 | worker 2 | `S/ClipAudioReader.swift`, `S/ClipTranscriber.swift` | sound, loudness, 30 s parts, speech |
| 5 | worker 2 | `S/ClipFinderNativeImpl.swift` | bridge implementation, shared-file inbox, subtitle disk cache |
| 5 | worker 2 | edit `iosApp/iosApp/iOSApp.swift`, `iosApp/iosApp/Info.plist` | registration, speech permission text |
| 6 | worker 3 | `K/ShowGuesser.kt`, `K/EpisodeSubtitleSource.kt`, `K/ClipFinderState.kt`, `K/ClipFinderPipeline.kt`, `K/ClipFinderSession.kt`, `K/ClipFinderParts.kt` | guess, subtitles, run, real wiring, screen parts |
| 6 | worker 3 | rewrite `K/ClipFinderScreen.kt` | the screen (keeps `clipSourceLabel`, `CLIP_FINDER_STAGES`) |
| 6 | worker 3 | edit `features/streams/StreamLaunchStore.kt`, `StreamDestination.kt`, `MainAppContent.kt` | start time hand-off |
| 6 | worker 3 | `T/ShowGuesserTest.kt`, `T/EpisodeSubtitleSourceTest.kt`, `T/ClipFinderPipelineTest.kt`, `T/ClipFinderStateTest.kt` | tests (section E) |

`K` = `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder`, `T` = the same under `commonTest`,
`S` = `iosApp/iosApp/ClipFinder` (new folder; Xcode synchronized folders compile it by itself, like `Player/`:
NO `project.pbxproj` change). No file collides between workers. Every new file is under 300 lines.

#### D. Steps, one worker after the other in the same work tree
Tool for every worker: never hand-type the files. This script copies every "File:" block of section H byte for
byte into the work tree (`write`) or compares them (`check`). Paste it as it stands (no indentation):
```bash
cat > /tmp/clip_files.py <<'PY'
import re, sys, os
mode, plan, tree = sys.argv[1], sys.argv[2], sys.argv[3].rstrip("/")
only = sys.argv[4:]                                    # optional: path fragments to limit to
text = open(plan, encoding="utf-8").read()
blocks = re.findall(r"^##### File: `([^`]+)`\n```[a-z]*\n(.*?)\n```$", text, re.M | re.S)
assert len(blocks) == 15, "expected 15 file blocks, found %d" % len(blocks)
bad = 0
for path, body in blocks:
    if only and not any(o in path for o in only): continue
    full, body = os.path.join(tree, path), body + "\n"
    if mode == "write":
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w", encoding="utf-8").write(body)
        print("wrote", path)
    elif not os.path.exists(full) or open(full, encoding="utf-8").read() != body:
        bad += 1; print("DIFFERENT", path)
if mode == "check": print("all files match the plan" if not bad else "%d files differ" % bad); sys.exit(1 if bad else 0)
PY
```
0. Everyone: `fork/dev-tree.sh` (the work tree must be at the milestone 3 state), then save the script above.
1. Worker 1 (milestone 4): `python3 /tmp/clip_files.py write docs/PLAN.md ../nuvio-work ClipFinderNative.kt ClipPage ClipMediaFetcher`
   (5 files). Read each against section F. Do not change the contract.
2. Worker 2 (milestone 5): `python3 /tmp/clip_files.py write docs/PLAN.md ../nuvio-work ClipAudioReader ClipTranscriber ClipFinderNativeImpl`
   (3 files), then save the edit script of section G as `/tmp/clip_edits.py`. It is run once, by worker 3.
   Read each Swift file against section F.
3. Worker 3 (milestone 6): `python3 /tmp/clip_files.py write docs/PLAN.md ../nuvio-work ShowGuesser EpisodeSubtitleSource ClipFinderState ClipFinderPipeline ClipFinderSession ClipFinderParts ClipFinderScreen.kt`
   (7 files), `python3 /tmp/clip_edits.py ../nuvio-work` (prints "edits applied"), write the four test files of
   section E (tests first is not possible here: nothing runs locally, so the order is tests + code together, then
   "Fork check"). Run the pre-flight (section F), then `fork/dev-tree.sh save`.
4. Lead: commit `fork/nuvio-share-resume.patch` + docs, push, wait for "Fork check". Kotlin compile errors are
   fixed in the work tree (then save again). A Swift file is only changed for a reason found by reading; after
   any change `python3 /tmp/clip_files.py check ...` will say so, which is fine if it is on purpose.
5. Lead: `gh workflow run TestFlight --ref clip-finder-share` (the one Mac build). Then the phone checks (section I).
6. When green on the phone: tick 4, 5, 6; add to `docs/ARCHITECTURE.md` decisions: "Clip video goes to a temporary
   file, deleted after the sound is read", "Kotlin interface in commonMain implemented in Swift (no iosMain)",
   "Subtitle cache lives on the Swift side of the bridge", "`StreamLaunch.clipStartMs` beats stored progress";
   fix the Data flow items 2-4 and the Data model line to match; remove "Held in memory only".

#### E. Tests (commonTest, package `com.nuvio.app.features.clipfinder`; made-up words and names only)
`ClipPageParserTest.kt` is given in full in section H. The other four are written by worker 3 to this list. Use
`kotlinx.coroutines.test.runTest`; build subtitle text and clip lines from generated nonsense words the way
`ClipMatcherTest` does (its `vocabulary` idea), never real dialogue. Helper for all: `srt(cues)` that prints
`index\nHH:MM:SS,mmm --> HH:MM:SS,mmm\ntext\n\n` for 60 cues of 6 nonsense words, one every 4 s.
- `ShowGuesserTest`
  - `hint`: "Made Up Show S2E5 lamp" -> (2, 5); "season 3 episode 4" -> (3, 4); "watch 2x05" -> (2, 5);
    "best of season 7" -> (7, null); "1920x1080 edit" and "no numbers" -> (null, null).
  - `queries("Made Up Show S2E5 the lamp scene #madeupshow #fyp")` == ["Made Up Show", "Up Show", "Show", "madeupshow"].
  - `queries("lol #MadeUpShow #fyp #viral")` starts with "Made Up Show", then "MadeUpShow"; no generic tag.
  - `queries("Invented Drama is wild. Wait for it")` contains "Invented Drama" and nothing starting with "Wait".
  - `queries("that scene tho")` == ["that scene tho"]; `queries("")` is empty; a link in the caption is never a query.
  - `guess`: fake search returns `[ShowGuess("tt001","series","Made Up Show"), ShowGuess("tt002","series","Made Up Show Again")]`
    for "Made Up Show" and nothing else -> ids ["tt001", "tt002"], and the search was called once (stops at an exact name).
  - `guess` with a search that throws `IllegalStateException` for every query -> empty list; a
    `CancellationException` is rethrown.
  - `guess("the #madeupshow finale", ...)` where "madeupshow" returns "Made Up Show" -> found (squashed names match).
- `EpisodeSubtitleSourceTest` (fake add-on: `listSubtitles` returns `ClipSubtitleLink("https://subs.example.test/<id>.srt", "eng")`,
  `download` returns the episode's `srt`; count the calls; cache = a `MutableMap`; `now` = a variable)
  - cache: `cues()` twice -> 1 download, second answer equals the first; `decodeCues(encodeCues(x)) == x` for a
    cue whose text has a line break; a tab in a cue becomes a space; `decodeCues("rubbish")` is empty.
  - language: links `[("…/fr.srt","fre"), ("…/en.srt","English")]` -> only `en.srt` is downloaded;
    `isEnglish` true for "eng", "en", "en-US", "English", false for "fre", "spa", "".
  - a first English subtitle that throws, or has fewer than 20 cues -> the second is used; both bad -> null, nothing cached.
  - in-flight cap: 20 episodes, `listSubtitles` does `active++; peak = max(peak, active); delay(50); active--`
    -> `peak == 6`, `tried == 20`.
  - early stop: 30 episodes, clip lines = 12 cues in a row of episode 3 -> `decisive`, `tried == 6`,
    `candidates[0].videoId` is episode 3, at most 6 downloads.
  - time budget: `download` adds 10 000 to the clock, `deadlineMs = 15 000` -> `tried == 6`, not decisive.
  - `keep`: search show A (no match), then show B with `keep = resultA.best` -> top candidate is B's episode.
  - `orderEpisodes` with hint (2, 5): S2E5 first, then the rest of season 2 in order, then season 1; without a
    hint: season then episode; 500 episodes in -> 400 out.
- `ClipFinderPipelineTest` (`FakeNative : ClipFinderNative` answers at once inside the call: `readPage` ->
  `onNote("Page loaded", "yes, after 3 s")` then `onPage(json)` or `onFailed("Reading link", msg)`; `listen` records
  its arguments, sends `onNote("Audio", "41 s")`, the lines, then `onDone()` or `onFailed("Listening", msg)`;
  counts `cancel()`; pass `work = EmptyCoroutineContext`; collect every emitted state in a list)
  - happy path, link: page JSON as in `ClipPageParserTest` (caption "Made Up Show S2E5 ... #madeupshow"), 12
    episodes in 2 seasons, lines from S2E5 -> last state: `stage == Done`, not failed, `answers[0]` is S2E5 of
    "Made Up Show", `listen` got the page's video addresses and page address, note labels in order: Page loaded,
    Caption, Author, Video address found, Audio, Lines heard, Show guesses, Subtitles, Candidates; S2E5 was in
    the first batch (subtitle list calls <= 6).
  - shared file `file:///x/My%20clip.mp4`: `readPage` never called, `listen` got `[source]` and "", ends failed
    with `ClipMessages.NO_CAPTION` at `Searching`, `lines` kept.
  - each failure ends with `failed == true`, the right `stage`, message and file hint: no bridge (`NO_BRIDGE`);
    page failed (native message, hint); page without a video address (`NO_VIDEO`, hint, `listen` not called);
    `listen` failed (native message, stage `Listening`, hint for a link, no hint for a file); no lines
    (`NO_SPEECH`); search finds nothing (`NO_SHOW`); `loadEpisodes` throws (`NO_EPISODES`); add-on lists no
    subtitles (`NO_SUBTITLES`, note "Subtitles" == "0 of 12 episodes"); lines of other nonsense words (`NO_MATCH`).
  - a native side that never answers: after `advanceTimeBy(46_000)` the state is failed with `PAGE_TIMEOUT` and
    `cancel()` was called; cancelling the job of a waiting run also calls `cancel()`.
- `ClipFinderStateTest`: `withNote` replaces in place and appends new labels; `clipStartMs` (250 000..400 000 ->
  240 000 from clip start, 400 000 after the clip; start 4 000 -> 0); `clipClock(247_000) == "4:07"`,
  `clipClock(3_729_000) == "1:02:09"`, `clipClock(-5) == "0:00"`; `clipStageMark` for a running, a failed and a
  finished state; `clipAnswerTitle` for an episode with and without a title and for a movie.
The existing `ClipFinderScreenTest` and `ClipMatcherTest` must stay green unchanged.

#### F. Pre-flight before pushing (Swift cannot compile here, so every line of this list counts)
Script checks (run from the repo root; all must pass):
```bash
W=../nuvio-work; S=$W/iosApp/iosApp/ClipFinder
python3 /tmp/clip_files.py check docs/PLAN.md $W                      # all files match the plan
ls $S                                                                 # exactly the 5 Swift files of section C
grep -nE '@MainActor|\bawait\b|\basync (let|throws|->)|Task *\{|Task\.detached|import SwiftUI' $S/*.swift   # prints nothing
for f in $S/*.swift; do python3 - "$f" <<'PY'
import sys
s = open(sys.argv[1], encoding="utf-8").read()
assert s.count("{") == s.count("}") and s.count("(") == s.count(")") and s.count("[") == s.count("]"), sys.argv[1] + ": unbalanced brackets"
assert max(len(l) for l in s.split("\n")) < 220 and s.count("\n") < 300, sys.argv[1] + ": too long"
PY
done
python3 - $W <<'PY'                                                   # the two sides of the contract agree
import re, sys
k = open(sys.argv[1] + "/composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderNative.kt").read()
s = open(sys.argv[1] + "/iosApp/iosApp/ClipFinder/ClipFinderNativeImpl.swift").read()
for sig in ("func readPage(link: String, listener: ClipNativeListener)", "func listen(mediaUrls: [String], pageUrl: String, listener: ClipNativeListener)",
            "func cancel()", "func cacheRead(key: String) -> String?", "func cacheWrite(key: String, text: String)",
            "ClipFinderBridge.shared.register(impl:", "listener.onNote(label:", "listener.onPage(pageJson:", "listener.onLine(text: text, startMs: startMs, endMs: endMs)",
            "listener.onDone()", "listener.onFailed(stage:"):
    assert sig in s, "Swift side lacks: " + sig
for sig in ("fun readPage(link: String, listener: ClipNativeListener)", "fun listen(mediaUrls: List<String>, pageUrl: String, listener: ClipNativeListener)",
            "fun cancel()", "fun cacheRead(key: String): String?", "fun cacheWrite(key: String, text: String)", "fun onNote(label: String, value: String)",
            "fun onPage(pageJson: String)", "fun onLine(text: String, startMs: Long, endMs: Long)", "fun onDone()", "fun onFailed(stage: String, message: String)",
            "fun register(impl: ClipFinderNative)"):
    assert sig in k, "Kotlin side lacks: " + sig
assert len(re.findall(r"^\s*fun ", k, re.M)) == 12, "ClipFinderNative.kt must declare exactly 12 functions"
print("contract OK")
PY
python3 -c "import plistlib,sys; p=plistlib.load(open(sys.argv[1],'rb')); assert p['NSSpeechRecognitionUsageDescription'] and p['CFBundleDocumentTypes']; print('plist OK')" $W/iosApp/iosApp/Info.plist
git -C $W diff --stat fork-baseline -- iosApp/iosApp/iOSApp.swift | tail -1      # 1 file changed, 5 insertions(+)
git -C $W diff --stat fork-baseline -- iosApp/iosApp.xcodeproj | tail -1        # still: 1 file changed, 137 insertions(+)
pip install -q tree-sitter tree-sitter-swift && python3 - $S <<'PY'          # optional but cheap: Swift syntax
import glob, sys, tree_sitter_swift
from tree_sitter import Language, Parser
p = Parser(Language(tree_sitter_swift.language()))
for f in sorted(glob.glob(sys.argv[1] + "/*.swift")):
    assert not p.parse(open(f, "rb").read()).root_node.has_error, f + ": syntax error"
print("swift syntax OK")
PY
fork/dev-tree.sh save
```
Reading checks for every Swift file (do them even if the script passes; they are the things a compiler would catch):
1. Imports are exactly: `ClipPageReader` Foundation, UIKit, WebKit | `ClipMediaFetcher` Foundation |
   `ClipAudioReader` AVFoundation, Foundation | `ClipTranscriber` AVFoundation, Foundation, Speech |
   `ClipFinderNativeImpl` Foundation, ComposeApp. Only that last file names Kotlin types.
2. Language mode is Swift 5 (`SWIFT_VERSION = 5.0`, no strict concurrency setting). Keep it boring: no
   `@MainActor`, `async`, `await`, `Task`, actors or `Sendable` annotations. Plain classes calling UIKit/WebKit
   compile in this project (precedent: `OrientationLockCoordinator`); `@MainActor` classes called from callbacks do
   so only inside `DispatchQueue.main.async` (precedent: `ShareViewController`).
3. Every system callback that touches `self` goes through `DispatchQueue.main.async { }` first, and only plain
   values (`String`, `[HTTPCookie]`, numbers, the private `Word` structs) are carried into that block; no `var`
   declared outside is read inside it (copy to a `let` first, as `failureText`, `size`, `found`, `done` do).
4. No Swift type is named like a Kotlin one. Kotlin exports `ClipLine`, `ClipCandidate`, `ClipPage`, `ClipNote`,
   `ClipAnswer`, `ClipEpisode`, `ClipHint`, `ClipStage`, `ClipFinderState`, `ClipFinderBridge`, `ClipFinderNative`,
   `ClipNativeListener`, `ClipFinderSession`, `ClipFinderPipeline`... Swift types are `ClipPageResult`,
   `ClipPageReader`, `ClipMediaFetcher`, `ClipAudio`, `ClipAudioReader`, `ClipTranscriber`, `ClipFinderRegistration`,
   `ClipFileInbox`, `ClipFinderNativeImpl`, `ClipSubtitleDiskCache`. Do not add a Kotlin class with one of these names.
5. `ClipFinderNativeImpl` is `NSObject, ClipFinderNative` (like `MPVPlayerBridgeImpl: NSObject, NuvioPlayerBridge`);
   Kotlin `Long` is `Int64`, `List<String>` is `[String]`, `String?` is `String?`; parameter labels equal the Kotlin
   parameter names. A Kotlin function name must not start with `init`, `new`, `copy` or `alloc`.
6. API names used (all exist since iOS 16 or earlier; the deployment target is 16.1, so no `#available`):
   `WKWebViewConfiguration.websiteDataStore/.allowsInlineMediaPlayback/.mediaTypesRequiringUserActionForPlayback`,
   `WKWebsiteDataStore.nonPersistent()`, `WKWebView.load/.evaluateJavaScript(_:completionHandler:)/.stopLoading`,
   `httpCookieStore.getAllCookies`, `HTTPCookie.requestHeaderFields(with:)`, `URLSessionConfiguration.ephemeral`,
   `URLSession.downloadTask(with:completionHandler:)`, `AVURLAsset.tracks(withMediaType:)` (deprecated: a warning,
   kept on purpose because it needs no `await`), `AVAssetReader`, `AVAssetReaderAudioMixOutput(audioTracks:audioSettings:)`,
   `copyNextSampleBuffer`, `CMSampleBufferGetFormatDescription`, `CMAudioFormatDescriptionGetStreamBasicDescription`,
   `CMSampleBufferGetDataBuffer`, `CMBlockBufferGetDataLength`, `CMBlockBufferCopyDataBytes(_:atOffset:dataLength:destination:)`,
   `SFSpeechRecognizer.requestAuthorization`, `SFSpeechRecognizer(locale:)`, `.supportsOnDeviceRecognition`, `.isAvailable`,
   `SFSpeechURLRecognitionRequest(url:)`, `.requiresOnDeviceRecognition`, `.shouldReportPartialResults`, `.taskHint`,
   `recognitionTask(with:resultHandler:)`, `SFTranscriptionSegment.substring/.timestamp/.duration`,
   `URL.startAccessingSecurityScopedResource()`. If you are not sure a name is right, do not swap it for another
   from memory: flag it to the lead.
7. `Info.plist` has `NSSpeechRecognitionUsageDescription` (without it iOS kills the app at the permission prompt).
   No microphone key: the microphone is never used.
8. The page script is inside `#""" ... """#`: it must not contain `"""#`, and it uses single quotes only.
What each check proves: Fork check = Kotlin compiles (all of `K`, the three edited upstream files) and the tests
pass; nothing about Swift. Mac build = Swift compiles and links (errors appear in the first minutes as `error:`
lines naming a `ClipFinder/` file in `fork/state/build.log`, artifact `build-log`). Phone = everything in section I.

#### G. Edits to existing files (script; tested against the milestone 3 work tree: 5 files, only added or replaced lines)
Save as `/tmp/clip_edits.py`, run once: `python3 /tmp/clip_edits.py ../nuvio-work`.
```python
import sys
W = sys.argv[1].rstrip("/")
APP = W + "/composeApp/src/commonMain/kotlin/com/nuvio/app/"

def edit(path, pairs):
    text = open(path, encoding="utf-8").read()
    for old, new, count in pairs:
        assert text.count(old) == count, "%s: expected %d of %r, found %d" % (path, count, old[:60], text.count(old))
        text = text.replace(old, new)
    open(path, "w", encoding="utf-8").write(text)

if "clipStartMs" in open(APP + "features/streams/StreamLaunchStore.kt", encoding="utf-8").read():
    sys.exit("already applied: nothing changed")

# 1. StreamLaunch gets an explicit start time (not watch progress)
edit(APP + "features/streams/StreamLaunchStore.kt", [(
    "    val downloadIntent: Boolean = false,\n",
    "    val downloadIntent: Boolean = false,\n"
    "    /** Clip finder: start playback at this time, whatever watch progress is stored. Never saved as progress by itself. */\n"
    "    val clipStartMs: Long? = null,\n", 1)])

# 2. StreamDestination: a tapped stream starts at clipStartMs when the launch has one (2 places, inside StreamsScreen(...))
path = APP + "StreamDestination.kt"
text = open(path, encoding="utf-8").read()
start = text.index("            StreamsScreen(\n")
end = text.index("                onBack = onBack,\n", start)
block = text[start:end]
old = ("                        resolvedResumePositionMs = resolvedResumePositionMs,\n"
       "                        resolvedResumeProgressFraction = resolvedResumeProgressFraction,\n")
new = ("                        resolvedResumePositionMs = launch.clipStartMs ?: resolvedResumePositionMs,\n"
       "                        resolvedResumeProgressFraction = resolvedResumeProgressFraction.takeIf { launch.clipStartMs == null },\n")
assert block.count(old) == 2, "StreamDestination.kt: expected 2 stream-tap lambdas, found %d" % block.count(old)
open(path, "w", encoding="utf-8").write(text[:start] + block.replace(old, new) + text[end:])

# 3. MainAppContent: open a candidate in the normal stream list with the start time
edit(APP + "MainAppContent.kt", [
    ("import com.nuvio.app.features.clipfinder.CLIP_FINDER_TITLE\n",
     "import com.nuvio.app.features.clipfinder.CLIP_FINDER_TITLE\nimport com.nuvio.app.features.clipfinder.ClipAnswer\n", 1),
    ("        val onPlay: ContentPlayAction =\n",
     "        fun openClipAnswer(answer: ClipAnswer, startMs: Long) {\n"
     "            val launchId = StreamLaunchStore.put(\n"
     "                StreamLaunch(\n"
     "                    profileId = activePlaybackProfileId,\n"
     "                    type = answer.show.type,\n"
     "                    videoId = answer.candidate.videoId,\n"
     "                    parentMetaId = answer.show.metaId,\n"
     "                    parentMetaType = answer.show.type,\n"
     "                    title = answer.show.name,\n"
     "                    poster = answer.show.poster,\n"
     "                    seasonNumber = answer.candidate.season,\n"
     "                    episodeNumber = answer.candidate.episode,\n"
     "                    episodeTitle = answer.episodeTitle,\n"
     "                    episodeThumbnail = answer.thumbnail,\n"
     "                    manualSelection = true,\n"
     "                    startFromBeginning = true,\n"
     "                    clipStartMs = startMs,\n"
     "                ),\n"
     "            )\n"
     "            navController.navigate(StreamRoute(launchId = launchId, title = answer.show.name))\n"
     "        }\n\n"
     "        val onPlay: ContentPlayAction =\n", 1),
    ("                        ClipFinderScreen(source = route.source, onBack = onBack)\n",
     "                        ClipFinderScreen(source = route.source, onBack = onBack, onOpen = ::openClipAnswer)\n", 1),
])

# 4. iOSApp.swift: register the Swift side at start; keep the URL object of a shared file
edit(W + "/iosApp/iosApp/iOSApp.swift", [
    ("    @UIApplicationDelegateAdaptor(OrientationLockAppDelegate.self) private var appDelegate\n",
     "    @UIApplicationDelegateAdaptor(OrientationLockAppDelegate.self) private var appDelegate\n\n"
     "    init() {\n"
     "        ClipFinderRegistration.register()\n"
     "    }\n", 1),
    ("                .onOpenURL { url in\n",
     "                .onOpenURL { url in\n"
     "                    ClipFileInbox.shared.remember(url)\n", 1),
])

# 5. Info.plist: the text iOS shows when it asks for speech recognition
edit(W + "/iosApp/iosApp/Info.plist", [(
    "\t<key>CFBundleDocumentTypes</key>\n",
    "\t<key>NSSpeechRecognitionUsageDescription</key>\n"
    "\t<string>Nuvio listens to a clip you share, on this iPhone only, to find the episode it comes from.</string>\n"
    "\t<key>CFBundleDocumentTypes</key>\n", 1)])
print("edits applied")
```
Why these edits are enough: `openClipAnswer` puts a `StreamLaunch` with `manualSelection = true` (no auto-play, no
reuse of the last link, no downloaded copy) and `startFromBeginning = true` (the stream list shows no "resume"
banner and ignores stored progress), and `clipStartMs`. The two lambdas in `StreamDestination` are the only way a
manually tapped stream reaches `openSelectedStream`, whose result becomes `PlayerLaunch.initialPositionMs`
(internal player, external player, debrid, P2P alike). A start time of 0 is fine.

#### H. The files
Write them with the script of section D, step 0. The block header is the path inside the work tree.

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderNative.kt`
```kotlin
package com.nuvio.app.features.clipfinder

/**
 * The iPhone-only work, done in Swift (iosApp/iosApp/ClipFinder/ClipFinderNativeImpl.swift).
 * [readPage] and [listen] return at once and answer through the listener, always on the main
 * thread. Only one of them runs at a time; starting one stops the other.
 */
interface ClipFinderNative {
    /** Loads the web page off-screen. Ends with exactly one onPage or onFailed. */
    fun readPage(link: String, listener: ClipNativeListener)

    /**
     * Turns a clip's sound into text. [mediaUrls] is either one file:// address (a shared video)
     * or the video addresses found on the page, best first; [pageUrl] is sent as the referer.
     * Calls onLine for each line, then ends with exactly one onDone or onFailed.
     */
    fun listen(mediaUrls: List<String>, pageUrl: String, listener: ClipNativeListener)

    /** Stops whatever runs. The listener of the stopped work is not called again. */
    fun cancel()

    /** Subtitle cache on disk (about 50 MB). Safe from any thread. Null when not stored. */
    fun cacheRead(key: String): String?

    fun cacheWrite(key: String, text: String)
}

interface ClipNativeListener {
    /** A diagnostic line for the screen, for example ("Audio", "312 s"). */
    fun onNote(label: String, value: String)

    /** [pageJson] is what the page says about itself; read it with [ClipPageParser]. */
    fun onPage(pageJson: String)

    fun onLine(text: String, startMs: Long, endMs: Long)

    fun onDone()

    /** [stage] is "Reading link" or "Listening"; [message] is plain English for the screen. */
    fun onFailed(stage: String, message: String)
}

/** Swift registers its implementation here when the app starts (iOSApp.swift). */
object ClipFinderBridge {
    private var registered: ClipFinderNative? = null

    fun register(impl: ClipFinderNative) {
        registered = impl
    }

    fun current(): ClipFinderNative? = registered
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipPageParser.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull

/** What a clip's web page says about itself. Every field may be empty. */
data class ClipPage(
    val pageUrl: String = "",
    val caption: String = "",
    val author: String = "",
    val videoUrls: List<String> = emptyList(),
)

/**
 * Reads the JSON text made by the page script in ClipPageReader.swift:
 * {"url", "title", "metas": {name: content}, "videos": [addresses of video elements],
 * "scripts": [text of each JSON script tag]}. The sites change their pages often, so nothing here
 * depends on one exact shape: every JSON script is searched for an object that looks like a clip
 * and for the keys that hold video addresses. Never throws; unknown input gives an empty page.
 */
object ClipPageParser {
    private const val MAX_NODES = 300_000
    private const val MAX_DEPTH = 60
    private const val MAX_URLS = 6
    private val urlKeys = setOf(
        "playAddr", "PlayAddr", "play_addr", "downloadAddr", "DownloadAddr", "download_addr",
        "video_url", "video_versions", "contentUrl",
    )
    private val captionMetas = listOf("og:description", "twitter:description", "description", "og:title")
    private val videoMetas = listOf("og:video:secure_url", "og:video", "og:video:url", "twitter:player:stream")

    private class Found {
        var caption = ""
        var author = ""
        val urls = mutableListOf<String>()
        var nodes = 0
    }

    fun parse(pageJson: String): ClipPage = runCatching { parseOrThrow(pageJson) }.getOrDefault(ClipPage())

    private fun parseOrThrow(pageJson: String): ClipPage {
        val root = Json.parseToJsonElement(pageJson) as? JsonObject ?: return ClipPage()
        val metas = root["metas"] as? JsonObject
        val found = Found()
        for (script in (root["scripts"] as? JsonArray).orEmpty()) {
            val text = (script as? JsonPrimitive)?.contentOrNull ?: continue
            val element = runCatching { Json.parseToJsonElement(text) }.getOrNull() ?: continue
            walk(element, found, 0)
        }
        val elementUrls = (root["videos"] as? JsonArray).orEmpty().mapNotNull { (it as? JsonPrimitive)?.contentOrNull }
        val metaUrls = videoMetas.mapNotNull { metas?.text(it)?.takeIf(String::isNotBlank) }
        val urls = (elementUrls + found.urls + metaUrls)
            .map { it.trim() }
            .filter { it.startsWith("https://", ignoreCase = true) || it.startsWith("http://", ignoreCase = true) }
            .distinct()
            .take(MAX_URLS)
        val caption = found.caption.ifBlank {
            captionMetas.firstNotNullOfOrNull { metas?.text(it)?.takeIf(String::isNotBlank) } ?: root.text("title")
        }
        return ClipPage(
            pageUrl = root.text("url"),
            caption = caption.trim().take(2_000),
            author = found.author.trim().take(100),
            videoUrls = urls,
        )
    }

    private fun walk(element: JsonElement, found: Found, depth: Int) {
        found.nodes++
        if (depth > MAX_DEPTH || found.nodes > MAX_NODES) return
        when (element) {
            is JsonObject -> {
                readClip(element, found)
                for ((key, value) in element) {
                    if (key in urlKeys) collectUrls(value, found.urls, 0)
                    walk(value, found, depth + 1)
                }
            }
            is JsonArray -> for (child in element) walk(child, found, depth + 1)
            else -> Unit
        }
    }

    /**
     * TikTok: {"desc": "...", "video": {...}, "author": {"uniqueId": "..."} or "name"}.
     * Instagram: {"caption": {"text": "..."}, "video_versions": [...], "user": {"username": "..."}}.
     * The first clip with a caption wins.
     */
    private fun readClip(obj: JsonObject, found: Found) {
        if (found.caption.isNotBlank()) return
        val tiktok = obj["video"] is JsonObject && obj["desc"] is JsonPrimitive
        val instagram = "video_versions" in obj || "video_url" in obj
        if (!tiktok && !instagram) return
        val caption = if (tiktok) obj.text("desc") else (obj["caption"] as? JsonObject)?.text("text") ?: obj.text("caption")
        val owner = if (tiktok) obj["author"] else obj["user"] ?: obj["owner"]
        val author = when (owner) {
            is JsonObject -> owner.text("uniqueId").ifBlank { owner.text("username") }.ifBlank { owner.text("nickname") }
            is JsonPrimitive -> owner.contentOrNull.orEmpty()
            else -> ""
        }
        if (caption.isNotBlank()) found.caption = caption
        if (found.author.isBlank()) found.author = author
    }

    private fun collectUrls(value: JsonElement, into: MutableList<String>, depth: Int) {
        if (depth > 3 || into.size >= 12) return
        when (value) {
            is JsonPrimitive -> {
                val text = value.contentOrNull ?: return
                if (value.isString && text.startsWith("http") && text !in into) into += text
            }
            is JsonArray -> for (child in value) collectUrls(child, into, depth + 1)
            is JsonObject -> for (child in value.values) collectUrls(child, into, depth + 1)
        }
    }

    private fun JsonObject.text(key: String): String = (this[key] as? JsonPrimitive)?.contentOrNull.orEmpty()
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipPageParserTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlinx.serialization.json.add
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/** Sample pages are made up to look like the shapes the sites use; no real captions, names or addresses. */
class ClipPageParserTest {
    private val pageUrl = "https://www.tiktok.com/@sample.user/video/7000000000000000001"

    private fun page(
        scripts: List<String> = emptyList(),
        videos: List<String> = emptyList(),
        metas: Map<String, String> = emptyMap(),
        title: String = "",
    ): String = buildJsonObject {
        put("url", pageUrl)
        put("title", title)
        put("metas", buildJsonObject { metas.forEach { (key, value) -> put(key, value) } })
        put("videos", buildJsonArray { videos.forEach { add(it) } })
        put("scripts", buildJsonArray { scripts.forEach { add(it) } })
    }.toString()

    private fun item(scope: String) = """{"__DEFAULT_SCOPE__":{"webapp.app-context":{"language":"en"},"$scope":{"itemInfo":{"itemStruct":{"id":"7000000000000000001","desc":"Made Up Show S2E5 the lamp scene #madeupshow #fyp","author":{"uniqueId":"sample.user","nickname":"Sample"},"video":{"duration":41,"playAddr":"https://v16.example.test/play.mp4?token=a","downloadAddr":"https://v16.example.test/download.mp4?token=b","bitrateInfo":[{"PlayAddr":{"UrlList":["https://v16.example.test/play.mp4?token=a","https://v19.example.test/alt.mp4"]}}]},"music":{"playUrl":"https://music.example.test/song.mp3"}}}}}}"""

    @Test
    fun `reads caption author and video addresses from the desktop page shape`() {
        val result = ClipPageParser.parse(page(scripts = listOf(item("webapp.video-detail"))))
        assertEquals("Made Up Show S2E5 the lamp scene #madeupshow #fyp", result.caption)
        assertEquals("sample.user", result.author)
        assertEquals(pageUrl, result.pageUrl)
        assertEquals(
            listOf("https://v16.example.test/play.mp4?token=a", "https://v16.example.test/download.mp4?token=b", "https://v19.example.test/alt.mp4"),
            result.videoUrls,
        )
    }

    @Test
    fun `mobile page shape works and the video element comes first`() {
        val result = ClipPageParser.parse(
            page(
                scripts = listOf("""{"unrelated":true}""", item("webapp.reflow.video.detail")),
                videos = listOf("blob:https://www.tiktok.com/abc", "https://v16.example.test/element.mp4"),
            ),
        )
        assertEquals("Made Up Show S2E5 the lamp scene #madeupshow #fyp", result.caption)
        assertEquals("https://v16.example.test/element.mp4", result.videoUrls.first())
        assertEquals(4, result.videoUrls.size)
    }

    @Test
    fun `older page shape with the author as plain text`() {
        val sigi = """{"ItemModule":{"7000000000000000001":{"desc":"Another Made Up Show #clips","author":"plain.name","video":{"playAddr":"https://v.example.test/a.mp4"}}}}"""
        val result = ClipPageParser.parse(page(scripts = listOf(sigi)))
        assertEquals("Another Made Up Show #clips", result.caption)
        assertEquals("plain.name", result.author)
        assertEquals(listOf("https://v.example.test/a.mp4"), result.videoUrls)
    }

    @Test
    fun `instagram reel shape`() {
        val reel = """{"require":[["x",{"items":[{"caption":{"text":"Invented Drama season 3 episode 4"},"user":{"username":"sample_ig"},"video_versions":[{"url":"https://scontent.example.test/v1.mp4","width":720},{"url":"https://scontent.example.test/v2.mp4"}]}]}]]}"""
        val result = ClipPageParser.parse(page(scripts = listOf(reel)))
        assertEquals("Invented Drama season 3 episode 4", result.caption)
        assertEquals("sample_ig", result.author)
        assertEquals(listOf("https://scontent.example.test/v1.mp4", "https://scontent.example.test/v2.mp4"), result.videoUrls)
    }

    @Test
    fun `falls back to the page's meta tags and title`() {
        val withMetas = ClipPageParser.parse(
            page(metas = mapOf("og:description" to " Some Invented Show clip ", "og:video" to "https://cdn.example.test/og.mp4"), title = "ignored"),
        )
        assertEquals("Some Invented Show clip", withMetas.caption)
        assertEquals(listOf("https://cdn.example.test/og.mp4"), withMetas.videoUrls)
        assertEquals("Only A Title", ClipPageParser.parse(page(title = "Only A Title")).caption)
    }

    @Test
    fun `an item without a caption still gives its video and the meta caption`() {
        val noCaption = """{"a":{"desc":"","author":{"uniqueId":"quiet.user"},"video":{"playAddr":"https://v.example.test/quiet.mp4"}}}"""
        val result = ClipPageParser.parse(page(scripts = listOf(noCaption), metas = mapOf("og:description" to "From the meta tag")))
        assertEquals("From the meta tag", result.caption)
        assertEquals("quiet.user", result.author)
        assertEquals(listOf("https://v.example.test/quiet.mp4"), result.videoUrls)
    }

    @Test
    fun `broken input never throws and gives an empty page`() {
        for (bad in listOf("", "not json", "[1,2]", "{\"scripts\":7,\"videos\":{},\"metas\":[]}", page(scripts = listOf("{broken", "", "null", "[[[[")))) {
            val result = ClipPageParser.parse(bad)
            assertEquals("", result.caption)
            assertEquals(emptyList<String>(), result.videoUrls)
        }
    }
}
```

##### File: `iosApp/iosApp/ClipFinder/ClipPageReader.swift`
```swift
import Foundation
import UIKit
import WebKit

struct ClipPageResult {
    let pageJson: String?
    let error: String?
    let cookies: [HTTPCookie]
    let userAgent: String
}

/// Loads the shared link in an off-screen web view (the normal iOS web view, nothing faked) and hands
/// back what the page says about itself as JSON text; Kotlin (ClipPageParser) reads it.
/// One reader per link. Call it on the main thread only; it answers on the main thread, once.
final class ClipPageReader {
    private static let maxPolls = 25
    private static let script = #"""
    (function () {
      var out = { url: location.href, title: document.title || '', metas: {}, videos: [], scripts: [] };
      var known = false;
      try {
        var metas = document.querySelectorAll('meta[property], meta[name]');
        for (var i = 0; i < metas.length; i++) {
          var key = metas[i].getAttribute('property') || metas[i].getAttribute('name') || '';
          if (key.indexOf('og:') === 0 || key.indexOf('twitter:') === 0 || key === 'description') {
            out.metas[key] = metas[i].getAttribute('content') || '';
          }
        }
      } catch (e) {}
      try {
        var videos = document.querySelectorAll('video, video source');
        for (var j = 0; j < videos.length; j++) {
          var list = [videos[j].currentSrc, videos[j].src];
          for (var k = 0; k < list.length; k++) {
            var address = list[k];
            if (address && address.indexOf('http') === 0 && out.videos.indexOf(address) < 0) {
              out.videos.push(address);
              known = true;
            }
          }
        }
      } catch (e) {}
      try {
        var scripts = document.querySelectorAll('script');
        var total = 0;
        for (var s = 0; s < scripts.length; s++) {
          var type = (scripts[s].type || '').toLowerCase();
          var id = scripts[s].id || '';
          var named = id === '__UNIVERSAL_DATA_FOR_REHYDRATION__' || id === 'SIGI_STATE' || id === '__NEXT_DATA__';
          if (!named && type.indexOf('json') < 0) { continue; }
          var text = scripts[s].textContent || '';
          if (text.length < 20 || total + text.length > 3000000) { continue; }
          total += text.length;
          out.scripts.push(text);
          if (named) { known = true; }
        }
      } catch (e) {}
      var state = known ? '1' : (document.readyState === 'complete' ? '2' : '0');
      return state + JSON.stringify(out);
    })()
    """#

    private var webView: WKWebView?
    private var polls = 0
    private var lastPayload: String?
    private var finished = false
    private var note: ((String, String) -> Void)?
    private var completion: ((ClipPageResult) -> Void)?

    func read(link: String, note: @escaping (String, String) -> Void, completion: @escaping (ClipPageResult) -> Void) {
        self.note = note
        self.completion = completion
        guard let url = URL(string: link), let scheme = url.scheme?.lowercased(), scheme == "http" || scheme == "https" else {
            finish(page: nil, error: "This is not a web link.", cookies: [], userAgent: "")
            return
        }
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = WKWebsiteDataStore.nonPersistent()
        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = .all
        let view = WKWebView(frame: CGRect(x: 0, y: 0, width: 390, height: 844), configuration: configuration)
        view.isUserInteractionEnabled = false
        view.alpha = 0.01
        if let window = ClipPageReader.keyWindow() {
            window.insertSubview(view, at: 0)
        }
        webView = view
        view.load(URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 20))
        schedulePoll()
    }

    func cancel() {
        finished = true
        completion = nil
        note = nil
        closeWebView()
    }

    private static func keyWindow() -> UIWindow? {
        var fallback: UIWindow?
        for scene in UIApplication.shared.connectedScenes {
            guard let windowScene = scene as? UIWindowScene else { continue }
            for window in windowScene.windows {
                if window.isKeyWindow { return window }
                if fallback == nil { fallback = window }
            }
        }
        return fallback
    }

    private func schedulePoll() {
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { [weak self] in
            self?.poll()
        }
    }

    private func poll() {
        guard !finished, let view = webView else { return }
        polls += 1
        view.evaluateJavaScript(ClipPageReader.script) { [weak self] value, _ in
            let text = value as? String
            DispatchQueue.main.async {
                self?.handle(text)
            }
        }
    }

    private func handle(_ text: String?) {
        guard !finished else { return }
        if let text = text, text.count > 1 {
            lastPayload = String(text.dropFirst())
            let state = String(text.prefix(1))
            if (state == "1" && polls >= 3) || (state == "2" && polls >= 6) {
                finishWithPage()
                return
            }
        }
        if polls >= ClipPageReader.maxPolls {
            finishWithPage()
            return
        }
        schedulePoll()
    }

    private func finishWithPage() {
        guard let payload = lastPayload, let view = webView else {
            note?("Page loaded", "no")
            finish(page: nil, error: "The page did not load. Check the connection; the site may also have blocked the request.", cookies: [], userAgent: "")
            return
        }
        note?("Page loaded", "yes, after \(polls) s")
        view.evaluateJavaScript("navigator.userAgent") { [weak self] value, _ in
            let agent = (value as? String) ?? ""
            view.configuration.websiteDataStore.httpCookieStore.getAllCookies { cookies in
                DispatchQueue.main.async {
                    self?.finish(page: payload, error: nil, cookies: cookies, userAgent: agent)
                }
            }
        }
    }

    private func finish(page: String?, error: String?, cookies: [HTTPCookie], userAgent: String) {
        guard !finished else { return }
        finished = true
        let done = completion
        completion = nil
        note = nil
        closeWebView()
        done?(ClipPageResult(pageJson: page, error: error, cookies: cookies, userAgent: userAgent))
    }

    private func closeWebView() {
        webView?.stopLoading()
        webView?.removeFromSuperview()
        webView = nil
    }
}
```

##### File: `iosApp/iosApp/ClipFinder/ClipMediaFetcher.swift`
```swift
import Foundation

/// Downloads the clip's video file to a temporary file, sending what the web view was given for the
/// page (its cookies, its own User-Agent, the page as referer). The caller deletes the file.
/// Call it on the main thread only; it answers on the main thread, once.
final class ClipMediaFetcher {
    private var urls: [String] = []
    private var pageUrl = ""
    private var cookies: [HTTPCookie] = []
    private var userAgent = ""
    private var note: ((String, String) -> Void)?
    private var completion: ((URL?, String?) -> Void)?
    private var session: URLSession?
    private var task: URLSessionDownloadTask?
    private var cancelled = false

    func fetch(
        urls: [String],
        pageUrl: String,
        cookies: [HTTPCookie],
        userAgent: String,
        note: @escaping (String, String) -> Void,
        completion: @escaping (URL?, String?) -> Void
    ) {
        self.urls = Array(urls.prefix(4))
        self.pageUrl = pageUrl
        self.cookies = cookies
        self.userAgent = userAgent
        self.note = note
        self.completion = completion
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 30
        configuration.timeoutIntervalForResource = 120
        configuration.httpShouldSetCookies = false
        session = URLSession(configuration: configuration)
        attempt(0, lastError: "No video address was found on the page.")
    }

    func cancel() {
        cancelled = true
        completion = nil
        note = nil
        task?.cancel()
        task = nil
        session?.invalidateAndCancel()
        session = nil
    }

    private func attempt(_ index: Int, lastError: String) {
        guard !cancelled else { return }
        guard index < urls.count, let session = session else {
            finish(nil, lastError)
            return
        }
        guard let url = URL(string: urls[index]), let host = url.host else {
            attempt(index + 1, lastError: lastError)
            return
        }
        var request = URLRequest(url: url)
        if !pageUrl.isEmpty { request.setValue(pageUrl, forHTTPHeaderField: "Referer") }
        if !userAgent.isEmpty { request.setValue(userAgent, forHTTPHeaderField: "User-Agent") }
        let matching = cookies.filter { ClipMediaFetcher.cookie($0, belongsTo: host) }
        for (name, value) in HTTPCookie.requestHeaderFields(with: matching) {
            request.setValue(value, forHTTPHeaderField: name)
        }
        let target = FileManager.default.temporaryDirectory.appendingPathComponent("nuvio-clip-" + UUID().uuidString + ".mp4")
        let newTask = session.downloadTask(with: request) { [weak self] location, response, error in
            let status = (response as? HTTPURLResponse)?.statusCode ?? 0
            let mime = (response?.mimeType ?? "").lowercased()
            var failure: String?
            var bytes: Int64 = 0
            if let error = error {
                failure = "the download failed (" + error.localizedDescription + ")"
            } else if status < 200 || status > 299 {
                failure = "the video server refused the download (HTTP \(status))"
            } else if mime.hasPrefix("text/") || mime.contains("json") {
                failure = "the address returned a web page, not a video"
            } else if let location = location {
                do {
                    try FileManager.default.moveItem(at: location, to: target)
                    let attributes = try FileManager.default.attributesOfItem(atPath: target.path)
                    bytes = (attributes[FileAttributeKey.size] as? NSNumber)?.int64Value ?? 0
                    if bytes < 20_000 { failure = "the download was too small to be a video (\(bytes) bytes)" }
                } catch {
                    failure = "the downloaded file could not be kept"
                }
            } else {
                failure = "the download returned nothing"
            }
            let failureText = failure
            let size = bytes
            DispatchQueue.main.async {
                guard let self = self, !self.cancelled else {
                    try? FileManager.default.removeItem(at: target)
                    return
                }
                if let failureText = failureText {
                    try? FileManager.default.removeItem(at: target)
                    self.note?("Download", "address \(index + 1): " + failureText)
                    self.attempt(index + 1, lastError: "The clip's video could not be downloaded: " + failureText + ".")
                } else {
                    self.note?("Download", String(format: "HTTP %d, %.1f MB", status, Double(size) / 1_048_576.0))
                    self.finish(target, nil)
                }
            }
        }
        task = newTask
        newTask.resume()
    }

    private func finish(_ file: URL?, _ error: String?) {
        let done = completion
        completion = nil
        note = nil
        task = nil
        session?.finishTasksAndInvalidate()
        session = nil
        done?(file, error)
    }

    private static func cookie(_ cookie: HTTPCookie, belongsTo host: String) -> Bool {
        var domain = cookie.domain.lowercased()
        if domain.hasPrefix(".") { domain = String(domain.dropFirst()) }
        let lowerHost = host.lowercased()
        return !domain.isEmpty && (lowerHost == domain || lowerHost.hasSuffix("." + domain))
    }
}
```

##### File: `iosApp/iosApp/ClipFinder/ClipAudioReader.swift`
```swift
import AVFoundation
import Foundation

struct ClipAudio {
    let samples: [Int16]
    let sampleRate: Int
    let error: String?
}

/// Reads a video file's sound into memory as 16-bit mono (6 minutes at 16 kHz is about 12 MB) and
/// writes short WAV parts for the speech recogniser. No main-thread needs: plain functions.
enum ClipAudioReader {
    private static let maxClipSeconds = 600.0

    /// Runs on a background queue. Reads at most 10 minutes of sound as 16-bit mono.
    static func read(_ fileURL: URL) -> ClipAudio {
        let asset = AVURLAsset(url: fileURL)
        guard let track = asset.tracks(withMediaType: .audio).first else {
            return ClipAudio(samples: [], sampleRate: 16000, error: "This video has no sound track, or the file could not be opened.")
        }
        let reader: AVAssetReader
        do {
            reader = try AVAssetReader(asset: asset)
        } catch {
            return ClipAudio(samples: [], sampleRate: 16000, error: "The video could not be read (" + error.localizedDescription + ").")
        }
        let settings: [String: Any] = [
            AVFormatIDKey: kAudioFormatLinearPCM,
            AVSampleRateKey: 16000,
            AVNumberOfChannelsKey: 1,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsFloatKey: false,
            AVLinearPCMIsBigEndianKey: false,
            AVLinearPCMIsNonInterleaved: false,
        ]
        let output = AVAssetReaderAudioMixOutput(audioTracks: [track], audioSettings: settings)
        output.alwaysCopiesSampleData = false
        guard reader.canAdd(output) else {
            return ClipAudio(samples: [], sampleRate: 16000, error: "The sound of this video cannot be decoded.")
        }
        reader.add(output)
        guard reader.startReading() else {
            let reason = reader.error?.localizedDescription ?? "unknown reason"
            return ClipAudio(samples: [], sampleRate: 16000, error: "The sound of this video cannot be decoded (" + reason + ").")
        }
        var samples: [Int16] = []
        var rate = 16000
        var channels = 1
        var formatKnown = false
        while let buffer = output.copyNextSampleBuffer() {
            if !formatKnown, let description = CMSampleBufferGetFormatDescription(buffer),
               let basic = CMAudioFormatDescriptionGetStreamBasicDescription(description)?.pointee {
                formatKnown = true
                rate = max(8000, Int(basic.mSampleRate))
                channels = max(1, Int(basic.mChannelsPerFrame))
                if basic.mBitsPerChannel != 16 {
                    reader.cancelReading()
                    return ClipAudio(samples: [], sampleRate: rate, error: "The sound of this video came in an unexpected format.")
                }
                samples.reserveCapacity(rate * 120)
            }
            guard let block = CMSampleBufferGetDataBuffer(buffer) else { continue }
            let count = CMBlockBufferGetDataLength(block) / 2
            if count == 0 { continue }
            var part = [Int16](repeating: 0, count: count)
            let status = part.withUnsafeMutableBytes { raw -> OSStatus in
                guard let base = raw.baseAddress else { return -1 }
                return CMBlockBufferCopyDataBytes(block, atOffset: 0, dataLength: count * 2, destination: base)
            }
            if status != kCMBlockBufferNoErr { continue }
            if channels == 1 {
                samples.append(contentsOf: part)
            } else {
                var frame = 0
                while (frame + 1) * channels <= count {
                    var total = 0
                    for channel in 0..<channels { total += Int(part[frame * channels + channel]) }
                    samples.append(Int16(total / channels))
                    frame += 1
                }
            }
            if Double(samples.count) / Double(rate) >= maxClipSeconds { break }
        }
        reader.cancelReading()
        if samples.isEmpty {
            return ClipAudio(samples: [], sampleRate: rate, error: "No sound could be read from this video.")
        }
        return ClipAudio(samples: samples, sampleRate: rate, error: nil)
    }

    /// A WAV file (16-bit mono) of one part, made louder by `gain` and clipped to the valid range.
    static func wav(_ part: ArraySlice<Int16>, sampleRate: Int, gain: Float) -> Data {
        let byteCount = UInt32(part.count * 2)
        var header: [UInt8] = []
        header += Array("RIFF".utf8)
        header += le32(36 + byteCount)
        header += Array("WAVE".utf8)
        header += Array("fmt ".utf8)
        header += le32(16)
        header += le16(1)
        header += le16(1)
        header += le32(UInt32(sampleRate))
        header += le32(UInt32(sampleRate * 2))
        header += le16(2)
        header += le16(16)
        header += Array("data".utf8)
        header += le32(byteCount)
        var scaled: [Int16] = []
        scaled.reserveCapacity(part.count)
        for sample in part {
            let value = Float(sample) * gain
            scaled.append(Int16(max(Float(-32768), min(Float(32767), value))))
        }
        var data = Data(header)
        scaled.withUnsafeBufferPointer { pointer in
            data.append(pointer)
        }
        return data
    }

    private static func le32(_ value: UInt32) -> [UInt8] {
        [UInt8(value & 0xff), UInt8((value >> 8) & 0xff), UInt8((value >> 16) & 0xff), UInt8((value >> 24) & 0xff)]
    }

    private static func le16(_ value: UInt16) -> [UInt8] {
        [UInt8(value & 0xff), UInt8((value >> 8) & 0xff)]
    }
}
```

##### File: `iosApp/iosApp/ClipFinder/ClipTranscriber.swift`
```swift
import AVFoundation
import Foundation
import Speech

/// Turns a video file's sound into text on this iPhone: reads the sound as 16 kHz mono, lifts quiet
/// clips, cuts it into 30 s parts (one long request only returns the last sentence) and runs Apple's
/// on-device recogniser on each part. Call it on the main thread only; it answers on the main thread.
final class ClipTranscriber {
    private struct Word {
        let text: String
        let start: Double
        let end: Double
    }

    private static let partSeconds = 30.0
    private static let stepSeconds = 28.0
    private static let partTimeout = 45.0
    private static let totalTimeout = 300.0
    private static let wordsPerLine = 10

    private var note: ((String, String) -> Void)?
    private var line: ((String, Int64, Int64) -> Void)?
    private var completion: ((String?) -> Void)?
    private var cancelled = false
    private var started = Date()
    private var recognizer: SFSpeechRecognizer?
    private var task: SFSpeechRecognitionTask?
    private var samples: [Int16] = []
    private var sampleRate = 16000
    private var gain: Float = 1
    private var partIndex = 0
    private var partCount = 0
    private var partToken = 0
    private var closedToken = 0
    private var partFile: URL?
    private var partOffset = 0.0
    private var partLength = 0.0
    private var committed: [Word] = []
    private var latest: [Word] = []

    func transcribe(
        fileURL: URL,
        note: @escaping (String, String) -> Void,
        line: @escaping (String, Int64, Int64) -> Void,
        completion: @escaping (String?) -> Void
    ) {
        self.note = note
        self.line = line
        self.completion = completion
        started = Date()
        SFSpeechRecognizer.requestAuthorization { [weak self] status in
            DispatchQueue.main.async {
                self?.authorized(status, fileURL: fileURL)
            }
        }
    }

    func cancel() {
        cancelled = true
        completion = nil
        note = nil
        line = nil
        cleanUp()
    }

    private func authorized(_ status: SFSpeechRecognizerAuthorizationStatus, fileURL: URL) {
        guard !cancelled else { return }
        guard status == .authorized else {
            finish("Speech recognition is switched off for Nuvio. Allow it in Settings > Apps > Nuvio > Speech Recognition, then try again.")
            return
        }
        guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US")), recognizer.supportsOnDeviceRecognition else {
            finish("This iPhone has no on-device English speech recognition yet. Switch on Settings > General > Keyboard > Enable Dictation with English (US), wait a few minutes for the download, then try again.")
            return
        }
        guard recognizer.isAvailable else {
            finish("Speech recognition is not available right now. Try again in a minute.")
            return
        }
        self.recognizer = recognizer
        note?("Speech", "on this iPhone, English (US)")
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let audio = ClipAudioReader.read(fileURL)
            DispatchQueue.main.async {
                self?.audioRead(audio)
            }
        }
    }

    private func audioRead(_ audio: ClipAudio) {
        guard !cancelled else { return }
        if let error = audio.error {
            finish(error)
            return
        }
        samples = audio.samples
        sampleRate = audio.sampleRate
        let seconds = Double(samples.count) / Double(sampleRate)
        note?("Audio", String(format: "%.0f s", seconds))
        guard seconds >= 1.0 else {
            finish("The clip is too short to listen to.")
            return
        }
        var sum = 0.0
        for sample in samples {
            let value = Double(sample) / 32768.0
            sum += value * value
        }
        let rms = (sum / Double(samples.count)).squareRoot()
        let level = rms > 0 ? 20.0 * log10(rms) : -120.0
        gain = rms > 0 ? Float(min(max(0.1 / rms, 1.0), 40.0)) : 1
        note?("Loudness", String(format: "%.0f dB, made %.1f times louder", level, Double(gain)))
        partCount = max(1, Int(((max(seconds - 2.0, 1.0)) / ClipTranscriber.stepSeconds).rounded(.up)))
        partIndex = 0
        nextPart()
    }

    private func nextPart() {
        guard !cancelled else { return }
        if partIndex >= partCount {
            finish(nil)
            return
        }
        if Date().timeIntervalSince(started) > ClipTranscriber.totalTimeout {
            note?("Listening", "stopped at the time limit, part \(partIndex) of \(partCount)")
            finish(nil)
            return
        }
        guard let recognizer = recognizer else {
            finish("Speech recognition stopped.")
            return
        }
        let first = Int(Double(partIndex) * ClipTranscriber.stepSeconds * Double(sampleRate))
        let last = min(samples.count, first + Int(ClipTranscriber.partSeconds * Double(sampleRate)))
        guard first < last, last - first > sampleRate / 2 else {
            partIndex += 1
            nextPart()
            return
        }
        note?("Listening", "part \(partIndex + 1) of \(partCount)")
        let file = FileManager.default.temporaryDirectory.appendingPathComponent("nuvio-clip-part-" + UUID().uuidString + ".wav")
        do {
            try ClipAudioReader.wav(samples[first..<last], sampleRate: sampleRate, gain: gain).write(to: file)
        } catch {
            finish("There is no room to store a short sound file.")
            return
        }
        partFile = file
        partOffset = Double(first) / Double(sampleRate)
        partLength = Double(last - first) / Double(sampleRate)
        committed = []
        latest = []
        partToken += 1
        let token = partToken
        let request = SFSpeechURLRecognitionRequest(url: file)
        request.requiresOnDeviceRecognition = true
        request.shouldReportPartialResults = true
        request.taskHint = .dictation
        task = recognizer.recognitionTask(with: request) { [weak self] result, error in
            var words: [Word]?
            if let result = result {
                words = result.bestTranscription.segments.map { segment in
                    Word(text: segment.substring, start: segment.timestamp, end: segment.timestamp + segment.duration)
                }
            }
            let found = words
            let done = (result?.isFinal ?? false) || error != nil
            DispatchQueue.main.async {
                self?.heard(token: token, words: found, done: done)
            }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + ClipTranscriber.partTimeout) { [weak self] in
            self?.heard(token: token, words: nil, done: true)
        }
    }

    /// The recogniser reports the growing sentence again and again, and starts from nothing after a
    /// pause. Each finished sentence is kept before the next one replaces it.
    private func heard(token: Int, words: [Word]?, done: Bool) {
        guard !cancelled, token == partToken, token != closedToken else { return }
        if let words = words, !words.isEmpty {
            if ClipTranscriber.startsNewSentence(words, after: latest) {
                committed.append(contentsOf: latest)
            }
            latest = words
        }
        guard done else { return }
        closedToken = token
        task?.cancel()
        task = nil
        if let file = partFile { try? FileManager.default.removeItem(at: file) }
        partFile = nil
        committed.append(contentsOf: latest)
        latest = []
        sendLines()
        partIndex += 1
        nextPart()
    }

    private static func startsNewSentence(_ new: [Word], after old: [Word]) -> Bool {
        guard let oldLast = old.last, let newFirst = new.first else { return false }
        if oldLast.start > 0 && newFirst.start > oldLast.start { return true }
        return old.count >= 3 && new.count * 2 < old.count
    }

    private func sendLines() {
        var index = 0
        while index < committed.count {
            let end = min(index + ClipTranscriber.wordsPerLine, committed.count)
            let group = Array(committed[index..<end])
            index = end
            let text = group.map { $0.text }.joined(separator: " ")
            let timed = group[group.count - 1].end > 0
            let startSeconds = partOffset + (timed ? group[0].start : 0)
            let endSeconds = partOffset + (timed ? max(group[group.count - 1].end, group[0].start) : partLength)
            line?(text, Int64(startSeconds * 1000.0), Int64(endSeconds * 1000.0))
        }
        committed = []
    }

    private func finish(_ error: String?) {
        let done = completion
        completion = nil
        note = nil
        line = nil
        cleanUp()
        done?(error)
    }

    private func cleanUp() {
        task?.cancel()
        task = nil
        if let file = partFile { try? FileManager.default.removeItem(at: file) }
        partFile = nil
        samples = []
        recognizer = nil
    }
}
```

##### File: `iosApp/iosApp/ClipFinder/ClipFinderNativeImpl.swift`
```swift
import Foundation
import ComposeApp

enum ClipFinderRegistration {
    static func register() {
        ClipFinderBridge.shared.register(impl: ClipFinderNativeImpl())
    }
}

/// Keeps the URL objects iOS hands over for shared video files: only those objects carry the right
/// to read a file that lives outside the app. Main thread only.
final class ClipFileInbox {
    static let shared = ClipFileInbox()
    private var urls: [String: URL] = [:]

    private init() {}

    func remember(_ url: URL) {
        if url.isFileURL { urls[url.absoluteString] = url }
    }

    func url(for source: String) -> URL? {
        urls[source] ?? URL(string: source)
    }
}

/// The Swift side of the Kotlin interface ClipFinderNative. Kotlin may call from any thread; all work
/// is moved to the main thread, and every listener call is made on the main thread.
final class ClipFinderNativeImpl: NSObject, ClipFinderNative {
    private let cache = ClipSubtitleDiskCache()
    private var run = 0
    private var pageReader: ClipPageReader?
    private var fetcher: ClipMediaFetcher?
    private var transcriber: ClipTranscriber?
    private var afterListening: (() -> Void)?
    private var cookies: [HTTPCookie] = []
    private var userAgent = ""

    func readPage(link: String, listener: ClipNativeListener) {
        DispatchQueue.main.async {
            self.stopWork()
            self.run += 1
            let run = self.run
            let reader = ClipPageReader()
            self.pageReader = reader
            reader.read(link: link, note: { label, value in
                listener.onNote(label: label, value: value)
            }, completion: { result in
                guard run == self.run else { return }
                self.pageReader = nil
                self.cookies = result.cookies
                self.userAgent = result.userAgent
                if let page = result.pageJson {
                    listener.onPage(pageJson: page)
                } else {
                    listener.onFailed(stage: "Reading link", message: result.error ?? "The page could not be read.")
                }
            })
        }
    }

    func listen(mediaUrls: [String], pageUrl: String, listener: ClipNativeListener) {
        DispatchQueue.main.async {
            self.stopWork()
            self.run += 1
            let run = self.run
            guard let first = mediaUrls.first else {
                listener.onFailed(stage: "Reading link", message: "No video address was found.")
                return
            }
            if first.lowercased().hasPrefix("file:") {
                guard let file = ClipFileInbox.shared.url(for: first) else {
                    listener.onFailed(stage: "Listening", message: "The shared video could not be found.")
                    return
                }
                let scoped = file.startAccessingSecurityScopedResource()
                self.transcribe(file, run: run, listener: listener) {
                    if scoped { file.stopAccessingSecurityScopedResource() }
                }
                return
            }
            let fetcher = ClipMediaFetcher()
            self.fetcher = fetcher
            listener.onNote(label: "Download", value: "started")
            fetcher.fetch(urls: mediaUrls, pageUrl: pageUrl, cookies: self.cookies, userAgent: self.userAgent, note: { label, value in
                listener.onNote(label: label, value: value)
            }, completion: { file, error in
                guard run == self.run else {
                    if let file = file { try? FileManager.default.removeItem(at: file) }
                    return
                }
                self.fetcher = nil
                guard let file = file else {
                    listener.onFailed(stage: "Reading link", message: error ?? "The clip's video could not be downloaded.")
                    return
                }
                self.transcribe(file, run: run, listener: listener) {
                    try? FileManager.default.removeItem(at: file)
                }
            })
        }
    }

    func cancel() {
        DispatchQueue.main.async {
            self.run += 1
            self.stopWork()
        }
    }

    func cacheRead(key: String) -> String? {
        cache.read(key)
    }

    func cacheWrite(key: String, text: String) {
        cache.write(key, text)
    }

    private func transcribe(_ file: URL, run: Int, listener: ClipNativeListener, cleanUp: @escaping () -> Void) {
        let transcriber = ClipTranscriber()
        self.transcriber = transcriber
        afterListening = cleanUp
        transcriber.transcribe(fileURL: file, note: { label, value in
            listener.onNote(label: label, value: value)
        }, line: { text, startMs, endMs in
            listener.onLine(text: text, startMs: startMs, endMs: endMs)
        }, completion: { error in
            guard run == self.run else { return }
            self.transcriber = nil
            self.runAfterListening()
            if let error = error {
                listener.onFailed(stage: "Listening", message: error)
            } else {
                listener.onDone()
            }
        })
    }

    private func stopWork() {
        pageReader?.cancel()
        pageReader = nil
        fetcher?.cancel()
        fetcher = nil
        transcriber?.cancel()
        transcriber = nil
        runAfterListening()
    }

    private func runAfterListening() {
        let work = afterListening
        afterListening = nil
        work?()
    }
}

/// Subtitle text the search already fetched, kept in the app's Caches folder (iOS may empty it).
/// Capped at about 50 MB: the oldest files go first. Safe to call from any thread.
final class ClipSubtitleDiskCache {
    private struct Entry {
        let url: URL
        let size: Int
        let date: Date
    }

    private static let maxBytes = 50 * 1024 * 1024
    private static let trimToBytes = 40 * 1024 * 1024

    private let folder: URL
    private let lock = NSLock()
    private var writes = 0

    init() {
        let base = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory
        folder = base.appendingPathComponent("clipfinder-subs", isDirectory: true)
        try? FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
    }

    func read(_ key: String) -> String? {
        try? String(contentsOf: file(key), encoding: .utf8)
    }

    func write(_ key: String, _ text: String) {
        guard !text.isEmpty, text.utf8.count <= 2_000_000 else { return }
        try? text.write(to: file(key), atomically: true, encoding: .utf8)
        lock.lock()
        writes += 1
        let due = writes % 40 == 1
        lock.unlock()
        if due { trim() }
    }

    private func file(_ key: String) -> URL {
        var safe = ""
        for character in key.prefix(120) {
            safe.append(character.isLetter || character.isNumber || character == "-" || character == "." ? character : "_")
        }
        return folder.appendingPathComponent(safe + ".txt")
    }

    private func trim() {
        lock.lock()
        defer { lock.unlock() }
        let keys: [URLResourceKey] = [.fileSizeKey, .contentModificationDateKey]
        guard let files = try? FileManager.default.contentsOfDirectory(at: folder, includingPropertiesForKeys: keys) else { return }
        var entries: [Entry] = []
        var total = 0
        for url in files {
            let values = try? url.resourceValues(forKeys: Set(keys))
            let size = values?.fileSize ?? 0
            entries.append(Entry(url: url, size: size, date: values?.contentModificationDate ?? Date.distantPast))
            total += size
        }
        guard total > ClipSubtitleDiskCache.maxBytes else { return }
        for entry in entries.sorted(by: { $0.date < $1.date }) {
            if total <= ClipSubtitleDiskCache.trimToBytes { break }
            try? FileManager.default.removeItem(at: entry.url)
            total -= entry.size
        }
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ShowGuesser.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlinx.coroutines.CancellationException

/** A season and episode named in the caption ("S2E5", "season 2 episode 5", "2x05"). */
data class ClipHint(val season: Int? = null, val episode: Int? = null)

/** A show or movie from Nuvio's own search that the caption may be about. */
data class ShowGuess(val metaId: String, val type: String, val name: String, val poster: String? = null)

/**
 * Caption -> search words -> up to 3 shows. A guess is only a candidate: the subtitle match
 * decides, so a wrong guess costs time but never gives a wrong answer.
 */
object ShowGuesser {
    private const val MAX_QUERIES = 6
    private val seasonEpisode = listOf(
        Regex("""\bs(\d{1,2})\s*[-.:,]?\s*e(?:p(?:isode)?)?\s*(\d{1,3})\b""", RegexOption.IGNORE_CASE),
        Regex("""\bseason\s*(\d{1,2})\W{0,3}ep(?:isode)?\W{0,2}(\d{1,3})\b""", RegexOption.IGNORE_CASE),
        Regex("""\b(\d{1,2})x(\d{2,3})\b"""),
    )
    private val seasonOnly = Regex("""\bseason\s*(\d{1,2})\b""", RegexOption.IGNORE_CASE)
    private val link = Regex("""https?://\S+""")
    private val joiners = setOf("of", "the", "and", "in", "a", "is", "to")

    /** Hashtags that never name a show. Lowercase. */
    private val genericTags = setOf(
        "fyp", "fy", "fypage", "foryou", "foryoupage", "foryourpage", "viral", "trending", "xyzbca", "tiktok",
        "reels", "reel", "explore", "shorts", "capcut", "edit", "edits", "tv", "tvshow", "tvshows", "tvseries",
        "series", "show", "movie", "movies", "film", "films", "clip", "clips", "tvclips", "movieclips", "scene",
        "scenes", "moments", "bestmoments", "funny", "comedy", "humor", "lol", "drama", "sitcom", "cartoon",
        "animation", "netflix", "hbo", "hulu", "prime", "disney", "parati", "best",
    )

    fun hint(caption: String): ClipHint {
        for (pattern in seasonEpisode) {
            val match = pattern.find(caption) ?: continue
            return ClipHint(match.groupValues[1].toIntOrNull(), match.groupValues[2].toIntOrNull())
        }
        return ClipHint(seasonOnly.find(caption)?.groupValues?.get(1)?.toIntOrNull(), null)
    }

    /** Search words to try, best first, at most 6. */
    fun queries(caption: String): List<String> {
        val text = caption.replace(link, " ")
        val tokens = text.split(Regex("""\s+""")).filter { it.isNotBlank() }
        val tags = tokens.filter { it.startsWith("#") }
            .map { token -> token.drop(1).takeWhile { it.isLetterOrDigit() || it == '_' } }
            .filter { it.length >= 3 && it.lowercase() !in genericTags }
        val plainTokens = tokens.filter { !it.startsWith("#") && !it.startsWith("@") }
        val plain = plainTokens.joinToString(" ")

        val result = mutableListOf<String>()
        // 1. the words just before "S2E5"
        seasonEpisode.firstNotNullOfOrNull { it.find(plain) }?.let { match ->
            val before = words(plain.substring(0, match.range.first)).takeLast(4)
            for (count in listOf(4, 2, 1)) {
                if (before.isNotEmpty()) result += before.takeLast(count).joinToString(" ")
            }
        }
        // 2. runs of Capitalised Words ("South Park", "Lord of the Rings")
        result += capitalisedRuns(plainTokens)
        // 3. hashtags, "SouthPark" split into "South Park"
        for (tag in tags) {
            val split = splitCamel(tag)
            result += split
            if (split != tag) result += tag
        }
        // 4. a short caption as a whole
        val all = words(plain)
        if (all.size in 1..5) result += all.joinToString(" ")
        // 5. nothing better: the first words, and the longest word
        if (result.isEmpty() && all.isNotEmpty()) {
            result += all.take(4).joinToString(" ")
            result += all.maxByOrNull { it.length }.orEmpty()
        }
        return result.map { it.trim() }.filter { it.length >= 3 }.distinctBy { it.lowercase() }.take(MAX_QUERIES)
    }

    /**
     * Runs [search] for each query and keeps results whose name fits the caption. Score: the name
     * equals the query 100; the caption holds the whole name 90; the name starts with the query 60;
     * the first result of a query 30. Earlier queries and higher results win ties. Stops at the
     * first query that gives a result named exactly like it.
     */
    suspend fun guess(caption: String, search: suspend (String) -> List<ShowGuess>, max: Int = 3): List<ShowGuess> {
        val captionKey = squash(caption)
        val scored = LinkedHashMap<String, Pair<ShowGuess, Int>>()
        for ((queryIndex, query) in queries(caption).withIndex()) {
            val results = try {
                search(query)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                emptyList()
            }
            for ((rank, result) in results.take(8).withIndex()) {
                val score = score(result.name, query, captionKey, rank) - queryIndex - rank
                if (score <= 0) continue
                val old = scored[result.metaId]
                if (old == null || old.second < score) scored[result.metaId] = result to score
            }
            if (scored.values.any { it.second >= 95 }) break
        }
        return scored.values.sortedByDescending { it.second }.map { it.first }.take(max)
    }

    private fun score(name: String, query: String, captionKey: String, rank: Int): Int {
        val nameKey = squash(name)
        val queryKey = squash(query)
        return when {
            nameKey.isEmpty() || queryKey.isEmpty() -> 0
            nameKey == queryKey -> 100
            nameKey.length >= 4 && nameKey in captionKey -> 90
            queryKey.length >= 4 && nameKey.startsWith(queryKey) -> 60
            rank == 0 -> 30
            else -> 0
        }
    }

    /** Letters and digits only, lowercase, no spaces: "South Park!" and "#southpark" both give "southpark". */
    internal fun squash(text: String): String = ClipText.normalize(text.replace('#', ' ')).joinToString("")

    /** Words of letters, digits and apostrophes. Done by hand: no Unicode classes in a Regex (they differ on iOS). */
    private fun words(text: String): List<String> {
        val result = mutableListOf<String>()
        val current = StringBuilder()
        for (char in text) {
            if (char.isLetterOrDigit() || char == '\'') {
                current.append(char)
            } else if (current.isNotEmpty()) {
                result += current.toString()
                current.clear()
            }
        }
        if (current.isNotEmpty()) result += current.toString()
        return result
    }

    private fun capitalisedRuns(tokens: List<String>): List<String> {
        val runs = mutableListOf<String>()
        val current = mutableListOf<String>()
        fun flush() {
            while (current.isNotEmpty() && current.last().lowercase() in joiners) current.removeAt(current.size - 1)
            if (current.size >= 2) runs += current.joinToString(" ")
            current.clear()
        }
        for (token in tokens) {
            val word = token.trim { !it.isLetterOrDigit() }
            val capital = word.isNotEmpty() && word.first().isUpperCase() && word.none { it.isDigit() }
            val joins = current.isNotEmpty() && word.lowercase() in joiners
            if (capital || joins) current += word else flush()
            if (token.isNotEmpty() && token.last() in ".!?:;,") flush()
        }
        flush()
        return runs
    }

    private fun splitCamel(tag: String): String {
        val out = StringBuilder()
        for ((index, char) in tag.withIndex()) {
            if (index > 0 && char.isUpperCase() && tag[index - 1].isLowerCase()) out.append(' ')
            out.append(if (char == '_') ' ' else char)
        }
        return out.toString()
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/EpisodeSubtitleSource.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import com.nuvio.app.features.player.PlayerSubtitleCueParser
import com.nuvio.app.features.player.SubtitleSyncCue
import com.nuvio.app.features.player.normalizeLanguageCode
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withTimeoutOrNull

/**
 * One episode (or a movie: season and episode null). [videoId] is what the streams screen needs,
 * [subtitleId] what subtitle add-ons need (an IMDb id such as "tt0121955:14:2").
 */
data class ClipEpisode(
    val videoId: String,
    val subtitleId: String,
    val type: String,
    val season: Int? = null,
    val episode: Int? = null,
    val title: String? = null,
    val thumbnail: String? = null,
)

data class ClipSubtitleLink(val url: String, val language: String)

interface ClipSubtitleCache {
    fun read(key: String): String?
    fun write(key: String, text: String)
}

/** The hinted episode first, then the rest of its season, then everything else in order. At most 400. */
fun orderEpisodes(episodes: List<ClipEpisode>, hint: ClipHint): List<ClipEpisode> =
    episodes.sortedWith(
        compareBy<ClipEpisode>(
            { if (hint.season != null && it.season == hint.season && hint.episode != null && it.episode == hint.episode) 0 else 1 },
            { if (hint.season != null && it.season == hint.season) 0 else 1 },
            { it.season ?: 0 },
            { it.episode ?: 0 },
        ),
    ).take(400)

/**
 * Fetches one English subtitle per episode through the installed subtitle add-ons, at most
 * [inFlight] episodes at a time, and matches as it goes so it can stop at a decisive match.
 */
class EpisodeSubtitleSource(
    private val listSubtitles: suspend (type: String, subtitleId: String) -> List<ClipSubtitleLink>,
    private val download: suspend (url: String) -> String,
    private val cache: ClipSubtitleCache,
    private val now: () -> Long,
    private val inFlight: Int = 6,
) {
    data class SearchResult(
        /** The episodes behind [candidates], to carry into the search of the next show. */
        val best: List<EpisodeCues>,
        val candidates: List<ClipCandidate>,
        val tried: Int,
        val withSubtitles: Int,
        val decisive: Boolean,
    )

    /**
     * Goes through [episodes] in order, [inFlight] at a time, until all are tried, [deadlineMs]
     * (a [now] value) passes, or the best candidate is decisive. [keep] holds the best episodes of
     * shows searched before, so the candidates rank across shows. Matching only the best so far
     * plus the new batch gives the same top 3 as matching everything, because each episode is
     * scored on its own.
     */
    suspend fun search(
        showId: String,
        episodes: List<ClipEpisode>,
        lines: List<ClipLine>,
        deadlineMs: Long,
        keep: List<EpisodeCues> = emptyList(),
        onProgress: (tried: Int, total: Int, withSubtitles: Int) -> Unit = { _, _, _ -> },
    ): SearchResult {
        var best = keep
        var candidates = if (keep.isEmpty()) emptyList() else ClipMatcher.match(lines, keep)
        var tried = 0
        var withSubtitles = 0
        for (batch in episodes.chunked(inFlight)) {
            if (now() >= deadlineMs) break
            val loaded = coroutineScope {
                batch.map { episode -> async { episode to cues(showId, episode) } }.awaitAll()
            }
            tried += batch.size
            val fresh = loaded.mapNotNull { (episode, cues) ->
                cues?.let { EpisodeCues(episode.videoId, episode.season, episode.episode, it) }
            }
            withSubtitles += fresh.size
            if (fresh.isNotEmpty()) {
                val pool = best + fresh
                candidates = ClipMatcher.match(lines, pool)
                best = candidates.mapNotNull { candidate -> pool.firstOrNull { it.videoId == candidate.videoId } }
            }
            onProgress(tried, episodes.size, withSubtitles)
            if (isDecisive(candidates)) return SearchResult(best, candidates, tried, withSubtitles, decisive = true)
        }
        return SearchResult(best, candidates, tried, withSubtitles, decisive = false)
    }

    /** Cues of one episode: from the cache, else the first English subtitle that parses (2 tried). Null when none. */
    suspend fun cues(showId: String, episode: ClipEpisode): List<SubtitleSyncCue>? {
        val key = "$showId/${episode.videoId}"
        val cached = runCatching { cache.read(key) }.getOrNull()?.let { decodeCues(it) }
        if (!cached.isNullOrEmpty()) return cached
        val links = quietly(LIST_TIMEOUT_MS) { listSubtitles(episode.type, episode.subtitleId) }.orEmpty()
            .filter { isEnglish(it.language) }
            .take(2)
        for (link in links) {
            val text = quietly(FILE_TIMEOUT_MS) { download(link.url) } ?: continue
            val cues = runCatching { PlayerSubtitleCueParser.parse(text, link.url) }.getOrDefault(emptyList())
            if (cues.size < MIN_CUES) continue
            runCatching { cache.write(key, encodeCues(cues)) }
            return cues
        }
        return null
    }

    /** Null on a time-out or any failure; cancelling the search still cancels. */
    private suspend fun <T> quietly(timeoutMs: Long, block: suspend () -> T): T? =
        withTimeoutOrNull(timeoutMs) {
            try {
                block()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                null
            }
        }

    companion object {
        const val DECISIVE_HITS = 8
        private const val MIN_CUES = 20
        private const val LIST_TIMEOUT_MS = 12_000L
        private const val FILE_TIMEOUT_MS = 15_000L
        private const val LINE_BREAK = '\u001F'

        /** Confident (the matcher's own rule) and at least 8 shared word triples: stop searching. */
        fun isDecisive(candidates: List<ClipCandidate>): Boolean =
            candidates.firstOrNull()?.let { it.confident && it.hits >= DECISIVE_HITS } == true

        fun isEnglish(language: String): Boolean {
            val code = (normalizeLanguageCode(language) ?: language).lowercase()
            return code == "en" || code == "eng" || code.startsWith("en-")
        }

        /** One cue per line: start, end, text, separated by tabs. Line breaks inside a cue are kept as a control character. */
        fun encodeCues(cues: List<SubtitleSyncCue>): String = cues.joinToString("\n") { cue ->
            "${cue.startTimeMs}\t${cue.endTimeMs}\t${cue.text.replace('\t', ' ').replace('\n', LINE_BREAK)}"
        }

        fun decodeCues(text: String): List<SubtitleSyncCue> = text.lineSequence().mapNotNull { line ->
            val parts = line.split('\t', limit = 3)
            if (parts.size < 3) return@mapNotNull null
            val start = parts[0].toLongOrNull() ?: return@mapNotNull null
            val end = parts[1].toLongOrNull() ?: return@mapNotNull null
            SubtitleSyncCue(start, end, parts[2].replace(LINE_BREAK, '\n'))
        }.toList()
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderState.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.math.roundToInt

enum class ClipStage { ReadingLink, Listening, Searching, Done }

/** One diagnostic line on the screen ("Audio: 312 s"). Real data from the run, so a screenshot shows where it broke. */
data class ClipNote(val label: String, val value: String)

data class ClipAnswer(
    val candidate: ClipCandidate,
    val show: ShowGuess,
    val episodeTitle: String? = null,
    val thumbnail: String? = null,
)

data class ClipFinderState(
    val source: String = "",
    /** The stage that runs now, or the one that failed when [failed] is true. */
    val stage: ClipStage = ClipStage.ReadingLink,
    val failed: Boolean = false,
    val message: String = "",
    val showFileHint: Boolean = false,
    val progress: String = "",
    val notes: List<ClipNote> = emptyList(),
    val lines: List<ClipLine> = emptyList(),
    val answers: List<ClipAnswer> = emptyList(),
) {
    /** A note with the same label is replaced where it stands; a new label goes to the end. */
    fun withNote(label: String, value: String): ClipFinderState {
        val note = ClipNote(label, value)
        val index = notes.indexOfFirst { it.label == label }
        return copy(notes = if (index < 0) notes + note else notes.toMutableList().also { it[index] = note })
    }
}

internal const val CLIP_LEAD_IN_MS = 10_000L

internal object ClipMessages {
    const val NO_BRIDGE = "Clip finder only works in the iPhone app."
    const val PAGE_TIMEOUT = "Reading the link took longer than 45 s."
    const val PAGE_FAILED = "The page could not be read."
    const val NO_VIDEO = "Nuvio could not find the video's address on the page. The site may have asked for a login or changed its page."
    const val LISTEN_TIMEOUT = "Listening took longer than 7 minutes and was stopped."
    const val NO_SPEECH = "No speech was heard in this clip (music only, or not in English)."
    const val NO_CAPTION = "This clip has no caption, so Nuvio cannot guess the show. Typing the show name comes in the next update."
    const val NO_SHOW = "No show or movie in your catalogs matches the caption. Typing the show name comes in the next update."
    const val NO_EPISODES = "The episode list of the guessed shows could not be loaded."
    const val NO_SUBTITLES = "No English subtitles were found. Check that a subtitle add-on (OpenSubtitles) is switched on in Nuvio."
    const val NO_MATCH = "No match: what was heard does not line up with the subtitles of the guessed shows."
    const val FILE_HINT = "Other way: save the video to your iPhone, then in the Files app hold it, tap Share and pick Nuvio."
    fun unexpected(error: Throwable): String = "Something went wrong: " + (error.message ?: error.toString()).take(200)
}

/** Where playback starts: 10 s before the matched moment, or right after it. */
internal fun clipStartMs(candidate: ClipCandidate, afterClip: Boolean): Long =
    if (afterClip) candidate.endMs else maxOf(0L, candidate.startMs - CLIP_LEAD_IN_MS)

/** "4:07" or "1:02:09". */
internal fun clipClock(ms: Long): String {
    val total = maxOf(0L, ms) / 1000
    val hours = total / 3600
    val minutes = (total % 3600) / 60
    val seconds = (total % 60).toString().padStart(2, '0')
    return if (hours > 0) "$hours:${minutes.toString().padStart(2, '0')}:$seconds" else "$minutes:$seconds"
}

/** "South Park, season 14 episode 2: Title" or just the movie's name. */
internal fun clipAnswerTitle(answer: ClipAnswer): String {
    val season = answer.candidate.season
    val episode = answer.candidate.episode
    if (season == null || episode == null) return answer.show.name
    val title = answer.episodeTitle?.takeIf { it.isNotBlank() }?.let { ": $it" }.orEmpty()
    return "${answer.show.name}, season $season episode $episode$title"
}

/** "at 4:07 to 9:30, 86% sure" or "..., 31% (weak)". */
internal fun clipAnswerDetail(answer: ClipAnswer): String {
    val c = answer.candidate
    val percent = (c.confidence * 100).roundToInt()
    return "at ${clipClock(c.startMs)} to ${clipClock(c.endMs)}, " + if (c.confident) "$percent% sure" else "$percent% (weak)"
}

/** "done", "now", "failed" or "" for stage number [index] (0..2) of CLIP_FINDER_STAGES. */
internal fun clipStageMark(state: ClipFinderState, index: Int): String = when {
    index < state.stage.ordinal -> "done"
    index > state.stage.ordinal -> ""
    state.failed -> "failed"
    else -> "now"
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderPipeline.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.coroutines.CoroutineContext
import kotlin.coroutines.resume
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

/**
 * The whole run for one shared clip: read the link, listen, search episodes. Everything that
 * touches the phone or the network is passed in, so this is tested with fakes.
 * Call [run] from the main thread; [emit] may be called from another thread.
 */
class ClipFinderPipeline(
    private val native: ClipFinderNative?,
    private val searchShows: suspend (query: String) -> List<ShowGuess>,
    private val loadEpisodes: suspend (ShowGuess) -> List<ClipEpisode>,
    private val subtitles: EpisodeSubtitleSource,
    private val now: () -> Long,
    private val work: CoroutineContext = Dispatchers.Default,
) {
    private class NativeResult(
        val page: String? = null,
        val lines: List<ClipLine> = emptyList(),
        val error: String? = null,
        val failedStage: String = "",
    )

    suspend fun run(source: String, emit: (ClipFinderState) -> Unit) {
        val run = Run(source, emit)
        try {
            run.stages()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            run.fail(ClipMessages.unexpected(e))
        }
    }

    private inner class Run(private val source: String, private val emit: (ClipFinderState) -> Unit) {
        private val state = MutableStateFlow(ClipFinderState(source = source))
        private val isFile = source.startsWith("file:", ignoreCase = true)

        fun change(block: (ClipFinderState) -> ClipFinderState) {
            state.update(block)
            emit(state.value)
        }

        fun note(label: String, value: String) = change { it.withNote(label, value) }

        fun fail(message: String, fileHint: Boolean = false) =
            change { it.copy(failed = true, message = message, showFileHint = fileHint, progress = "") }

        suspend fun stages() {
            emit(state.value)
            val phone = this@ClipFinderPipeline.native ?: return fail(ClipMessages.NO_BRIDGE)

            // 1. Reading link
            var caption = ""
            var mediaUrls = listOf(source)
            var pageUrl = ""
            if (!isFile) {
                val read = withTimeoutOrNull(PAGE_TIMEOUT_MS) { call { phone.readPage(source, it) } }
                    ?: return fail(ClipMessages.PAGE_TIMEOUT, fileHint = true)
                val pageJson = read.page ?: return fail(read.error ?: ClipMessages.PAGE_FAILED, fileHint = true)
                val page = ClipPageParser.parse(pageJson)
                caption = page.caption
                mediaUrls = page.videoUrls
                pageUrl = page.pageUrl.ifBlank { source }
                note("Caption", caption.ifBlank { "none" }.take(120))
                if (page.author.isNotBlank()) note("Author", page.author)
                note("Video address found", if (mediaUrls.isEmpty()) "no" else "yes (${mediaUrls.size})")
                if (mediaUrls.isEmpty()) return fail(ClipMessages.NO_VIDEO, fileHint = true)
            } else {
                change { it.copy(stage = ClipStage.Listening) }
            }

            // 2. Listening (for a link the download still counts as reading the link)
            val heard = withTimeoutOrNull(LISTEN_TIMEOUT_MS) { call { phone.listen(mediaUrls, pageUrl, it) } }
                ?: return fail(ClipMessages.LISTEN_TIMEOUT, fileHint = !isFile)
            if (heard.error != null) {
                if (heard.failedStage == CLIP_FINDER_STAGES[1]) change { it.copy(stage = ClipStage.Listening) }
                return fail(heard.error, fileHint = !isFile)
            }
            val lines = heard.lines
            change { it.copy(stage = ClipStage.Listening, lines = lines).withNote("Lines heard", lines.size.toString()) }
            if (lines.sumOf { ClipText.normalize(it.text).size } < MIN_WORDS) return fail(ClipMessages.NO_SPEECH)

            // 3. Searching episodes
            change { it.copy(stage = ClipStage.Searching, progress = "Guessing the show") }
            if (caption.isBlank()) return fail(ClipMessages.NO_CAPTION)
            val guesses = ShowGuesser.guess(caption, searchShows)
            note("Show guesses", guesses.joinToString { it.name }.ifBlank { "none" })
            if (guesses.isEmpty()) return fail(ClipMessages.NO_SHOW)
            val hint = ShowGuesser.hint(caption)
            val deadline = now() + SEARCH_BUDGET_MS
            val owners = mutableMapOf<String, Pair<ShowGuess, ClipEpisode>>()
            var best = emptyList<EpisodeCues>()
            var candidates = emptyList<ClipCandidate>()
            var tried = 0
            var withSubtitles = 0
            for (guess in guesses) {
                if (now() >= deadline) break
                change { it.copy(progress = "Loading the episode list of ${guess.name}") }
                val episodes = orderEpisodes(quietly { loadEpisodes(guess) }.orEmpty(), hint)
                if (episodes.isEmpty()) continue
                for (episode in episodes) owners[episode.videoId] = guess to episode
                val showDeadline = minOf(deadline, now() + SHOW_BUDGET_MS)
                val result = withContext(work) {
                    subtitles.search(guess.metaId, episodes, lines, showDeadline, best) { done, total, found ->
                        change { it.copy(progress = "Searching ${guess.name}: $done of $total episodes, $found with subtitles") }
                    }
                }
                best = result.best
                candidates = result.candidates
                tried += result.tried
                withSubtitles += result.withSubtitles
                if (result.decisive) break
                if (result.tried < episodes.size) note("Search", "stopped at the time limit in ${guess.name}")
            }
            note("Subtitles", "$withSubtitles of $tried episodes")
            if (tried == 0) return fail(ClipMessages.NO_EPISODES)
            if (withSubtitles == 0) return fail(ClipMessages.NO_SUBTITLES)
            val answers = candidates.filter { it.hits >= ClipMatcher.MIN_HITS }.mapNotNull { candidate ->
                owners[candidate.videoId]?.let { (show, episode) -> ClipAnswer(candidate, show, episode.title, episode.thumbnail) }
            }
            note("Candidates", answers.size.toString())
            if (answers.isEmpty()) return fail(ClipMessages.NO_MATCH)
            change { it.copy(stage = ClipStage.Done, answers = answers, progress = "") }
        }

        /** Starts one native call and waits for its end. Cancelling (or a time-out) stops the native work. */
        private suspend fun call(start: (ClipNativeListener) -> Unit): NativeResult =
            suspendCancellableCoroutine { continuation ->
                val lines = mutableListOf<ClipLine>()
                var ended = false
                fun end(result: NativeResult) {
                    if (ended) return
                    ended = true
                    continuation.resume(result)
                }
                continuation.invokeOnCancellation {
                    ended = true
                    native?.cancel()
                }
                start(object : ClipNativeListener {
                    override fun onNote(label: String, value: String) {
                        if (ended) return
                        if (label == "Audio") change { it.copy(stage = ClipStage.Listening) }
                        note(label, value)
                    }

                    override fun onPage(pageJson: String) = end(NativeResult(page = pageJson))

                    override fun onLine(text: String, startMs: Long, endMs: Long) {
                        if (!ended) lines += ClipLine(text, startMs, endMs)
                    }

                    override fun onDone() = end(NativeResult(lines = lines.toList()))

                    override fun onFailed(stage: String, message: String) =
                        end(NativeResult(error = message, failedStage = stage))
                })
            }

        private suspend fun <T> quietly(block: suspend () -> T): T? =
            try {
                block()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                null
            }
    }

    companion object {
        const val PAGE_TIMEOUT_MS = 45_000L
        const val LISTEN_TIMEOUT_MS = 420_000L
        const val SEARCH_BUDGET_MS = 240_000L
        const val SHOW_BUDGET_MS = 120_000L
        /** Fewer recognised words than this cannot be matched: "no speech". */
        const val MIN_WORDS = 6
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderSession.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import com.nuvio.app.features.addons.AddonRepository
import com.nuvio.app.features.addons.enabledAddons
import com.nuvio.app.features.addons.httpGetTextWithHeaders
import com.nuvio.app.features.catalog.fetchCatalogPage
import com.nuvio.app.features.details.MetaDetailsRepository
import com.nuvio.app.features.player.addonSubtitleRequests
import com.nuvio.app.features.player.loadAddonSubtitles
import com.nuvio.app.features.streams.epochMs
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull

/**
 * The one running Clip finder search. It lives outside the screen so that going to the stream list
 * and back does not start the search again.
 */
object ClipFinderSession {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val _state = MutableStateFlow(ClipFinderState())
    val state: StateFlow<ClipFinderState> = _state.asStateFlow()
    private var job: Job? = null
    private var runId = 0

    /** Starts the search for [source]. Does nothing when that clip is already running or shown, unless [restart]. */
    fun start(source: String, restart: Boolean = false) {
        if (!restart && _state.value.source == source) return
        job?.cancel()
        val id = ++runId
        _state.value = ClipFinderState(source = source)
        val native = ClipFinderBridge.current()
        val cache = object : ClipSubtitleCache {
            override fun read(key: String): String? = native?.cacheRead(key)
            override fun write(key: String, text: String) {
                native?.cacheWrite(key, text)
            }
        }
        val pipeline = ClipFinderPipeline(
            native = native,
            searchShows = ::clipSearchShows,
            loadEpisodes = ::clipLoadEpisodes,
            subtitles = EpisodeSubtitleSource(::clipListSubtitles, ::clipDownloadText, cache, ::epochMs),
            now = ::epochMs,
        )
        job = scope.launch {
            pipeline.run(source) { if (id == runId) _state.value = it }
        }
    }
}

private suspend fun <T> quietly(timeoutMs: Long, block: suspend () -> T): T? =
    withTimeoutOrNull(timeoutMs) {
        try {
            block()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            null
        }
    }

/** Nuvio's own search: every search catalog (series and movies) of the switched-on add-ons, results mixed by rank. */
internal suspend fun clipSearchShows(query: String): List<ShowGuess> = coroutineScope {
    AddonRepository.initialize()
    val catalogs = AddonRepository.uiState.value.addons.enabledAddons().mapNotNull { it.manifest }.flatMap { manifest ->
        manifest.catalogs
            .filter { catalog ->
                (catalog.type == "series" || catalog.type == "movie") &&
                    catalog.extra.any { it.name == "search" } &&
                    catalog.extra.none { it.isRequired && it.name != "search" }
            }
            .map { manifest to it }
    }.take(6)
    val pages = catalogs.map { (manifest, catalog) ->
        async {
            quietly(8_000L) {
                fetchCatalogPage(manifest.transportUrl, catalog.type, catalog.id, search = query, maxItems = 8).items
            }.orEmpty()
        }
    }.awaitAll()
    val mixed = (0 until 8).flatMap { rank -> pages.mapNotNull { it.getOrNull(rank) } }
        .map { ShowGuess(it.id, it.type, it.name, it.poster) }
        .distinctBy { it.metaId }
    // Subtitle add-ons only know IMDb ids ("tt..."), so those results go first when there are any.
    mixed.filter { it.metaId.startsWith("tt") }.ifEmpty { mixed }
}

/** The episodes of a series (specials and season 0 left out), or the movie itself as one entry. */
internal suspend fun clipLoadEpisodes(show: ShowGuess): List<ClipEpisode> {
    val meta = quietly(25_000L) { MetaDetailsRepository.fetch(show.type, show.metaId) } ?: return emptyList()
    val imdbId = listOf(meta.id, meta.imdbId.orEmpty(), show.metaId).firstOrNull { it.startsWith("tt") }
    val episodes = meta.videos.filter { (it.season ?: 0) > 0 && it.episode != null }
    if (episodes.isEmpty()) {
        return listOf(ClipEpisode(videoId = meta.id, subtitleId = imdbId ?: meta.id, type = show.type))
    }
    return episodes.map { video ->
        val subtitleId = if (video.id.startsWith("tt") || imdbId == null) video.id else "$imdbId:${video.season}:${video.episode}"
        ClipEpisode(video.id, subtitleId, show.type, video.season, video.episode, video.title, video.thumbnail)
    }
}

internal suspend fun clipListSubtitles(type: String, subtitleId: String): List<ClipSubtitleLink> =
    loadAddonSubtitles(addonSubtitleRequests(type, subtitleId)).map { ClipSubtitleLink(it.url, it.language) }

internal suspend fun clipDownloadText(url: String): String = httpGetTextWithHeaders(url, emptyMap())
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderScreen.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
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

/** [onOpen] gets the tapped candidate and the time to start playing from, in milliseconds. */
@Composable
fun ClipFinderScreen(source: String, onBack: () -> Unit, onOpen: (ClipAnswer, Long) -> Unit = { _, _ -> }) {
    val colors = MaterialTheme.nuvio.colors
    val current by ClipFinderSession.state.collectAsStateWithLifecycle()
    val state = if (current.source == source) current else ClipFinderState(source = source)
    var afterClip by rememberSaveable { mutableStateOf(false) }
    LaunchedEffect(source) { ClipFinderSession.start(source) }

    NuvioScreen {
        item { NuvioScreenHeader(title = CLIP_FINDER_TITLE, onBack = onBack) }
        item {
            NuvioSurfaceCard {
                NuvioSectionLabel(if (isClipFile(source)) "Shared video" else "Shared link")
                Text(clipSourceLabel(source), style = MaterialTheme.typography.bodyMedium, color = colors.textPrimary)
            }
        }
        item { ClipStagesCard(state) }
        if (state.failed) {
            item { ClipFailureCard(state, onRetry = { ClipFinderSession.start(source, restart = true) }) }
        }
        if (state.answers.isNotEmpty()) {
            item { ClipAnswersCard(state.answers, afterClip, onAfterClip = { afterClip = it }, onOpen = onOpen) }
        }
        if (state.notes.isNotEmpty()) {
            item { ClipNotesCard(state.notes) }
        }
        if (state.lines.isNotEmpty()) {
            item { ClipLinesCard(state.lines) }
        }
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderParts.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.nuvio.app.core.ui.Chip
import com.nuvio.app.core.ui.NuvioPrimaryButton
import com.nuvio.app.core.ui.NuvioSectionLabel
import com.nuvio.app.core.ui.NuvioSurfaceCard
import com.nuvio.app.core.ui.nuvio

@Composable
internal fun ClipStagesCard(state: ClipFinderState) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Steps")
        CLIP_FINDER_STAGES.forEachIndexed { index, stage ->
            val mark = clipStageMark(state, index)
            Text(
                text = "${index + 1}. $stage" + if (mark.isEmpty()) "" else " ($mark)",
                style = MaterialTheme.typography.bodyMedium,
                color = if (mark == "now" || mark == "failed") colors.textPrimary else colors.textMuted,
            )
        }
        if (state.progress.isNotBlank()) {
            Text(state.progress, style = MaterialTheme.typography.bodyMedium, color = colors.textPrimary)
        }
    }
}

@Composable
internal fun ClipFailureCard(state: ClipFinderState, onRetry: () -> Unit) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Stopped at: ${CLIP_FINDER_STAGES.getOrElse(state.stage.ordinal) { "" }}")
        Text(state.message, style = MaterialTheme.typography.bodyMedium, color = colors.textPrimary)
        if (state.showFileHint) {
            Text(ClipMessages.FILE_HINT, style = MaterialTheme.typography.bodyMedium, color = colors.textMuted)
        }
        NuvioPrimaryButton(text = "Try again", modifier = Modifier.padding(top = 8.dp), onClick = onRetry)
    }
}

@Composable
internal fun ClipAnswersCard(
    answers: List<ClipAnswer>,
    afterClip: Boolean,
    onAfterClip: (Boolean) -> Unit,
    onOpen: (ClipAnswer, Long) -> Unit,
) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Found (tap one, then pick a stream)")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(vertical = 8.dp)) {
            Chip(label = "From clip start", selected = !afterClip, onClick = { onAfterClip(false) })
            Chip(label = "After the clip", selected = afterClip, onClick = { onAfterClip(true) })
        }
        answers.forEach { answer ->
            val startMs = clipStartMs(answer.candidate, afterClip)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onOpen(answer, startMs) }
                    .padding(vertical = 8.dp),
            ) {
                Text(clipAnswerTitle(answer), style = MaterialTheme.typography.titleMedium, color = colors.textPrimary)
                Text(
                    text = clipAnswerDetail(answer) + ". Plays from ${clipClock(startMs)}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = colors.textMuted,
                )
            }
        }
    }
}

@Composable
internal fun ClipNotesCard(notes: List<ClipNote>) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Details (for a screenshot if something fails)")
        notes.forEach { note ->
            Text("${note.label}: ${note.value}", style = MaterialTheme.typography.bodySmall, color = colors.textMuted)
        }
    }
}

@Composable
internal fun ClipLinesCard(lines: List<ClipLine>) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Heard (first lines)")
        lines.take(6).forEach { line ->
            Text("${clipClock(line.startMs)}  ${line.text}", style = MaterialTheme.typography.bodySmall, color = colors.textMuted)
        }
    }
}
```

#### I. On the phone (after the Mac build), risks, and what the screen shows
Mo does by hand, once: (1) tap "Allow" when iOS asks "Nuvio would like to access Speech Recognition" on the first
clip; (2) Settings > General > Keyboard > Enable Dictation on, with English (US) as a keyboard or dictation language,
so the on-device English model is on the phone; (3) keep the OpenSubtitles v3 add-on and one catalog add-on with
search (Cinemeta) switched on in Nuvio; (4) for the backup route: save the clip, then Files app > hold the video >
Share > Nuvio.
Try it: share the South Park test clip from TikTok to Nuvio. Expected: the three steps tick off, "Found" lists
season 14 episode 2 first, tap it, pick a stream, the scene is on screen within 20 s. If anything stops, send a
screenshot of the whole Clip finder screen: the "Details" card names the step and the reason.

Top 5 ways it can fail on the phone, and what the screen then shows:
1. TikTok gives the web view a login, captcha or consent page, or changed its page data. Screen: "Page loaded:
   yes", "Video address found: no", stopped at "Reading link" with "Nuvio could not find the video's address on
   the page..." and the Files hint. Next step: the screenshot's Caption line tells whether any page data arrived;
   fix `urlKeys` / `readClip` in `ClipPageParser` (Kotlin, no Mac build needed to test with a new sample).
2. The video server refuses the download (403: address tied to something the web view had and URLSession lacks).
   Screen: "Download: address 1: the video server refused the download (HTTP 403)", stopped at "Reading link",
   Files hint. Fallback plan if it happens: download inside the web view (`WKDownload`) in the next build.
3. Speech: permission denied, no on-device English model, or nothing recognised. Screen: stopped at "Listening"
   with the Settings path to fix it, or "Lines heard: 0" and "No speech was heard in this clip".
4. Search: wrong or no show guess, catalog ids that are not IMDb ids, OpenSubtitles slow or refusing many
   requests, or the time budget ends before the right episode (South Park has 300+). Screen: "Show guesses: ...",
   "Subtitles: 0 of 60 episodes" with "No English subtitles were found", or "Search: stopped at the time limit in
   <show>" with "No match". A second try is faster: fetched subtitles are cached.
5. Hand-off or build: the Mac build fails on a Swift error (no new TestFlight build; fix from `build.log`), the
   bridge is not registered (screen: "Clip finder only works in the iPhone app."), or the player starts at 0:00
   instead of the moment (then `clipStartMs` did not reach `PlayerLaunch`; check the two lambdas of section G).
Shared file route: if iOS does not let Nuvio read the file, the screen says "This video has no sound track, or the
file could not be opened." at "Listening".

ASSUMPTIONS (cannot be checked from here; each has a visible symptom above)
- B1 TikTok's page for the web view's default user agent holds the item JSON or a `<video>` with a direct https
  address (not `blob:`), within 25 s, without a login. Confidence: medium.
- B2 The video address works for `URLSession` with the web view's cookies, referer and user agent. Medium.
- B3 `AVAssetReaderAudioMixOutput` converts to 16 kHz mono 16-bit as asked. If it keeps another rate or channel
  count the code adapts (it reads the real format); another bit depth stops with "unexpected format".
- B4 On-device recognition of a 30 s WAV file returns within 45 s and reports partial results the way the Mac test
  saw. If partial results carry no times, lines get the part's start time (the matcher does not use clip times).
- B5 The Swift compiles as written (never compiled; syntax-parsed only). The Kotlin interface names reach Swift
  unchanged (`ClipFinderNative`, `ClipNativeListener`, `ClipFinderBridge.shared`), as `NuvioPlayerBridge` does.
- B6 A file opened in place can be read after `startAccessingSecurityScopedResource()` on the URL object kept by
  `ClipFileInbox` (iOS gives that right to the object passed to `.onOpenURL`, not to a rebuilt address).
- B7 The OpenSubtitles add-on answers about 6 requests at a time for a few hundred episodes without blocking.
- B8 App Store Connect accepts the build with the new speech permission text (a refusal is an ITMS line at upload).
- B9 The Kotlin in section H compiles; it was written without a compiler. "Fork check" settles it in 8 min.

- [x] **7a. Find the show without a good caption** (Mac build 3; notes below)
  - Phone 2026-11-16: works (Mo). Its done-when (3) and (6) were not shown yet: they are check 5 of 7c.
  - Why: Mo's first phone test (2026-11-16) read the link and heard 11 lines, then stopped at "Show guesses:
    none" for the caption "The best part of Modern family.❤️❤️#edit #movieedit #modernfamily #fyp #viral".
  - Build (Mo's picks of 2026-11-16): smarter reading of the caption (hashtags glued to emoji, half-capitalised
    names, words after "of"); names compared squashed against known titles (shows of earlier clips, popular
    catalog titles) and search results; the poster's handle, the site's hashtag list, sound title and keywords
    as clues; text on the video frames (Apple Vision); "previously on ..." and spoken season/episode numbers;
    a quick check of the names heard ("Nancy") against one subtitle file per suspect; Apple's on-device model
    as a weak clue (iOS 26, iPhone 15 Pro Max); a small memory of shows and posters of earlier clips; the
    type-the-show box that reuses what was heard; Details lists every search tried. Not built (Mo): Continue
    Watching or library candidates, episodes near his watch progress.
  - Done when: (1) "Fork check" is green, including the tests with that caption; (2) on the phone that clip
    reaches a Modern Family episode; (3) a clip with no caption (shared video file) reaches its episode after
    typing the show, with "Listening" run once; (4) a second clip of the same show or poster shows "shared
    before" or "this poster before" in Details; (5) Details shows `Text on screen`, `Known titles`, `Searches`
    and, when the clues are weak, `Apple's model`; (6) no clip ever stops only because the caption is empty.
  - Try it: share the Modern Family clip again; then a saved video from Files and type the show's name.
  - Files: clipfinder/* (13 Kotlin files, 9 test files), iosApp/iosApp/ClipFinder/ (2 new Swift files, 1 changed).
  - Wait for OK before starting (25 files, a new stored text on the phone).

### Milestone 7a implementation notes (written 2026-11-16)
Checked against the work tree as it is on TestFlight (milestones 4-6 applied). Same rules as the 4-6 notes: paths
are inside `../nuvio-work` unless they start with `fork/` or `docs/`; `K`, `T`, `S` mean the same folders; where
these notes differ from older text, these notes win.

Not checked here: nothing below was compiled or run (no Kotlin, Gradle or Swift in the cloud workspace), and the
Swift was not even syntax-parsed this time (installing the parser was refused; the workers run that step in F).
Every test value in section H was traced by hand against the code; the filler, core and cut functions were also
run as a Python copy. Kotlin errors show in "Fork check" (8 min). Swift errors only show in the Mac build.

Why (Mo's first phone test, 2026-11-16): reading the link and listening WORKED (page after 3 s, caption and
author read, download HTTP 200 6.4 MB, 35 s of sound, 11 lines heard). It stopped at "Searching episodes" with
"Show guesses: none". The caption was `The best part of Modern family.❤️❤️#edit #movieedit #modernfamily #fyp #viral`,
the poster `wiqhwu2001`. Three causes, all in `ShowGuesser.queries`: (1) tokens were cut at spaces only, so
`family.❤️❤️#edit` was one plain word; (2) only runs of 2+ Capitalised words became a search, so "Modern family"
gave nothing; (3) the searches left were "movieedit" and "modernfamily", and Nuvio's catalog search only matches
whole words. Nothing compared the hashtag with a list of names.

#### A. Decisions
1. One new step, `ClipShowFinder` (Kotlin, tested), turns all clues into at most 15 suspects, best first; the
   best 3 get the full episode search (decision 13 orders them when there are several).
   A suspect is still only a candidate: the subtitle match decides. Sources and scores (0..110), in order:
   | # | Source | Score |
   |---|---|---|
   | 1 | This poster's last confident match (`ClipMemory.showFor`) | 92 |
   | 2 | A known title's name fits a hashtag (caption or the site's own list), the handle, the caption, the text on screen, the words after "previously on", the sound title or a keyword of the page. Known titles = shows of earlier clips (+3) and popular catalog titles | 100 tag is the name; 90 name plus filler ("suitsedit", "best.suits_clips2"); 85 the name's words stand in the caption, on screen or after "previously on"; 82 in the sound title; 78 in a keyword; 70 a tag holds the name |
   | 3 | Search of the first 3, 2, 1 words heard after "previously on", accepted when the name is exactly those words | 88 |
   | 3b | Search of the page's first 3 keywords as they are, accepted when the name is exactly the keyword | 86 |
   | 4 | Nuvio's search with `ShowGuesser.scored` (the old guess, now with scores) over the caption plus on-screen lines that name an episode | 100 / 90 / 60 / 30 as before |
   | 5 | Only when nothing reached 90: for the first 2 tags, search the tag without filler ("suitsedit" -> "suits") and the tag cut in two ("modernfamily" -> "modern family", ... at most 8 cuts, all at once); a result counts only if its name fits the tag | 100 / 90 / 70 |
   | 5b | Only when nothing reached 90 and something was heard: Apple's on-device model names up to 3 titles (decision 14); a name counts when a known title or a search result has exactly that name | 60 |
   | 6 | Only when nothing reached 70: the 8 most shared shows of earlier clips | 40 |
   Steps 3-4 are skipped once a suspect has 100 (steps 5, 5b: 90). A typed name replaces all of this: known titles
   and one search of the typed words (an "S2E5" in it becomes the episode hint), results in search order.
2. Mo's scope change (2026-11-16 00:07): NO Continue Watching, library or watch-progress use (what TikTok shows
   him is not what he watches), so no "episodes near his progress first". Instead every confident match is
   remembered: show id, type, name, count, last time, and poster handle -> show. One store for both.
3. "Squashed" names: lowercase letters and digits, nothing else (`ClipNames.key`). Hashtags are found at every
   `#`, also glued to an emoji or a full stop. A tag made only of filler words ("movieedit", "tvclips") is no clue.
4. `ShowGuesser.queries` (the search words) gets three fixes: a `#` always starts a new token; a Capitalised word
   followed by a lowercase word is a search ("Modern family"); the words after the last "of" or "from" up to the
   sentence end are a search ("best part of made up show." -> "made up show"). Stop words are never a search
   start. The four old exact-list tests still pass unchanged (traced).
5. Popular titles: the first page (at most 100 items) of every series or movie catalog without a required filter
   of the switched-on add-ons, at most 8 catalogs, 8 s each, fetched with the existing `fetchCatalogPage` and kept
   in memory until the app restarts. With Cinemeta that is "Popular" for series and movies. IMDb ids preferred.
6. Storage: upstream's pattern is an `expect object ...Storage` per feature with an `NSUserDefaults` actual in
   `iosMain` (for example `LibraryDisplaySettingsStorage`), plus actuals for Android and desktop. Fork check
   compiles only the Android side and the Mac build only the iOS side, so three new actual files are three chances
   of a build error. The same store (`UserDefaults.standard`, key `clipfinder.memory`) is reached through two new
   methods on the existing bridge instead: `settingRead` / `settingWrite`, 6 lines of Swift, no `iosMain` file.
   The text is tab-separated lines (`S id type count time name`, `P handle id time`), capped at 100 shows and 300
   posters (oldest go first), about 20 KB at most. Not in the subtitle cache: iOS may empty Caches.
7. Text on screen: `ClipFrameReader` (Swift, 42 lines) takes 5 frames (0.5, 3, 8, 20, 45 s; a time after the end
   is skipped) with `AVAssetImageGenerator.copyCGImage` and reads them with `VNRecognizeTextRequest`, accurate
   level, no language correction, on a background queue, BEFORE listening starts, because the temporary video is
   deleted after listening. It costs about 2 s. The text goes to Kotlin once (`onScreenText`, one piece per line).
   Kotlin uses it three ways: episode hint ("S2E5"), name fit against known titles, and lines that name an episode
   are added to the search text. No new permission and no Info.plist key: Vision needs none.
8. Heard clues: the words after "previously on" (step 3 above), and a spoken "season two episode five" (number
   words up to twenty become digits) as the episode hint. Hint order: typed, caption, screen, heard; a source
   that names the episode beats one that only names a season.
9. Type-the-show box (SPEC 7): shown as soon as something was heard and the search stage has started, also while
   a search still runs (typing stops it) and after a wrong answer. `ClipFinderSession.searchTyped` calls
   `ClipFinderPipeline.runTyped(previous state, name)`: the heard lines and clues live in the state, so nothing is
   read or listened to again. Typed matches are remembered like any other.
10. "No caption" no longer stops anything; `ClipMessages.NO_CAPTION` is gone. With no usable clue the screen says
    so and shows the box.
11. Details panel (for the next screenshot): `Text on screen`, `Known titles: 148 popular, 3 shared before`,
    `Searches: "Modern family": 3, "modernfamily": 0` (every search and its result count, or "failed"),
    `Show guesses: Modern Family (name, popular title)` (each with the clue that named it), `Show typed`.
12. More words from the page (coordinator, 2026-11-16; Kotlin only): `ClipPageParser` also reads, from the clip's
    own JSON object, the sound's title and maker (TikTok `music.title` / `music.authorName`; Instagram
    `clips_metadata.original_sound_info.original_audio_title` and `music_info.music_asset_info.title` /
    `display_artist`), the site's hashtag list (`textExtra[].hashtagName`, `challenges[].title`) and, anywhere in
    the page data, keyword lists (`suggestedWords`, `keywords`, `keywordTags`; at most 12 texts of 3-60
    characters). Each is its own field of `ClipClues` with its own weight (table above). The sound title is not
    used as a search phrase: most are "original sound - <poster>". ASSUMPTION: these key names are from memory
    of the sites' page data, not from a saved page; a missing key just gives nothing. Details shows `Sound` and
    `Keywords` when found. When the page data lacks the handle it is taken from the link (`/@name/`).
13. Quick name check (`ClipNameCheck`, Kotlin): names heard = words with a capital first letter and lowercase
    rest, 3+ letters, not the first word of a line or sentence, not in a short list of common capitalised words
    (days, months, "God", "English"...). When there are 2+ names, 2+ suspects and not exactly one strong suspect
    (90+), ONE subtitle file of each of the first 15 suspects is fetched (the hinted or first episode, through
    `EpisodeSubtitleSource.cues`, so it is cached and reused by the full search), 5 shows at a time, 45 s limit.
    Suspects are reordered by how many names their file holds (ties keep the higher score first); the best 3 go
    to the full search. Details shows `Names heard` and `Name check: Made Up Show 2, Invented Drama 0`.
14. Apple's on-device language model (Mo approved 2026-11-16, iPhone 15 Pro Max; this replaces the "do not plan"
    of the first brief). `ClipModelGuesser.swift` (46 lines) asks `FoundationModels` once per clip: the heard
    lines (at most 1 500 characters) and the caption (300), "answer with at most 3 titles, one per line".
    Kotlin (`ClipModelGuess`, tested) builds the question and reads the answer; each title is a 60-point suspect
    that the subtitle match must confirm. On-device, no key, no network: within CLAUDE.md's "no cloud AI".
    Guards: `#if canImport(FoundationModels)`, `if #available(iOS 26.0, *)`, `SystemLanguageModel.default.isAvailable`;
    the deployment target stays 16.1. When the model cannot be asked, Details shows why
    (`Apple's model: needs iOS 26 with Apple Intelligence` / `not available on this iPhone (...)` / `no answer in 12 s`
    / `failed (...)`) and the search carries on. Kotlin waits at most 12 s.
    API names checked against Apple's documentation on 2026-11-16 (developer.apple.com, JSON pages):
    `static var default: SystemLanguageModel`, `var isAvailable: Bool`, `var availability: SystemLanguageModel.Availability`
    (`.available` / `.unavailable(reason)`), `func respond(to prompt: String, options: GenerationOptions = GenerationOptions()) async throws -> LanguageModelSession.Response<String>`,
    `Response.content`, all iOS 26.0+. `LanguageModelSession(instructions: "...")` with a string literal is
    copied from the sample in Apple's overview; the initializer's full declaration could not be read (the page
    only names `init(model:tools:instructions:)`), so that one line is the least sure (about 85%). It is the only
    Swift file here that uses `Task` and `await` (the API has no callback form).
    How to drop it alone if the Mac build fails on it: delete `S/ClipModelGuesser.swift` and replace the body of
    `askModel` in `ClipFinderNativeImpl.swift` with `listener.onAnswer(text: nil, problem: "left out of this build")`.
    No Kotlin change.
15. Left alone on purpose: `ClipTranscriber`, `ClipAudioReader`, `ClipMediaFetcher`, the matcher,
    `EpisodeSubtitleSource`, and every upstream file: section G is empty.

#### B. Contract changes between Swift and Kotlin (do not change one side alone)
Five additions to `ClipFinderNative.kt`; everything else is as in the 4-6 notes:
```
protocol ClipFinderNative   func settingRead(key: String) -> String?        // UserDefaults "clipfinder.<key>"
                            func settingWrite(key: String, text: String)
                            func askModel(prompt: String, listener: ClipModelListener)   // returns at once
protocol ClipNativeListener func onScreenText(text: String)                 // during listen, at most once, before any onLine
protocol ClipModelListener  func onAnswer(text: String?, problem: String?)  // exactly once; text nil = problem says why
```
- `askModel` is independent of `readPage` / `listen` / `cancel`: a late answer after Kotlin's 12 s is ignored.
- `onScreenText` is called on the main thread, only when at least one piece of text was read, pieces joined by
  `\n`. Kotlin keeps at most 40 pieces of at most 80 characters.
- `settingRead` / `settingWrite` are called by Kotlin on the main thread; the only key is `memory`.
- The `listen` order is now: notes, `onScreenText` (optional), `onNote("Audio", ...)`, `onLine`..., `onDone` or `onFailed`.
- New notes Kotlin adds: `Sound`, `Keywords`, `Text on screen`, `Known titles`, `Searches`, `Apple's model`,
  `Names heard`, `Name check`, `Show typed`. `Show guesses` now names the clue.

#### C. Files
| Worker | File | What |
|---|---|---|
| 1 | new `K/ClipNames.kt`, `T/ClipNamesTest.kt` | `ClipClues`; squashed-name fit, tags, filler, cuts, "previously on", episode hint |
| 1 | new `K/ClipMemory.kt`, `T/ClipMemoryTest.kt` | shows of earlier clips and poster -> show, one capped text |
| 1 | new `K/ClipShowFinder.kt`, `T/ClipShowFinderTest.kt` | clues -> suspects (decision 1), search log |
| 1 | changed `K/ShowGuesser.kt`, `T/ShowGuesserTest.kt` | decision 4; `scored`; `genericTags` internal; 2 new tests |
| 1 | new `K/ClipNameCheck.kt`, `T/ClipNameCheckTest.kt` | names heard, one subtitle file per suspect (decision 13) |
| 1 | new `K/ClipModelGuess.kt`, `T/ClipModelGuessTest.kt` | question for Apple's model, reading its answer |
| 1 | changed `K/ClipPageParser.kt`, `T/ClipPageParserTest.kt` | sound title, keywords, hashtag list (decision 12) |
| 2 | changed `K/ClipFinderNative.kt` | section B |
| 2 | changed `K/ClipFinderState.kt`, `T/ClipFinderStateTest.kt` | `clues` in the state, messages, `clipCanType` |
| 2 | changed `K/ClipFinderPipeline.kt`, `T/ClipFinderPipelineTest.kt` | finder + memory instead of the search function, `runTyped`, screen text |
| 2 | changed `K/ClipFinderSession.kt` | wiring, `searchTyped`, `clipPopularShows`, `clipAskModel` (12 s) |
| 2 | changed `K/ClipFinderScreen.kt`, `K/ClipFinderParts.kt` | the type-the-show card (`NuvioInputField`, upstream) |
| 3 | new `S/ClipFrameReader.swift` | 5 frames -> text (Vision) |
| 3 | new `S/ClipModelGuesser.swift` | Apple's on-device model (decision 14); last, so it can be dropped alone |
| 3 | changed `S/ClipFinderNativeImpl.swift` | frames before listening, `settingRead` / `settingWrite`, `askModel` (39 lines added, 3 changed) |

25 files, every one under 300 lines except the pipeline test (346, a test file). No upstream file is edited, no
`project.pbxproj` change (synchronized folder), no Info.plist change, no new dependency.

#### D. Steps, one worker after the other in the same work tree
Never hand-type the files. This script copies the "File:" blocks of THIS section only (the old `/tmp/clip_files.py`
counts the blocks of the whole plan and now stops with "expected 15"; do not use it). Paste as it stands:
```bash
cat > /tmp/clip7a_files.py <<'PY'
import re, sys, os
mode, plan, tree = sys.argv[1], sys.argv[2], sys.argv[3].rstrip("/")
only = sys.argv[4:]                                    # optional: path fragments to limit to
text = open(plan, encoding="utf-8").read()
text = text[text.index("### Milestone 7a implementation notes"):text.index("\n- [ ] **7b.")]
blocks = re.findall(r"^##### File: `([^`]+)`\n```[a-z]*\n(.*?)\n```$", text, re.M | re.S)
assert len(blocks) == 25, "expected 25 file blocks, found %d" % len(blocks)
bad = 0
for path, body in blocks:
    if only and not any(o in path for o in only): continue
    full, body = os.path.join(tree, path), body + "\n"
    if mode == "write":
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w", encoding="utf-8").write(body)
        print("wrote", path)
    elif not os.path.exists(full) or open(full, encoding="utf-8").read() != body:
        bad += 1; print("DIFFERENT", path)
if mode == "check": print("all files match the plan" if not bad else "%d files differ" % bad); sys.exit(1 if bad else 0)
PY
```
0. Everyone: `fork/dev-tree.sh` (the work tree must hold milestones 4-6: `ls ../nuvio-work/iosApp/iosApp/ClipFinder`
   lists 5 Swift files), then save the script above.
1. Worker 1 (pure logic): `python3 /tmp/clip7a_files.py write docs/PLAN.md ../nuvio-work ClipNames ClipMemory ClipShowFinder ShowGuesser ClipNameCheck ClipModelGuess ClipPageParser`
   (14 files). Read the seven Kotlin files against decisions 1, 3, 4, 6, 8, 12, 13 and the tests against the code: for each
   `assertEquals` follow the code by hand once. Report any value you cannot reproduce; do not "fix" a test.
   The tree does not compile between worker 1 and worker 2 (the pipeline still uses the old constructor): fine.
2. Worker 2 (glue and screen): `python3 /tmp/clip7a_files.py write docs/PLAN.md ../nuvio-work ClipFinderNative ClipFinderState ClipFinderPipeline ClipFinderSession ClipFinderScreen ClipFinderParts`
   (8 files: `ClipFinderState` and `ClipFinderPipeline` also match their tests). Then
   `grep -rn "NO_CAPTION\|searchShows" ../nuvio-work/composeApp/src` must print nothing, and
   `grep -rlw "ClipFinderNative" ../nuvio-work/composeApp/src` must list exactly `ClipFinderNative.kt`,
   `ClipFinderPipeline.kt`, `ClipFinderSession.kt` and `ClipFinderPipelineTest.kt` (no other class implements it).
3. Worker 3 (Swift): `python3 /tmp/clip7a_files.py write docs/PLAN.md ../nuvio-work ClipFrameReader ClipFinderNativeImpl ClipModelGuesser`
   (3 files). Read all three line by line against section F; `ClipModelGuesser.swift` last (decision 14 says how
   to take it out again). Run the pre-flight, then `fork/dev-tree.sh save`.
4. Lead: commit `fork/nuvio-share-resume.patch` + docs, push, wait for "Fork check". Kotlin errors are fixed in
   the work tree (then save again); a test is never weakened: if a traced value was wrong, find out which side is
   wrong first. Review the Swift once more, then `gh workflow run TestFlight --ref clip-finder-share` (one Mac build).
5. When green on the phone: tick 7a; `docs/ARCHITECTURE.md`: data flow item 5 becomes "`ClipShowFinder`: poster
   memory, known titles (earlier clips, popular catalogs), search, typed name"; data model gets `ClipClues`,
   `ClipSuspect`, "Disk: `UserDefaults` key `clipfinder.memory` (shows and poster handles, never a clip)"; decisions
   log: "Candidates from earlier clips, not from Continue Watching (Mo)", "Memory through the bridge, not an
   expect/actual storage object", "Frames are read before listening", "Apple's on-device model allowed as a weak
   clue (Mo); still no cloud AI", "Many suspects are ordered by the names heard before the full search"; `docs/LESSONS.md`: "A caption test must use
   a real caption's shape: hashtags glued to emoji, half-capitalised names" (already added with this plan).

#### E. Tests (all nine test files are given in full in section H)
Made-up names only, with one exception Mo asked for: the caption of his first phone test, word for word, and the
title it names ("Modern Family"). A caption and a title are not show dialogue.
- `ClipNamesTest` (10 tests): tags from that caption are `modernfamily` and the handle; `#modernfamily`,
  `#ModernFamily` and a missing "The" score 100; filler around the name 90; the name inside a longer tag 70; the
  name written in the caption or on screen (also `MADE UP SHOW:` and `(Invented Drama)`) 85; short or unrelated
  names 0; typed names; `core`, `isFiller`, `splits`; "previously on"; the hint order; the handle from a link.
- `ClipMemoryTest` (7): empty; rank by count then recency; poster -> last show; no picture address and no tab
  in the text; a broken text is empty; blank id or name not kept; the cap of 100 drops the oldest and their posters.
- `ClipNameCheckTest` (5): names heard; shouted, short and apostrophe words are no names; when the check runs;
  the order by names found in one file each (a speaker label "NANCY:" is not counted, as in the matcher); 15 at most.
- `ClipModelGuessTest` (3): titles from a numbered or bulleted answer; a sentence gives none; the question.
- `ClipPageParserTest` (2 new, 7 old unchanged): sound title, hashtag list and keywords from a made-up TikTok
  item; audio title from a made-up Instagram reel; a page without them gives empty fields.
- `ClipShowFinderTest` (13): keywords and the sound title name the show; titles from the on-device model are
  60-point suspects and an unavailable model is only a note; that caption finds "Modern Family" from the known titles with no search at all;
  a bare `#modernfamily` does too; that caption finds it through a fake search ("Modern family") when no title
  is known, and the note reads `"Modern family": 1`; a tag cut in two; the handle "madeup.clips"; poster memory
  first and earlier shows as the last resort; shared before beats popular; "previously on"; typed name only;
  typed name with "s2e5"; failures give nothing and a cancel is passed on.
- `ShowGuesserTest` (2 new, 8 old unchanged): that caption gives exactly `["Modern family", "modernfamily"]`;
  the fake search then finds the show.
- `ClipFinderPipelineTest` (6 new, 1 changed, 12 old): two suspects with the same fit: the names heard put the
  right show first and the other show is only sampled; notes now include `Text on screen`, `Known titles`,
  `Searches`; a confident match is remembered and the poster alone finds the show the next time (blank caption,
  search finds nothing); hashtag + popular title; a title on the video frames of a shared file with no caption
  reaches S2E5 in the first batch; typing the show after "no show" reaches the episode with `listen` called once,
  and a wrong typed name ends with `NO_TYPED_SHOW`; a shared video with no clue ends with `NO_SHOW` (was `NO_CAPTION`).
- `ClipFinderStateTest` (1 new): `clipCanType`.
`ClipMatcherTest`, `ClipPageParserTest`, `EpisodeSubtitleSourceTest`, `ClipFinderScreenTest` stay green unchanged.

#### F. Pre-flight before pushing
```bash
W=../nuvio-work; S=$W/iosApp/iosApp/ClipFinder
python3 /tmp/clip7a_files.py check docs/PLAN.md $W                    # all files match the plan
ls $S | wc -l                                                         # 7
git -C $W status --porcelain | grep -v 'features/clipfinder/\|iosApp/iosApp/ClipFinder/'   # prints nothing: no other file touched
grep -nE '@MainActor|\bawait\b|\basync (let|throws|->)|Task *\{|Task\.detached|import SwiftUI' $S/*.swift | grep -v ClipModelGuesser.swift   # prints nothing
grep -cE '\bawait\b|Task *\{' $S/ClipModelGuesser.swift               # 2: one Task, one await, nowhere else
for f in $S/*.swift; do python3 - "$f" <<'PY'
import sys
s = open(sys.argv[1], encoding="utf-8").read()
assert s.count("{") == s.count("}") and s.count("(") == s.count(")") and s.count("[") == s.count("]"), sys.argv[1] + ": unbalanced brackets"
assert max(len(l) for l in s.split("\n")) < 220 and s.count("\n") < 300, sys.argv[1] + ": too long"
PY
done
python3 - $W <<'PY'                                                   # the two sides of the contract agree
import re, sys
k = open(sys.argv[1] + "/composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderNative.kt").read()
s = open(sys.argv[1] + "/iosApp/iosApp/ClipFinder/ClipFinderNativeImpl.swift").read()
for sig in ("func settingRead(key: String) -> String?", "func settingWrite(key: String, text: String)",
            "listener.onScreenText(text:", "ClipFrameReader.read(file)", "func cacheRead(key: String) -> String?",
            "func askModel(prompt: String, listener: ClipModelListener)", "listener.onAnswer(text: text, problem: problem)",
            "ClipModelGuesser.guess(prompt: prompt)",
            "listener.onLine(text: text, startMs: startMs, endMs: endMs)", "listener.onDone()"):
    assert sig in s, "Swift side lacks: " + sig
for sig in ("fun settingRead(key: String): String?", "fun settingWrite(key: String, text: String)", "fun onScreenText(text: String)",
            "fun askModel(prompt: String, listener: ClipModelListener)", "fun onAnswer(text: String?, problem: String?)"):
    assert sig in k, "Kotlin side lacks: " + sig
assert len(re.findall(r"^\s*fun ", k, re.M)) == 17, "ClipFinderNative.kt must declare exactly 17 functions"
print("contract OK")
PY
pip install -q tree-sitter tree-sitter-swift && python3 - $S <<'PY'          # Swift syntax (not run when this plan was written)
import glob, sys, tree_sitter_swift
from tree_sitter import Language, Parser
p = Parser(Language(tree_sitter_swift.language()))
for f in sorted(glob.glob(sys.argv[1] + "/*.swift")):
    assert not p.parse(open(f, "rb").read()).root_node.has_error, f + ": syntax error"
print("swift syntax OK")
PY
fork/dev-tree.sh save
```
Reading checks for the three Swift files (the 4-6 list, points 2-5, still applies, except that
`ClipModelGuesser.swift` may use `Task` and `await`):
1. `ClipFrameReader.swift` imports exactly AVFoundation, CoreGraphics, Foundation, Vision and names no Kotlin
   type. It is an `enum` with one `static func read(_ fileURL: URL) -> [String]`, no stored state, no `self`.
2. API names, all older than iOS 16.1 (no `#available`): `AVAssetImageGenerator(asset:)`,
   `.appliesPreferredTrackTransform`, `.maximumSize`, `copyCGImage(at:actualTime:)` (throws; deprecated since
   iOS 18: a warning, kept on purpose because the replacement needs `await` or a callback counter),
   `CMTime(seconds:preferredTimescale:)`, `VNRecognizeTextRequest()` (iOS 13), `.recognitionLevel = .accurate`,
   `.usesLanguageCorrection`, `VNImageRequestHandler(cgImage:options:)`, `perform(_:)` (throws),
   `request.results` (`[VNRecognizedTextObservation]?` since the iOS 15 SDK), `topCandidates(1)`,
   `VNRecognizedText.string` / `.confidence` (a `Float`), `UserDefaults.standard.string(forKey:)` / `.set(_:forKey:)`.
   If you are not sure a name is right, do not swap it for another from memory: flag it to the lead.
3. `ClipFinderNativeImpl.transcribe`: `afterListening = cleanUp` is set BEFORE the background block (so a cancel
   during frame reading still deletes the temporary file); the background block carries only `file`, `run`,
   `listener`; everything that touches `self` is inside `DispatchQueue.main.async`; `guard run == self.run` comes
   before `onScreenText`; `startListening` holds the old body of `transcribe` unchanged.
4. `settingRead` / `settingWrite` sit next to `cacheRead` / `cacheWrite`, same shape, labels `key:` and `text:`.
5. No Swift type is named like a Kotlin one: the new Swift types are `ClipFrameReader` and `ClipModelGuesser`;
   the new Kotlin types are `ClipClues`, `ClipNames`, `ClipMemory`, `ClipShowFinder`, `ClipSuspect`,
   `ClipNameCheck`, `ClipModelGuess`, `ClipModelAnswer`, `ClipModelListener`.
6. `ClipModelGuesser.swift`: `import FoundationModels` and the whole `ask` function are inside
   `#if canImport(FoundationModels)`; `ask` is marked `@available(iOS 26.0, *)` and only called inside
   `if #available(iOS 26.0, *)`; every path calls `completion` exactly once; the `Task` copies its two `var`s to
   `let`s before `DispatchQueue.main.async`; nothing else in the app names a FoundationModels type. API names
   are those of decision 14; do not swap one from memory.
What each check proves: Fork check = all Kotlin compiles and the 150-odd tests pass; nothing about Swift. Mac
build = Swift compiles and links. Phone = section I.

#### G. Edits to existing upstream files
None. Everything is inside `features/clipfinder/` (Kotlin) and `iosApp/iosApp/ClipFinder/` (Swift).

#### H. The files
Write them with the script of section D. The block header is the path inside the work tree.

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipNames.kt`
```kotlin
package com.nuvio.app.features.clipfinder

/** What is known about a clip besides its sound. Every field may be empty. */
data class ClipClues(
    val caption: String = "",
    /** The poster's handle, without "@". */
    val author: String = "",
    /** The sound's title and maker as the site names them ("original sound - Made Up Show"). */
    val sound: String = "",
    /** Search words the site attached to the clip. */
    val keywords: List<String> = emptyList(),
    /** Hashtags the site lists for the clip, besides those in the caption. */
    val hashtags: List<String> = emptyList(),
    /** Words read from a few frames of the video, one entry per piece of text. */
    val screenText: List<String> = emptyList(),
    /** A show name typed by the user. When set it is the only clue used to pick the show. */
    val typed: String = "",
)

/**
 * Compares show names with the clues without needing an exact match: names are squashed to
 * lowercase letters and digits, so "#ModernFamily", "modernfamilyclips" and the handle
 * "modern.family" all fit "Modern Family". Pure functions, no network.
 */
object ClipNames {
    private const val MAX_SPLITS = 8

    /** Words that posters glue to a show's name in a hashtag or handle. */
    private val ends = listOf(
        "clips", "clip", "edits", "edit", "scenes", "scene", "moments", "videos", "video", "vids", "quotes",
        "memes", "meme", "shorts", "reels", "fanpage", "fans", "fan", "page", "daily", "official", "best",
        "funny", "tiktok", "tv", "hd",
    )
    private val fillers = ends + listOf("show", "series", "season", "episode", "movie", "film", "the")
    private val numberWords = listOf(
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
        "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
    )

    /** Letters, digits and spaces only, so that "SHOW: part 1" and "(Show)" keep their words. */
    private fun plain(text: String): String = buildString {
        for (char in text) append(if (char.isLetterOrDigit() || char.isWhitespace() || char == '\'' || char == '’') char else ' ')
    }

    private fun words(text: String): List<String> = ClipText.normalize(plain(text))

    /** "Made Up Show!" -> "madeupshow". */
    fun key(text: String): String = words(text).joinToString("")

    /** The hashtags of the caption and the poster's handle, squashed; tags that never name a show are left out. */
    fun tags(clues: ClipClues): List<String> {
        val result = mutableListOf<String>()
        var index = clues.caption.indexOf('#')
        while (index >= 0) {
            result += key(clues.caption.substring(index + 1).takeWhile { it.isLetterOrDigit() || it == '_' })
            index = clues.caption.indexOf('#', index + 1)
        }
        for (tag in clues.hashtags) result += key(tag)
        result += key(clues.author)
        return result.filter { it.length >= 3 && it !in ShowGuesser.genericTags && !isFiller(it) }.distinct()
    }

    /** The caption, the text on screen and [heardTitle] as lists of words. */
    fun texts(clues: ClipClues, heardTitle: String = ""): List<List<String>> =
        wordLists(listOf(clues.caption, heardTitle) + clues.screenText)

    /** Each text as its list of words; texts without words are left out. */
    fun wordLists(texts: List<String>): List<List<String>> = texts.map { words(it) }.filter { it.isNotEmpty() }

    /**
     * How well a show's [name] fits the clues: 100 a tag is the name; 90 a tag is the name plus
     * filler ("suitsclips", "bestsuitsedits2"); 85 the name's words stand together in a text
     * (caption, screen, heard), 82 in the [sound] title, 78 in one of the site's [keywords];
     * 70 a tag holds the name somewhere; 0 no fit. A leading "The" may be missing in a tag.
     */
    fun score(
        name: String,
        tags: List<String>,
        texts: List<List<String>>,
        sound: List<List<String>> = emptyList(),
        keywords: List<List<String>> = emptyList(),
    ): Int {
        val nameWords = words(name)
        val full = nameWords.joinToString("")
        if (full.length < 3) return 0
        val keys = if (nameWords.size > 1 && nameWords.first() == "the" && full.length >= 7) listOf(full, full.drop(3)) else listOf(full)
        var best = 0
        for (key in keys) {
            for (tag in tags) {
                val fit = when {
                    tag == key -> 100
                    key.length >= 4 && fitsWithFiller(tag, key) -> 90
                    key.length >= 6 && key in tag -> 70
                    else -> 0
                }
                if (fit > best) best = fit
            }
        }
        if (nameWords.size >= 2 || full.length >= 5) {
            val written = when {
                texts.any { holdsRun(it, nameWords) } -> 85
                sound.any { holdsRun(it, nameWords) } -> 82
                keywords.any { holdsRun(it, nameWords) } -> 78
                else -> 0
            }
            if (written > best) best = written
        }
        return best
    }

    /** How well [name] fits what the user typed: 100 the same; 85 the name starts with it; 75 the name holds it. */
    fun typedScore(name: String, typed: String): Int {
        val nameKey = key(name)
        val want = key(typed)
        return when {
            nameKey.isEmpty() || want.length < 2 -> 0
            nameKey == want -> 100
            want.length >= 3 && nameKey.startsWith(want) -> 85
            want.length >= 4 && want in nameKey -> 75
            else -> 0
        }
    }

    /** The tag without filler at its ends: "suitsedit" -> "suits", "bestmadeupshowclips" -> "madeupshow". */
    fun core(tag: String): String {
        var text = tag.trim { it.isDigit() }
        var changed = true
        while (changed) {
            changed = false
            for (filler in ends) {
                if (text.length - filler.length < 4) continue
                if (text.endsWith(filler)) {
                    text = text.dropLast(filler.length)
                    changed = true
                } else if (text.startsWith(filler)) {
                    text = text.drop(filler.length)
                    changed = true
                }
            }
        }
        return text
    }

    /** "modernfamily" -> "modern family", "moder nfamily", ...: both parts 3+ letters, cuts near the middle first, at most 8. */
    fun splits(text: String): List<String> =
        (3..text.length - 3).sortedBy { cut -> kotlin.math.abs(cut * 2 - text.length) }.take(MAX_SPLITS)
            .map { cut -> text.substring(0, cut) + " " + text.substring(cut) }

    /** The words heard right after "previously on" (at most 4), or "". */
    fun heardTitle(lines: List<ClipLine>): String {
        val heard = lines.flatMap { words(it.text) }
        for (index in 0 until heard.size - 2) {
            if (heard[index] == "previously" && heard[index + 1] == "on") {
                return heard.subList(index + 2, minOf(heard.size, index + 6)).joinToString(" ")
            }
        }
        return ""
    }

    /**
     * Season and episode from what the user typed, the caption, the text on screen or what was heard
     * ("season two episode five"), in that order. A source naming the episode beats one naming only a season.
     */
    fun hint(clues: ClipClues, lines: List<ClipLine>): ClipHint {
        val heard = lines.flatMap { words(it.text) }.joinToString(" ") { word ->
            val number = numberWords.indexOf(word)
            if (number >= 0) number.toString() else word
        }
        val hints = listOf(clues.typed, clues.caption, clues.screenText.joinToString(" . "), heard).map { ShowGuesser.hint(it) }
        return hints.firstOrNull { it.episode != null } ?: hints.firstOrNull { it.season != null } ?: ClipHint()
    }

    /** "https://site.example/@some.name/video/1" -> "some.name"; "" when the link has no handle. */
    fun authorInLink(link: String): String =
        link.substringAfter("/@", "").takeWhile { it.isLetterOrDigit() || it == '.' || it == '_' }

    /** True for text made only of filler words and digits: "movieedit", "clips2", "". */
    internal fun isFiller(rest: String): Boolean {
        val text = rest.trim { it.isDigit() }
        if (text.isEmpty()) return true
        return fillers.any { text.startsWith(it) && isFiller(text.drop(it.length)) }
    }

    /** True when [tag] is [key] with nothing but filler before and after it. */
    private fun fitsWithFiller(tag: String, key: String): Boolean {
        var index = tag.indexOf(key)
        while (index >= 0) {
            if (isFiller(tag.substring(0, index)) && isFiller(tag.substring(index + key.length))) return true
            index = tag.indexOf(key, index + 1)
        }
        return false
    }

    private fun holdsRun(text: List<String>, run: List<String>): Boolean =
        (0..text.size - run.size).any { start -> run.indices.all { text[start + it] == run[it] } }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipMemory.kt`
```kotlin
package com.nuvio.app.features.clipfinder

/**
 * What Clip finder remembers on this phone, as one small text: the shows of earlier clips (how
 * often, when last) and which show a poster's clips came from. Never a clip, its sound or its
 * words. [read] and [write] are the phone's key-value store; a broken or missing text is empty.
 */
class ClipMemory(
    private val read: () -> String?,
    private val write: (String) -> Unit,
    private val now: () -> Long,
) {
    data class SeenShow(val show: ShowGuess, val count: Int, val lastMs: Long)

    /** [posters]: handle -> (show id, time). */
    data class Stored(
        val shows: List<SeenShow> = emptyList(),
        val posters: Map<String, Pair<String, Long>> = emptyMap(),
    )

    /** Shows of earlier clips: most often shared first, then most recent. */
    fun shows(): List<ShowGuess> =
        load().shows.sortedWith(compareByDescending<SeenShow> { it.count }.thenByDescending { it.lastMs }).map { it.show }

    /** The show this poster's last matched clip was from. */
    fun showFor(author: String): ShowGuess? {
        val key = posterKey(author)
        if (key.isEmpty()) return null
        val stored = load()
        val showId = stored.posters[key]?.first ?: return null
        return stored.shows.firstOrNull { it.show.metaId == showId }?.show
    }

    /** Counts one more clip of [show] and ties [author] (may be blank) to it. The oldest entries go when full. */
    fun remember(author: String, show: ShowGuess) {
        if (show.metaId.isBlank() || show.name.isBlank()) return
        val stored = load()
        val time = now()
        val count = (stored.shows.firstOrNull { it.show.metaId == show.metaId }?.count ?: 0) + 1
        val shows = (stored.shows.filter { it.show.metaId != show.metaId } + SeenShow(show.copy(poster = null), count, time))
            .sortedByDescending { it.lastMs }
            .take(MAX_SHOWS)
        val key = posterKey(author)
        val posters = (if (key.isEmpty()) stored.posters else stored.posters + (key to (show.metaId to time)))
            .entries
            .filter { entry -> shows.any { it.show.metaId == entry.value.first } }
            .sortedByDescending { it.value.second }
            .take(MAX_POSTERS)
            .associate { it.key to it.value }
        write(encode(Stored(shows, posters)))
    }

    private fun load(): Stored = runCatching { decode(read()) }.getOrDefault(Stored())

    companion object {
        /** The name of the stored text in the phone's key-value store. */
        const val KEY = "memory"
        const val MAX_SHOWS = 100
        const val MAX_POSTERS = 300

        /** "@Some.Name " -> "some.name". */
        fun posterKey(author: String): String = clean(author).trim().removePrefix("@").lowercase().take(60)

        /** One line per entry, fields separated by tabs: "S id type count time name" or "P handle id time". */
        fun encode(stored: Stored): String =
            (
                stored.shows.map { "S\t${clean(it.show.metaId)}\t${clean(it.show.type)}\t${it.count}\t${it.lastMs}\t${clean(it.show.name)}" } +
                    stored.posters.map { (poster, value) -> "P\t${clean(poster)}\t${clean(value.first)}\t${value.second}" }
                ).joinToString("\n")

        fun decode(text: String?): Stored {
            val shows = mutableListOf<SeenShow>()
            val posters = LinkedHashMap<String, Pair<String, Long>>()
            for (line in text.orEmpty().lines()) {
                val parts = line.split('\t')
                if (parts[0] == "S" && parts.size == 6) {
                    val count = parts[3].toIntOrNull() ?: continue
                    val time = parts[4].toLongOrNull() ?: continue
                    if (parts[1].isBlank() || parts[5].isBlank()) continue
                    shows += SeenShow(ShowGuess(parts[1], parts[2], parts[5]), count, time)
                } else if (parts[0] == "P" && parts.size == 4) {
                    val time = parts[3].toLongOrNull() ?: continue
                    if (parts[1].isNotBlank()) posters[parts[1]] = parts[2] to time
                }
            }
            return Stored(shows, posters)
        }

        private fun clean(text: String): String = text.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipShowFinder.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope

/** A show the clip may be from: how strongly the clues point at it (0..110) and which clue did. */
data class ClipSuspect(val show: ShowGuess, val score: Int, val why: String)

/**
 * Clues -> up to 15 shows that may be the clip's, best first; [ClipNameCheck] and the pipeline narrow
 * them to 3. A suspect is only a candidate: the subtitle match decides, so a wrong one costs time but
 * never gives a wrong answer. Sources, in order: the show this poster's clips were from before; names
 * of known titles (shows of earlier clips, popular catalog titles) in the hashtags, the handle, the
 * caption, the sound title, the site's keywords, the text on screen or after "previously on"; Nuvio's
 * search; hashtags cut in two; titles named by Apple's on-device model; the most shared shows of
 * earlier clips. A typed name replaces all other clues.
 */
class ClipShowFinder(
    private val search: suspend (query: String) -> List<ShowGuess>,
    private val popular: suspend () -> List<ShowGuess>,
    private val memory: ClipMemory,
    private val askModel: suspend (prompt: String) -> ClipModelAnswer = { ClipModelAnswer(problem = "not asked") },
) {
    private val searches = mutableListOf<String>()

    /** [onNote] gets diagnostic lines for the screen: how many titles were known, and every search with its result count. */
    suspend fun find(
        clues: ClipClues,
        lines: List<ClipLine>,
        max: Int = MAX_SHOWS,
        onNote: (label: String, value: String) -> Unit = { _, _ -> },
    ): List<ClipSuspect> {
        searches.clear()
        val suspects = pick(clues, lines, max, onNote)
        onNote("Searches", searches.joinToString().ifBlank { "none" }.take(500))
        return suspects
    }

    private suspend fun pick(clues: ClipClues, lines: List<ClipLine>, max: Int, onNote: (String, String) -> Unit): List<ClipSuspect> {
        val found = LinkedHashMap<String, ClipSuspect>()
        fun add(show: ShowGuess, score: Int, why: String) {
            val old = found[show.metaId]
            if (score > 0 && (old == null || old.score < score)) found[show.metaId] = ClipSuspect(show, score, why)
        }
        fun top(): Int = found.values.maxOfOrNull { it.score } ?: 0
        fun best(): List<ClipSuspect> = found.values.sortedByDescending { it.score }.take(max)

        val shared = runCatching { memory.shows() }.getOrDefault(emptyList())
        val known = shared + quietly { popular() }.orEmpty()
        onNote("Known titles", "${known.size - shared.size} popular, ${shared.size} shared before")

        if (clues.typed.isNotBlank()) {
            for (query in ShowGuesser.queries(clues.typed).ifEmpty { listOf(clues.typed) }.take(3)) {
                for (show in known) add(show, ClipNames.typedScore(show.name, query), "typed")
                for ((rank, show) in safeSearch(query).take(5).withIndex()) {
                    add(show, maxOf(ClipNames.typedScore(show.name, query), 80 - rank), "typed")
                }
                if (found.isNotEmpty()) break
            }
            return best()
        }

        // 1. This poster's clips were matched before.
        runCatching { memory.showFor(clues.author) }.getOrNull()?.let { add(it, 92, "this poster before") }

        // 2. Names of known titles in the hashtags, the handle, the caption, the text on screen, "previously on ...".
        val tags = ClipNames.tags(clues)
        val heard = ClipNames.heardTitle(lines)
        val texts = ClipNames.texts(clues, heard)
        val sound = ClipNames.wordLists(listOf(clues.sound))
        val keywords = ClipNames.wordLists(clues.keywords)
        for ((index, show) in known.withIndex()) {
            val earlier = index < shared.size
            val score = ClipNames.score(show.name, tags, texts, sound, keywords)
            if (score > 0) add(show, score + if (earlier) 3 else 0, if (earlier) "name, shared before" else "name, popular title")
        }

        // 3. "Previously on <name>": search the first words heard after it.
        if (top() < 100 && heard.isNotBlank()) {
            val heardWords = heard.split(' ')
            for (count in minOf(3, heardWords.size) downTo 1) {
                val query = heardWords.take(count).joinToString(" ")
                val hit = safeSearch(query).firstOrNull { ClipNames.key(it.name) == ClipNames.key(query) } ?: continue
                add(hit, 88, "heard after \"previously on\"")
                break
            }
        }

        // 3b. The site's own keywords for the clip, searched as they are; a result counts when it has that exact name.
        if (top() < 100) {
            for (keyword in clues.keywords.take(3)) {
                val hit = safeSearch(keyword).firstOrNull { ClipNames.key(it.name) == ClipNames.key(keyword) } ?: continue
                add(hit, 86, "keyword of the page")
            }
        }

        // 4. Nuvio's search with words from the caption and from titles on screen ("Made Up Show S2E5").
        if (top() < 100) {
            val titles = clues.screenText.filter { ShowGuesser.hint(it).episode != null }
            val text = (listOf(clues.caption) + titles).joinToString("\n").trim()
            val results = ShowGuesser.scored(text) { query -> safeSearch(query) }
            for ((show, score) in results) add(show, score, "search")
        }

        // 5. Hashtags and handles written without spaces: without filler ("suitsedit" -> "suits"), then cut in two.
        if (top() < 90) {
            for (tag in tags.take(2)) {
                val core = ClipNames.core(tag)
                val queries = (if (core != tag) listOf(core) else emptyList()) + ClipNames.splits(core)
                val results = coroutineScope { queries.map { query -> async { safeSearch(query) } }.awaitAll() }.flatten()
                for (show in results) add(show, ClipNames.score(show.name, listOf(tag), emptyList()), "hashtag or handle, search")
                if (top() >= 90) break
            }
        }

        // 5b. Apple's on-device model reads what was heard and names up to 3 titles: weak clues, confirmed like all others.
        if (top() < 90 && lines.isNotEmpty()) {
            val answer = quietly { askModel(ClipModelGuess.prompt(clues, lines)) } ?: ClipModelAnswer(problem = "failed")
            val named = ClipModelGuess.names(answer.text)
            onNote("Apple's model", answer.problem.ifBlank { named.joinToString().ifBlank { "named nothing" } })
            for (name in named) {
                val hit = known.firstOrNull { ClipNames.key(it.name) == ClipNames.key(name) }
                    ?: safeSearch(name).firstOrNull { ClipNames.key(it.name) == ClipNames.key(name) }
                    ?: continue
                add(hit, 60, "Apple's model")
            }
        }

        // 6. Nothing points anywhere: the shows shared most often before.
        if (top() < 70) for (show in shared.take(8)) add(show, 40, "shared before")
        return best()
    }

    /** Never throws (except when cancelled); every search is written down as "query": number of results. */
    private suspend fun safeSearch(query: String): List<ShowGuess> {
        val text = query.trim()
        if (text.length < 3) return emptyList()
        val results = quietly { search(text) }
        searches += "\"$text\": " + (results?.size?.toString() ?: "failed")
        return results.orEmpty()
    }

    private suspend fun <T> quietly(block: suspend () -> T): T? =
        try {
            block()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            null
        }

    companion object {
        const val MAX_SHOWS = ClipNameCheck.MAX_SUSPECTS
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ShowGuesser.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlinx.coroutines.CancellationException

/** A season and episode named in the caption ("S2E5", "season 2 episode 5", "2x05"). */
data class ClipHint(val season: Int? = null, val episode: Int? = null)

/** A show or movie from Nuvio's own search that the caption may be about. */
data class ShowGuess(val metaId: String, val type: String, val name: String, val poster: String? = null)

/**
 * Caption -> search words -> shows from Nuvio's search. One of the sources of [ClipShowFinder].
 * A guess is only a candidate: the subtitle match decides.
 */
object ShowGuesser {
    private const val MAX_QUERIES = 6
    private val seasonEpisode = listOf(
        Regex("""\bs(\d{1,2})\s*[-.:,]?\s*e(?:p(?:isode)?)?\s*(\d{1,3})\b""", RegexOption.IGNORE_CASE),
        Regex("""\bseason\s*(\d{1,2})\W{0,3}ep(?:isode)?\W{0,2}(\d{1,3})\b""", RegexOption.IGNORE_CASE),
        Regex("""\b(\d{1,2})x(\d{2,3})\b"""),
    )
    private val seasonOnly = Regex("""\bseason\s*(\d{1,2})\b""", RegexOption.IGNORE_CASE)
    private val link = Regex("""https?://\S+""")
    private val joiners = setOf("of", "the", "and", "in", "a", "is", "to")
    private val stopWords = joiners + setOf("for", "it", "on", "at", "by", "from", "with", "this", "that", "my", "when", "or", "but", "so", "vs")

    /** Hashtags that never name a show. Lowercase. */
    internal val genericTags = setOf(
        "fyp", "fy", "fypage", "foryou", "foryoupage", "foryourpage", "viral", "trending", "xyzbca", "tiktok",
        "reels", "reel", "explore", "shorts", "capcut", "edit", "edits", "tv", "tvshow", "tvshows", "tvseries",
        "series", "show", "movie", "movies", "film", "films", "clip", "clips", "tvclips", "movieclips", "scene",
        "scenes", "moments", "bestmoments", "funny", "comedy", "humor", "lol", "drama", "sitcom", "cartoon",
        "animation", "netflix", "hbo", "hulu", "prime", "disney", "parati", "best",
    )

    fun hint(caption: String): ClipHint {
        for (pattern in seasonEpisode) {
            val match = pattern.find(caption) ?: continue
            return ClipHint(match.groupValues[1].toIntOrNull(), match.groupValues[2].toIntOrNull())
        }
        return ClipHint(seasonOnly.find(caption)?.groupValues?.get(1)?.toIntOrNull(), null)
    }

    /** Search words to try, best first, at most 6. */
    fun queries(caption: String): List<String> {
        // A hashtag glued to other text or an emoji ("family.#edit") still starts a new token.
        val text = caption.replace(link, " ").replace("#", " #")
        val tokens = text.split(Regex("""\s+""")).filter { it.isNotBlank() }
        val tags = tokens.filter { it.startsWith("#") }
            .map { token -> token.drop(1).takeWhile { it.isLetterOrDigit() || it == '_' } }
            .filter { it.length >= 3 && it.lowercase() !in genericTags && !ClipNames.isFiller(it.lowercase()) }
        val plainTokens = tokens.filter { !it.startsWith("#") && !it.startsWith("@") }
        val plain = plainTokens.joinToString(" ")

        val result = mutableListOf<String>()
        // 1. the words just before "S2E5"
        seasonEpisode.firstNotNullOfOrNull { it.find(plain) }?.let { match ->
            val before = words(plain.substring(0, match.range.first)).takeLast(4)
            for (count in listOf(4, 2, 1)) {
                if (before.isNotEmpty()) result += before.takeLast(count).joinToString(" ")
            }
        }
        // 2. runs of Capitalised Words ("South Park", "Lord of the Rings")
        result += capitalisedRuns(plainTokens)
        // 2b. a Capitalised word with the lowercase word after it ("Modern family"); the words after "of" or "from"
        result += loosePairs(plainTokens)
        result += wordsAfter(plainTokens)
        // 3. hashtags, "SouthPark" split into "South Park"
        for (tag in tags) {
            val split = splitCamel(tag)
            result += split
            if (split != tag) result += tag
        }
        // 4. a short caption as a whole
        val all = words(plain)
        if (all.size in 1..5) result += all.joinToString(" ")
        // 5. nothing better: the first words, and the longest word
        if (result.isEmpty() && all.isNotEmpty()) {
            result += all.take(4).joinToString(" ")
            result += all.maxByOrNull { it.length }.orEmpty()
        }
        return result.map { it.trim() }.filter { it.length >= 3 }.distinctBy { it.lowercase() }.take(MAX_QUERIES)
    }

    /**
     * Runs [search] for each query and keeps results whose name fits the caption. Score: the name
     * equals the query 100; the caption holds the whole name 90; the name starts with the query 60;
     * the first result of a query 30. Earlier queries and higher results win ties. Stops at the
     * first query that gives a result named exactly like it.
     */
    suspend fun guess(caption: String, search: suspend (String) -> List<ShowGuess>, max: Int = 3): List<ShowGuess> =
        scored(caption, search).map { it.first }.take(max)

    /** What [guess] does, with each result's score, best first. */
    suspend fun scored(caption: String, search: suspend (String) -> List<ShowGuess>): List<Pair<ShowGuess, Int>> {
        val captionKey = squash(caption)
        val byId = LinkedHashMap<String, Pair<ShowGuess, Int>>()
        for ((queryIndex, query) in queries(caption).withIndex()) {
            val results = try {
                search(query)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                emptyList()
            }
            for ((rank, result) in results.take(8).withIndex()) {
                val score = score(result.name, query, captionKey, rank) - queryIndex - rank
                if (score <= 0) continue
                val old = byId[result.metaId]
                if (old == null || old.second < score) byId[result.metaId] = result to score
            }
            if (byId.values.any { it.second >= 95 }) break
        }
        return byId.values.sortedByDescending { it.second }
    }

    private fun score(name: String, query: String, captionKey: String, rank: Int): Int {
        val nameKey = squash(name)
        val queryKey = squash(query)
        return when {
            nameKey.isEmpty() || queryKey.isEmpty() -> 0
            nameKey == queryKey -> 100
            nameKey.length >= 4 && nameKey in captionKey -> 90
            queryKey.length >= 4 && nameKey.startsWith(queryKey) -> 60
            rank == 0 -> 30
            else -> 0
        }
    }

    /** Letters and digits only, lowercase, no spaces: "South Park!" and "#southpark" both give "southpark". */
    internal fun squash(text: String): String = ClipText.normalize(text.replace('#', ' ')).joinToString("")

    /** Words of letters, digits and apostrophes. Done by hand: no Unicode classes in a Regex (they differ on iOS). */
    private fun words(text: String): List<String> {
        val result = mutableListOf<String>()
        val current = StringBuilder()
        for (char in text) {
            if (char.isLetterOrDigit() || char == '\'') {
                current.append(char)
            } else if (current.isNotEmpty()) {
                result += current.toString()
                current.clear()
            }
        }
        if (current.isNotEmpty()) result += current.toString()
        return result
    }

    private fun capitalisedRuns(tokens: List<String>): List<String> {
        val runs = mutableListOf<String>()
        val current = mutableListOf<String>()
        fun flush() {
            while (current.isNotEmpty() && current.last().lowercase() in joiners) current.removeAt(current.size - 1)
            if (current.size >= 2) runs += current.joinToString(" ")
            current.clear()
        }
        for (token in tokens) {
            val word = token.trim { !it.isLetterOrDigit() }
            val capital = word.isNotEmpty() && word.first().isUpperCase() && word.none { it.isDigit() }
            val joins = current.isNotEmpty() && word.lowercase() in joiners
            if (capital || joins) current += word else flush()
            if (token.isNotEmpty() && token.last() in ".!?:;,") flush()
        }
        flush()
        return runs
    }

    private fun loosePairs(tokens: List<String>): List<String> {
        val pairs = mutableListOf<String>()
        for (index in 0 until tokens.size - 1) {
            if (tokens[index].last() in ".!?:;,") continue
            val first = tokens[index].trim { !it.isLetterOrDigit() }
            val second = tokens[index + 1].trim { !it.isLetterOrDigit() }
            val capital = first.isNotEmpty() && first.first().isUpperCase() && first.none { it.isDigit() } && first.lowercase() !in stopWords
            val lower = second.isNotEmpty() && second.first().isLowerCase() && second.none { it.isDigit() } && second.lowercase() !in stopWords
            if (capital && lower) pairs += "$first $second"
        }
        return pairs
    }

    /** "The best part of Modern family." -> "Modern family": up to 4 words after the last "of" or "from", to the sentence end. */
    private fun wordsAfter(tokens: List<String>): List<String> {
        val index = tokens.indexOfLast { it.lowercase() == "of" || it.lowercase() == "from" }
        if (index < 0) return emptyList()
        val rest = mutableListOf<String>()
        for (token in tokens.drop(index + 1).take(4)) {
            val word = token.trim { !it.isLetterOrDigit() }
            if (word.isNotEmpty()) rest += word
            if (token.last() in ".!?:;,") break
        }
        val name = rest.dropWhile { it.lowercase() in stopWords }
        return if (name.isEmpty()) emptyList() else listOf(name.joinToString(" "))
    }

    private fun splitCamel(tag: String): String {
        val out = StringBuilder()
        for ((index, char) in tag.withIndex()) {
            if (index > 0 && char.isUpperCase() && tag[index - 1].isLowerCase()) out.append(' ')
            out.append(if (char == '_') ' ' else char)
        }
        return out.toString()
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipNameCheck.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import com.nuvio.app.features.player.SubtitleSyncCue
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope

/**
 * A quick way to order many suspects before the long episode search: the names heard in the clip
 * ("Nancy", "Pepper") are looked up in ONE subtitle file of each show. A show whose people are
 * named in the clip goes first. Only an ordering: the episode search still decides.
 */
object ClipNameCheck {
    /** At most this many shows get the quick check. */
    const val MAX_SUSPECTS = 15
    /** This many shows go on to the full episode search. */
    const val KEEP = 3
    private const val STRONG = 90
    private const val MAX_NAMES = 12

    /** Capitalised words that are not names of people in a show. Lowercase. */
    private val common = setOf(
        "god", "jesus", "christmas", "okay", "yeah", "yes", "sir", "miss", "mrs", "dad", "mom", "mum", "mister", "doctor",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "january", "february", "march",
        "april", "may", "june", "july", "august", "september", "october", "november", "december", "english", "american",
        "america", "french", "spanish", "german", "italian", "chinese", "british", "internet", "google", "the", "and", "but",
    )

    /**
     * Words heard with a capital letter that are neither the first word of a line or sentence nor
     * common words: most likely names. Each once, in the order heard, at most 12.
     */
    fun names(lines: List<ClipLine>): List<String> {
        val names = LinkedHashSet<String>()
        for (line in lines) {
            val tokens = line.text.split(' ').filter { it.isNotBlank() }
            for (index in 1 until tokens.size) {
                if (tokens[index - 1].last() in ".!?") continue
                val word = tokens[index].trim { !it.isLetter() }
                if (word.length < 3 || !word.first().isUpperCase() || word.drop(1).any { !it.isLowerCase() }) continue
                if (word.lowercase() !in common) names += word
            }
        }
        return names.take(MAX_NAMES)
    }

    /** Worth doing with 2+ names and 2+ suspects, unless exactly one suspect is strong (90 or more). */
    fun needed(suspects: List<ClipSuspect>, names: List<String>): Boolean =
        names.size >= 2 && suspects.size >= 2 && !(suspects[0].score >= STRONG && suspects[1].score < STRONG)

    /**
     * Orders the first 15 [suspects] by how many of [names] stand in the cues [sample] returns for the
     * show (null: no subtitle found, counts as 0), 5 shows at a time. Equal counts keep the higher score first.
     */
    suspend fun rank(
        suspects: List<ClipSuspect>,
        names: List<String>,
        sample: suspend (ShowGuess) -> List<SubtitleSyncCue>?,
    ): List<Pair<ClipSuspect, Int>> {
        val wanted = names.map { it.lowercase() }
        val counted = suspects.take(MAX_SUSPECTS).chunked(5).flatMap { group ->
            coroutineScope {
                group.map { suspect -> async { suspect to count(sample(suspect.show), wanted) } }.awaitAll()
            }
        }
        return counted.sortedWith(compareByDescending<Pair<ClipSuspect, Int>> { it.second }.thenByDescending { it.first.score })
    }

    private fun count(cues: List<SubtitleSyncCue>?, wanted: List<String>): Int {
        if (cues.isNullOrEmpty()) return 0
        val words = cues.flatMap { ClipText.normalize(it.text) }.toSet()
        return wanted.count { it in words }
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipModelGuess.kt`
```kotlin
package com.nuvio.app.features.clipfinder

/** What Apple's on-device language model said: its text, or why it could not be asked. */
data class ClipModelAnswer(val text: String = "", val problem: String = "")

/**
 * The question for Apple's on-device language model and the reading of its answer. The model only
 * names titles; each name is a weak clue that the subtitle match must confirm. Nothing leaves the phone.
 */
object ClipModelGuess {
    private const val MAX_HEARD = 1_500
    private const val MAX_CAPTION = 300
    private val numbering = Regex("""^\d{1,2}[.)]\s+""")

    fun prompt(clues: ClipClues, lines: List<ClipLine>): String = buildString {
        append("These lines were heard in a short clip from a TV show or a movie.\n")
        if (clues.caption.isNotBlank()) append("Caption of the clip: ").append(clues.caption.take(MAX_CAPTION)).append('\n')
        append("Lines: ").append(lines.joinToString(" ") { it.text }.take(MAX_HEARD)).append('\n')
        append("Which TV show or movie is it most likely from? Answer with at most 3 titles, one per line, titles only.")
    }

    /** At most 3 titles from the answer: numbering, bullets, quotes and "(2019)" are taken off; sentences are dropped. */
    fun names(answer: String): List<String> =
        answer.lines()
            .map { line ->
                line.trim().replace(numbering, "").trimStart { it in "-*• " }.substringBefore(" (").trim { it in "\"'“”*_ " }
            }
            .filter { name -> name.length in 2..60 && name.count { it == ' ' } < 8 }
            .distinctBy { it.lowercase() }
            .take(3)
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipPageParser.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull

/** What a clip's web page says about itself. Every field may be empty. */
data class ClipPage(
    val pageUrl: String = "",
    val caption: String = "",
    val author: String = "",
    val videoUrls: List<String> = emptyList(),
    /** The sound's title and maker ("original sound - Made Up Show - Sample"). */
    val sound: String = "",
    /** Search words the site attached to the clip. */
    val keywords: List<String> = emptyList(),
    /** Hashtags the site lists for the clip, without "#". */
    val hashtags: List<String> = emptyList(),
)

/**
 * Reads the JSON text made by the page script in ClipPageReader.swift:
 * {"url", "title", "metas": {name: content}, "videos": [addresses of video elements],
 * "scripts": [text of each JSON script tag]}. Besides the caption it keeps other words that may
 * name the show: the sound's title, the site's keywords and its hashtag list. The sites change their pages often, so nothing here
 * depends on one exact shape: every JSON script is searched for an object that looks like a clip
 * and for the keys that hold video addresses. Never throws; unknown input gives an empty page.
 */
object ClipPageParser {
    private const val MAX_NODES = 300_000
    private const val MAX_DEPTH = 60
    private const val MAX_URLS = 6
    private const val MAX_WORDS = 12
    private val keywordKeys = setOf("suggestedWords", "keywords", "keywordTags")
    private val urlKeys = setOf(
        "playAddr", "PlayAddr", "play_addr", "downloadAddr", "DownloadAddr", "download_addr",
        "video_url", "video_versions", "contentUrl",
    )
    private val captionMetas = listOf("og:description", "twitter:description", "description", "og:title")
    private val videoMetas = listOf("og:video:secure_url", "og:video", "og:video:url", "twitter:player:stream")

    private class Found {
        var caption = ""
        var author = ""
        val urls = mutableListOf<String>()
        var sound = ""
        val keywords = mutableListOf<String>()
        val hashtags = mutableListOf<String>()
        var nodes = 0
    }

    fun parse(pageJson: String): ClipPage = runCatching { parseOrThrow(pageJson) }.getOrDefault(ClipPage())

    private fun parseOrThrow(pageJson: String): ClipPage {
        val root = Json.parseToJsonElement(pageJson) as? JsonObject ?: return ClipPage()
        val metas = root["metas"] as? JsonObject
        val found = Found()
        for (script in (root["scripts"] as? JsonArray).orEmpty()) {
            val text = (script as? JsonPrimitive)?.contentOrNull ?: continue
            val element = runCatching { Json.parseToJsonElement(text) }.getOrNull() ?: continue
            walk(element, found, 0)
        }
        val elementUrls = (root["videos"] as? JsonArray).orEmpty().mapNotNull { (it as? JsonPrimitive)?.contentOrNull }
        val metaUrls = videoMetas.mapNotNull { metas?.text(it)?.takeIf(String::isNotBlank) }
        val urls = (elementUrls + found.urls + metaUrls)
            .map { it.trim() }
            .filter { it.startsWith("https://", ignoreCase = true) || it.startsWith("http://", ignoreCase = true) }
            .distinct()
            .take(MAX_URLS)
        val caption = found.caption.ifBlank {
            captionMetas.firstNotNullOfOrNull { metas?.text(it)?.takeIf(String::isNotBlank) } ?: root.text("title")
        }
        return ClipPage(
            pageUrl = root.text("url"),
            caption = caption.trim().take(2_000),
            author = found.author.trim().take(100),
            videoUrls = urls,
            sound = found.sound.trim().take(200),
            keywords = found.keywords.toList(),
            hashtags = found.hashtags.toList(),
        )
    }

    private fun walk(element: JsonElement, found: Found, depth: Int) {
        found.nodes++
        if (depth > MAX_DEPTH || found.nodes > MAX_NODES) return
        when (element) {
            is JsonObject -> {
                readClip(element, found)
                for ((key, value) in element) {
                    if (key in urlKeys) collectUrls(value, found.urls, 0)
                    if (key in keywordKeys) collectWords(value, found.keywords, 0)
                    walk(value, found, depth + 1)
                }
            }
            is JsonArray -> for (child in element) walk(child, found, depth + 1)
            else -> Unit
        }
    }

    /**
     * TikTok: {"desc": "...", "video": {...}, "author": {"uniqueId": "..."} or "name"}.
     * Instagram: {"caption": {"text": "..."}, "video_versions": [...], "user": {"username": "..."}}.
     * The first clip with a caption wins.
     */
    private fun readClip(obj: JsonObject, found: Found) {
        if (found.caption.isNotBlank()) return
        val tiktok = obj["video"] is JsonObject && obj["desc"] is JsonPrimitive
        val instagram = "video_versions" in obj || "video_url" in obj
        if (!tiktok && !instagram) return
        val caption = if (tiktok) obj.text("desc") else (obj["caption"] as? JsonObject)?.text("text") ?: obj.text("caption")
        val owner = if (tiktok) obj["author"] else obj["user"] ?: obj["owner"]
        val author = when (owner) {
            is JsonObject -> owner.text("uniqueId").ifBlank { owner.text("username") }.ifBlank { owner.text("nickname") }
            is JsonPrimitive -> owner.contentOrNull.orEmpty()
            else -> ""
        }
        if (caption.isNotBlank()) found.caption = caption
        if (found.author.isBlank()) found.author = author
        readExtras(obj, found)
    }

    /**
     * More words about the clip. TikTok: {"music": {"title", "authorName"}, "textExtra": [{"hashtagName"}],
     * "challenges": [{"title"}]}. Instagram: {"clips_metadata": {"original_sound_info": {"original_audio_title"},
     * "music_info": {"music_asset_info": {"title", "display_artist"}}}}.
     */
    private fun readExtras(obj: JsonObject, found: Found) {
        if (found.sound.isBlank()) {
            val music = obj["music"] as? JsonObject
            val reel = obj["clips_metadata"] as? JsonObject
            val original = reel?.get("original_sound_info") as? JsonObject
            val asset = (reel?.get("music_info") as? JsonObject)?.get("music_asset_info") as? JsonObject
            found.sound = listOf(
                music?.text("title"), music?.text("authorName"), original?.text("original_audio_title"),
                asset?.text("title"), asset?.text("display_artist"),
            ).filter { !it.isNullOrBlank() }.joinToString(" - ")
        }
        for (entry in (obj["textExtra"] as? JsonArray).orEmpty() + (obj["challenges"] as? JsonArray).orEmpty()) {
            val tag = (entry as? JsonObject)?.let { it.text("hashtagName").ifBlank { it.text("title") } }.orEmpty().trim()
            if (tag.isNotEmpty() && tag !in found.hashtags && found.hashtags.size < MAX_WORDS) found.hashtags += tag
        }
    }

    private fun collectWords(value: JsonElement, into: MutableList<String>, depth: Int) {
        if (depth > 2 || into.size >= MAX_WORDS) return
        when (value) {
            is JsonPrimitive -> {
                val text = value.contentOrNull?.trim().orEmpty()
                if (value.isString && text.length in 3..60 && text !in into) into += text
            }
            is JsonArray -> for (child in value) collectWords(child, into, depth + 1)
            is JsonObject -> for (child in value.values) collectWords(child, into, depth + 1)
        }
    }

    private fun collectUrls(value: JsonElement, into: MutableList<String>, depth: Int) {
        if (depth > 3 || into.size >= 12) return
        when (value) {
            is JsonPrimitive -> {
                val text = value.contentOrNull ?: return
                if (value.isString && text.startsWith("http") && text !in into) into += text
            }
            is JsonArray -> for (child in value) collectUrls(child, into, depth + 1)
            is JsonObject -> for (child in value.values) collectUrls(child, into, depth + 1)
        }
    }

    private fun JsonObject.text(key: String): String = (this[key] as? JsonPrimitive)?.contentOrNull.orEmpty()
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipNamesTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/** Names, handles and captions here are made up, except one real caption and the show title it names. */
class ClipNamesTest {
    private val phoneCaption = "The best part of Modern family.❤️❤️#edit #movieedit #modernfamily #fyp #viral"

    private fun line(text: String) = ClipLine(text, 0, 1_000)

    @Test
    fun `hashtags are found even when glued to other text and filler tags are dropped`() {
        assertEquals(listOf("modernfamily", "wiqhwu2001"), ClipNames.tags(ClipClues(caption = phoneCaption, author = "wiqhwu2001")))
        assertEquals(listOf("madeupshow", "sampleuser"), ClipNames.tags(ClipClues(caption = "lol #Made_Up_Show #fyp", author = "sample.user")))
        assertTrue(ClipNames.tags(ClipClues()).isEmpty())
    }

    @Test
    fun `a squashed hashtag is the show name`() {
        assertEquals(100, ClipNames.score("Modern Family", listOf("modernfamily"), emptyList()))
        assertEquals(100, ClipNames.score("Modern Family", ClipNames.tags(ClipClues(caption = "#ModernFamily")), emptyList()))
        assertEquals(100, ClipNames.score("The Made Up Show", listOf("madeupshow"), emptyList()))
    }

    @Test
    fun `a tag or handle with filler around the name still fits`() {
        assertEquals(90, ClipNames.score("Modern Family", listOf("modernfamilyclips"), emptyList()))
        assertEquals(90, ClipNames.score("Suits", listOf("suitsedit"), emptyList()))
        assertEquals(90, ClipNames.score("Suits", ClipNames.tags(ClipClues(author = "best.suits_clips2")), emptyList()))
        assertEquals(70, ClipNames.score("Invented Drama", listOf("inventeddramafanatic"), emptyList()))
    }

    @Test
    fun `a name written out in the caption or on screen fits`() {
        val caption = ClipNames.texts(ClipClues(caption = phoneCaption))
        assertEquals(85, ClipNames.score("Modern Family", emptyList(), caption))
        val screen = ClipNames.texts(ClipClues(screenText = listOf("MADE UP SHOW: best bits", "(Invented Drama)")))
        assertEquals(85, ClipNames.score("Made Up Show", emptyList(), screen))
        assertEquals(85, ClipNames.score("Invented Drama", emptyList(), screen))
    }

    @Test
    fun `short or unrelated names do not fit`() {
        assertEquals(0, ClipNames.score("Lost", emptyList(), listOf(listOf("i", "lost", "my", "keys"))))
        assertEquals(0, ClipNames.score("Other Thing", listOf("madeupshow"), listOf(listOf("made", "up", "show"))))
        assertEquals(0, ClipNames.score("Suits", listOf("suitsmedia"), emptyList()))
        assertEquals(0, ClipNames.score("!!", listOf("madeupshow"), emptyList()))
    }

    @Test
    fun `a typed name fits the same name or its start`() {
        assertEquals(100, ClipNames.typedScore("Modern Family", "modern family"))
        assertEquals(100, ClipNames.typedScore("Modern Family", " ModernFamily "))
        assertEquals(85, ClipNames.typedScore("Made Up Show Again", "made up"))
        assertEquals(75, ClipNames.typedScore("The Made Up Show", "made up"))
        assertEquals(0, ClipNames.typedScore("Other Thing", "made up"))
        assertEquals(0, ClipNames.typedScore("Other Thing", ""))
    }

    @Test
    fun `filler is taken off a tag and a tag is cut in two`() {
        assertEquals("suits", ClipNames.core("suitsedit"))
        assertEquals("madeupshow", ClipNames.core("bestmadeupshowclips"))
        assertEquals("madeupshow", ClipNames.core("madeupshow"))
        assertTrue(ClipNames.isFiller("movieedit"))
        assertFalse(ClipNames.isFiller("modernfamily"))
        val cuts = ClipNames.splits("modernfamily")
        assertEquals("modern family", cuts.first())
        assertEquals(7, cuts.size)
        assertTrue("invented drama" in ClipNames.splits("inventeddrama"))
        assertTrue(ClipNames.splits("abcde").isEmpty())
    }

    @Test
    fun `the words after previously on are kept`() {
        assertEquals("made up show bako", ClipNames.heardTitle(listOf(line("Previously on Made Up Show."), line("bako ritu"))))
        assertEquals("", ClipNames.heardTitle(listOf(line("bako ritu nesa"))))
        assertEquals("", ClipNames.heardTitle(listOf(line("previously on"))))
        assertEquals("", ClipNames.heardTitle(emptyList()))
    }

    @Test
    fun `season and episode come from the caption then the screen then what was heard`() {
        val heard = listOf(line("this is season two episode five"))
        assertEquals(ClipHint(2, 5), ClipNames.hint(ClipClues(caption = "no numbers"), heard))
        assertEquals(ClipHint(3, 4), ClipNames.hint(ClipClues(screenText = listOf("bako", "Made Up Show S3E4")), heard))
        assertEquals(ClipHint(1, 2), ClipNames.hint(ClipClues(caption = "wow S1E2", screenText = listOf("Made Up Show S3E4")), heard))
        assertEquals(ClipHint(3, 4), ClipNames.hint(ClipClues(caption = "best of season 7", screenText = listOf("S3E4")), emptyList()))
        assertEquals(ClipHint(6, 1), ClipNames.hint(ClipClues(caption = "wow S1E2", typed = "made up show s6e1"), heard))
        assertEquals(ClipHint(null, null), ClipNames.hint(ClipClues(), emptyList()))
    }

    @Test
    fun `the handle is read from the link`() {
        assertEquals("sample.user", ClipNames.authorInLink("https://clips.example.test/@sample.user/video/7000000000000000001"))
        assertEquals("", ClipNames.authorInLink("https://clips.example.test/reel/abc"))
    }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipMemoryTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** Names, ids and handles here are made up. */
class ClipMemoryTest {
    private val showA = ShowGuess("tt001", "series", "Made Up Show")
    private val showB = ShowGuess("tt002", "movie", "Invented Drama")
    private var stored: String? = null
    private var clock = 0L
    private val memory = ClipMemory({ stored }, { stored = it }, { clock })

    private fun remember(author: String, show: ShowGuess, at: Long) {
        clock = at
        memory.remember(author, show)
    }

    @Test
    fun `nothing stored gives nothing`() {
        assertTrue(memory.shows().isEmpty())
        assertNull(memory.showFor("sample.user"))
        assertNull(memory.showFor(""))
    }

    @Test
    fun `shows are ranked by how often and how recently they were shared`() {
        remember("Sample.User", showA, 1_000)
        remember("other", showB, 2_000)
        assertEquals(listOf(showB, showA), memory.shows())
        remember("", showA, 3_000)
        assertEquals(listOf(showA, showB), memory.shows())
        assertEquals(2, ClipMemory.decode(stored).shows.first { it.show == showA }.count)
    }

    @Test
    fun `a poster leads to the show of the last matched clip`() {
        remember("Sample.User", showA, 1_000)
        assertEquals(showA, memory.showFor("@SAMPLE.user "))
        assertNull(memory.showFor("someone.else"))
        remember("sample.user", showB, 2_000)
        assertEquals(showB, memory.showFor("sample.user"))
    }

    @Test
    fun `the picture address is not stored and tabs cannot break the text`() {
        remember("a\tb", ShowGuess("tt003", "series", "Made\tUp\nShow", poster = "https://img.example.test/p.jpg"), 1_000)
        assertEquals(listOf(ShowGuess("tt003", "series", "Made Up Show")), memory.shows())
        assertEquals("tt003", memory.showFor("a b")?.metaId)
    }

    @Test
    fun `a broken text counts as empty and can be written over`() {
        stored = "rubbish\nS\tonly two\nP\tx\ty\tnot a number\nS\ttt9\tseries\tx\t5\tName"
        assertTrue(memory.shows().isEmpty())
        assertNull(memory.showFor("x"))
        remember("sample.user", showA, 1_000)
        assertEquals(listOf(showA), memory.shows())
    }

    @Test
    fun `a show without an id or a name is not kept`() {
        remember("sample.user", ShowGuess("", "series", "Made Up Show"), 1_000)
        remember("sample.user", ShowGuess("tt001", "series", " "), 2_000)
        assertNull(stored)
    }

    @Test
    fun `the oldest shows and their posters go when the store is full`() {
        for (number in 1..ClipMemory.MAX_SHOWS + 5) {
            remember("poster$number", ShowGuess("tt$number", "series", "Show $number"), number * 1_000L)
        }
        assertEquals(ClipMemory.MAX_SHOWS, memory.shows().size)
        assertNull(memory.showFor("poster5"))
        assertEquals("tt6", memory.showFor("poster6")?.metaId)
        assertEquals(ClipMemory.MAX_SHOWS, ClipMemory.decode(stored).posters.size)
    }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipShowFinderTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.coroutines.cancellation.CancellationException
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue
import kotlinx.coroutines.test.runTest

/** Names, ids and handles here are made up, except one real caption and the show title it names. */
class ClipShowFinderTest {
    private val phoneCaption = "The best part of Modern family.❤️❤️#edit #movieedit #modernfamily #fyp #viral"
    private val family = ShowGuess("tt100", "series", "Modern Family")
    private val showA = ShowGuess("tt001", "series", "Made Up Show")
    private val showB = ShowGuess("tt002", "series", "Invented Drama")
    private val other = ShowGuess("tt003", "series", "Other Thing")

    private var stored: String? = null
    private val memory = ClipMemory({ stored }, { stored = it }, { 1_000L })
    private val asked = mutableListOf<String>()
    private val notes = mutableMapOf<String, String>()

    private fun finder(
        popular: List<ShowGuess> = emptyList(),
        model: ClipModelAnswer = ClipModelAnswer(problem = "not asked"),
        search: (String) -> List<ShowGuess> = { emptyList() },
    ) = ClipShowFinder({ query -> asked += query; search(query) }, { popular }, memory, { model })

    private suspend fun ClipShowFinder.names(clues: ClipClues, lines: List<ClipLine> = emptyList()) =
        find(clues, lines) { label, value -> notes[label] = value }.map { it.show.name }

    @Test
    fun `the phone caption finds the show in the list of known titles when the search finds nothing`() = runTest {
        val found = finder(popular = listOf(other, family)).find(ClipClues(caption = phoneCaption, author = "wiqhwu2001"), emptyList())
        assertEquals(listOf("Modern Family"), found.map { it.show.name })
        assertEquals(100, found.first().score)
        assertTrue(asked.isEmpty(), "an exact hashtag needs no search")
    }

    @Test
    fun `a bare hashtag finds the show in the list of known titles`() = runTest {
        assertEquals(listOf("Modern Family"), finder(popular = listOf(other, family)).names(ClipClues(caption = "#modernfamily")))
    }

    @Test
    fun `the phone caption finds the show through the search when no title is known`() = runTest {
        val subject = finder(search = { query -> if (query.equals("modern family", ignoreCase = true)) listOf(family) else emptyList() })
        assertEquals(listOf("Modern Family"), subject.names(ClipClues(caption = phoneCaption, author = "wiqhwu2001")))
        assertEquals("\"Modern family\": 1", notes["Searches"])
        assertEquals("0 popular, 0 shared before", notes["Known titles"])
    }

    @Test
    fun `a hashtag without spaces is cut in two for the search`() = runTest {
        val subject = finder(search = { query -> if (query == "invented drama") listOf(showB) else emptyList() })
        assertEquals(listOf("Invented Drama"), subject.names(ClipClues(caption = "#inventeddrama")))
        assertTrue("\"inventeddrama\": 0" in notes.getValue("Searches"))
        assertTrue("\"invented drama\": 1" in notes.getValue("Searches"))
    }

    @Test
    fun `the poster's handle names the show`() = runTest {
        val subject = finder(search = { query -> if (query == "madeup") listOf(ShowGuess("tt007", "series", "Madeup")) else emptyList() })
        val found = subject.find(ClipClues(author = "madeup.clips"), emptyList())
        assertEquals(listOf("tt007"), found.map { it.show.metaId })
        assertEquals(90, found.first().score)
    }

    @Test
    fun `a poster seen before comes first and earlier shows are the last resort`() = runTest {
        memory.remember("sample.user", showA)
        memory.remember("sample.user", showA)
        memory.remember("someone.else", showB)
        val known = finder().find(ClipClues(author = "someone.else"), emptyList())
        assertEquals(listOf("Invented Drama"), known.map { it.show.name })
        assertEquals("this poster before", known.first().why)
        val unknown = finder().find(ClipClues(), emptyList())
        assertEquals(listOf("Made Up Show", "Invented Drama"), unknown.map { it.show.name })
        assertEquals(listOf(40, 40), unknown.map { it.score })
        finder().names(ClipClues())
        assertEquals("0 popular, 2 shared before", notes["Known titles"])
    }

    @Test
    fun `a show shared before beats a popular title with the same fit`() = runTest {
        memory.remember("", showA)
        val twin = ShowGuess("tt900", "series", "Made Up Show")
        val found = finder(popular = listOf(twin)).find(ClipClues(caption = "#madeupshow"), emptyList())
        assertEquals(listOf("tt001", "tt900"), found.map { it.show.metaId })
        assertEquals(listOf(103, 100), found.map { it.score })
    }

    @Test
    fun `previously on names the show`() = runTest {
        val subject = finder(search = { query -> if (query == "made up show") listOf(showA) else emptyList() })
        val found = subject.find(ClipClues(), listOf(ClipLine("Previously on Made Up Show", 0, 1_000)))
        assertEquals(listOf("Made Up Show"), found.map { it.show.name })
        assertEquals(88, found.first().score)
    }

    @Test
    fun `keywords of the page and the sound title name the show`() = runTest {
        val byKeyword = finder(search = { query -> if (query == "made up show") listOf(showA) else emptyList() })
            .find(ClipClues(keywords = listOf("lamp scene", "made up show")), emptyList())
        assertEquals(listOf("Made Up Show" to 86), byKeyword.map { it.show.name to it.score })
        val bySound = finder(popular = listOf(other, showB)).find(ClipClues(sound = "original sound - Invented Drama"), emptyList())
        assertEquals(listOf("Invented Drama" to 82), bySound.map { it.show.name to it.score })
        val byList = finder(popular = listOf(showA)).find(ClipClues(hashtags = listOf("MadeUpShow", "fyp")), emptyList())
        assertEquals(listOf("Made Up Show" to 100), byList.map { it.show.name to it.score })
    }

    @Test
    fun `titles named by the on-device model are weak suspects and an unavailable model is only a note`() = runTest {
        val heard = listOf(ClipLine("bako ritu nesa", 0, 1_000))
        val subject = finder(model = ClipModelAnswer("1. Made Up Show\n2. Nothing Real"), search = { query ->
            if (query == "Made Up Show") listOf(showA) else emptyList()
        })
        val found = subject.find(ClipClues(), heard) { label, value -> notes[label] = value }
        assertEquals(listOf("Made Up Show" to 60), found.map { it.show.name to it.score })
        assertEquals("Apple's model", found.first().why)
        assertEquals("Made Up Show, Nothing Real", notes["Apple's model"])
        val off = finder(model = ClipModelAnswer(problem = "needs iOS 26 with Apple Intelligence"))
        assertTrue(off.names(ClipClues(), heard).isEmpty())
        assertEquals("needs iOS 26 with Apple Intelligence", notes["Apple's model"])
    }

    @Test
    fun `a typed name is the only clue`() = runTest {
        val reunion = ShowGuess("tt200", "series", "Modern Family Reunion")
        val subject = finder(popular = listOf(other, family), search = { query -> if (query == "modern family") listOf(reunion) else emptyList() })
        val found = subject.find(ClipClues(caption = "#otherthing", typed = "modern family"), emptyList())
        assertEquals(listOf("tt100", "tt200"), found.map { it.show.metaId })
        assertEquals(listOf(100, 85), found.map { it.score })
    }

    @Test
    fun `a typed name with an episode searches the name only`() = runTest {
        val subject = finder(search = { query -> if (query == "made up show") listOf(showA) else emptyList() })
        assertEquals(listOf("Made Up Show"), subject.names(ClipClues(typed = "made up show s2e5")))
        assertEquals(listOf("made up show"), asked)
    }

    @Test
    fun `failures give no suspects and a cancel is passed on`() = runTest {
        val failing = ClipShowFinder({ throw IllegalStateException("offline") }, { throw IllegalStateException("offline") }, memory)
        assertTrue(failing.names(ClipClues(caption = "Made Up Show S2E5 #madeupshow")).isEmpty())
        assertTrue("\"Made Up Show\": failed" in notes.getValue("Searches"))
        val cancelled = ClipShowFinder({ throw CancellationException("stopped") }, { emptyList() }, memory)
        assertFailsWith<CancellationException> { cancelled.find(ClipClues(caption = "Made Up Show S2E5"), emptyList()) }
    }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ShowGuesserTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.coroutines.cancellation.CancellationException
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue
import kotlinx.coroutines.test.runTest

/** Captions, names and ids here are made up. */
class ShowGuesserTest {

    @Test
    fun `season and episode are read from the caption`() {
        assertEquals(ClipHint(2, 5), ShowGuesser.hint("Made Up Show S2E5 lamp"))
        assertEquals(ClipHint(3, 4), ShowGuesser.hint("season 3 episode 4"))
        assertEquals(ClipHint(2, 5), ShowGuesser.hint("watch 2x05"))
        assertEquals(ClipHint(7, null), ShowGuesser.hint("best of season 7"))
        assertEquals(ClipHint(null, null), ShowGuesser.hint("1920x1080 edit"))
        assertEquals(ClipHint(null, null), ShowGuesser.hint("no numbers"))
    }

    @Test
    fun `words before the episode number come first`() {
        assertEquals(
            listOf("Made Up Show", "Up Show", "Show", "madeupshow"),
            ShowGuesser.queries("Made Up Show S2E5 the lamp scene #madeupshow #fyp"),
        )
    }

    @Test
    fun `a camel case hashtag is split and generic tags are dropped`() {
        val queries = ShowGuesser.queries("lol #MadeUpShow #fyp #viral")
        assertEquals(listOf("Made Up Show", "MadeUpShow"), queries.take(2))
        assertTrue(queries.none { it.equals("fyp", true) || it.equals("viral", true) })
    }

    @Test
    fun `a run of capital words is a query and the sentence after it is not`() {
        val queries = ShowGuesser.queries("Invented Drama is wild. Wait for it")
        assertTrue("Invented Drama" in queries)
        assertTrue(queries.none { it.startsWith("Wait") })
    }

    @Test
    fun `a short plain caption is used whole and nothing gives nothing`() {
        assertEquals(listOf("that scene tho"), ShowGuesser.queries("that scene tho"))
        assertTrue(ShowGuesser.queries("").isEmpty())
        assertTrue(ShowGuesser.queries("https://example.test/abc").isEmpty())
        assertTrue(ShowGuesser.queries("watch https://example.test/video/123 now").none { it.contains("http") })
    }

    @Test
    fun `a hashtag glued to an emoji and a half capitalised name are still read`() {
        // The caption of Mo's first phone test, as it was (a caption, not show dialogue).
        val caption = "The best part of Modern family.❤️❤️#edit #movieedit #modernfamily #fyp #viral"
        assertEquals(listOf("Modern family", "modernfamily"), ShowGuesser.queries(caption))
        assertEquals(listOf("made up show"), ShowGuesser.queries("best part of made up show. #fyp"))
    }

    @Test
    fun `that caption finds the show through the search`() = runTest {
        val caption = "The best part of Modern family.❤️❤️#edit #movieedit #modernfamily #fyp #viral"
        val found = ShowGuesser.guess(caption, { query ->
            if (query.equals("modern family", ignoreCase = true)) listOf(ShowGuess("tt100", "series", "Modern Family")) else emptyList()
        })
        assertEquals(listOf("Modern Family"), found.map { it.name })
    }

    @Test
    fun `the search stops at an exact name and keeps the other results`() = runTest {
        val calls = mutableListOf<String>()
        val found = ShowGuesser.guess("Made Up Show S2E5 the lamp scene #madeupshow #fyp", { query ->
            calls += query
            if (query == "Made Up Show") {
                listOf(ShowGuess("tt001", "series", "Made Up Show"), ShowGuess("tt002", "series", "Made Up Show Again"))
            } else {
                emptyList()
            }
        })
        assertEquals(listOf("tt001", "tt002"), found.map { it.metaId })
        assertEquals(1, calls.size)
    }

    @Test
    fun `a search that fails gives no guess and a cancel is passed on`() = runTest {
        val none = ShowGuesser.guess("Made Up Show S2E5", { throw IllegalStateException("offline") })
        assertTrue(none.isEmpty())
        assertFailsWith<CancellationException> {
            ShowGuesser.guess("Made Up Show S2E5", { throw CancellationException("stopped") })
        }
    }

    @Test
    fun `a hashtag without spaces still finds the show`() = runTest {
        val found = ShowGuesser.guess("the #madeupshow finale", { query ->
            if (query == "madeupshow") listOf(ShowGuess("tt003", "series", "Made Up Show")) else emptyList()
        })
        assertEquals(listOf("tt003"), found.map { it.metaId })
    }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipNameCheckTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import com.nuvio.app.features.player.SubtitleSyncCue
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import kotlinx.coroutines.test.runTest

/** Names and lines here are made up. */
class ClipNameCheckTest {
    private fun line(text: String) = ClipLine(text, 0, 1_000)
    private fun suspect(id: String, score: Int) = ClipSuspect(ShowGuess(id, "series", "Show $id"), score, "test")

    @Test
    fun `names are capitalised words that do not start a line or a sentence`() {
        val lines = listOf(line("Nancy said that Pepper went. Then on Monday i saw Nancy"), line("so Pepper, come here"))
        assertEquals(listOf("Pepper", "Nancy"), ClipNameCheck.names(lines))
    }

    @Test
    fun `shouted words short words and words with an apostrophe are not names`() {
        assertTrue(ClipNameCheck.names(listOf(line("we met at NASA with O'Brien and Al and God"))).isEmpty())
        assertTrue(ClipNameCheck.names(emptyList()).isEmpty())
    }

    @Test
    fun `the check runs with two names and no single strong suspect`() {
        val names = listOf("Nancy", "Pepper")
        assertTrue(ClipNameCheck.needed(listOf(suspect("a", 85), suspect("b", 85)), names))
        assertTrue(ClipNameCheck.needed(listOf(suspect("a", 103), suspect("b", 100)), names))
        assertFalse(ClipNameCheck.needed(listOf(suspect("a", 100), suspect("b", 85)), names))
        assertFalse(ClipNameCheck.needed(listOf(suspect("a", 85)), names))
        assertFalse(ClipNameCheck.needed(listOf(suspect("a", 85), suspect("b", 85)), listOf("Nancy")))
    }

    @Test
    fun `suspects are ordered by the names found in one subtitle file`() = runTest {
        val suspects = listOf(suspect("a", 85), suspect("b", 70), suspect("c", 85), suspect("d", 40))
        val asked = mutableListOf<String>()
        val ranked = ClipNameCheck.rank(suspects, listOf("Nancy", "Pepper")) { show ->
            asked += show.metaId
            when (show.metaId) {
                "b" -> listOf(SubtitleSyncCue(0, 1_000, "NANCY: hello there"), SubtitleSyncCue(2_000, 3_000, "Pepper, wait!"))
                "c" -> listOf(SubtitleSyncCue(0, 1_000, "oh nancy"))
                "d" -> null
                else -> emptyList()
            }
        }
        assertEquals(listOf("c" to 1, "b" to 1, "a" to 0, "d" to 0), ranked.map { it.first.show.metaId to it.second })
        assertEquals(listOf("a", "b", "c", "d"), asked.sorted())
    }

    @Test
    fun `only the first fifteen suspects are checked`() = runTest {
        var asked = 0
        val ranked = ClipNameCheck.rank(List(20) { suspect("s$it", 50) }, listOf("Nancy", "Pepper")) {
            asked++
            null
        }
        assertEquals(15, asked)
        assertEquals(15, ranked.size)
    }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipModelGuessTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/** Names and lines here are made up. */
class ClipModelGuessTest {
    @Test
    fun `titles are read from a numbered or bulleted answer`() {
        val answer = "1. Made Up Show\n2) \"Invented Drama\" (2019)\n- Other Thing\n4. Fourth Title"
        assertEquals(listOf("Made Up Show", "Invented Drama", "Other Thing"), ClipModelGuess.names(answer))
        assertEquals(listOf("24 Lamps"), ClipModelGuess.names("24 Lamps\n24 lamps\n"))
    }

    @Test
    fun `a sentence or an empty answer gives no title`() {
        assertTrue(ClipModelGuess.names("I am not sure which show this clip is from because the lines are short").isEmpty())
        assertTrue(ClipModelGuess.names("").isEmpty())
    }

    @Test
    fun `the question holds the lines and the caption when there is one`() {
        val lines = listOf(ClipLine("bako ritu", 0, 1_000), ClipLine("nesa dako", 1_000, 2_000))
        val withCaption = ClipModelGuess.prompt(ClipClues(caption = "wow #fyp"), lines)
        assertTrue("Caption of the clip: wow #fyp\n" in withCaption)
        assertTrue("Lines: bako ritu nesa dako\n" in withCaption)
        assertFalse("Caption" in ClipModelGuess.prompt(ClipClues(), lines))
        val long = ClipModelGuess.prompt(ClipClues(), List(400) { ClipLine("bako ritu nesa", 0, 1_000) })
        assertTrue(long.length < 1_800)
    }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipPageParserTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlinx.serialization.json.add
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/** Sample pages are made up to look like the shapes the sites use; no real captions, names or addresses. */
class ClipPageParserTest {
    private val pageUrl = "https://www.tiktok.com/@sample.user/video/7000000000000000001"

    private fun page(
        scripts: List<String> = emptyList(),
        videos: List<String> = emptyList(),
        metas: Map<String, String> = emptyMap(),
        title: String = "",
    ): String = buildJsonObject {
        put("url", pageUrl)
        put("title", title)
        put("metas", buildJsonObject { metas.forEach { (key, value) -> put(key, value) } })
        put("videos", buildJsonArray { videos.forEach { add(it) } })
        put("scripts", buildJsonArray { scripts.forEach { add(it) } })
    }.toString()

    private fun item(scope: String) = """{"__DEFAULT_SCOPE__":{"webapp.app-context":{"language":"en"},"$scope":{"itemInfo":{"itemStruct":{"id":"7000000000000000001","desc":"Made Up Show S2E5 the lamp scene #madeupshow #fyp","author":{"uniqueId":"sample.user","nickname":"Sample"},"video":{"duration":41,"playAddr":"https://v16.example.test/play.mp4?token=a","downloadAddr":"https://v16.example.test/download.mp4?token=b","bitrateInfo":[{"PlayAddr":{"UrlList":["https://v16.example.test/play.mp4?token=a","https://v19.example.test/alt.mp4"]}}]},"music":{"playUrl":"https://music.example.test/song.mp3"}}}}}}"""

    @Test
    fun `reads caption author and video addresses from the desktop page shape`() {
        val result = ClipPageParser.parse(page(scripts = listOf(item("webapp.video-detail"))))
        assertEquals("Made Up Show S2E5 the lamp scene #madeupshow #fyp", result.caption)
        assertEquals("sample.user", result.author)
        assertEquals(pageUrl, result.pageUrl)
        assertEquals(
            listOf("https://v16.example.test/play.mp4?token=a", "https://v16.example.test/download.mp4?token=b", "https://v19.example.test/alt.mp4"),
            result.videoUrls,
        )
    }

    @Test
    fun `mobile page shape works and the video element comes first`() {
        val result = ClipPageParser.parse(
            page(
                scripts = listOf("""{"unrelated":true}""", item("webapp.reflow.video.detail")),
                videos = listOf("blob:https://www.tiktok.com/abc", "https://v16.example.test/element.mp4"),
            ),
        )
        assertEquals("Made Up Show S2E5 the lamp scene #madeupshow #fyp", result.caption)
        assertEquals("https://v16.example.test/element.mp4", result.videoUrls.first())
        assertEquals(4, result.videoUrls.size)
    }

    @Test
    fun `older page shape with the author as plain text`() {
        val sigi = """{"ItemModule":{"7000000000000000001":{"desc":"Another Made Up Show #clips","author":"plain.name","video":{"playAddr":"https://v.example.test/a.mp4"}}}}"""
        val result = ClipPageParser.parse(page(scripts = listOf(sigi)))
        assertEquals("Another Made Up Show #clips", result.caption)
        assertEquals("plain.name", result.author)
        assertEquals(listOf("https://v.example.test/a.mp4"), result.videoUrls)
    }

    @Test
    fun `instagram reel shape`() {
        val reel = """{"require":[["x",{"items":[{"caption":{"text":"Invented Drama season 3 episode 4"},"user":{"username":"sample_ig"},"video_versions":[{"url":"https://scontent.example.test/v1.mp4","width":720},{"url":"https://scontent.example.test/v2.mp4"}]}]}]]}"""
        val result = ClipPageParser.parse(page(scripts = listOf(reel)))
        assertEquals("Invented Drama season 3 episode 4", result.caption)
        assertEquals("sample_ig", result.author)
        assertEquals(listOf("https://scontent.example.test/v1.mp4", "https://scontent.example.test/v2.mp4"), result.videoUrls)
    }

    @Test
    fun `falls back to the page's meta tags and title`() {
        val withMetas = ClipPageParser.parse(
            page(metas = mapOf("og:description" to " Some Invented Show clip ", "og:video" to "https://cdn.example.test/og.mp4"), title = "ignored"),
        )
        assertEquals("Some Invented Show clip", withMetas.caption)
        assertEquals(listOf("https://cdn.example.test/og.mp4"), withMetas.videoUrls)
        assertEquals("Only A Title", ClipPageParser.parse(page(title = "Only A Title")).caption)
    }

    @Test
    fun `an item without a caption still gives its video and the meta caption`() {
        val noCaption = """{"a":{"desc":"","author":{"uniqueId":"quiet.user"},"video":{"playAddr":"https://v.example.test/quiet.mp4"}}}"""
        val result = ClipPageParser.parse(page(scripts = listOf(noCaption), metas = mapOf("og:description" to "From the meta tag")))
        assertEquals("From the meta tag", result.caption)
        assertEquals("quiet.user", result.author)
        assertEquals(listOf("https://v.example.test/quiet.mp4"), result.videoUrls)
    }

    @Test
    fun `the sound title the keywords and the hashtag list are read from a tiktok item`() {
        val item = """{"x":{"itemStruct":{"desc":"lol","author":{"uniqueId":"sample.user"},"video":{"playAddr":"https://v.example.test/a.mp4"},"music":{"title":"original sound - Made Up Show","authorName":"Sample","playUrl":"https://music.example.test/s.mp3"},"textExtra":[{"hashtagName":"madeupshow"},{"hashtagName":""},{"hashtagName":"fyp"}],"challenges":[{"title":"madeupshow"},{"title":"lampscene"}],"suggestedWords":["made up show","lamp scene","x"]}}}"""
        val result = ClipPageParser.parse(page(scripts = listOf(item)))
        assertEquals("original sound - Made Up Show - Sample", result.sound)
        assertEquals(listOf("madeupshow", "fyp", "lampscene"), result.hashtags)
        assertEquals(listOf("made up show", "lamp scene"), result.keywords)
        assertEquals("lol", result.caption)
    }

    @Test
    fun `the audio title is read from an instagram reel and a page without these has none`() {
        val reel = """{"items":[{"caption":{"text":"wow"},"user":{"username":"sample_ig"},"video_versions":[{"url":"https://scontent.example.test/v1.mp4"}],"clips_metadata":{"original_sound_info":{"original_audio_title":"Invented Drama theme"},"music_info":{"music_asset_info":{"title":"Lamp Song","display_artist":"Some Band"}}}}]}"""
        assertEquals("Invented Drama theme - Lamp Song - Some Band", ClipPageParser.parse(page(scripts = listOf(reel))).sound)
        val plain = ClipPageParser.parse(page(scripts = listOf(item("webapp.video-detail"))))
        assertEquals("", plain.sound)
        assertEquals(emptyList<String>(), plain.keywords)
        assertEquals(emptyList<String>(), plain.hashtags)
    }

    @Test
    fun `broken input never throws and gives an empty page`() {
        for (bad in listOf("", "not json", "[1,2]", "{\"scripts\":7,\"videos\":{},\"metas\":[]}", page(scripts = listOf("{broken", "", "null", "[[[[")))) {
            val result = ClipPageParser.parse(bad)
            assertEquals("", result.caption)
            assertEquals(emptyList<String>(), result.videoUrls)
        }
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderNative.kt`
```kotlin
package com.nuvio.app.features.clipfinder

/**
 * The iPhone-only work, done in Swift (iosApp/iosApp/ClipFinder/ClipFinderNativeImpl.swift).
 * [readPage] and [listen] return at once and answer through the listener, always on the main
 * thread. Only one of them runs at a time; starting one stops the other.
 */
interface ClipFinderNative {
    /** Loads the web page off-screen. Ends with exactly one onPage or onFailed. */
    fun readPage(link: String, listener: ClipNativeListener)

    /**
     * Turns a clip's sound into text. [mediaUrls] is either one file:// address (a shared video)
     * or the video addresses found on the page, best first; [pageUrl] is sent as the referer.
     * Calls onScreenText at most once (words read from a few frames, before the video file is
     * deleted), then onLine for each line, then ends with exactly one onDone or onFailed.
     */
    fun listen(mediaUrls: List<String>, pageUrl: String, listener: ClipNativeListener)

    /** Stops whatever runs. The listener of the stopped work is not called again. */
    fun cancel()

    /** Subtitle cache on disk (about 50 MB). Safe from any thread. Null when not stored. */
    fun cacheRead(key: String): String?

    fun cacheWrite(key: String, text: String)

    /** Small texts that must survive (the phone's key-value store, not the cache). Null when not stored. */
    fun settingRead(key: String): String?

    fun settingWrite(key: String, text: String)

    /**
     * Asks Apple's on-device language model (iOS 26 and later with Apple Intelligence on). Returns at
     * once and answers exactly once; when the model cannot be asked the answer carries the reason.
     */
    fun askModel(prompt: String, listener: ClipModelListener)
}

interface ClipModelListener {
    /** [text] is the model's answer, or null with [problem] saying in plain English why there is none. */
    fun onAnswer(text: String?, problem: String?)
}

interface ClipNativeListener {
    /** A diagnostic line for the screen, for example ("Audio", "312 s"). */
    fun onNote(label: String, value: String)

    /** [pageJson] is what the page says about itself; read it with [ClipPageParser]. */
    fun onPage(pageJson: String)

    /** Words shown in the video (titles such as "Made Up Show S2E5"), one piece of text per line. */
    fun onScreenText(text: String)

    fun onLine(text: String, startMs: Long, endMs: Long)

    fun onDone()

    /** [stage] is "Reading link" or "Listening"; [message] is plain English for the screen. */
    fun onFailed(stage: String, message: String)
}

/** Swift registers its implementation here when the app starts (iOSApp.swift). */
object ClipFinderBridge {
    private var registered: ClipFinderNative? = null

    fun register(impl: ClipFinderNative) {
        registered = impl
    }

    fun current(): ClipFinderNative? = registered
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderState.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.math.roundToInt

enum class ClipStage { ReadingLink, Listening, Searching, Done }

/** One diagnostic line on the screen ("Audio: 312 s"). Real data from the run, so a screenshot shows where it broke. */
data class ClipNote(val label: String, val value: String)

data class ClipAnswer(
    val candidate: ClipCandidate,
    val show: ShowGuess,
    val episodeTitle: String? = null,
    val thumbnail: String? = null,
)

data class ClipFinderState(
    val source: String = "",
    /** The stage that runs now, or the one that failed when [failed] is true. */
    val stage: ClipStage = ClipStage.ReadingLink,
    val failed: Boolean = false,
    val message: String = "",
    val showFileHint: Boolean = false,
    val progress: String = "",
    val notes: List<ClipNote> = emptyList(),
    val lines: List<ClipLine> = emptyList(),
    /** What is known about the clip besides its sound; kept so a typed show name can search again. */
    val clues: ClipClues = ClipClues(),
    val answers: List<ClipAnswer> = emptyList(),
) {
    /** A note with the same label is replaced where it stands; a new label goes to the end. */
    fun withNote(label: String, value: String): ClipFinderState {
        val note = ClipNote(label, value)
        val index = notes.indexOfFirst { it.label == label }
        return copy(notes = if (index < 0) notes + note else notes.toMutableList().also { it[index] = note })
    }
}

internal const val CLIP_LEAD_IN_MS = 10_000L

internal object ClipMessages {
    const val NO_BRIDGE = "Clip finder only works in the iPhone app."
    const val PAGE_TIMEOUT = "Reading the link took longer than 45 s."
    const val PAGE_FAILED = "The page could not be read."
    const val NO_VIDEO = "Nuvio could not find the video's address on the page. The site may have asked for a login or changed its page."
    const val LISTEN_TIMEOUT = "Listening took longer than 7 minutes and was stopped."
    const val NO_SPEECH = "No speech was heard in this clip (music only, or not in English)."
    const val NO_SHOW = "Nuvio could not work out the show from the caption, the hashtags, the poster or the text on screen. Type its name below."
    const val NO_TYPED_SHOW = "No show or movie in your catalogs has that name. Check the spelling and try again."
    const val NO_EPISODES = "The episode list of the guessed shows could not be loaded."
    const val NO_SUBTITLES = "No English subtitles were found. Check that a subtitle add-on (OpenSubtitles) is switched on in Nuvio."
    const val NO_MATCH = "No match: what was heard does not line up with the subtitles of the guessed shows. If you know the show, type its name below."
    const val FILE_HINT = "Other way: save the video to your iPhone, then in the Files app hold it, tap Share and pick Nuvio."
    fun unexpected(error: Throwable): String = "Something went wrong: " + (error.message ?: error.toString()).take(200)
}

/** The type-the-show box is shown once there is something heard to search with. */
internal fun clipCanType(state: ClipFinderState): Boolean =
    state.lines.isNotEmpty() && (state.stage == ClipStage.Searching || state.stage == ClipStage.Done)

/** Where playback starts: 10 s before the matched moment, or right after it. */
internal fun clipStartMs(candidate: ClipCandidate, afterClip: Boolean): Long =
    if (afterClip) candidate.endMs else maxOf(0L, candidate.startMs - CLIP_LEAD_IN_MS)

/** "4:07" or "1:02:09". */
internal fun clipClock(ms: Long): String {
    val total = maxOf(0L, ms) / 1000
    val hours = total / 3600
    val minutes = (total % 3600) / 60
    val seconds = (total % 60).toString().padStart(2, '0')
    return if (hours > 0) "$hours:${minutes.toString().padStart(2, '0')}:$seconds" else "$minutes:$seconds"
}

/** "South Park, season 14 episode 2: Title" or just the movie's name. */
internal fun clipAnswerTitle(answer: ClipAnswer): String {
    val season = answer.candidate.season
    val episode = answer.candidate.episode
    if (season == null || episode == null) return answer.show.name
    val title = answer.episodeTitle?.takeIf { it.isNotBlank() }?.let { ": $it" }.orEmpty()
    return "${answer.show.name}, season $season episode $episode$title"
}

/** "at 4:07 to 9:30, 86% sure" or "..., 31% (weak)". */
internal fun clipAnswerDetail(answer: ClipAnswer): String {
    val c = answer.candidate
    val percent = (c.confidence * 100).roundToInt()
    return "at ${clipClock(c.startMs)} to ${clipClock(c.endMs)}, " + if (c.confident) "$percent% sure" else "$percent% (weak)"
}

/** "done", "now", "failed" or "" for stage number [index] (0..2) of CLIP_FINDER_STAGES. */
internal fun clipStageMark(state: ClipFinderState, index: Int): String = when {
    index < state.stage.ordinal -> "done"
    index > state.stage.ordinal -> ""
    state.failed -> "failed"
    else -> "now"
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderPipeline.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.coroutines.CoroutineContext
import kotlin.coroutines.resume
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

/**
 * The whole run for one shared clip: read the link, listen, search episodes. Everything that
 * touches the phone or the network is passed in, so this is tested with fakes.
 * Call [run] from the main thread; [emit] may be called from another thread.
 */
class ClipFinderPipeline(
    private val native: ClipFinderNative?,
    private val finder: ClipShowFinder,
    private val loadEpisodes: suspend (ShowGuess) -> List<ClipEpisode>,
    private val subtitles: EpisodeSubtitleSource,
    private val memory: ClipMemory,
    private val now: () -> Long,
    private val work: CoroutineContext = Dispatchers.Default,
) {
    private class NativeResult(
        val page: String? = null,
        val lines: List<ClipLine> = emptyList(),
        val screenText: List<String> = emptyList(),
        val error: String? = null,
        val failedStage: String = "",
    )

    suspend fun run(source: String, emit: (ClipFinderState) -> Unit) =
        guarded(Run(ClipFinderState(source = source), emit)) { it.stages() }

    /**
     * Searches again with a show name the user typed. [previous] is the state of the finished (or
     * stopped) run: what was heard and the other clues are reused, nothing is read or listened to again.
     */
    suspend fun runTyped(previous: ClipFinderState, typed: String, emit: (ClipFinderState) -> Unit) {
        val start = previous.copy(
            stage = ClipStage.Searching,
            failed = false,
            message = "",
            showFileHint = false,
            progress = "",
            notes = previous.notes.filter { it.label !in SEARCH_NOTES },
            answers = emptyList(),
            clues = previous.clues.copy(typed = typed.trim().take(MAX_TYPED)),
        )
        guarded(Run(start, emit)) { it.search() }
    }

    private suspend fun guarded(run: Run, block: suspend (Run) -> Unit) {
        try {
            block(run)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            run.fail(ClipMessages.unexpected(e))
        }
    }

    private inner class Run(start: ClipFinderState, private val emit: (ClipFinderState) -> Unit) {
        private val state = MutableStateFlow(start)
        private val source = start.source
        private val isFile = source.startsWith("file:", ignoreCase = true)

        fun change(block: (ClipFinderState) -> ClipFinderState) {
            state.update(block)
            emit(state.value)
        }

        fun note(label: String, value: String) = change { it.withNote(label, value) }

        fun fail(message: String, fileHint: Boolean = false) =
            change { it.copy(failed = true, message = message, showFileHint = fileHint, progress = "") }

        suspend fun stages() {
            emit(state.value)
            val phone = this@ClipFinderPipeline.native ?: return fail(ClipMessages.NO_BRIDGE)

            // 1. Reading link
            var pageClues = ClipClues()
            var mediaUrls = listOf(source)
            var pageUrl = ""
            if (!isFile) {
                val read = withTimeoutOrNull(PAGE_TIMEOUT_MS) { call { phone.readPage(source, it) } }
                    ?: return fail(ClipMessages.PAGE_TIMEOUT, fileHint = true)
                val pageJson = read.page ?: return fail(read.error ?: ClipMessages.PAGE_FAILED, fileHint = true)
                val page = ClipPageParser.parse(pageJson)
                mediaUrls = page.videoUrls
                pageUrl = page.pageUrl.ifBlank { source }
                pageClues = ClipClues(
                    caption = page.caption,
                    author = page.author.ifBlank { ClipNames.authorInLink(pageUrl) },
                    sound = page.sound,
                    keywords = page.keywords,
                    hashtags = page.hashtags,
                )
                note("Caption", pageClues.caption.ifBlank { "none" }.take(120))
                if (pageClues.author.isNotBlank()) note("Author", pageClues.author)
                if (pageClues.sound.isNotBlank()) note("Sound", pageClues.sound.take(100))
                if (pageClues.keywords.isNotEmpty()) note("Keywords", pageClues.keywords.joinToString().take(160))
                note("Video address found", if (mediaUrls.isEmpty()) "no" else "yes (${mediaUrls.size})")
                if (mediaUrls.isEmpty()) return fail(ClipMessages.NO_VIDEO, fileHint = true)
            } else {
                change { it.copy(stage = ClipStage.Listening) }
            }

            // 2. Listening (for a link the download still counts as reading the link)
            val heard = withTimeoutOrNull(LISTEN_TIMEOUT_MS) { call { phone.listen(mediaUrls, pageUrl, it) } }
                ?: return fail(ClipMessages.LISTEN_TIMEOUT, fileHint = !isFile)
            if (heard.error != null) {
                if (heard.failedStage == CLIP_FINDER_STAGES[1]) change { it.copy(stage = ClipStage.Listening) }
                return fail(heard.error, fileHint = !isFile)
            }
            val lines = heard.lines
            val clues = pageClues.copy(screenText = heard.screenText)
            change { it.copy(stage = ClipStage.Listening, lines = lines, clues = clues).withNote("Lines heard", lines.size.toString()) }
            note("Text on screen", clues.screenText.joinToString(" | ").ifBlank { "none" }.take(200))
            if (lines.sumOf { ClipText.normalize(it.text).size } < MIN_WORDS) return fail(ClipMessages.NO_SPEECH)
            search()
        }

        /** 3. Searching episodes, from the clues and lines in the state. A missing caption never stops it. */
        suspend fun search() {
            val clues = state.value.clues
            val lines = state.value.lines
            change { it.copy(stage = ClipStage.Searching, progress = "Working out the show") }
            if (clues.typed.isNotBlank()) note("Show typed", clues.typed)
            var suspects = finder.find(clues, lines) { label, value -> note(label, value) }
            val hint = ClipNames.hint(clues, lines)
            val episodeLists = mutableMapOf<String, List<ClipEpisode>>()
            suspend fun episodesOf(show: ShowGuess): List<ClipEpisode> =
                episodeLists.getOrPut(show.metaId) { orderEpisodes(quietly { loadEpisodes(show) }.orEmpty(), hint) }

            // Many suspects: one subtitle file of each tells which show has the people named in the clip.
            val names = ClipNameCheck.names(lines)
            if (ClipNameCheck.needed(suspects, names)) {
                change { it.copy(progress = "Checking which show has the names heard") }
                note("Names heard", names.joinToString())
                val ranked = withTimeoutOrNull(NAME_CHECK_MS) {
                    ClipNameCheck.rank(suspects, names) { show ->
                        episodesOf(show).firstOrNull()?.let { episode -> subtitles.cues(show.metaId, episode) }
                    }
                }
                if (ranked != null) {
                    note("Name check", ranked.joinToString { "${it.first.show.name} ${it.second}" }.take(300))
                    suspects = ranked.map { it.first }
                }
            }
            val chosen = suspects.take(ClipNameCheck.KEEP)
            val guesses = chosen.map { it.show }
            note("Show guesses", chosen.joinToString { "${it.show.name} (${it.why})" }.ifBlank { "none" })
            if (guesses.isEmpty()) return fail(if (clues.typed.isBlank()) ClipMessages.NO_SHOW else ClipMessages.NO_TYPED_SHOW)
            val deadline = now() + SEARCH_BUDGET_MS
            val owners = mutableMapOf<String, Pair<ShowGuess, ClipEpisode>>()
            var best = emptyList<EpisodeCues>()
            var candidates = emptyList<ClipCandidate>()
            var tried = 0
            var withSubtitles = 0
            for (guess in guesses) {
                if (now() >= deadline) break
                change { it.copy(progress = "Loading the episode list of ${guess.name}") }
                val episodes = episodesOf(guess)
                if (episodes.isEmpty()) continue
                for (episode in episodes) owners[episode.videoId] = guess to episode
                val showDeadline = minOf(deadline, now() + SHOW_BUDGET_MS)
                val result = withContext(work) {
                    subtitles.search(guess.metaId, episodes, lines, showDeadline, best) { done, total, found ->
                        change { it.copy(progress = "Searching ${guess.name}: $done of $total episodes, $found with subtitles") }
                    }
                }
                best = result.best
                candidates = result.candidates
                tried += result.tried
                withSubtitles += result.withSubtitles
                if (result.decisive) break
                if (result.tried < episodes.size) note("Search", "stopped at the time limit in ${guess.name}")
            }
            note("Subtitles", "$withSubtitles of $tried episodes")
            if (tried == 0) return fail(ClipMessages.NO_EPISODES)
            if (withSubtitles == 0) return fail(ClipMessages.NO_SUBTITLES)
            val answers = candidates.filter { it.hits >= ClipMatcher.MIN_HITS }.mapNotNull { candidate ->
                owners[candidate.videoId]?.let { (show, episode) -> ClipAnswer(candidate, show, episode.title, episode.thumbnail) }
            }
            note("Candidates", answers.size.toString())
            if (answers.isEmpty()) return fail(ClipMessages.NO_MATCH)
            change { it.copy(stage = ClipStage.Done, answers = answers, progress = "") }
            // A confident match is remembered (show and poster only), so the next clip of this show or poster starts there.
            val top = answers.first()
            if (top.candidate.confident) runCatching { memory.remember(clues.author, top.show) }
        }

        /** Starts one native call and waits for its end. Cancelling (or a time-out) stops the native work. */
        private suspend fun call(start: (ClipNativeListener) -> Unit): NativeResult =
            suspendCancellableCoroutine { continuation ->
                val lines = mutableListOf<ClipLine>()
                val screen = mutableListOf<String>()
                var ended = false
                fun end(result: NativeResult) {
                    if (ended) return
                    ended = true
                    continuation.resume(result)
                }
                continuation.invokeOnCancellation {
                    ended = true
                    native?.cancel()
                }
                start(object : ClipNativeListener {
                    override fun onNote(label: String, value: String) {
                        if (ended) return
                        if (label == "Audio") change { it.copy(stage = ClipStage.Listening) }
                        note(label, value)
                    }

                    override fun onPage(pageJson: String) = end(NativeResult(page = pageJson))

                    override fun onScreenText(text: String) {
                        if (ended) return
                        screen += text.lines().map { it.trim().take(MAX_TYPED) }.filter { it.isNotEmpty() }.take(maxOf(0, MAX_SCREEN_LINES - screen.size))
                    }

                    override fun onLine(text: String, startMs: Long, endMs: Long) {
                        if (!ended) lines += ClipLine(text, startMs, endMs)
                    }

                    override fun onDone() = end(NativeResult(lines = lines.toList(), screenText = screen.toList()))

                    override fun onFailed(stage: String, message: String) =
                        end(NativeResult(error = message, failedStage = stage))
                })
            }

        private suspend fun <T> quietly(block: suspend () -> T): T? =
            try {
                block()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                null
            }
    }

    companion object {
        const val PAGE_TIMEOUT_MS = 45_000L
        const val LISTEN_TIMEOUT_MS = 420_000L
        const val SEARCH_BUDGET_MS = 240_000L
        const val SHOW_BUDGET_MS = 120_000L
        /** Fewer recognised words than this cannot be matched: "no speech". */
        const val MIN_WORDS = 6
        const val MAX_TYPED = 80
        const val NAME_CHECK_MS = 45_000L
        const val MAX_SCREEN_LINES = 40
        /** Notes of a search; removed when a typed show name starts a new search. */
        private val SEARCH_NOTES =
            setOf("Show typed", "Known titles", "Searches", "Names heard", "Name check", "Show guesses", "Search", "Subtitles", "Candidates")
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderSession.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import com.nuvio.app.features.addons.AddonRepository
import com.nuvio.app.features.addons.enabledAddons
import com.nuvio.app.features.addons.httpGetTextWithHeaders
import com.nuvio.app.features.catalog.fetchCatalogPage
import com.nuvio.app.features.details.MetaDetailsRepository
import com.nuvio.app.features.player.addonSubtitleRequests
import com.nuvio.app.features.player.loadAddonSubtitles
import com.nuvio.app.features.streams.epochMs
import kotlin.coroutines.resume
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull

/**
 * The one running Clip finder search. It lives outside the screen so that going to the stream list
 * and back does not start the search again.
 */
object ClipFinderSession {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val _state = MutableStateFlow(ClipFinderState())
    val state: StateFlow<ClipFinderState> = _state.asStateFlow()
    private var job: Job? = null
    private var runId = 0
    private var pipeline: ClipFinderPipeline? = null

    /** Starts the search for [source]. Does nothing when that clip is already running or shown, unless [restart]. */
    fun start(source: String, restart: Boolean = false) {
        if (!restart && _state.value.source == source) return
        job?.cancel()
        val id = ++runId
        _state.value = ClipFinderState(source = source)
        val native = ClipFinderBridge.current()
        val cache = object : ClipSubtitleCache {
            override fun read(key: String): String? = native?.cacheRead(key)
            override fun write(key: String, text: String) {
                native?.cacheWrite(key, text)
            }
        }
        val memory = ClipMemory(
            read = { native?.settingRead(ClipMemory.KEY) },
            write = { text -> native?.settingWrite(ClipMemory.KEY, text) },
            now = ::epochMs,
        )
        val created = ClipFinderPipeline(
            native = native,
            finder = ClipShowFinder(::clipSearchShows, ::clipPopularShows, memory) { prompt -> clipAskModel(native, prompt) },
            loadEpisodes = ::clipLoadEpisodes,
            subtitles = EpisodeSubtitleSource(::clipListSubtitles, ::clipDownloadText, cache, ::epochMs),
            memory = memory,
            now = ::epochMs,
        )
        pipeline = created
        job = scope.launch {
            created.run(source) { if (id == runId) _state.value = it }
        }
    }

    /** Searches again with a show name the user typed, reusing what was heard. Stops a search that still runs. */
    fun searchTyped(name: String) {
        val current = _state.value
        val active = pipeline ?: return
        if (name.isBlank() || !clipCanType(current)) return
        job?.cancel()
        val id = ++runId
        job = scope.launch {
            active.runTyped(current, name) { if (id == runId) _state.value = it }
        }
    }
}

private const val MODEL_TIMEOUT_MS = 12_000L

/** One question to Apple's on-device model through the bridge; a missing bridge or no answer in 12 s is a problem text. */
internal suspend fun clipAskModel(native: ClipFinderNative?, prompt: String): ClipModelAnswer {
    val phone = native ?: return ClipModelAnswer(problem = "only in the iPhone app")
    return withTimeoutOrNull(MODEL_TIMEOUT_MS) {
        suspendCancellableCoroutine { continuation ->
            phone.askModel(
                prompt,
                object : ClipModelListener {
                    override fun onAnswer(text: String?, problem: String?) {
                        if (continuation.isActive) continuation.resume(ClipModelAnswer(text.orEmpty(), problem.orEmpty()))
                    }
                },
            )
        }
    } ?: ClipModelAnswer(problem = "no answer in 12 s")
}

private var popularShows: List<ShowGuess> = emptyList()

/**
 * Well-known titles to compare hashtags and handles with: the first page of every plain catalog
 * (series and movies, no required filter) of the switched-on add-ons, for example Cinemeta's
 * "Popular". Fetched once per app start; an empty answer is asked for again next time.
 */
internal suspend fun clipPopularShows(): List<ShowGuess> {
    if (popularShows.isNotEmpty()) return popularShows
    AddonRepository.initialize()
    val catalogs = AddonRepository.uiState.value.addons.enabledAddons().mapNotNull { it.manifest }.flatMap { manifest ->
        manifest.catalogs
            .filter { catalog -> (catalog.type == "series" || catalog.type == "movie") && catalog.extra.none { it.isRequired } }
            .map { manifest to it }
    }.take(8)
    val pages = coroutineScope {
        catalogs.map { (manifest, catalog) ->
            async {
                quietly(8_000L) { fetchCatalogPage(manifest.transportUrl, catalog.type, catalog.id, maxItems = 100).items }.orEmpty()
            }
        }.awaitAll()
    }
    val shows = pages.flatten().filter { it.name.isNotBlank() }.map { ShowGuess(it.id, it.type, it.name, it.poster) }.distinctBy { it.metaId }
    popularShows = shows.filter { it.metaId.startsWith("tt") }.ifEmpty { shows }
    return popularShows
}

private suspend fun <T> quietly(timeoutMs: Long, block: suspend () -> T): T? =
    withTimeoutOrNull(timeoutMs) {
        try {
            block()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            null
        }
    }

/** Nuvio's own search: every search catalog (series and movies) of the switched-on add-ons, results mixed by rank. */
internal suspend fun clipSearchShows(query: String): List<ShowGuess> = coroutineScope {
    AddonRepository.initialize()
    val catalogs = AddonRepository.uiState.value.addons.enabledAddons().mapNotNull { it.manifest }.flatMap { manifest ->
        manifest.catalogs
            .filter { catalog ->
                (catalog.type == "series" || catalog.type == "movie") &&
                    catalog.extra.any { it.name == "search" } &&
                    catalog.extra.none { it.isRequired && it.name != "search" }
            }
            .map { manifest to it }
    }.take(6)
    val pages = catalogs.map { (manifest, catalog) ->
        async {
            quietly(8_000L) {
                fetchCatalogPage(manifest.transportUrl, catalog.type, catalog.id, search = query, maxItems = 8).items
            }.orEmpty()
        }
    }.awaitAll()
    val mixed = (0 until 8).flatMap { rank -> pages.mapNotNull { it.getOrNull(rank) } }
        .map { ShowGuess(it.id, it.type, it.name, it.poster) }
        .distinctBy { it.metaId }
    // Subtitle add-ons only know IMDb ids ("tt..."), so those results go first when there are any.
    mixed.filter { it.metaId.startsWith("tt") }.ifEmpty { mixed }
}

/** The episodes of a series (specials and season 0 left out), or the movie itself as one entry. */
internal suspend fun clipLoadEpisodes(show: ShowGuess): List<ClipEpisode> {
    val meta = quietly(25_000L) { MetaDetailsRepository.fetch(show.type, show.metaId) } ?: return emptyList()
    val imdbId = listOf(meta.id, meta.imdbId.orEmpty(), show.metaId).firstOrNull { it.startsWith("tt") }
    val episodes = meta.videos.filter { (it.season ?: 0) > 0 && it.episode != null }
    if (episodes.isEmpty()) {
        return listOf(ClipEpisode(videoId = meta.id, subtitleId = imdbId ?: meta.id, type = show.type))
    }
    return episodes.map { video ->
        val subtitleId = if (video.id.startsWith("tt") || imdbId == null) video.id else "$imdbId:${video.season}:${video.episode}"
        ClipEpisode(video.id, subtitleId, show.type, video.season, video.episode, video.title, video.thumbnail)
    }
}

internal suspend fun clipListSubtitles(type: String, subtitleId: String): List<ClipSubtitleLink> =
    loadAddonSubtitles(addonSubtitleRequests(type, subtitleId)).map { ClipSubtitleLink(it.url, it.language) }

internal suspend fun clipDownloadText(url: String): String = httpGetTextWithHeaders(url, emptyMap())
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderScreen.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
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

/** [onOpen] gets the tapped candidate and the time to start playing from, in milliseconds. */
@Composable
fun ClipFinderScreen(source: String, onBack: () -> Unit, onOpen: (ClipAnswer, Long) -> Unit = { _, _ -> }) {
    val colors = MaterialTheme.nuvio.colors
    val current by ClipFinderSession.state.collectAsStateWithLifecycle()
    val state = if (current.source == source) current else ClipFinderState(source = source)
    var afterClip by rememberSaveable { mutableStateOf(false) }
    LaunchedEffect(source) { ClipFinderSession.start(source) }

    NuvioScreen {
        item { NuvioScreenHeader(title = CLIP_FINDER_TITLE, onBack = onBack) }
        item {
            NuvioSurfaceCard {
                NuvioSectionLabel(if (isClipFile(source)) "Shared video" else "Shared link")
                Text(clipSourceLabel(source), style = MaterialTheme.typography.bodyMedium, color = colors.textPrimary)
            }
        }
        item { ClipStagesCard(state) }
        if (state.failed) {
            item { ClipFailureCard(state, onRetry = { ClipFinderSession.start(source, restart = true) }) }
        }
        if (state.answers.isNotEmpty()) {
            item { ClipAnswersCard(state.answers, afterClip, onAfterClip = { afterClip = it }, onOpen = onOpen) }
        }
        if (clipCanType(state)) {
            item { ClipTypeCard(onSearch = { ClipFinderSession.searchTyped(it) }) }
        }
        if (state.notes.isNotEmpty()) {
            item { ClipNotesCard(state.notes) }
        }
        if (state.lines.isNotEmpty()) {
            item { ClipLinesCard(state.lines) }
        }
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderParts.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.nuvio.app.core.ui.Chip
import com.nuvio.app.core.ui.NuvioInputField
import com.nuvio.app.core.ui.NuvioPrimaryButton
import com.nuvio.app.core.ui.NuvioSectionLabel
import com.nuvio.app.core.ui.NuvioSurfaceCard
import com.nuvio.app.core.ui.nuvio

@Composable
internal fun ClipStagesCard(state: ClipFinderState) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Steps")
        CLIP_FINDER_STAGES.forEachIndexed { index, stage ->
            val mark = clipStageMark(state, index)
            Text(
                text = "${index + 1}. $stage" + if (mark.isEmpty()) "" else " ($mark)",
                style = MaterialTheme.typography.bodyMedium,
                color = if (mark == "now" || mark == "failed") colors.textPrimary else colors.textMuted,
            )
        }
        if (state.progress.isNotBlank()) {
            Text(state.progress, style = MaterialTheme.typography.bodyMedium, color = colors.textPrimary)
        }
    }
}

@Composable
internal fun ClipFailureCard(state: ClipFinderState, onRetry: () -> Unit) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Stopped at: ${CLIP_FINDER_STAGES.getOrElse(state.stage.ordinal) { "" }}")
        Text(state.message, style = MaterialTheme.typography.bodyMedium, color = colors.textPrimary)
        if (state.showFileHint) {
            Text(ClipMessages.FILE_HINT, style = MaterialTheme.typography.bodyMedium, color = colors.textMuted)
        }
        NuvioPrimaryButton(text = "Try again", modifier = Modifier.padding(top = 8.dp), onClick = onRetry)
    }
}

@Composable
internal fun ClipAnswersCard(
    answers: List<ClipAnswer>,
    afterClip: Boolean,
    onAfterClip: (Boolean) -> Unit,
    onOpen: (ClipAnswer, Long) -> Unit,
) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Found (tap one, then pick a stream)")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(vertical = 8.dp)) {
            Chip(label = "From clip start", selected = !afterClip, onClick = { onAfterClip(false) })
            Chip(label = "After the clip", selected = afterClip, onClick = { onAfterClip(true) })
        }
        answers.forEach { answer ->
            val startMs = clipStartMs(answer.candidate, afterClip)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onOpen(answer, startMs) }
                    .padding(vertical = 8.dp),
            ) {
                Text(clipAnswerTitle(answer), style = MaterialTheme.typography.titleMedium, color = colors.textPrimary)
                Text(
                    text = clipAnswerDetail(answer) + ". Plays from ${clipClock(startMs)}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = colors.textMuted,
                )
            }
        }
    }
}

/** The show name typed here is searched with what was already heard: nothing is read or listened to again. */
@Composable
internal fun ClipTypeCard(onSearch: (String) -> Unit) {
    val colors = MaterialTheme.nuvio.colors
    var name by rememberSaveable { mutableStateOf("") }
    NuvioSurfaceCard {
        NuvioSectionLabel("Know the show? Type its name")
        Text(
            text = "Nuvio searches it with what it already heard. Nothing is listened to again.",
            style = MaterialTheme.typography.bodySmall,
            color = colors.textMuted,
        )
        NuvioInputField(
            value = name,
            onValueChange = { name = it.take(80) },
            placeholder = "Show or movie name",
            modifier = Modifier.padding(vertical = 8.dp),
        )
        NuvioPrimaryButton(text = "Search this show", enabled = name.isNotBlank(), onClick = { onSearch(name) })
    }
}

@Composable
internal fun ClipNotesCard(notes: List<ClipNote>) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Details (for a screenshot if something fails)")
        notes.forEach { note ->
            Text("${note.label}: ${note.value}", style = MaterialTheme.typography.bodySmall, color = colors.textMuted)
        }
    }
}

@Composable
internal fun ClipLinesCard(lines: List<ClipLine>) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Heard (first lines)")
        lines.take(6).forEach { line ->
            Text("${clipClock(line.startMs)}  ${line.text}", style = MaterialTheme.typography.bodySmall, color = colors.textMuted)
        }
    }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipFinderStateTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.test.Test
import kotlin.test.assertEquals

class ClipFinderStateTest {
    private fun candidate(startMs: Long, endMs: Long, season: Int? = 2, episode: Int? = 5, confident: Boolean = true) =
        ClipCandidate("tt001:2:5", season, episode, startMs, endMs, 0.86, 12, confident)

    private fun answer(season: Int?, episode: Int?, title: String?) =
        ClipAnswer(candidate(0, 1_000, season, episode), ShowGuess("tt001", "series", "Made Up Show"), title)

    @Test
    fun `a note with the same label is replaced in place and a new label goes last`() {
        val state = ClipFinderState().withNote("A", "1").withNote("B", "2").withNote("A", "3")
        assertEquals(listOf(ClipNote("A", "3"), ClipNote("B", "2")), state.notes)
    }

    @Test
    fun `playback starts ten seconds before the moment or right after it`() {
        val found = candidate(250_000, 400_000)
        assertEquals(240_000L, clipStartMs(found, afterClip = false))
        assertEquals(400_000L, clipStartMs(found, afterClip = true))
        assertEquals(0L, clipStartMs(candidate(4_000, 20_000), afterClip = false))
    }

    @Test
    fun `clock text`() {
        assertEquals("4:07", clipClock(247_000))
        assertEquals("1:02:09", clipClock(3_729_000))
        assertEquals("0:00", clipClock(-5))
    }

    @Test
    fun `stage marks for a running, a failed and a finished run`() {
        val running = ClipFinderState(stage = ClipStage.Searching)
        assertEquals(listOf("done", "done", "now"), (0..2).map { clipStageMark(running, it) })
        val failed = ClipFinderState(stage = ClipStage.Listening, failed = true)
        assertEquals(listOf("done", "failed", ""), (0..2).map { clipStageMark(failed, it) })
        val finished = ClipFinderState(stage = ClipStage.Done)
        assertEquals(listOf("done", "done", "done"), (0..2).map { clipStageMark(finished, it) })
    }

    @Test
    fun `answer titles for an episode with and without a title and for a movie`() {
        assertEquals("Made Up Show, season 2 episode 5: The Lamp", clipAnswerTitle(answer(2, 5, "The Lamp")))
        assertEquals("Made Up Show, season 2 episode 5", clipAnswerTitle(answer(2, 5, null)))
        assertEquals("Made Up Show, season 2 episode 5", clipAnswerTitle(answer(2, 5, "  ")))
        assertEquals("Made Up Show", clipAnswerTitle(answer(null, null, null)))
    }

    @Test
    fun `answer detail says how sure the match is`() {
        assertEquals("at 4:07 to 9:30, 86% sure", clipAnswerDetail(ClipAnswer(candidate(247_000, 570_000), ShowGuess("tt001", "series", "Made Up Show"))))
        assertEquals(
            "at 0:10 to 0:20, 86% (weak)",
            clipAnswerDetail(ClipAnswer(candidate(10_000, 20_000, confident = false), ShowGuess("tt001", "series", "Made Up Show"))),
        )
    }

    @Test
    fun `the type box appears once something was heard and the search has started`() {
        val heard = listOf(ClipLine("bako ritu", 0, 1_000))
        assertEquals(false, clipCanType(ClipFinderState(stage = ClipStage.Searching)))
        assertEquals(false, clipCanType(ClipFinderState(stage = ClipStage.Listening, lines = heard)))
        assertEquals(true, clipCanType(ClipFinderState(stage = ClipStage.Searching, lines = heard)))
        assertEquals(true, clipCanType(ClipFinderState(stage = ClipStage.Searching, lines = heard, failed = true)))
        assertEquals(true, clipCanType(ClipFinderState(stage = ClipStage.Done, lines = heard)))
    }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipFinderPipelineTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.coroutines.EmptyCoroutineContext
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.add
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/** Everything here is made up: names, captions, subtitle words and addresses. */
@OptIn(ExperimentalCoroutinesApi::class)
class ClipFinderPipelineTest {
    private val link = "https://clips.example.test/@sample.user/video/7000000000000000001"
    private val element = "https://v16.example.test/element.mp4"
    private val play = "https://v16.example.test/play.mp4"
    private val caption = "Made Up Show S2E5 the lamp scene #madeupshow #fyp"
    private val show = ShowGuess("tt001", "series", "Made Up Show")
    private val episodes = (1..2).flatMap { season ->
        (1..6).map { number -> ClipEpisode("tt001:$season:$number", "tt001:$season:$number", "series", season, number, "Title $season-$number") }
    }
    private val texts = episodes.associate { it.videoId to ClipTestText.cueTexts(it.season!! * 100 + it.episode!!) }
    private val clipLines = ClipTestText.linesFrom(texts.getValue("tt001:2:5"), 20..31)

    private fun pageJson(videos: List<String> = listOf(element), playAddr: String? = play, text: String = caption): String = buildJsonObject {
        put("url", link)
        put("title", "")
        put("metas", buildJsonObject {})
        put("videos", buildJsonArray { videos.forEach { add(it) } })
        put(
            "scripts",
            buildJsonArray {
                add(
                    buildJsonObject {
                        put(
                            "item",
                            buildJsonObject {
                                put("desc", text)
                                put("author", buildJsonObject { put("uniqueId", "sample.user") })
                                put("video", buildJsonObject { if (playAddr != null) put("playAddr", playAddr) })
                            },
                        )
                    }.toString(),
                )
            },
        )
    }.toString()

    private class FakeNative(
        val pageJson: String? = null,
        val pageError: String = "The page did not load.",
        val lines: List<ClipLine> = emptyList(),
        val listenError: String? = null,
        val silent: Boolean = false,
        val screenText: List<String> = emptyList(),
    ) : ClipFinderNative {
        var readLinks = 0
        var listenCalls = 0
        var cancels = 0
        var listenMedia: List<String>? = null
        var listenPage: String? = null

        override fun readPage(link: String, listener: ClipNativeListener) {
            readLinks++
            if (silent) return
            listener.onNote("Page loaded", "yes, after 3 s")
            if (pageJson != null) listener.onPage(pageJson) else listener.onFailed("Reading link", pageError)
        }

        override fun listen(mediaUrls: List<String>, pageUrl: String, listener: ClipNativeListener) {
            listenCalls++
            listenMedia = mediaUrls
            listenPage = pageUrl
            if (silent) return
            listener.onNote("Audio", "41 s")
            if (listenError != null) return listener.onFailed("Listening", listenError)
            if (screenText.isNotEmpty()) listener.onScreenText(screenText.joinToString("\n"))
            lines.forEach { listener.onLine(it.text, it.startMs, it.endMs) }
            listener.onDone()
        }

        override fun cancel() {
            cancels++
        }

        override fun cacheRead(key: String): String? = null

        override fun cacheWrite(key: String, text: String) = Unit

        override fun settingRead(key: String): String? = null

        override fun settingWrite(key: String, text: String) = Unit

        override fun askModel(prompt: String, listener: ClipModelListener) = listener.onAnswer(null, "not in tests")
    }

    private inner class Harness(
        val native: FakeNative?,
        val addon: FakeSubtitleAddon = FakeSubtitleAddon(texts),
        val search: suspend (String) -> List<ShowGuess> = { query -> if (query == "Made Up Show") listOf(show) else emptyList() },
        val load: suspend (ShowGuess) -> List<ClipEpisode> = { episodes },
        val popular: suspend () -> List<ShowGuess> = { emptyList() },
        val stored: MutableMap<String, String> = mutableMapOf(),
    ) {
        val states = mutableListOf<ClipFinderState>()
        val last: ClipFinderState get() = states.last()
        val memory = ClipMemory({ stored["memory"] }, { stored["memory"] = it }, { 1_000L })

        private fun pipeline(): ClipFinderPipeline {
            val subtitles = EpisodeSubtitleSource({ _, id -> addon.list(id) }, { url -> addon.download(url) }, MapSubtitleCache(), { 0L })
            return ClipFinderPipeline(native, ClipShowFinder(search, popular, memory), load, subtitles, memory, { 0L }, EmptyCoroutineContext)
        }

        suspend fun run(source: String = link) = pipeline().run(source) { states += it }

        suspend fun typed(name: String) = pipeline().runTyped(last, name) { states += it }
    }

    private fun assertFailed(h: Harness, stage: ClipStage, message: String, fileHint: Boolean) {
        assertTrue(h.last.failed)
        assertEquals(stage, h.last.stage)
        assertEquals(message, h.last.message)
        assertEquals(fileHint, h.last.showFileHint)
    }

    @Test
    fun `a link goes all the way to the episode`() = runTest {
        val fake = FakeNative(pageJson = pageJson(), lines = clipLines)
        val h = Harness(fake)
        h.run()
        assertEquals(ClipStage.Done, h.last.stage)
        assertFalse(h.last.failed)
        val top = h.last.answers.first()
        assertEquals("tt001:2:5", top.candidate.videoId)
        assertEquals(2, top.candidate.season)
        assertEquals(5, top.candidate.episode)
        assertEquals("Made Up Show", top.show.name)
        assertEquals(listOf(element, play), fake.listenMedia)
        assertEquals(link, fake.listenPage)
        assertEquals(
            listOf(
                "Page loaded", "Caption", "Author", "Video address found", "Audio", "Lines heard", "Text on screen",
                "Known titles", "Searches", "Show guesses", "Subtitles", "Candidates",
            ),
            h.last.notes.map { it.label },
        )
        assertTrue(h.addon.listCalls <= 6, "the hinted episode must be in the first batch")
        assertEquals("\"Made Up Show\": 1", h.last.notes.first { it.label == "Searches" }.value)
        assertEquals("0 popular, 0 shared before", h.last.notes.first { it.label == "Known titles" }.value)
    }

    @Test
    fun `a confident match is remembered and the poster alone finds the show next time`() = runTest {
        val stored = mutableMapOf<String, String>()
        val first = Harness(FakeNative(pageJson = pageJson(), lines = clipLines), stored = stored)
        first.run()
        assertEquals(listOf(show), first.memory.shows())
        assertEquals(show, first.memory.showFor("sample.user"))
        val second = Harness(FakeNative(pageJson = pageJson(text = ""), lines = clipLines), search = { emptyList() }, stored = stored)
        second.run()
        assertEquals(ClipStage.Done, second.last.stage)
        assertEquals("tt001:2:5", second.last.answers.first().candidate.videoId)
        assertTrue("this poster before" in second.last.notes.first { it.label == "Show guesses" }.value)
    }

    @Test
    fun `a hashtag without spaces finds a popular title when the search finds nothing`() = runTest {
        val fake = FakeNative(pageJson = pageJson(text = "lol #madeupshow #fyp"), lines = clipLines)
        val h = Harness(fake, search = { emptyList() }, popular = { listOf(show) })
        h.run()
        assertEquals(ClipStage.Done, h.last.stage)
        assertEquals("Made Up Show", h.last.answers.first().show.name)
        assertEquals("1 popular, 0 shared before", h.last.notes.first { it.label == "Known titles" }.value)
    }

    @Test
    fun `a title read from the video frames finds the show and the episode of a shared video`() = runTest {
        val fake = FakeNative(lines = clipLines, screenText = listOf("Made Up Show S2E5", "bako ritu"))
        val h = Harness(fake)
        h.run("file:///x/clip.mp4")
        assertEquals(ClipStage.Done, h.last.stage)
        assertEquals("tt001:2:5", h.last.answers.first().candidate.videoId)
        assertEquals("Made Up Show S2E5 | bako ritu", h.last.notes.first { it.label == "Text on screen" }.value)
        assertTrue(h.addon.listCalls <= 6, "the episode named on screen must be in the first batch")
    }

    @Test
    fun `with several suspects the names heard pick the show to search first`() = runTest {
        val showB = ShowGuess("tt002", "series", "Invented Drama")
        val episodesB = (1..3).map { ClipEpisode("tt002:1:$it", "tt002:1:$it", "series", 1, it, "Other $it") }
        val textsB = episodesB.associate { it.videoId to ClipTestText.cueTexts(900 + it.episode!!) }
        val first = listOf("bako Nancy ritu Pepper nesa dako") + ClipTestText.cueTexts(101).drop(1)
        val addon = FakeSubtitleAddon(texts + textsB + ("tt001:1:1" to first))
        val heard = clipLines + ClipLine("then Nancy told Pepper again", 60_000, 63_000)
        val h = Harness(
            FakeNative(pageJson = pageJson(text = "Invented Drama or Made Up Show"), lines = heard),
            addon = addon,
            search = { emptyList() },
            load = { guess -> if (guess.metaId == "tt002") episodesB else episodes },
            popular = { listOf(showB, show) },
        )
        h.run()
        assertEquals("Nancy, Pepper", h.last.notes.first { it.label == "Names heard" }.value)
        assertEquals("Made Up Show 2, Invented Drama 0", h.last.notes.first { it.label == "Name check" }.value)
        assertEquals(ClipStage.Done, h.last.stage)
        assertEquals("tt001:2:5", h.last.answers.first().candidate.videoId)
        assertTrue(addon.downloaded.none { "tt002:1:2" in it }, "the other show is only sampled, not searched")
    }

    @Test
    fun `typing the show searches again without reading or listening again`() = runTest {
        val fake = FakeNative(lines = clipLines)
        val h = Harness(fake, search = { query -> if (query == "made up show") listOf(show) else emptyList() })
        h.run("file:///x/clip.mp4")
        assertFailed(h, ClipStage.Searching, ClipMessages.NO_SHOW, fileHint = false)
        assertTrue(clipCanType(h.last))
        h.typed("  made up show ")
        assertEquals(ClipStage.Done, h.last.stage)
        assertFalse(h.last.failed)
        assertEquals("tt001:2:5", h.last.answers.first().candidate.videoId)
        assertEquals("made up show", h.last.notes.first { it.label == "Show typed" }.value)
        assertEquals(1, fake.listenCalls)
        assertEquals(0, fake.readLinks)
        h.typed("no such thing")
        assertFailed(h, ClipStage.Searching, ClipMessages.NO_TYPED_SHOW, fileHint = false)
        assertTrue(h.last.notes.none { it.label == "Subtitles" })
        assertEquals(1, fake.listenCalls)
    }

    @Test
    fun `a shared video skips the page and asks for the show when no clue names it`() = runTest {
        val fake = FakeNative(lines = clipLines)
        val h = Harness(fake)
        val file = "file:///x/My%20clip.mp4"
        h.run(file)
        assertEquals(0, fake.readLinks)
        assertEquals(listOf(file), fake.listenMedia)
        assertEquals("", fake.listenPage)
        assertFailed(h, ClipStage.Searching, ClipMessages.NO_SHOW, fileHint = false)
        assertEquals(clipLines, h.last.lines)
        assertEquals("none", h.last.notes.first { it.label == "Show guesses" }.value)
        assertEquals("none", h.last.notes.first { it.label == "Searches" }.value)
    }

    @Test
    fun `no bridge`() = runTest {
        val h = Harness(null)
        h.run()
        assertFailed(h, ClipStage.ReadingLink, ClipMessages.NO_BRIDGE, fileHint = false)
    }

    @Test
    fun `the page cannot be read`() = runTest {
        val h = Harness(FakeNative(pageError = "The page did not load."))
        h.run()
        assertFailed(h, ClipStage.ReadingLink, "The page did not load.", fileHint = true)
    }

    @Test
    fun `a page without a video address`() = runTest {
        val fake = FakeNative(pageJson = pageJson(videos = emptyList(), playAddr = null), lines = clipLines)
        val h = Harness(fake)
        h.run()
        assertFailed(h, ClipStage.ReadingLink, ClipMessages.NO_VIDEO, fileHint = true)
        assertEquals(0, fake.listenCalls)
    }

    @Test
    fun `listening fails for a link and for a file`() = runTest {
        val forLink = Harness(FakeNative(pageJson = pageJson(), listenError = "The video could not be downloaded."))
        forLink.run()
        assertFailed(forLink, ClipStage.Listening, "The video could not be downloaded.", fileHint = true)
        val forFile = Harness(FakeNative(listenError = "The video could not be opened."))
        forFile.run("file:///x/clip.mp4")
        assertFailed(forFile, ClipStage.Listening, "The video could not be opened.", fileHint = false)
    }

    @Test
    fun `no speech`() = runTest {
        val h = Harness(FakeNative(pageJson = pageJson(), lines = emptyList()))
        h.run()
        assertFailed(h, ClipStage.Listening, ClipMessages.NO_SPEECH, fileHint = false)
    }

    @Test
    fun `no show found`() = runTest {
        val h = Harness(FakeNative(pageJson = pageJson(), lines = clipLines), search = { emptyList() })
        h.run()
        assertFailed(h, ClipStage.Searching, ClipMessages.NO_SHOW, fileHint = false)
    }

    @Test
    fun `the episode list cannot be loaded`() = runTest {
        val h = Harness(FakeNative(pageJson = pageJson(), lines = clipLines), load = { throw IllegalStateException("offline") })
        h.run()
        assertFailed(h, ClipStage.Searching, ClipMessages.NO_EPISODES, fileHint = false)
    }

    @Test
    fun `the add-on lists no subtitles`() = runTest {
        val addon = FakeSubtitleAddon(texts)
        addon.links = { emptyList() }
        val h = Harness(FakeNative(pageJson = pageJson(), lines = clipLines), addon = addon)
        h.run()
        assertFailed(h, ClipStage.Searching, ClipMessages.NO_SUBTITLES, fileHint = false)
        assertEquals("0 of 12 episodes", h.last.notes.first { it.label == "Subtitles" }.value)
    }

    @Test
    fun `other words match nothing`() = runTest {
        val h = Harness(FakeNative(pageJson = pageJson(), lines = ClipTestText.unrelatedLines()))
        h.run()
        assertFailed(h, ClipStage.Searching, ClipMessages.NO_MATCH, fileHint = false)
    }

    @Test
    fun `a native side that never answers is stopped after 45 seconds`() = runTest {
        val fake = FakeNative(silent = true)
        val h = Harness(fake)
        val job = launch { h.run() }
        advanceTimeBy(46_000)
        runCurrent()
        assertFailed(h, ClipStage.ReadingLink, ClipMessages.PAGE_TIMEOUT, fileHint = true)
        assertEquals(1, fake.cancels)
        job.join()
    }

    @Test
    fun `cancelling a waiting run stops the native work`() = runTest {
        val fake = FakeNative(silent = true)
        val h = Harness(fake)
        val job = launch { h.run() }
        runCurrent()
        assertEquals(1, fake.readLinks)
        job.cancel()
        job.join()
        assertEquals(1, fake.cancels)
    }
}
```

##### File: `iosApp/iosApp/ClipFinder/ClipFrameReader.swift`
```swift
import AVFoundation
import CoreGraphics
import Foundation
import Vision

/// Reads the words shown on a few frames of the clip (titles such as "Made Up Show S2E5") with Apple
/// Vision, on this iPhone only. No state and no main-thread needs: call it on a background queue.
enum ClipFrameReader {
    private static let frameSeconds: [Double] = [0.5, 3.0, 8.0, 20.0, 45.0]
    private static let maxLines = 40

    /// Returns each distinct piece of text once, in the order found. Empty when nothing can be read.
    static func read(_ fileURL: URL) -> [String] {
        let generator = AVAssetImageGenerator(asset: AVURLAsset(url: fileURL))
        generator.appliesPreferredTrackTransform = true
        generator.maximumSize = CGSize(width: 1280, height: 1280)
        var lines: [String] = []
        var seen = Set<String>()
        for seconds in frameSeconds {
            let time = CMTime(seconds: seconds, preferredTimescale: 600)
            guard let image = try? generator.copyCGImage(at: time, actualTime: nil) else { continue }
            let request = VNRecognizeTextRequest()
            request.recognitionLevel = .accurate
            request.usesLanguageCorrection = false
            let handler = VNImageRequestHandler(cgImage: image, options: [:])
            do {
                try handler.perform([request])
            } catch {
                continue
            }
            for observation in request.results ?? [] {
                guard let best = observation.topCandidates(1).first, best.confidence >= 0.3 else { continue }
                let text = best.string.trimmingCharacters(in: .whitespacesAndNewlines)
                guard text.count >= 3, text.count <= 80, !seen.contains(text.lowercased()) else { continue }
                seen.insert(text.lowercased())
                lines.append(text)
                if lines.count >= maxLines { return lines }
            }
        }
        return lines
    }
}
```

##### File: `iosApp/iosApp/ClipFinder/ClipFinderNativeImpl.swift`
```swift
import Foundation
import ComposeApp

enum ClipFinderRegistration {
    static func register() {
        ClipFinderBridge.shared.register(impl: ClipFinderNativeImpl())
    }
}

/// Keeps the URL objects iOS hands over for shared video files: only those objects carry the right
/// to read a file that lives outside the app. Main thread only.
final class ClipFileInbox {
    static let shared = ClipFileInbox()
    private var urls: [String: URL] = [:]

    private init() {}

    func remember(_ url: URL) {
        if url.isFileURL { urls[url.absoluteString] = url }
    }

    func url(for source: String) -> URL? {
        urls[source] ?? URL(string: source)
    }
}

/// The Swift side of the Kotlin interface ClipFinderNative. Kotlin may call from any thread; all work
/// is moved to the main thread, and every listener call is made on the main thread.
final class ClipFinderNativeImpl: NSObject, ClipFinderNative {
    private let cache = ClipSubtitleDiskCache()
    private var run = 0
    private var pageReader: ClipPageReader?
    private var fetcher: ClipMediaFetcher?
    private var transcriber: ClipTranscriber?
    private var afterListening: (() -> Void)?
    private var cookies: [HTTPCookie] = []
    private var userAgent = ""

    func readPage(link: String, listener: ClipNativeListener) {
        DispatchQueue.main.async {
            self.stopWork()
            self.run += 1
            let run = self.run
            let reader = ClipPageReader()
            self.pageReader = reader
            reader.read(link: link, note: { label, value in
                listener.onNote(label: label, value: value)
            }, completion: { result in
                guard run == self.run else { return }
                self.pageReader = nil
                self.cookies = result.cookies
                self.userAgent = result.userAgent
                if let page = result.pageJson {
                    listener.onPage(pageJson: page)
                } else {
                    listener.onFailed(stage: "Reading link", message: result.error ?? "The page could not be read.")
                }
            })
        }
    }

    func listen(mediaUrls: [String], pageUrl: String, listener: ClipNativeListener) {
        DispatchQueue.main.async {
            self.stopWork()
            self.run += 1
            let run = self.run
            guard let first = mediaUrls.first else {
                listener.onFailed(stage: "Reading link", message: "No video address was found.")
                return
            }
            if first.lowercased().hasPrefix("file:") {
                guard let file = ClipFileInbox.shared.url(for: first) else {
                    listener.onFailed(stage: "Listening", message: "The shared video could not be found.")
                    return
                }
                let scoped = file.startAccessingSecurityScopedResource()
                self.transcribe(file, run: run, listener: listener) {
                    if scoped { file.stopAccessingSecurityScopedResource() }
                }
                return
            }
            let fetcher = ClipMediaFetcher()
            self.fetcher = fetcher
            listener.onNote(label: "Download", value: "started")
            fetcher.fetch(urls: mediaUrls, pageUrl: pageUrl, cookies: self.cookies, userAgent: self.userAgent, note: { label, value in
                listener.onNote(label: label, value: value)
            }, completion: { file, error in
                guard run == self.run else {
                    if let file = file { try? FileManager.default.removeItem(at: file) }
                    return
                }
                self.fetcher = nil
                guard let file = file else {
                    listener.onFailed(stage: "Reading link", message: error ?? "The clip's video could not be downloaded.")
                    return
                }
                self.transcribe(file, run: run, listener: listener) {
                    try? FileManager.default.removeItem(at: file)
                }
            })
        }
    }

    func cancel() {
        DispatchQueue.main.async {
            self.run += 1
            self.stopWork()
        }
    }

    func cacheRead(key: String) -> String? {
        cache.read(key)
    }

    func cacheWrite(key: String, text: String) {
        cache.write(key, text)
    }

    func settingRead(key: String) -> String? {
        UserDefaults.standard.string(forKey: "clipfinder." + key)
    }

    func settingWrite(key: String, text: String) {
        UserDefaults.standard.set(text, forKey: "clipfinder." + key)
    }

    func askModel(prompt: String, listener: ClipModelListener) {
        ClipModelGuesser.guess(prompt: prompt) { text, problem in
            listener.onAnswer(text: text, problem: problem)
        }
    }

    /// Reads the words on a few frames first (the file is deleted after listening), then listens.
    private func transcribe(_ file: URL, run: Int, listener: ClipNativeListener, cleanUp: @escaping () -> Void) {
        afterListening = cleanUp
        DispatchQueue.global(qos: .userInitiated).async {
            let screenLines = ClipFrameReader.read(file)
            DispatchQueue.main.async {
                guard run == self.run else { return }
                if !screenLines.isEmpty {
                    listener.onScreenText(text: screenLines.joined(separator: "\n"))
                }
                self.startListening(file, run: run, listener: listener)
            }
        }
    }

    private func startListening(_ file: URL, run: Int, listener: ClipNativeListener) {
        let transcriber = ClipTranscriber()
        self.transcriber = transcriber
        transcriber.transcribe(fileURL: file, note: { label, value in
            listener.onNote(label: label, value: value)
        }, line: { text, startMs, endMs in
            listener.onLine(text: text, startMs: startMs, endMs: endMs)
        }, completion: { error in
            guard run == self.run else { return }
            self.transcriber = nil
            self.runAfterListening()
            if let error = error {
                listener.onFailed(stage: "Listening", message: error)
            } else {
                listener.onDone()
            }
        })
    }

    private func stopWork() {
        pageReader?.cancel()
        pageReader = nil
        fetcher?.cancel()
        fetcher = nil
        transcriber?.cancel()
        transcriber = nil
        runAfterListening()
    }

    private func runAfterListening() {
        let work = afterListening
        afterListening = nil
        work?()
    }
}

/// Subtitle text the search already fetched, kept in the app's Caches folder (iOS may empty it).
/// Capped at about 50 MB: the oldest files go first. Safe to call from any thread.
final class ClipSubtitleDiskCache {
    private struct Entry {
        let url: URL
        let size: Int
        let date: Date
    }

    private static let maxBytes = 50 * 1024 * 1024
    private static let trimToBytes = 40 * 1024 * 1024

    private let folder: URL
    private let lock = NSLock()
    private var writes = 0

    init() {
        let base = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory
        folder = base.appendingPathComponent("clipfinder-subs", isDirectory: true)
        try? FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
    }

    func read(_ key: String) -> String? {
        try? String(contentsOf: file(key), encoding: .utf8)
    }

    func write(_ key: String, _ text: String) {
        guard !text.isEmpty, text.utf8.count <= 2_000_000 else { return }
        try? text.write(to: file(key), atomically: true, encoding: .utf8)
        lock.lock()
        writes += 1
        let due = writes % 40 == 1
        lock.unlock()
        if due { trim() }
    }

    private func file(_ key: String) -> URL {
        var safe = ""
        for character in key.prefix(120) {
            let ok = character.isLetter || character.isNumber || character == "-" || character == "."
            safe.append(ok ? character : "_")
        }
        return folder.appendingPathComponent(safe + ".txt")
    }

    private func trim() {
        lock.lock()
        defer { lock.unlock() }
        let keys: [URLResourceKey] = [.fileSizeKey, .contentModificationDateKey]
        guard let files = try? FileManager.default.contentsOfDirectory(at: folder, includingPropertiesForKeys: keys) else { return }
        var entries: [Entry] = []
        var total = 0
        for url in files {
            let values = try? url.resourceValues(forKeys: Set(keys))
            let size = values?.fileSize ?? 0
            entries.append(Entry(url: url, size: size, date: values?.contentModificationDate ?? Date.distantPast))
            total += size
        }
        guard total > ClipSubtitleDiskCache.maxBytes else { return }
        for entry in entries.sorted(by: { $0.date < $1.date }) {
            if total <= ClipSubtitleDiskCache.trimToBytes { break }
            try? FileManager.default.removeItem(at: entry.url)
            total -= entry.size
        }
    }
}
```

##### File: `iosApp/iosApp/ClipFinder/ClipModelGuesser.swift`
```swift
import Foundation
#if canImport(FoundationModels)
import FoundationModels
#endif

/// Asks Apple's on-device language model (iOS 26 and later, Apple Intelligence switched on) which show
/// a clip may be from. Nothing leaves the iPhone. The completion gets the model's text, or a short
/// reason why it could not be asked; it is called exactly once, on the main thread when the model ran.
enum ClipModelGuesser {
    static func guess(prompt: String, completion: @escaping (String?, String?) -> Void) {
        #if canImport(FoundationModels)
        if #available(iOS 26.0, *) {
            ask(prompt, completion)
            return
        }
        #endif
        completion(nil, "needs iOS 26 with Apple Intelligence")
    }

    #if canImport(FoundationModels)
    @available(iOS 26.0, *)
    private static func ask(_ prompt: String, _ completion: @escaping (String?, String?) -> Void) {
        let model = SystemLanguageModel.default
        guard model.isAvailable else {
            completion(nil, "not available on this iPhone (" + String(describing: model.availability) + ")")
            return
        }
        Task {
            var text: String?
            var problem: String?
            do {
                let session = LanguageModelSession(instructions: "You name the TV show or movie a clip comes from. Answer with titles only.")
                let response = try await session.respond(to: prompt)
                text = response.content
            } catch {
                problem = "failed (" + error.localizedDescription + ")"
            }
            let answer = text
            let failure = problem
            DispatchQueue.main.async {
                completion(answer, failure)
            }
        }
    }
    #endif
}
```

#### I. On the phone (after the Mac build), risks, and what the screen shows
Try it (nothing to set up; no new permission prompt):
1. Share the Modern Family clip of 2026-11-16 again. Expected: "Show guesses: Modern Family (...)", then the
   episode. Details must show `Known titles`, `Searches` and `Text on screen` lines.
   On the iPhone 15 Pro Max with Apple Intelligence on, a clip with a useless caption shows an `Apple's model:`
   line with titles; with it off, the line says why and the search carries on.
2. Share a second clip by the same poster or of the same show: "Show guesses" starts with "(this poster
   before)" or "(name, shared before)".
3. Share a saved video from the Files app (no caption): the "Know the show? Type its name" card appears under
   the steps; type the name, tap "Search this show": the "Listening" step does not run again.
4. Share a clip with the show's name and episode written on the video: `Text on screen` shows it.
If anything stops, send a screenshot of the whole screen including Details.

Top ways it can fail, and what the screen then shows:
1. Mac build fails on `ClipFrameReader.swift` or the changed `ClipFinderNativeImpl.swift` (no new TestFlight
   build): fix from `build.log`. Most likely lines: `LanguageModelSession(instructions:)` (decision 14 says
   how to drop that file alone), `request.results ?? []`, `copyCGImage(at:actualTime:)`.
2. `Text on screen: none` on a clip that clearly shows a title: the 5 frame times missed it, or Vision read
   nothing at this size. Fix in Swift (more frames, larger `maximumSize`): needs a Mac build.
3. `Known titles: 0 popular`: no catalog without a required filter is switched on, or the fetch failed in 8 s.
   The search route still works; fix `clipPopularShows` (Kotlin).
4. Right show, long wait: a wrong suspect is searched first (a popular title whose name is a common word in the
   caption, such as a one-word name of 5+ letters). `Show guesses` shows the order; tune scores in `ClipNames`.
5. A typed name finds nothing: `Searches: "<name>": 0` shows what Nuvio's search answered.
6. Memory misleads: a poster who posts many shows gets last time's show first (score 92, below an exact
   hashtag). Cost: one wasted show search of at most 120 s. If it annoys, lower 92 or count per poster.

ASSUMPTIONS (cannot be checked from here)
- C1 The Swift compiles as written (never compiled, not syntax-parsed). Confidence: medium-high for the frame
  reader and the bridge, about 85% for `ClipModelGuesser.swift` (new framework, `Task` in Swift 5 mode).
- C8 Apple's model answers within 12 s on an iPhone 15 Pro Max, does not refuse TV dialogue (a refusal shows as
  `Apple's model: failed (...)`), and names real titles often enough to help. Its guesses are never trusted.
- C9 The page-data key names of decision 12 (`music`, `textExtra`, `suggestedWords`, `clips_metadata`...) are what
  the sites send today. From memory, not from a saved page. `Sound` / `Keywords` in Details will tell.
- C10 Apple's speech recogniser writes names with a capital letter ("Nancy") and little else; if it capitalises
  nothing, `Names heard` never appears and the name check is simply skipped.
- C2 `AVAssetImageGenerator.copyCGImage` reads the downloaded TikTok file and the security-scoped shared file
  from a background queue, and a time past the end throws (then that frame is skipped) or returns the last frame.
- C3 Five accurate Vision passes on 1280-pixel frames take about 2 s on Mo's iPhone. Not measured.
- C4 Cinemeta's "Popular" pages come back through `fetchCatalogPage` without extra arguments (the home screen
  does the same) and hold about 100 titles each. "Modern Family" may not be among them; then the search
  ("Modern family" from the caption, or "modern family" from the cut hashtag) finds it.
- C5 Nuvio's catalog search finds a show from its exact name in any letter case ("Modern family").
- C6 The Kotlin compiles; `ClipShowFinder` uses nothing newer than what the 4-6 code already uses.
- C7 Up to 8 searches at once (the cut hashtag) do not get Nuvio's add-ons rate-limited. Each search asks at most
  6 catalogs, so the worst case is 48 small requests, once per clip, only when nothing else matched.


- [ ] **7b. Fallbacks, tuning, ship** (Mac build 6; as before. Do 7c, 7d and 7e below FIRST: 7b tunes with their Match and Timings lines)
  - Build: clear failure messages (SPEC 8), 60 s stage limit with a message, tune matcher thresholds on Mo's
    real clips, flip the default to "After the clip" if Mo still wants SPEC 6 as written, add a Clip finder
    section to FORK.md.
  - Tune the 15% clip-share bar on Mo's real clips. In simulation, correct matches on noisy 6-min clips (45% wrong words) were confident only 72% of the time. Consider measuring share against matchable lines.
  - Done when: every SPEC check passes on the phone.
  - Try it: one clip of each kind: named show, no caption, music only, movie.
  - Files: clipfinder/*, FORK.md.

- [ ] **7c. Open the YouTube video, fix Instagram** (Mac build 4, together with 7d; notes below)
  - Why (Mo, 2026-11-16, after 7a worked): many clips are cut from a YouTube video, often not from a show at all
    (interviews, podcasts). And an Instagram reel stopped at "Video address found: no"; its caption was read as
    "585K likes, 550 comments - handle on December 15, 2025: "...", with the counts and quote marks in it.
  - Build: search YouTube with words from the page (no account, no API key of ours), read the captions of up to
    6 videos while the clip is listened to, keep only videos whose captions match what was heard (the same
    matcher as for episodes) and open the YouTube app at that moment: by itself when it is the only sure answer,
    on a tap otherwise. Instagram: try the embed page and the post page for the video address (never a blob:
    address), clean the og:description into caption + handle, and when there is still no video but the caption
    names a show, offer that show's page (episode list) and the type-the-show box. Details lists every
    Instagram page tried, every YouTube search and why a video's captions could not be read.
  - Done when: (1) "Fork check" is green, including the new YouTube, Instagram and pipeline tests; (2) on the
    phone a clip cut from a YouTube interview (no show) opens the YouTube app within 10 s of the clip's moment;
    (3) a show clip that is also on YouTube shows the episode first and the YouTube card below, and nothing
    opens by itself; (4) the Instagram reel that failed shows `Instagram: ...` in Details and either reaches
    listening or offers the show named in its caption; its `Caption` line has no "likes" and no quote marks,
    and `Author` is the handle; (5) 7a's open checks: a saved video with no caption reaches its episode after
    typing the show with "Listening" run once, and no clip stops only because the caption is empty.
  - Try it: share a clip of a YouTube interview or podcast; share a show clip; share the Instagram reel again;
    share a saved video from Files and type the show. Send a screenshot of Details for each.
  - Files: clipfinder/* (7 new, 6 changed Kotlin; 6 new test files, 1 changed), MainAppContent.kt (one line),
    iosApp/iosApp/ClipFinder/ClipPageReader.swift (page script only; droppable).
  - Wait for OK before starting (20+ files; a new kind of network use: YouTube's own page key).

- [ ] **7d. Faster and more accurate** (Mac build 4, together with 7c; notes below)
  - Why: Mo finds the search slow. Nothing on the screen says where the time goes, so first measure, and
    change only what the code shows is serial waiting.
  - Build: a `Timings` line in Details (seconds per stage, work beside the stages, total); while the clip is
    listened to, the show the page names strongly (score 90+) has its episode list and up to 36 subtitle files
    fetched into the cache, and YouTube is searched; episodes whose summary holds a rare word that was heard are
    tried earlier; a `Match` line with the numbers behind "sure" (shared phrases, share, runner-up) for 7b's
    tuning. No matcher threshold changes (that is 7b, with these numbers).
  - Done when: (1) "Fork check" is green, including the timing, ranking and prefetch tests; (2) every run on the
    phone ends with a `Timings` line; (3) for a clip whose page names the show (an exact hashtag), Details shows
    `Fetched while listening: <show>: N subtitle files` and the `subtitles` stage after listening is shorter
    than the `prefetch` work beside it; (4) the hypotheses H1-H4 of decision 9 are written down as confirmed or
    not, with the Timings lines of Mo's test clips, in docs/LESSONS.md or under "Later".
  - Try it: share the Modern Family clip again and read `Timings`, `Fetched while listening` and `Match`.
  - Files: in the 7c list (ClipTimings, ClipPrefetch, ClipEpisodeRank, ClipShowSearch, pipeline, session).

- [ ] **7e. Pick the show, land on the right moment** (Mac build 5, after Mo's phone check of 7c-7d; notes below)
  - Why (Mo, 2026-11-16): typing the show should give a list to tap, not a guess; and on some streams playback
    lands a few seconds off, because the subtitle file the clip was matched with can come from another release
    than the stream he picks.
  - Build: (1) under "Know the show?" a pick list fills as Mo types (poster, name, year, Series or Movie), from the
    catalogs' search plus the titles Nuvio knows, with the squashed-name matching of `ClipNames`; a tap searches
    exactly that show with what was already heard (no second listen). (2) Play-time check: when a stream opened
    from a Clip finder answer starts, the subtitle add-ons are asked what the player asks them (file name, size,
    hash); when they give a file made for this video, the clip's matched lines are found in it (offset, plus the 4%
    PAL speed difference) and the player seeks there ONCE, never after Mo moved himself. A toast and Details say
    what happened, e.g. "Moved to the matching line in this video's subtitles (+3.2 s)" or "Kept the clip time: no
    subtitles for this video". (3) Only in a stream list opened from Clip finder: the best match is pinned on top
    under "Best match for the clip" and up to 5 streams are tagged "Best match"; the order does not change, and
    Details says why (`Stream order`). (4) Lead-in 10 s -> 15 s.
  - Done when: (1) "Fork check" is green, with the new `ClipAlignTest`, `ClipPlayCheckTest`, `ClipStreamRankTest`,
    `ClipShowPickerTest` and the changed pipeline and state tests; (2) on the phone, typing "modern fam" lists Modern
    Family with poster and year, and a tap reaches the episode with "Listening" run once; (3) after an answer and a
    stream, a toast appears within 60 s of playback, Details has `Player` and `Player subtitles` lines, the player
    jumps at most once, and not at all when Mo seeks first; (4) a stream list opened from a normal show page looks
    as before; one opened from Clip finder has a `Stream order` line, and a pinned "Best match for the clip" exactly
    when that line starts "best match"; (5) Details has `Matched subtitle` after every search with an answer.
  - Try it: share the Modern Family clip; type "modern fam" and tap the show; tap the answer and a stream; read the
    toast. Then once more, and seek away in the first seconds: nothing may move you back. Screenshot Details each time.
  - Files: clipfinder/* (6 new, 4 rewritten, 6 edited Kotlin; 4 new test files, 2 edited), upstream
    `PlayerScreenContent.kt` (1 import + 1 call; new to the patch), `StreamDestination.kt` (already the fork's;
    3 imports, 1 call, 2 lines changed). No Swift, no new dependency, no new permission.
  - Wait for OK before starting (20+ files, one more upstream file in the patch).

### Milestones 7c-7d implementation notes (written 2026-11-16)
Checked against the work tree as it is on TestFlight (milestones 4-7a applied). Same rules as the 7a notes: paths
are inside `../nuvio-work` unless they start with `fork/` or `docs/`; `K` = `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder`,
`T` = the same package under `commonTest`, `S` = `iosApp/iosApp/ClipFinder`. Where these notes differ from older
text, these notes win. 7c and 7d are built together and tested with ONE Mac build (build 4).

Not checked here: nothing below was compiled or run (no Kotlin, Gradle or Swift in the cloud workspace). The one
Swift change (page script only) was syntax-parsed with tree-sitter-swift and its JavaScript with `node --check`.
The Instagram regular expressions and their test values were run as a Python copy; every other test value was
traced by hand against the code. Kotlin errors show in "Fork check" (8 min); Swift errors only in the Mac build.

Where the page keys come from: tiktok.com, instagram.com and youtube.com are blocked in the cloud workspace, so no
live page was saved. The key names below were read on 2026-11-16 in the source of two open-source tools,
downloaded with `pip download` (not installed, not run): youtube-transcript-api 1.2.5 (YouTube captions) and
yt-dlp 2026.10.26 (YouTube search pages, Instagram). Each key has a confidence; the Details lines added here say
on the phone which key failed.

#### A. Decisions
1. YouTube is searched BESIDE the show search, never instead of it and never before it. For a link it starts as
   soon as the page is read (it needs only the page's words) and runs while the clip is listened to; for a shared
   file it starts after listening (it needs the text on screen). The show search runs as before; only then are the
   YouTube videos checked against what was heard. YouTube has 60 s from its start; a slow YouTube never delays an
   episode answer by more than what is left of those 60 s, and a failed YouTube is only a Details line.
2. A YouTube video is shown only when its captions match what was heard by the matcher's own "confident" rule
   (4+ hits in the main cluster, 15% of the clip's phrases, twice the runner-up), each video matched on its own:
   re-uploads of the same video match equally and must not count as each other's runner-up. A wrong guess is
   therefore never shown and never opened. At most 3 are shown; among videos with at least 80% of the best hits
   the longest comes first (the full video, not a short cut of it).
3. What the screen does with the answers:
   | Episode answers | YouTube answers | Screen |
   |---|---|---|
   | confident | any | episode cards first, YouTube card below; nothing opens by itself |
   | weak only, or none | 1+ | stage "Done"; the YouTube card; the first video opens in the YouTube app by itself, once (`openYouTube`), at the same start time rule as episodes ("from clip start" or "after the clip") |
   | none | none | the old failure message |
   The YouTube card says "On YouTube (tap to open the YouTube app)", one line per video: "title (channel)" and
   "at 2:05 to 3:10, 88% sure. Opens at 2:05". A typed show name keeps the YouTube answers found before; a typed
   search that finds no episode still ends with its failure message (YouTube card stays visible).
4. Opening: `https://www.youtube.com/watch?v=<id>&t=<seconds>s` through Compose's `LocalUriHandler.openUri`. On iOS
   that is `UIApplication.open`, and YouTube's universal link opens the YouTube app when installed, Safari
   otherwise. No Swift, no Info.plist change (universal links need no `LSApplicationQueriesSchemes`).
   Confidence the app (not Safari) opens: about 85%. Confidence `t=` is honoured by the app: about 80%.
5. Reading YouTube without an account and without a key of our own (the youtube-transcript-api route):
   | Step | What is sent / read | Source | Confidence |
   |---|---|---|---|
   | search | GET `https://www.youtube.com/results?search_query=<words>&sp=EgIQAQ%253D%253D` with a desktop Safari User-Agent, `Accept-Language: en-US`, cookie `SOCS=CAI` (skips the consent page). A phone User-Agent gets m.youtube.com, whose data is a JS string | yt-dlp | 80% |
   | video ids | `"videoId":"<11 chars>"` (or `contentId`, new lockup view) counted from `ytInitialData` on, in page order, first 8 | yt-dlp | 80% |
   | page key | `"INNERTUBE_API_KEY":"..."` in the same page (else in the first watch page). Public: every visitor's page carries it; it is not our key and not a secret | youtube-transcript-api | 85% |
   | captions list | POST `https://www.youtube.com/youtubei/v1/player?key=<page key>` with `{"context":{"client":{"clientName":"ANDROID","clientVersion":"20.10.38"}},"videoId":"<id>"}`; read `videoDetails.title/author/lengthSeconds` and `captions.playerCaptionsTracklistRenderer.captionTracks[].baseUrl/languageCode/kind` (`asr` = automatic) | youtube-transcript-api | 65% (YouTube changes what it accepts from "ANDROID" clients often) |
   | token check | a `baseUrl` with `&exp=xpe` needs a token from YouTube's own player: skipped, Details says so | youtube-transcript-api | 60% |
   | captions | GET the `baseUrl` without `&fmt=srv3`: XML `<text start="1.5" dur="2.2">words</text>`, HTML-escaped inside | youtube-transcript-api | 80% |
   English only (`en`, `en-*`), captions written by people before automatic ones. Up to 3 searches, 6 videos (the
   best-ranked of each search in turn), 3 videos at a time, 10 s per request, answers capped at 6 MB.
   Mo's rule "no API keys" is kept: the app holds no key; the page's own public key is read each time.
6. YouTube search words (`ClipYouTube.queries`), best first, at most 3: the page's first keyword; the caption
   without links, hashtags and @names; the first 3 pieces of text on screen. Each needs 2+ words and 6+ letters,
   at most 10 words. Only when none of these gives a search: the first 2 hashtags without filler (5+ letters).
   Only when still nothing: the sound title, never "original sound - ...". No search when there is nothing: a
   `YouTube: no words to search with` line.
7. Instagram (7c part 2). Phone test 2026-11-16: the reel page (logged out) has no video address. Order of tries,
   stopping at the first that gives an https address:
   | Try | How | Source | Confidence it gives the video today |
   |---|---|---|---|
   | 0 | the shared page in the off-screen web view, as now | phone | failed once |
   | 1 | the embed page `https://www.instagram.com/p/<code>/embed/captioned/` as a plain download (iPhone Safari User-Agent, about a second): `video_url` (plain JSON, or escaped inside `contextJSON`), `video_versions[].url`, `<video src="https://...">`, `og:video` | older yt-dlp | 35% |
   | 2 | the post page `/p/<code>/` in the off-screen web view; its scripts with `xig_polaris_media` ... `video_versions[].url` are handed back whole as `raw` (Swift page script change) and searched as text when they are not JSON | yt-dlp 2026.10.26 (its logged-out web route) | 45% |
   | 3 | the embed page in the off-screen web view (scripts run, the player may fill `video_url`) | older yt-dlp | 30% |
   `blob:` and `http:` addresses are never used. The code is read from `/reel/`, `/reels/`, `/p/`, `/tv/`, also after a
   handle (`/sample.user/reel/<code>/`). Not built: Instagram's GraphQL route (needs a token taken from the page and
   impersonation; parked under Later). Confidence that at least one try works: about 55%. When none works, the
   reel still gets decision 8.
8. Instagram's og:description `585K likes, 550 comments - handle on December 15, 2025: "caption".` becomes the
   caption (counts, handle, date and quote marks removed, straight or curly) and the author (the handle). Any
   other text is kept as it is. Confidence the shape holds: high (seen on the phone).
9. No clip to hear (no video address, or no speech) but a clue names a show at score 85+ (its name in the caption,
   a hashtag, a keyword): the failure message gets "The caption names the show below: open it to pick the episode
   yourself." and a card "Open the show and pick the episode" lists up to 3 shows; a tap opens Nuvio's normal show
   page (`DetailRoute`, upstream) with its episode list. The type-the-show box also shows ("Nuvio finds the show so
   you can open it."); a typed name then only finds the show to open (`OPEN_TYPED_SHOW`), never searches subtitles.
10. Speed (7d). Where the time goes, from reading the code (NOT measured: there was no timing line until now):
   every step runs one after the other; popular catalogs (up to 8 x 8 s) are fetched inside the show guess after
   listening; subtitles are fetched in season order 6 at a time and each batch waits for its slowest file (the
   Modern Family clip was S1E20: up to 24 files before the right one); listening itself is the longest step and
   uses no network, so the network sits idle meanwhile. Changes, each with what it should do (hypotheses, to be
   confirmed with the `Timings` line, no number promised):
   - H1 Prefetch: while listening, the show the page alone names at 90+ (exact or filler hashtag, this poster's last
     show) gets its episode list and the subtitles of its first 36 episodes (hinted episode and season first) into
     the cache, 6 at a time; stopped when listening ends. Expected: for such clips the `subtitles` stage after
     listening shrinks to matching only; no change for other clips; a wrong guess costs only idle network.
   - H2 Episode order: episodes whose title or summary (`overview`, already loaded by upstream) hold a heard word
     of 4+ letters that is in at most a fifth of the summaries come first (rarer word, more weight); the hinted
     episode stays first and files already fetched come next. Expected: fewer episodes tried (`subtitles (N
     episodes)`) when a guest or a rare thing is named; never a different answer (order only).
   - H3 YouTube beside: expected `YouTube wait` near 0 s whenever the show search takes longer than YouTube.
   - H4 Popular titles fetched during listening (by the prefetch's own guess): expected a shorter `guess` stage.
   Accuracy: unchanged matcher. New `Match` line: "41 shared phrases of 160 heard (25%), next best 3", the numbers
   7b needs to tune the 15% bar on real clips.
11. `Timings` line (last Details line of every run): `page 6.1 s, download 3.2 s, YouTube 9.4 s (6 videos) beside,
   listen 21.4 s (part 3 of 3), guess 1.2 s, episode list 0.8 s, subtitles 4.0 s (12 episodes), YouTube wait 0.0 s,
   total 37.0 s` (example of the format, not a measurement). Stages are laps of one clock; "beside" marks work that
   ran next to them. Stage names: page, Instagram pages, download, frames, sound, listen, guess, names, episode
   list, subtitles, YouTube wait; beside: prefetch, YouTube.
12. Parked, each with the measurement that would bring it back: stop listening early once a confident match exists
   (when `listen` is more than half of `total`); a sliding window of 6 instead of batches (when `subtitles` is
   long with few episodes); reading frames while downloading (Swift, when `frames` is over 3 s); a matcher change
   for noisy speech (7b, from `Match` lines); Instagram's GraphQL route (when all three tries fail on real reels).

#### B. Contract changes between Swift and Kotlin
`ClipFinderNative.kt` does not change (still exactly 17 functions; the 7a pre-flight count stays). The only change
is in the JSON text that `readPage` hands back: an optional `"raw": [string, ...]`, the whole text of every script
that contains `video_url` or `video_versions`, whatever its type, at most 2,000,000 characters in all. Those
scripts are no longer also put in `"scripts"`. Kotlin treats a missing `raw` as empty, so worker 3 can be dropped
alone. No Kotlin API is newly called from Swift (no Kotlin/Native name changes). New Details lines, all from
Kotlin: `Instagram`, `Show from the caption`, `YouTube`, `YouTube searches`, `YouTube captions`, `YouTube match`,
`Fetched while listening`, `Match`, `Timings`.

#### C. Files
| Worker | File | What |
|---|---|---|
| 1 | new `K/ClipYouTube.kt`, `T/ClipYouTubeTest.kt` | search words, addresses, ids, page key, player answer, caption XML, the check (decisions 2, 5, 6) |
| 1 | new `K/ClipYouTubeFinder.kt`, `T/ClipYouTubeFinderTest.kt` | the YouTube requests and their Details lines (`ClipWebReply`, `FakeTube`) |
| 1 | new `K/ClipInstagram.kt`, `T/ClipInstagramTest.kt` | post code, description, video addresses, the tries (decisions 7, 8) |
| 1 | changed `K/ClipPageParser.kt` | reads `raw`; Instagram description -> caption and author |
| 1 | new `K/ClipTimings.kt`, `T/ClipTimingsTest.kt` | decision 11 |
| 1 | new `K/ClipEpisodeRank.kt`, `T/ClipEpisodeRankTest.kt` | H2; needs the `overview` edit of section G |
| 2 | new `K/ClipPrefetch.kt` | H1 |
| 2 | new `K/ClipShowSearch.kt` | the old pipeline search, moved, plus rank, prefetch reuse, `Match` line |
| 2 | changed `K/ClipFinderState.kt` | `youtube`, `openYouTube`, `shows`, `noClip`; 2 messages; `clipCanType`; `clipMatchDetail`, `clipVideoTitle` |
| 2 | changed `K/ClipFinderPipeline.kt`, new `T/ClipFinderPipelineWebTest.kt` | Instagram tries, prefetch and YouTube beside listening, offer shows, timings |
| 2 | changed `K/ClipFinderSession.kt` | wiring, `clipWebGet` / `clipWebPost` (upstream HTTP helpers), episode `overview`, `youTubeOpened` |
| 2 | changed `K/ClipFinderScreen.kt`, `K/ClipFinderParts.kt` | YouTube card and auto-open, shows card, type card text |
| 3 | changed `S/ClipPageReader.swift` | page script only (section B); last, droppable |

20 files written from section H, plus the edits of section G (`EpisodeSubtitleSource.kt` 1 line, `MainAppContent.kt`
1 line, `ClipFinderPipelineTest.kt` 3 assertions). Every file is under 300 lines except `ClipFinderPipeline.kt`
(341; splitting it is under Later). No `project.pbxproj` or Info.plist change, no new dependency, no new permission.

#### D. Steps, one worker after the other in the same work tree
Never hand-type the files. This script copies the "File:" blocks of THIS section only (the 7a script stops at
"- [ ] **7b." and still finds its 25). Paste as it stands:
```bash
cat > /tmp/clip7c_files.py <<'PY'
import re, sys, os
mode, plan, tree = sys.argv[1], sys.argv[2], sys.argv[3].rstrip("/")
only = sys.argv[4:]                                    # optional: path fragments to limit to
text = open(plan, encoding="utf-8").read()
text = text[text.index("### Milestones 7c-7d implementation notes"):text.index("\n- [ ] **8.")]
blocks = re.findall(r"^##### File: `([^`]+)`\n```[a-z]*\n(.*?)\n```$", text, re.M | re.S)
assert len(blocks) == 20, "expected 20 file blocks, found %d" % len(blocks)
bad = 0
for path, body in blocks:
    if only and not any(o in path for o in only): continue
    full, body = os.path.join(tree, path), body + "\n"
    if mode == "write":
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w", encoding="utf-8").write(body)
        print("wrote", path)
    elif not os.path.exists(full) or open(full, encoding="utf-8").read() != body:
        bad += 1; print("DIFFERENT", path)
if mode == "check": print("all files match the plan" if not bad else "%d files differ" % bad); sys.exit(1 if bad else 0)
PY
```
0. Everyone: `fork/dev-tree.sh` (the work tree must hold 7a: `ls ../nuvio-work/composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder | wc -l`
   prints 17), save the two scripts (this one and `/tmp/clip7c_edits.py` of section G), and
   `git -C ../nuvio-work status --porcelain > /tmp/clip7c_before.txt`.
1. Worker 1 (pure logic and its tests): `python3 /tmp/clip7c_files.py write docs/PLAN.md ../nuvio-work ClipYouTube ClipInstagram ClipPageParser ClipTimings ClipEpisodeRank`
   (11 files: `ClipYouTube` also matches `ClipYouTubeFinder` and both tests), then the `overview` edit of section G
   (`python3 /tmp/clip7c_edits.py ../nuvio-work overview`). Read the five Kotlin files against decisions 2, 5-8, 10,
   11 and follow each `assertEquals` of the five test files by hand once. Report any value you cannot reproduce; do
   not "fix" a test. The tree does not compile between worker 1 and worker 2 (`ClipYouTubeTest` uses
   `clipMatchDetail`, which worker 2 adds): fine.
2. Worker 2 (glue, screen, tests): `python3 /tmp/clip7c_files.py write docs/PLAN.md ../nuvio-work ClipPrefetch ClipShowSearch ClipFinderState ClipFinderPipeline ClipFinderSession ClipFinderScreen ClipFinderParts`
   (8 files: `ClipFinderPipeline` also matches `ClipFinderPipelineWebTest`), then
   `python3 /tmp/clip7c_edits.py ../nuvio-work main tests`. Then `grep -rn "ClipFinderScreen(" ../nuvio-work/composeApp/src/commonMain`
   must show the `onShow =` argument, and `grep -rlw "ClipFinderNative" ../nuvio-work/composeApp/src` must list exactly
   `ClipFinderNative.kt`, `ClipFinderPipeline.kt`, `ClipFinderSession.kt`, `ClipFinderPipelineTest.kt` and
   `ClipFinderPipelineWebTest.kt`.
3. Worker 3 (Swift, last): `cp ../nuvio-work/iosApp/iosApp/ClipFinder/ClipPageReader.swift /tmp/ClipPageReader.old.swift`,
   then `python3 /tmp/clip7c_files.py write docs/PLAN.md ../nuvio-work ClipPageReader` (1 file), then
   `diff /tmp/ClipPageReader.old.swift ../nuvio-work/iosApp/iosApp/ClipFinder/ClipPageReader.swift`: only the doc
   comment (2 lines added), `raw: []` in `out`, `var rawTotal = 0;` and the 6-line `media` block in the script loop
   (the `if (!named ...)` line moves below it) may differ. To drop it: copy the old file back (Kotlin then sees no
   `raw`; Instagram try 2 finds less). Run the pre-flight, then `fork/dev-tree.sh save`.
4. Lead: commit `fork/nuvio-share-resume.patch` + docs, push, wait for "Fork check". Kotlin errors are fixed in the
   work tree (then save again); a test is never weakened: if a traced value was wrong, find out which side is wrong
   first. Then `gh workflow run TestFlight --ref clip-finder-share` (one Mac build, about 70 min).
5. When green on the phone: tick 7c and 7d; `docs/ARCHITECTURE.md`: data flow gets "YouTube beside the show
   search, checked with the matcher, opened by universal link" and "Instagram: embed download, post page, embed page";
   decisions log: "YouTube read with its page's public key, no key of ours (Mo's rule kept)", "A YouTube video is
   shown only when its captions match", "Prefetch while listening at score 90+", "Episode order by rare words in
   summaries"; write H1-H4 as confirmed or not, with the Timings lines.

#### E. Tests (all six new test files are given in full in section H; all data made up)
- `ClipYouTubeTest` (9): ids from the results page in order, not before `ytInitialData`, and the page key; the
  player answer (details, tracks) and the English, people-first track choice; the token mark; caption XML with
  double escaping, `&#39;`, tags, attributes in any order, a blank cue and a missing `dur`; the three search sources;
  hashtags and sound only as fallbacks ("original sound" never); `openUrl` (`t=125s`, never negative) and the
  search address; the check keeps the full upload first and drops a video that does not match; title and detail
  text. Holds `ClipTubeSamples` (made-up player JSON, caption XML, results page).
- `ClipYouTubeFinderTest` (3): three videos give the exact Details lines (`2 lines (auto)`, `captions need
  YouTube's token`, `no English captions`), the cookie and User-Agent are sent; no words: no request at all; no page
  key: the watch page is tried and the line says why; a refused search shows `HTTP 429`. Holds `FakeTube`.
- `ClipInstagramTest` (6): post codes from 7 link shapes; the description in 3 real shapes and 2 non-matches;
  addresses at three escaping levels, an empty `video_versions`, `<video>` and `og:video`, never `blob:` or `http:`;
  the tries in order with the exact `Instagram` line; nothing found anywhere; the parser reads `raw` (JSON walked,
  text searched) and the description.
- `ClipTimingsTest` (2), `ClipEpisodeRankTest` (2): exact line; rare word first, common word ignored, hint and
  cache first.
- `ClipFinderPipelineWebTest` (5): a YouTube-only clip ends "Done" with `openYouTube`; an episode plus YouTube does
  not open by itself; an Instagram reel gets its address from the embed download (exact `Instagram` line, clean
  caption and author, page read once); no video: show offered, then a typed name gives `OPEN_TYPED_SHOW` with no
  listening; while a held `listen` waits, all 12 subtitle files are fetched and YouTube is asked, nothing is
  downloaded twice afterwards, the episode list is loaded once, `Timings` has `prefetch 0.0 s (12 files) beside`.
- `ClipFinderPipelineTest` (3 assertions changed in section G, nothing removed): the first test's Details labels now
  end `"Subtitles", "Match", "Candidates", "Timings"`; "a page without a video address" and "no speech" now expect
  the `OPEN_SHOW` sentence and the offered show (the old message is the start of the new one).
`ClipMatcherTest`, `ClipPageParserTest`, `EpisodeSubtitleSourceTest`, `ClipFinderStateTest`, `ClipFinderScreenTest`
and the 7a test files stay green unchanged (traced: `clipCanType` keeps its old answers when `noClip` is false; the
`ClipEpisode` constructor only gains a last parameter with a default).

#### F. Pre-flight before pushing
```bash
W=../nuvio-work; S=$W/iosApp/iosApp/ClipFinder
python3 /tmp/clip7c_files.py check docs/PLAN.md $W                    # all files match the plan
git -C $W status --porcelain | diff /tmp/clip7c_before.txt -            # prints nothing: no new changed or new upstream file
                                                                      # (MainAppContent.kt was already changed by the fork)
grep -c "overview" $W/composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/EpisodeSubtitleSource.kt   # 1
grep -n "onShow = { show ->" $W/composeApp/src/commonMain/kotlin/com/nuvio/app/MainAppContent.kt               # 1 line
grep -rniE "api[_-]?key\s*=|AIza" $W/composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/   # prints nothing: no key in the app
python3 - $W <<'PY'                                                   # the bridge is unchanged
import re, sys
k = open(sys.argv[1] + "/composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderNative.kt").read()
assert len(re.findall(r"^\s*fun ", k, re.M)) == 17, "ClipFinderNative.kt must still declare exactly 17 functions"
s = open(sys.argv[1] + "/iosApp/iosApp/ClipFinder/ClipPageReader.swift").read()
js = s[s.index('#"""') + 4:s.index('"""#')]
open("/tmp/clip7c_page.js", "w").write(js)
assert "raw: []" in js and "out.raw.push(text)" in js and "rawTotal + text.length <= 2000000" in js
print("contract OK")
PY
node --check /tmp/clip7c_page.js && echo "page script OK"            # node is in the cloud workspace (/opt/node22/bin)
pip install -q tree-sitter tree-sitter-swift && python3 - $S <<'PY'
import glob, sys, tree_sitter_swift
from tree_sitter import Language, Parser
p = Parser(Language(tree_sitter_swift.language()))
for f in sorted(glob.glob(sys.argv[1] + "/*.swift")):
    assert not p.parse(open(f, "rb").read()).root_node.has_error, f + ": syntax error"
print("swift syntax OK")
PY
fork/dev-tree.sh save
```
Reading checks for the Swift file: the change is inside the `#"""` JavaScript string only; no Swift line outside
the doc comment changes; `continue` after `out.raw.push(text)` keeps a raw script out of `out.scripts` (so the 3 MB
cap of `scripts` is not spent on it); the existing `known` early stop is untouched.
What each check proves: Fork check = all Kotlin compiles and the tests pass; nothing about Swift or the live sites.
Mac build = Swift compiles. Phone = section I.

#### G. Edits to existing files
Run after writing the files. Exact replacements; the script stops if a text is not found exactly once:
```bash
cat > /tmp/clip7c_edits.py <<'PY'
import sys, os
tree, parts = sys.argv[1].rstrip("/"), set(sys.argv[2:])
K = "composeApp/src/commonMain/kotlin/com/nuvio/app"
T = "composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder"
edits = {
  "overview": [(K + "/features/clipfinder/EpisodeSubtitleSource.kt",
    "    val thumbnail: String? = null,\n)",
    "    val thumbnail: String? = null,\n    /** The episode's summary from the add-on; [ClipEpisodeRank] reads it. */\n    val overview: String? = null,\n)")],
  "main": [(K + "/MainAppContent.kt",
    "ClipFinderScreen(source = route.source, onBack = onBack, onOpen = ::openClipAnswer)",
    "ClipFinderScreen(source = route.source, onBack = onBack, onOpen = ::openClipAnswer, onShow = { show -> navController.navigate(DetailRoute(type = show.type, id = show.metaId, title = show.name)) })")],
  "tests": [
    (T + "/ClipFinderPipelineTest.kt",
     "\"Known titles\", \"Searches\", \"Show guesses\", \"Subtitles\", \"Candidates\",",
     "\"Known titles\", \"Searches\", \"Show guesses\", \"Subtitles\", \"Match\", \"Candidates\", \"Timings\","),
    (T + "/ClipFinderPipelineTest.kt",
     "        assertFailed(h, ClipStage.ReadingLink, ClipMessages.NO_VIDEO, fileHint = true)\n",
     "        assertFailed(h, ClipStage.ReadingLink, ClipMessages.NO_VIDEO + \" \" + ClipMessages.OPEN_SHOW, fileHint = true)\n"
     "        assertEquals(listOf(show), h.last.shows)\n        assertTrue(clipCanType(h.last))\n"),
    (T + "/ClipFinderPipelineTest.kt",
     "        assertFailed(h, ClipStage.Listening, ClipMessages.NO_SPEECH, fileHint = false)\n",
     "        assertFailed(h, ClipStage.Listening, ClipMessages.NO_SPEECH + \" \" + ClipMessages.OPEN_SHOW, fileHint = false)\n"
     "        assertEquals(listOf(show), h.last.shows)\n"),
  ],
}
for part in sorted(parts):
    for path, old, new in edits[part]:
        full = os.path.join(tree, path)
        text = open(full, encoding="utf-8").read()
        assert text.count(old) == 1, "%s: expected the old text once, found %d" % (path, text.count(old))
        open(full, "w", encoding="utf-8").write(text.replace(old, new))
        print("edited", path)
PY
```
`MainAppContent.kt` is upstream, already changed by the fork on this very line; `DetailRoute` comes from the
`com.nuvio.app.navigation.*` import it already has, and `navController.navigate(DetailRoute(...))` is how it opens a
show elsewhere (the library poster). Nothing is reformatted.

#### H. The files
Write them with the script of section D. The block header is the path inside the work tree.

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipYouTube.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import com.nuvio.app.features.player.SubtitleSyncCue
import io.ktor.http.encodeURLParameter
import kotlin.math.roundToLong
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull

/** A YouTube video that may hold the clip, with its captions (empty when none could be read). */
data class ClipVideo(
    val id: String,
    val title: String = "",
    val channel: String = "",
    val seconds: Int = 0,
    val cues: List<SubtitleSyncCue> = emptyList(),
)

/** A YouTube video whose captions line up with what was heard: the clip comes from it. */
data class ClipVideoAnswer(val video: ClipVideo, val candidate: ClipCandidate)

/** One caption file of a video as YouTube lists it; [auto] for captions made by YouTube's own speech recognition. */
data class ClipCaptionTrack(val url: String, val language: String, val auto: Boolean)

/**
 * Reading YouTube without an account and without a key of our own, the way the open-source
 * youtube-transcript-api 1.2.5 does (its source was read on 2026-11-16): the results page lists video
 * ids and carries the page's own public INNERTUBE_API_KEY; the player answer for YouTube's Android app
 * lists the caption files; a caption file is XML (<text start="1.2" dur="3.4">words</text>). Pure
 * functions; the network is in [ClipYouTubeFinder].
 */
object ClipYouTube {
    /** A desktop browser: with a phone's User-Agent YouTube answers with m.youtube.com, whose page data is a JS string. */
    const val DESKTOP_AGENT =
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"
    const val ANDROID_CLIENT_VERSION = "20.10.38"
    const val MAX_QUERIES = 3
    private const val MAX_QUERY_WORDS = 10
    private const val MAX_IDS = 8
    private val idPattern = Regex("\"(?:videoId|contentId)\":\"([A-Za-z0-9_-]{11})\"")
    private val keyPattern = Regex("\"INNERTUBE_API_KEY\":\\s*\"([A-Za-z0-9_-]+)\"")
    private val textPattern = Regex("<text([^>]*)>([\\s\\S]*?)</text>")
    private val startPattern = Regex("start=\"([0-9.]+)\"")
    private val durationPattern = Regex("dur=\"([0-9.]+)\"")
    private val numbered = Regex("&#(\\d{1,6});")
    private val tagPattern = Regex("<[^>]*>")
    private val linkOrTag = Regex("(?:https?://|[#@])\\S+")
    private val originalSound = Regex("^\\s*original (?:sound|audio)\\b", RegexOption.IGNORE_CASE)

    /**
     * At most 3 searches, best first: the page's own keyword, the caption's words, the text on screen.
     * Hashtags only when none of these gives words; the sound title only when nothing else does
     * ("original sound - poster" never).
     */
    fun queries(clues: ClipClues): List<String> {
        val found = mutableListOf<String>()
        fun add(text: String) {
            val words = plainWords(text).take(MAX_QUERY_WORDS)
            if (words.size >= 2 && words.sumOf { it.length } >= 6) found += words.joinToString(" ")
        }
        clues.keywords.take(1).forEach { add(it) }
        add(clues.caption)
        add(clues.screenText.take(3).joinToString(" "))
        if (found.isEmpty()) {
            found += ClipNames.tags(clues.copy(author = "")).map { ClipNames.core(it) }.filter { it.length >= 5 }.take(2)
        }
        if (found.isEmpty() && !originalSound.containsMatchIn(clues.sound)) add(clues.sound)
        return found.distinctBy { it.lowercase() }.take(MAX_QUERIES)
    }

    /** Words with at least one letter; links, hashtags and @names left out. */
    private fun plainWords(text: String): List<String> =
        text.replace(linkOrTag, " ")
            .split(' ', '\n', '\t', '|')
            .map { word -> word.trim { !it.isLetterOrDigit() } }
            .filter { word -> word.any { it.isLetter() } }

    /** The results page, videos only ("EgIQAQ==" is YouTube's own filter value, written double-encoded as YouTube does). */
    fun searchUrl(query: String): String =
        "https://www.youtube.com/results?search_query=" + query.encodeURLParameter() + "&sp=EgIQAQ%253D%253D"

    fun watchUrl(id: String): String = "https://www.youtube.com/watch?v=$id"

    fun playerUrl(key: String): String = "https://www.youtube.com/youtubei/v1/player?key=$key"

    /** What YouTube's Android app sends to ask for a video's details and caption files. [id] is 11 safe characters. */
    fun playerBody(id: String): String =
        "{\"context\":{\"client\":{\"clientName\":\"ANDROID\",\"clientVersion\":\"$ANDROID_CLIENT_VERSION\"}},\"videoId\":\"$id\"}"

    /** Opens the YouTube app at [startMs] when it is installed (a universal link), else YouTube in Safari. */
    fun openUrl(id: String, startMs: Long): String = "https://www.youtube.com/watch?v=$id&t=${maxOf(0L, startMs / 1000)}s"

    /** Video ids in the order the results page lists them (counted from its ytInitialData when found), each once, at most 8. */
    fun videoIds(html: String): List<String> {
        val start = html.indexOf("ytInitialData")
        val part = if (start >= 0) html.substring(start) else html
        return idPattern.findAll(part).map { it.groupValues[1] }.distinct().take(MAX_IDS).toList()
    }

    /** The page's own public key for YouTube's internal API, or "". */
    fun apiKey(html: String): String = keyPattern.find(html)?.groupValues?.get(1).orEmpty()

    /** The video's name, channel and length, and its caption files, from the player answer; null when it is not JSON. */
    fun player(json: String, id: String): Pair<ClipVideo, List<ClipCaptionTrack>>? {
        val root = runCatching { Json.parseToJsonElement(json) }.getOrNull() as? JsonObject ?: return null
        val details = root["videoDetails"] as? JsonObject
        val video = ClipVideo(
            id = id,
            title = details.text("title"),
            channel = details.text("author"),
            seconds = details.text("lengthSeconds").toIntOrNull() ?: 0,
        )
        val renderer = (root["captions"] as? JsonObject)?.get("playerCaptionsTracklistRenderer") as? JsonObject
        val tracks = (renderer?.get("captionTracks") as? JsonArray).orEmpty().mapNotNull { entry ->
            val track = entry as? JsonObject ?: return@mapNotNull null
            val url = track.text("baseUrl")
            if (!url.startsWith("https://")) null else ClipCaptionTrack(url, track.text("languageCode"), track.text("kind") == "asr")
        }
        return video to tracks
    }

    /** English captions written by people first, else YouTube's own; null when there are none in English. */
    fun pickTrack(tracks: List<ClipCaptionTrack>): ClipCaptionTrack? =
        tracks.filter { track ->
            val code = track.language.lowercase()
            code == "en" || code.startsWith("en-")
        }.minByOrNull { if (it.auto) 1 else 0 }

    /** YouTube marks caption files that need a token from its own player with "&exp=xpe"; those cannot be read. */
    fun needsToken(track: ClipCaptionTrack): Boolean = "&exp=xpe" in track.url

    /** The plain XML form of the caption file (without "&fmt=srv3"). */
    fun captionUrl(track: ClipCaptionTrack): String = track.url.replace("&fmt=srv3", "")

    /** Cues from a caption file: <text start="seconds" dur="seconds">escaped words</text>. Anything else gives none. */
    fun cues(xml: String): List<SubtitleSyncCue> = textPattern.findAll(xml).mapNotNull { match ->
        val attributes = match.groupValues[1]
        val start = startPattern.find(attributes)?.groupValues?.get(1)?.toDoubleOrNull() ?: return@mapNotNull null
        val duration = durationPattern.find(attributes)?.groupValues?.get(1)?.toDoubleOrNull() ?: 2.0
        val text = unescape(match.groupValues[2]).replace(tagPattern, " ").trim()
        if (text.isEmpty()) null else SubtitleSyncCue((start * 1000).roundToLong(), ((start + duration) * 1000).roundToLong(), text)
    }.toList()

    /** XML escaping, and the HTML escaping YouTube puts inside it ("&amp;#39;" is an apostrophe). */
    private fun unescape(text: String): String {
        val once = text.replace("&amp;", "&")
        val named = once.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", "\"").replace("&#39;", "'").replace("&apos;", "'")
        val numbers = numbered.replace(named) { match ->
            val code = match.groupValues[1].toIntOrNull()
            if (code != null && code in 32..0xFFFF) Char(code).toString() else " "
        }
        return numbers.replace("&amp;", "&")
    }

    /**
     * The videos whose captions line up with what was heard: the matcher's confident rule, each video on
     * its own (re-uploads of the same video match equally, so they must not count as each other's
     * runner-up). At most 3. Among videos with at least 80% of the best hits the longest comes first:
     * the full video, not a short cut of it.
     */
    fun verify(videos: List<ClipVideo>, lines: List<ClipLine>): List<ClipVideoAnswer> {
        val matched = videos.filter { it.cues.isNotEmpty() }.mapNotNull { video ->
            ClipMatcher.match(lines, listOf(EpisodeCues(video.id, null, null, video.cues))).firstOrNull()
                ?.takeIf { it.confident }
                ?.let { ClipVideoAnswer(video, it) }
        }
        val best = matched.maxOfOrNull { it.candidate.hits } ?: return emptyList()
        return matched.sortedWith(
            compareByDescending<ClipVideoAnswer> { it.candidate.hits * 5 >= best * 4 }
                .thenByDescending { it.video.seconds }
                .thenByDescending { it.candidate.hits },
        ).take(3)
    }

    /** For Details: "Made Up Interview: 41 phrases", or "none of 5 videos". */
    fun matchNote(answers: List<ClipVideoAnswer>, checked: Int): String =
        if (answers.isEmpty()) {
            "none of $checked videos with captions"
        } else {
            answers.joinToString { "${it.video.title.ifBlank { it.video.id }.take(60)}: ${it.candidate.hits} phrases" }
        }

    private fun JsonObject?.text(key: String): String = (this?.get(key) as? JsonPrimitive)?.contentOrNull.orEmpty()
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipYouTubeTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import com.nuvio.app.features.player.SubtitleSyncCue
import kotlin.math.abs
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue
import kotlinx.serialization.json.add
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/** Made-up YouTube answers in the shapes youtube-transcript-api 1.2.5 and yt-dlp 2026.10.26 read. No real video. */
internal object ClipTubeSamples {
    /** A caption file with one cue every 4 s, each 3 s long (the same timing as [ClipTestText.srt]). */
    fun captionXml(texts: List<String>): String =
        "<?xml version=\"1.0\" encoding=\"utf-8\" ?><transcript>" +
            texts.mapIndexed { index, text -> "<text start=\"${index * 4}.0\" dur=\"3.0\">$text</text>" }.joinToString("") +
            "</transcript>"

    fun captionUrl(id: String, locked: Boolean = false): String =
        "https://www.youtube.com/api/timedtext?v=$id&lang=en" + (if (locked) "&exp=xpe" else "") + "&fmt=srv3"

    fun playerJson(id: String, title: String, seconds: Int, auto: Boolean = true, locked: Boolean = false, language: String = "en"): String =
        buildJsonObject {
            put(
                "videoDetails",
                buildJsonObject {
                    put("videoId", id)
                    put("title", title)
                    put("author", "Sample Channel")
                    put("lengthSeconds", seconds.toString())
                },
            )
            put(
                "captions",
                buildJsonObject {
                    put(
                        "playerCaptionsTracklistRenderer",
                        buildJsonObject {
                            put(
                                "captionTracks",
                                buildJsonArray {
                                    add(
                                        buildJsonObject {
                                            put("baseUrl", captionUrl(id, locked))
                                            put("languageCode", language)
                                            if (auto) put("kind", "asr")
                                        },
                                    )
                                },
                            )
                        },
                    )
                },
            )
        }.toString()

    /** A results page: one id before ytInitialData (not a result), the results, and the page key when [key] is not blank. */
    fun searchPage(ids: List<String>, key: String = "samplekey"): String {
        val results = ids.joinToString(",") { "{\"videoRenderer\":{\"videoId\":\"$it\",\"title\":{\"runs\":[{\"text\":\"x\"}]}}}" }
        val config = if (key.isBlank()) "" else "<script>ytcfg.set({\"INNERTUBE_API_KEY\":\"$key\",\"HL\":\"en\"});</script>"
        return "<html><head><link rel=\"preload\" data-x='{\"videoId\":\"PRELOADxxxx\"}'></head><body>" +
            "<script>var ytInitialData = {\"contents\":{\"twoColumnSearchResultsRenderer\":{\"primaryContents\":" +
            "{\"sectionListRenderer\":{\"contents\":[{\"itemSectionRenderer\":{\"contents\":[$results]}}]}}}}};</script>" +
            config + "</body></html>"
    }
}

/** Everything here is made up: ids, titles, captions and words. */
class ClipYouTubeTest {
    @Test
    fun `the results page gives the video ids in order and the page key`() {
        val page = ClipTubeSamples.searchPage(listOf("FULLvideo01", "SHORTcut001", "FULLvideo01"))
        assertEquals(listOf("FULLvideo01", "SHORTcut001"), ClipYouTube.videoIds(page))
        assertEquals("samplekey", ClipYouTube.apiKey(page))
        assertEquals("", ClipYouTube.apiKey("<html>consent page</html>"))
        assertEquals(emptyList(), ClipYouTube.videoIds("<html>consent page</html>"))
    }

    @Test
    fun `the player answer gives the details and the English captions, people's first`() {
        val (video, tracks) = ClipYouTube.player(ClipTubeSamples.playerJson("FULLvideo01", "Made Up Interview", 3600), "FULLvideo01")!!
        assertEquals(ClipVideo("FULLvideo01", "Made Up Interview", "Sample Channel", 3600), video)
        assertEquals(listOf(ClipCaptionTrack(ClipTubeSamples.captionUrl("FULLvideo01"), "en", true)), tracks)
        val people = ClipCaptionTrack("https://www.youtube.com/api/timedtext?v=a&lang=en-GB", "en-GB", false)
        val french = ClipCaptionTrack("https://www.youtube.com/api/timedtext?v=a&lang=fr", "fr", false)
        assertEquals(people, ClipYouTube.pickTrack(tracks + people + french))
        assertNull(ClipYouTube.pickTrack(listOf(french)))
        assertNull(ClipYouTube.player("<html>not json</html>", "x"))
        assertEquals("https://www.youtube.com/api/timedtext?v=FULLvideo01&lang=en", ClipYouTube.captionUrl(tracks.first()))
    }

    @Test
    fun `a caption file that needs YouTube's token is recognised`() {
        val (_, tracks) = ClipYouTube.player(ClipTubeSamples.playerJson("LOCKEDvid01", "x", 10, locked = true), "LOCKEDvid01")!!
        assertTrue(ClipYouTube.needsToken(tracks.first()))
        assertFalse(ClipYouTube.needsToken(ClipCaptionTrack(ClipTubeSamples.captionUrl("a"), "en", true)))
    }

    @Test
    fun `caption XML becomes cues, escaping undone and empty cues left out`() {
        val xml = "<?xml version=\"1.0\" encoding=\"utf-8\" ?><transcript>" +
            "<text start=\"1.5\" dur=\"2.25\">bako ritu &amp;amp; nesa</text>" +
            "<text dur=\"1.0\" start=\"4\">it&amp;#39;s <i>dako</i></text>" +
            "<text start=\"7.1\" dur=\"1\">zibo</text>" +
            "<text start=\"9\" dur=\"1\"> </text>" +
            "<text start=\"10\">tail</text></transcript>"
        assertEquals(
            listOf(
                SubtitleSyncCue(1_500, 3_750, "bako ritu & nesa"),
                SubtitleSyncCue(4_000, 5_000, "it's  dako"),
                SubtitleSyncCue(7_100, 8_100, "zibo"),
                SubtitleSyncCue(10_000, 12_000, "tail"),
            ),
            ClipYouTube.cues(xml),
        )
        assertEquals(emptyList(), ClipYouTube.cues("<html>no captions</html>"))
    }

    @Test
    fun `searches come from the keyword, the caption and the text on screen`() {
        val clues = ClipClues(
            caption = "The best part of Made Up Interview #madeupinterview @someone https://x.example.test/a",
            keywords = listOf("made up interview full", "other keyword"),
            screenText = listOf("SAMPLE GUEST", "ep", "4"),
        )
        assertEquals(listOf("made up interview full", "The best part of Made Up Interview", "SAMPLE GUEST ep"), ClipYouTube.queries(clues))
    }

    @Test
    fun `hashtags only without words, the sound only without anything else`() {
        assertEquals(listOf("madeupinterview"), ClipYouTube.queries(ClipClues(caption = "#madeupinterview #fyp")))
        assertEquals(emptyList(), ClipYouTube.queries(ClipClues(caption = "lol", sound = "original sound - sample.user")))
        assertEquals(listOf("Lamp Song Some Band"), ClipYouTube.queries(ClipClues(sound = "Lamp Song - Some Band")))
    }

    @Test
    fun `addresses to open and to search`() {
        assertEquals("https://www.youtube.com/watch?v=FULLvideo01&t=125s", ClipYouTube.openUrl("FULLvideo01", 125_900))
        assertEquals("https://www.youtube.com/watch?v=FULLvideo01&t=0s", ClipYouTube.openUrl("FULLvideo01", -10))
        assertEquals(
            "https://www.youtube.com/results?search_query=made%20up%20show&sp=EgIQAQ%253D%253D",
            ClipYouTube.searchUrl("made up show"),
        )
        assertTrue("\"videoId\":\"FULLvideo01\"" in ClipYouTube.playerBody("FULLvideo01"))
        assertTrue("\"clientName\":\"ANDROID\"" in ClipYouTube.playerBody("FULLvideo01"))
    }

    @Test
    fun `the check prefers the full upload and never keeps a video that does not match`() {
        val texts = ClipTestText.cueTexts(501)
        fun cuesOf(part: List<String>) = ClipYouTube.cues(ClipTubeSamples.captionXml(part))
        val full = ClipVideo("FULLvideo01", "Made Up Interview", "Sample Channel", 3_600, cuesOf(texts))
        val short = ClipVideo("SHORTcut001", "Best bit", "Sample Channel", 60, cuesOf(texts.subList(18, 34)))
        val other = ClipVideo("OTHERvid001", "Something else", "Other", 900, cuesOf(ClipTestText.cueTexts(777)))
        val empty = ClipVideo("NOCAPTION01", "No captions", "Other", 900)
        val lines = ClipTestText.linesFrom(texts, 20..31)
        val answers = ClipYouTube.verify(listOf(short, other, empty, full), lines)
        assertEquals(listOf("FULLvideo01", "SHORTcut001"), answers.map { it.video.id })
        assertTrue(answers.all { it.candidate.confident })
        assertTrue(abs(answers.first().candidate.startMs - 80_000L) <= 5_000L)
        assertEquals(emptyList(), ClipYouTube.verify(listOf(other, empty), lines))
        assertEquals("none of 1 videos with captions", ClipYouTube.matchNote(emptyList(), 1))
    }

    @Test
    fun `a YouTube answer is named and described like an episode`() {
        val candidate = ClipCandidate("FULLvideo01", null, null, 125_000, 190_000, 0.88, 40, true)
        assertEquals("at 2:05 to 3:10, 88% sure", clipMatchDetail(candidate))
        assertEquals(
            "Made Up Interview (Sample Channel)",
            clipVideoTitle(ClipVideoAnswer(ClipVideo("FULLvideo01", "Made Up Interview", "Sample Channel"), candidate)),
        )
        assertEquals("YouTube video", clipVideoTitle(ClipVideoAnswer(ClipVideo("FULLvideo01"), candidate)))
        assertEquals("Made Up Interview: 40 phrases", ClipYouTube.matchNote(listOf(ClipVideoAnswer(ClipVideo("FULLvideo01", "Made Up Interview"), candidate)), 3))
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipYouTubeFinder.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withTimeoutOrNull

/** What a web request gave back: the HTTP status and the text. */
data class ClipWebReply(val status: Int, val body: String)

/**
 * Finds YouTube videos that may hold the clip and reads their captions: up to 3 searches with words
 * from the clues, then the first 6 videos (the best-ranked of each search in turn), 3 at a time.
 * Whether a video really holds the clip is decided afterwards by [ClipYouTube.verify] with what was
 * heard, so this can run while the clip is still being listened to. Every step is written to the
 * Details panel. Never throws, except when cancelled.
 */
class ClipYouTubeFinder(
    private val get: suspend (url: String, headers: Map<String, String>) -> ClipWebReply,
    private val post: suspend (url: String, body: String, headers: Map<String, String>) -> ClipWebReply,
) {
    suspend fun collect(clues: ClipClues, onNote: (label: String, value: String) -> Unit): List<ClipVideo> {
        val queries = ClipYouTube.queries(clues)
        if (queries.isEmpty()) {
            onNote("YouTube", "no words to search with")
            return emptyList()
        }
        var key = ""
        val searches = mutableListOf<String>()
        val ranked = mutableListOf<List<String>>()
        for (query in queries) {
            val reply = quietly { get(ClipYouTube.searchUrl(query), PAGE_HEADERS) }
            val ok = reply != null && reply.status in 200..299
            val ids = if (reply != null && ok) ClipYouTube.videoIds(reply.body) else emptyList()
            if (key.isEmpty() && reply != null && ok) key = ClipYouTube.apiKey(reply.body)
            searches += "\"$query\": " + when {
                reply == null -> "failed"
                !ok -> "HTTP ${reply.status}"
                else -> ids.size.toString()
            }
            ranked += ids
        }
        onNote("YouTube searches", searches.joinToString().take(300))
        val ids = (0 until MAX_IDS_PER_SEARCH).flatMap { rank -> ranked.mapNotNull { it.getOrNull(rank) } }.distinct().take(MAX_VIDEOS)
        if (ids.isEmpty()) return emptyList()
        if (key.isEmpty()) {
            key = quietly { get(ClipYouTube.watchUrl(ids.first()), PAGE_HEADERS) }?.body?.let { ClipYouTube.apiKey(it) }.orEmpty()
        }
        if (key.isEmpty()) {
            onNote("YouTube captions", "the page key was not found, so no captions could be read")
            return emptyList()
        }
        val read = ids.chunked(IN_FLIGHT).flatMap { group ->
            coroutineScope { group.map { id -> async { video(id, key) } }.awaitAll() }
        }
        onNote("YouTube captions", read.joinToString { it.second }.take(400))
        return read.map { it.first }
    }

    /** One video: its details and caption files (as YouTube's Android app asks), then the English captions. */
    private suspend fun video(id: String, key: String): Pair<ClipVideo, String> {
        val reply = quietly { post(ClipYouTube.playerUrl(key), ClipYouTube.playerBody(id), API_HEADERS) }
            ?: return ClipVideo(id) to "$id failed"
        val (video, tracks) = ClipYouTube.player(reply.body, id) ?: return ClipVideo(id) to "$id unreadable"
        val track = ClipYouTube.pickTrack(tracks) ?: return video to "$id no English captions"
        if (ClipYouTube.needsToken(track)) return video to "$id captions need YouTube's token"
        val text = quietly { get(ClipYouTube.captionUrl(track), API_HEADERS) }?.body.orEmpty()
        val cues = ClipYouTube.cues(text)
        return video.copy(cues = cues) to "$id ${cues.size} lines" + if (track.auto) " (auto)" else ""
    }

    /** Null on a time-out or any failure; cancelling still cancels. */
    private suspend fun <T> quietly(block: suspend () -> T): T? =
        withTimeoutOrNull(REQUEST_MS) {
            try {
                block()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                null
            }
        }

    companion object {
        const val MAX_VIDEOS = 6
        private const val MAX_IDS_PER_SEARCH = 8
        private const val IN_FLIGHT = 3
        private const val REQUEST_MS = 10_000L
        /** "SOCS=CAI" answers YouTube's cookie question the way yt-dlp does, so no consent page comes back. */
        private val PAGE_HEADERS = mapOf(
            "User-Agent" to ClipYouTube.DESKTOP_AGENT,
            "Accept-Language" to "en-US,en;q=0.9",
            "Cookie" to "SOCS=CAI",
        )
        private val API_HEADERS = mapOf("Accept-Language" to "en-US")
    }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipYouTubeFinderTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import kotlinx.coroutines.test.runTest

/**
 * A made-up YouTube: answers by address, every request written down. Searches answer [searchIds]
 * (with the page key unless [keyOnSearch] is false), players answer [players] by video id, caption
 * files answer [captions] by address.
 */
internal class FakeTube(
    val searchIds: List<String> = emptyList(),
    val keyOnSearch: Boolean = true,
    val searchStatus: Int = 200,
    val players: Map<String, String> = emptyMap(),
    val captions: Map<String, String> = emptyMap(),
) {
    val asked = mutableListOf<String>()
    val headers = mutableListOf<Map<String, String>>()
    val bodies = mutableListOf<String>()

    suspend fun get(url: String, sent: Map<String, String>): ClipWebReply {
        asked += url
        headers += sent
        return when {
            url.startsWith("https://www.youtube.com/results") ->
                ClipWebReply(searchStatus, ClipTubeSamples.searchPage(searchIds, if (keyOnSearch) "samplekey" else ""))
            url.startsWith("https://www.youtube.com/watch") -> ClipWebReply(200, "<html>a watch page without a key</html>")
            else -> captions[url]?.let { ClipWebReply(200, it) } ?: ClipWebReply(404, "")
        }
    }

    suspend fun post(url: String, body: String, sent: Map<String, String>): ClipWebReply {
        asked += url
        bodies += body
        val id = players.keys.firstOrNull { "\"$it\"" in body } ?: throw IllegalStateException("HTTP 400")
        return ClipWebReply(200, players.getValue(id))
    }

    fun finder() = ClipYouTubeFinder({ url, sent -> get(url, sent) }, { url, body, sent -> post(url, body, sent) })
}

/** Everything here is made up: ids, titles, captions and words. */
class ClipYouTubeFinderTest {
    private val clues = ClipClues(caption = "Made up interview with a sample guest")

    @Test
    fun `searches, reads each video's captions and says why some could not be read`() = runTest {
        val tube = FakeTube(
            searchIds = listOf("AAAAAAAAAA1", "BBBBBBBBBB2", "CCCCCCCCCC3"),
            players = mapOf(
                "AAAAAAAAAA1" to ClipTubeSamples.playerJson("AAAAAAAAAA1", "Made Up Interview", 3_600),
                "BBBBBBBBBB2" to ClipTubeSamples.playerJson("BBBBBBBBBB2", "Locked", 600, locked = true),
                "CCCCCCCCCC3" to ClipTubeSamples.playerJson("CCCCCCCCCC3", "French", 600, language = "fr"),
            ),
            captions = mapOf(
                "https://www.youtube.com/api/timedtext?v=AAAAAAAAAA1&lang=en" to ClipTubeSamples.captionXml(listOf("bako ritu", "nesa dako")),
            ),
        )
        val notes = mutableListOf<Pair<String, String>>()
        val videos = tube.finder().collect(clues) { label, value -> notes += label to value }
        assertEquals(listOf("AAAAAAAAAA1", "BBBBBBBBBB2", "CCCCCCCCCC3"), videos.map { it.id })
        assertEquals(2, videos.first().cues.size)
        assertEquals("Made Up Interview", videos.first().title)
        assertEquals(3_600, videos.first().seconds)
        assertEquals(
            listOf(
                "YouTube searches" to "\"Made up interview with a sample guest\": 3",
                "YouTube captions" to "AAAAAAAAAA1 2 lines (auto), BBBBBBBBBB2 captions need YouTube's token, CCCCCCCCCC3 no English captions",
            ),
            notes,
        )
        assertEquals("SOCS=CAI", tube.headers.first()["Cookie"])
        assertEquals(ClipYouTube.DESKTOP_AGENT, tube.headers.first()["User-Agent"])
        assertTrue(tube.asked.contains(ClipYouTube.playerUrl("samplekey")))
        assertEquals(ClipYouTube.playerBody("AAAAAAAAAA1"), tube.bodies.first { "AAAAAAAAAA1" in it })
    }

    @Test
    fun `no words to search with asks nothing`() = runTest {
        val tube = FakeTube(searchIds = listOf("AAAAAAAAAA1"))
        val notes = mutableListOf<Pair<String, String>>()
        val videos = tube.finder().collect(ClipClues(caption = "lol")) { label, value -> notes += label to value }
        assertEquals(emptyList(), videos)
        assertEquals(listOf("YouTube" to "no words to search with"), notes)
        assertEquals(emptyList(), tube.asked)
    }

    @Test
    fun `without the page key no captions are read, and a refused search is noted`() = runTest {
        val tube = FakeTube(searchIds = listOf("AAAAAAAAAA1"), keyOnSearch = false)
        val notes = mutableListOf<Pair<String, String>>()
        val videos = tube.finder().collect(clues) { label, value -> notes += label to value }
        assertEquals(emptyList(), videos)
        assertEquals(ClipYouTube.watchUrl("AAAAAAAAAA1"), tube.asked.last())
        assertEquals("the page key was not found, so no captions could be read", notes.last().second)

        val refused = FakeTube(searchIds = listOf("AAAAAAAAAA1"), searchStatus = 429)
        val refusedNotes = mutableListOf<Pair<String, String>>()
        assertEquals(emptyList(), refused.finder().collect(clues) { label, value -> refusedNotes += label to value })
        assertEquals(listOf("YouTube searches" to "\"Made up interview with a sample guest\": HTTP 429"), refusedNotes)
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipInstagram.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.withTimeoutOrNull

/**
 * Instagram without a login. A logged-out reel page often has no video address (phone test, 2026-11-16:
 * "Video address found: no"), so the other pages of the same post are tried. Where each key comes from,
 * and how sure we are that Instagram still sends it:
 * - og:description "585K likes, 550 comments - handle on December 15, 2025: "caption"": seen on the phone. Sure.
 * - The /p/<code>/ page's JSON scripts with "xig_polaris_media" ... "video_versions": [{"url"}]: what yt-dlp
 *   2026.10.26 reads for logged-out posts (its source was read on 2026-11-16). Medium.
 * - The embed page /p/<code>/embed/captioned/ with "video_url" inside "shortcode_media" (plain JSON, or escaped
 *   inside "contextJSON"), or a <video src>: what older yt-dlp versions read. Low to medium.
 * - og:video: rarely sent to logged-out visitors today. Low.
 * A blob: address is never used (it only lives inside the page). Pure functions, plus [findVideo],
 * which gets the network passed in.
 */
object ClipInstagram {
    const val PHONE_AGENT =
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
    private const val HTTP_MS = 10_000L
    private const val MAX_URLS = 6
    /** A regular expression for any number of backslashes: the same key appears at several levels of JSON escaping. */
    private const val SLASHES = "\\\\*"
    private val link = Regex("instagram\\.com/(?:[A-Za-z0-9_.]+/)?(?:reels?|p|tv)/([A-Za-z0-9_-]{5,})", RegexOption.IGNORE_CASE)
    private val described =
        Regex("^\\s*(?:[\\d.,]+\\s*[KMBkmb]?\\s+(?:likes?|comments?),?\\s*)+-\\s+([A-Za-z0-9._]+)\\s+on\\s+([^:]{3,40}):\\s*([\\s\\S]*)$")
    private val videoKey = Regex("video_url$SLASHES\"\\s*:\\s*$SLASHES\"(https?:[^\"]*?)$SLASHES\"")
    private val versionsStart = Regex("video_versions$SLASHES\"\\s*:\\s*\\[")
    private val versionUrl = Regex("url$SLASHES\"\\s*:\\s*$SLASHES\"(https?:[^\"]*?)$SLASHES\"")
    private val videoTag = Regex("<video[^>]*\\ssrc=\"(https://[^\"]+)\"", RegexOption.IGNORE_CASE)
    private val ogVideo = Regex("<meta[^>]+property=\"og:video(?::secure_url)?\"[^>]+content=\"(https://[^\"]+)\"", RegexOption.IGNORE_CASE)

    /** The post's code in an Instagram link ("/reel/ABC123/", "/p/ABC123/", "/tv/ABC123/"), or "". */
    fun shortcode(url: String): String = link.find(url)?.groupValues?.get(1).orEmpty()

    fun postUrl(code: String): String = "https://www.instagram.com/p/$code/"

    fun embedUrl(code: String): String = "https://www.instagram.com/p/$code/embed/captioned/"

    /**
     * Instagram's og:description "N likes, N comments - handle on date: "caption"" -> the caption without
     * the counts and the quote marks, and the handle. Null for any other text.
     */
    fun description(text: String): Pair<String, String>? {
        val match = described.find(text) ?: return null
        var caption = match.groupValues[3].trim()
        if (caption.startsWith("\"") || caption.startsWith("“")) caption = caption.drop(1)
        if (caption.endsWith("\".") || caption.endsWith("”.")) caption = caption.dropLast(1)
        if (caption.endsWith("\"") || caption.endsWith("”")) caption = caption.dropLast(1)
        return caption.trim() to match.groupValues[1]
    }

    /** Video addresses written anywhere in a page or script text, at any level of JSON escaping. At most 6. */
    fun videoUrls(text: String): List<String> {
        val found = mutableListOf<String>()
        videoKey.findAll(text).forEach { found += it.groupValues[1] }
        for (start in versionsStart.findAll(text)) {
            val from = start.range.last + 1
            val close = text.indexOf(']', from)
            val to = minOf(if (close < 0) text.length else close, from + 4_000)
            versionUrl.find(text.substring(from, to))?.let { found += it.groupValues[1] }
        }
        videoTag.findAll(text).forEach { found += it.groupValues[1] }
        ogVideo.findAll(text).forEach { found += it.groupValues[1] }
        return found.map { unescape(it) }.filter { it.startsWith("https://") }.distinct().take(MAX_URLS)
    }

    fun hasVideoKey(text: String): Boolean = "video_url" in text || "video_versions" in text

    /** For Details: "812 KB, video key no". */
    fun describe(text: String): String = "${size(text)}, video key ${yesNo(hasVideoKey(text))}"

    /**
     * Tries the other pages of post [code] until one gives a video address: the embed page as a plain
     * download (cheap, about a second), then the /p/ page and the embed page in the off-screen web view
     * ([readPage] gives the page reader's JSON, or null). [tried] gets one line for Details, starting with
     * [first] (what the shared page gave), saying what each page returned.
     */
    suspend fun findVideo(
        code: String,
        webGet: suspend (String, Map<String, String>) -> ClipWebReply,
        readPage: suspend (String) -> String?,
        first: String,
        tried: (String) -> Unit,
    ): ClipPage? {
        val log = mutableListOf(first)
        var found: ClipPage? = null
        val reply = quietly { webGet(embedUrl(code), mapOf("User-Agent" to PHONE_AGENT, "Accept-Language" to "en-US,en;q=0.9")) }
        log += "embed download: " + if (reply == null) "failed" else "HTTP ${reply.status}, ${describe(reply.body)}"
        val direct = if (reply != null && reply.status in 200..299) videoUrls(reply.body) else emptyList()
        if (direct.isNotEmpty()) found = ClipPage(pageUrl = embedUrl(code), videoUrls = direct)
        for ((name, url) in listOf("post page" to postUrl(code), "embed page" to embedUrl(code))) {
            if (found != null) break
            val json = readPage(url)
            val page = json?.let { ClipPageParser.parse(it) }
            log += "$name: " + if (json == null || page == null) "did not load" else "${describe(json)}, addresses found: ${page.videoUrls.size}"
            if (page != null && page.videoUrls.isNotEmpty()) found = page
        }
        tried(log.joinToString("; "))
        return found
    }

    /** Undoes JSON escaping as many times as it was done ("https:\\/\\/" -> "https://"), then "&amp;". */
    internal fun unescape(text: String): String {
        var current = text
        repeat(4) {
            if ('\\' !in current) return current.replace("&amp;", "&")
            current = jsonLevel(current)
        }
        return current.replace("&amp;", "&")
    }

    private fun jsonLevel(text: String): String = buildString {
        var index = 0
        while (index < text.length) {
            val char = text[index]
            if (char != '\\' || index + 1 >= text.length) {
                append(char)
                index++
                continue
            }
            val next = text[index + 1]
            val code = if (next == 'u' && index + 5 < text.length) text.substring(index + 2, index + 6).toIntOrNull(16) else null
            if (code != null) {
                append(Char(code))
                index += 6
            } else {
                append(if (next == 'n') '\n' else if (next == 't') '\t' else next)
                index += 2
            }
        }
    }

    private fun size(text: String): String = "${text.length / 1024} KB"

    private fun yesNo(value: Boolean): String = if (value) "yes" else "no"

    private suspend fun <T> quietly(block: suspend () -> T): T? =
        withTimeoutOrNull(HTTP_MS) {
            try {
                block()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                null
            }
        }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipInstagramTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.add
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/** Made-up Instagram pages in the shapes yt-dlp reads (and the phone showed for the description). No real post. */
class ClipInstagramTest {
    private val described = "585K likes, 550 comments - sample.user on December 15, 2025: \"Made Up Show S2E5 the lamp scene #madeupshow\". "

    private fun pageJson(description: String = "", raw: List<String> = emptyList()): String = buildJsonObject {
        put("url", "https://www.instagram.com/p/DAbc123xyz/")
        put("title", "Instagram")
        put("metas", buildJsonObject { if (description.isNotEmpty()) put("og:description", description) })
        put("videos", buildJsonArray {})
        put("scripts", buildJsonArray {})
        put("raw", buildJsonArray { raw.forEach { add(it) } })
    }.toString()

    @Test
    fun `the post code is read from every kind of Instagram link`() {
        assertEquals("DAbc123xyz", ClipInstagram.shortcode("https://www.instagram.com/reel/DAbc123xyz/?igsh=c2FtcGxl"))
        assertEquals("DAbc123xyz", ClipInstagram.shortcode("https://www.instagram.com/sample.user/reel/DAbc123xyz/"))
        assertEquals("DAbc123xyz", ClipInstagram.shortcode("https://www.instagram.com/reels/DAbc123xyz/"))
        assertEquals("Cx_9-ab12", ClipInstagram.shortcode("https://instagram.com/p/Cx_9-ab12/"))
        assertEquals("DAbc123xyz", ClipInstagram.shortcode("https://www.instagram.com/tv/DAbc123xyz"))
        assertEquals("", ClipInstagram.shortcode("https://www.instagram.com/sample.user/"))
        assertEquals("", ClipInstagram.shortcode("https://clips.example.test/@a/video/1"))
        assertEquals("https://www.instagram.com/p/DAbc123xyz/embed/captioned/", ClipInstagram.embedUrl("DAbc123xyz"))
    }

    @Test
    fun `the description gives the caption without counts and quote marks, and the handle`() {
        assertEquals("Made Up Show S2E5 the lamp scene #madeupshow" to "sample.user", ClipInstagram.description(described))
        assertEquals(
            "Second line\nand more" to "made_up.clips",
            ClipInstagram.description("1,204 likes, 31 comments - made_up.clips on May 2, 2026: “Second line\nand more”"),
        )
        assertEquals("plain caption" to "sample_user", ClipInstagram.description("12 likes - sample_user on May 2, 2026: plain caption"))
        assertNull(ClipInstagram.description("Just a caption with 3 likes - nope"))
        assertNull(ClipInstagram.description(""))
    }

    @Test
    fun `video addresses are found at any level of escaping, blob and http never`() {
        assertEquals(
            listOf("https://cdn.example.test/v1.mp4?a=1&b=2"),
            ClipInstagram.videoUrls(
                """window.__additionalDataLoaded('/p/DAbc123xyz/',{"graphql":{"shortcode_media":{"is_video":true,"video_url":"https://cdn.example.test/v1.mp4?a=1&b=2"}}});""",
            ),
        )
        assertEquals(
            listOf("https://cdn.example.test/v2.mp4"),
            ClipInstagram.videoUrls("""{"contextJSON":"{\"context\":{\"media\":{\"video_url\":\"https:\\/\\/cdn.example.test\\/v2.mp4\"}}}"}"""),
        )
        assertEquals(
            listOf("https://cdn.example.test/v3.mp4"),
            ClipInstagram.videoUrls("""{"video_versions":[],"x":1,"video_versions":[{"type":101,"url":"https:\/\/cdn.example.test\/v3.mp4","width":720}]}"""),
        )
        assertEquals(
            listOf("https://cdn.example.test/v4.mp4", "https://cdn.example.test/v5.mp4"),
            ClipInstagram.videoUrls(
                """<video class="x" src="blob:https://www.instagram.com/abc"></video><video playsinline src="https://cdn.example.test/v4.mp4"></video><meta property="og:video" content="https://cdn.example.test/v5.mp4">""",
            ),
        )
        assertEquals(
            emptyList(),
            ClipInstagram.videoUrls("""{"video_url":"http://cdn.example.test/old.mp4","video_url":"blob:https://www.instagram.com/x"}"""),
        )
    }

    @Test
    fun `the embed download is tried first, then the post page in the web view`() = runTest {
        val read = mutableListOf<String>()
        val page = ClipInstagram.findVideo(
            code = "DAbc123xyz",
            webGet = { _, _ -> ClipWebReply(200, "<html>no video here</html>") },
            readPage = { url ->
                read += url
                pageJson(raw = listOf("""requireLazy(["x"],function(){ return {"items":[{"video_versions":[{"url":"https:\/\/cdn.example.test\/v6.mp4"}]}]} })"""))
            },
            first = "page: 1 KB, video key no",
        ) { line -> read += line }
        assertEquals(listOf("https://cdn.example.test/v6.mp4"), page?.videoUrls)
        assertEquals(
            listOf(
                "https://www.instagram.com/p/DAbc123xyz/",
                "page: 1 KB, video key no; embed download: HTTP 200, 0 KB, video key no; post page: 0 KB, video key yes, addresses found: 1",
            ),
            read,
        )
    }

    @Test
    fun `nothing found anywhere says so for each page`() = runTest {
        var line = ""
        val page = ClipInstagram.findVideo("DAbc123xyz", { _, _ -> throw IllegalStateException("offline") }, { null }, "page: 0 KB, video key no") { line = it }
        assertNull(page)
        assertEquals("page: 0 KB, video key no; embed download: failed; post page: did not load; embed page: did not load", line)
    }

    @Test
    fun `the page parser reads raw scripts and Instagram's description`() {
        val walked = ClipPageParser.parse(
            pageJson(
                raw = listOf(
                    """{"xig":{"items":[{"video_versions":[{"url":"https://cdn.example.test/v7.mp4"}],"caption":{"text":"Made Up Show lamp"},"user":{"username":"sample.user"}}]}}""",
                ),
            ),
        )
        assertEquals(listOf("https://cdn.example.test/v7.mp4"), walked.videoUrls)
        assertEquals("Made Up Show lamp", walked.caption)
        assertEquals("sample.user", walked.author)
        val fromMeta = ClipPageParser.parse(pageJson(description = described))
        assertEquals("Made Up Show S2E5 the lamp scene #madeupshow", fromMeta.caption)
        assertEquals("sample.user", fromMeta.author)
        assertEquals(emptyList(), fromMeta.videoUrls)
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipPageParser.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull

/** What a clip's web page says about itself. Every field may be empty. */
data class ClipPage(
    val pageUrl: String = "",
    val caption: String = "",
    val author: String = "",
    val videoUrls: List<String> = emptyList(),
    /** The sound's title and maker ("original sound - Made Up Show - Sample"). */
    val sound: String = "",
    /** Search words the site attached to the clip. */
    val keywords: List<String> = emptyList(),
    /** Hashtags the site lists for the clip, without "#". */
    val hashtags: List<String> = emptyList(),
)

/**
 * Reads the JSON text made by the page script in ClipPageReader.swift:
 * {"url", "title", "metas": {name: content}, "videos": [addresses of video elements],
 * "scripts": [text of each JSON script tag], "raw": [any script that names "video_url" or "video_versions"]}
 * ("raw" is missing when the page reader is older). Besides the caption it keeps other words that may
 * name the show: the sound's title, the site's keywords and its hashtag list. The sites change their pages often, so nothing here
 * depends on one exact shape: every JSON script is searched for an object that looks like a clip
 * and for the keys that hold video addresses; a raw script that is not JSON is searched as text
 * ([ClipInstagram.videoUrls]). Instagram's "N likes, N comments - handle on date: "caption"" description
 * gives the caption and the handle. Never throws; unknown input gives an empty page.
 */
object ClipPageParser {
    private const val MAX_NODES = 300_000
    private const val MAX_DEPTH = 60
    private const val MAX_URLS = 6
    private const val MAX_WORDS = 12
    private val keywordKeys = setOf("suggestedWords", "keywords", "keywordTags")
    private val urlKeys = setOf(
        "playAddr", "PlayAddr", "play_addr", "downloadAddr", "DownloadAddr", "download_addr",
        "video_url", "video_versions", "contentUrl",
    )
    private val captionMetas = listOf("og:description", "twitter:description", "description", "og:title")
    private val videoMetas = listOf("og:video:secure_url", "og:video", "og:video:url", "twitter:player:stream")

    private class Found {
        var caption = ""
        var author = ""
        val urls = mutableListOf<String>()
        var sound = ""
        val keywords = mutableListOf<String>()
        val hashtags = mutableListOf<String>()
        var nodes = 0
    }

    fun parse(pageJson: String): ClipPage = runCatching { parseOrThrow(pageJson) }.getOrDefault(ClipPage())

    private fun parseOrThrow(pageJson: String): ClipPage {
        val root = Json.parseToJsonElement(pageJson) as? JsonObject ?: return ClipPage()
        val metas = root["metas"] as? JsonObject
        val found = Found()
        for (script in (root["scripts"] as? JsonArray).orEmpty()) {
            val text = (script as? JsonPrimitive)?.contentOrNull ?: continue
            val element = runCatching { Json.parseToJsonElement(text) }.getOrNull() ?: continue
            walk(element, found, 0)
        }
        found.nodes = 0
        for (script in (root["raw"] as? JsonArray).orEmpty()) {
            val text = (script as? JsonPrimitive)?.contentOrNull ?: continue
            val element = runCatching { Json.parseToJsonElement(text) }.getOrNull()
            if (element != null) walk(element, found, 0) else found.urls += ClipInstagram.videoUrls(text)
        }
        val elementUrls = (root["videos"] as? JsonArray).orEmpty().mapNotNull { (it as? JsonPrimitive)?.contentOrNull }
        val metaUrls = videoMetas.mapNotNull { metas?.text(it)?.takeIf(String::isNotBlank) }
        val urls = (elementUrls + found.urls + metaUrls)
            .map { it.trim() }
            .filter { it.startsWith("https://", ignoreCase = true) || it.startsWith("http://", ignoreCase = true) }
            .distinct()
            .take(MAX_URLS)
        val metaCaption = captionMetas.firstNotNullOfOrNull { metas?.text(it)?.takeIf(String::isNotBlank) } ?: root.text("title")
        val described = ClipInstagram.description(metaCaption)
        val caption = found.caption.ifBlank { described?.first ?: metaCaption }
        return ClipPage(
            pageUrl = root.text("url"),
            caption = caption.trim().take(2_000),
            author = found.author.ifBlank { described?.second.orEmpty() }.trim().take(100),
            videoUrls = urls,
            sound = found.sound.trim().take(200),
            keywords = found.keywords.toList(),
            hashtags = found.hashtags.toList(),
        )
    }

    private fun walk(element: JsonElement, found: Found, depth: Int) {
        found.nodes++
        if (depth > MAX_DEPTH || found.nodes > MAX_NODES) return
        when (element) {
            is JsonObject -> {
                readClip(element, found)
                for ((key, value) in element) {
                    if (key in urlKeys) collectUrls(value, found.urls, 0)
                    if (key in keywordKeys) collectWords(value, found.keywords, 0)
                    walk(value, found, depth + 1)
                }
            }
            is JsonArray -> for (child in element) walk(child, found, depth + 1)
            else -> Unit
        }
    }

    /**
     * TikTok: {"desc": "...", "video": {...}, "author": {"uniqueId": "..."} or "name"}.
     * Instagram: {"caption": {"text": "..."}, "video_versions": [...], "user": {"username": "..."}}.
     * The first clip with a caption wins.
     */
    private fun readClip(obj: JsonObject, found: Found) {
        if (found.caption.isNotBlank()) return
        val tiktok = obj["video"] is JsonObject && obj["desc"] is JsonPrimitive
        val instagram = "video_versions" in obj || "video_url" in obj
        if (!tiktok && !instagram) return
        val caption = if (tiktok) obj.text("desc") else (obj["caption"] as? JsonObject)?.text("text") ?: obj.text("caption")
        val owner = if (tiktok) obj["author"] else obj["user"] ?: obj["owner"]
        val author = when (owner) {
            is JsonObject -> owner.text("uniqueId").ifBlank { owner.text("username") }.ifBlank { owner.text("nickname") }
            is JsonPrimitive -> owner.contentOrNull.orEmpty()
            else -> ""
        }
        if (caption.isNotBlank()) found.caption = caption
        if (found.author.isBlank()) found.author = author
        readExtras(obj, found)
    }

    /**
     * More words about the clip. TikTok: {"music": {"title", "authorName"}, "textExtra": [{"hashtagName"}],
     * "challenges": [{"title"}]}. Instagram: {"clips_metadata": {"original_sound_info": {"original_audio_title"},
     * "music_info": {"music_asset_info": {"title", "display_artist"}}}}.
     */
    private fun readExtras(obj: JsonObject, found: Found) {
        if (found.sound.isBlank()) {
            val music = obj["music"] as? JsonObject
            val reel = obj["clips_metadata"] as? JsonObject
            val original = reel?.get("original_sound_info") as? JsonObject
            val asset = (reel?.get("music_info") as? JsonObject)?.get("music_asset_info") as? JsonObject
            found.sound = listOf(
                music?.text("title"), music?.text("authorName"), original?.text("original_audio_title"),
                asset?.text("title"), asset?.text("display_artist"),
            ).filter { !it.isNullOrBlank() }.joinToString(" - ")
        }
        for (entry in (obj["textExtra"] as? JsonArray).orEmpty() + (obj["challenges"] as? JsonArray).orEmpty()) {
            val tag = (entry as? JsonObject)?.let { it.text("hashtagName").ifBlank { it.text("title") } }.orEmpty().trim()
            if (tag.isNotEmpty() && tag !in found.hashtags && found.hashtags.size < MAX_WORDS) found.hashtags += tag
        }
    }

    private fun collectWords(value: JsonElement, into: MutableList<String>, depth: Int) {
        if (depth > 2 || into.size >= MAX_WORDS) return
        when (value) {
            is JsonPrimitive -> {
                val text = value.contentOrNull?.trim().orEmpty()
                if (value.isString && text.length in 3..60 && text !in into) into += text
            }
            is JsonArray -> for (child in value) collectWords(child, into, depth + 1)
            is JsonObject -> for (child in value.values) collectWords(child, into, depth + 1)
        }
    }

    private fun collectUrls(value: JsonElement, into: MutableList<String>, depth: Int) {
        if (depth > 3 || into.size >= 12) return
        when (value) {
            is JsonPrimitive -> {
                val text = value.contentOrNull ?: return
                if (value.isString && text.startsWith("http") && text !in into) into += text
            }
            is JsonArray -> for (child in value) collectUrls(child, into, depth + 1)
            is JsonObject -> for (child in value.values) collectUrls(child, into, depth + 1)
        }
    }

    private fun JsonObject.text(key: String): String = (this[key] as? JsonPrimitive)?.contentOrNull.orEmpty()
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipTimings.kt`
```kotlin
package com.nuvio.app.features.clipfinder

/**
 * Seconds per stage for the Details panel ("Timings: page 6.1 s, download 3.2 s, ..., total 58.3 s"),
 * so the next screenshot shows where the time goes. [now] is a clock in milliseconds.
 */
class ClipTimings(private val now: () -> Long) {
    private val started = now()
    private var last = started
    private val parts = mutableListOf<String>()

    /** Ends the stage that ran since the last lap (or the start) and names it. */
    fun lap(stage: String, extra: String = "") {
        val time = now()
        parts += entry(stage, time - last, extra)
        last = time
    }

    /** Work that ran beside the stages, such as YouTube while listening. It does not move the lap clock. */
    fun beside(stage: String, ms: Long, extra: String = "") {
        parts += entry(stage, ms, extra) + " beside"
    }

    fun line(): String = (parts + "total ${seconds(now() - started)}").joinToString(", ")

    companion object {
        /** "6.1 s": tenths, cut not rounded, never below zero. */
        fun seconds(ms: Long): String {
            val time = maxOf(0L, ms)
            return "${time / 1000}.${time % 1000 / 100} s"
        }

        private fun entry(stage: String, ms: Long, extra: String): String =
            "$stage ${seconds(ms)}" + if (extra.isBlank()) "" else " ($extra)"
    }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipTimingsTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.test.Test
import kotlin.test.assertEquals

class ClipTimingsTest {
    @Test
    fun `stages, work beside them and the total`() {
        var clock = 0L
        val timings = ClipTimings { clock }
        clock = 6_100
        timings.lap("page")
        clock = 9_300
        timings.lap("download")
        timings.beside("YouTube", 9_400, "6 videos")
        clock = 30_700
        timings.lap("listen", "part 3 of 3")
        assertEquals(
            "page 6.1 s, download 3.2 s, YouTube 9.4 s (6 videos) beside, listen 21.4 s (part 3 of 3), total 30.7 s",
            timings.line(),
        )
    }

    @Test
    fun `seconds are cut to tenths and never negative`() {
        assertEquals("0.0 s", ClipTimings.seconds(-5))
        assertEquals("0.0 s", ClipTimings.seconds(59))
        assertEquals("1.9 s", ClipTimings.seconds(1_999))
        assertEquals("125.0 s", ClipTimings.seconds(125_000))
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipEpisodeRank.kt`
```kotlin
package com.nuvio.app.features.clipfinder

/**
 * A cheap first pass before downloading subtitles: episodes whose title or summary holds rare words
 * that were heard (a guest's name, "zibotu lamp") are searched earlier. Only the order changes; the
 * subtitle match still decides. A word in more than a fifth of the summaries (a main character's
 * name) says nothing about one episode and is ignored. The hinted episode stays first; episodes
 * already fetched while listening come next, because checking them costs nothing.
 */
object ClipEpisodeRank {
    private const val MIN_LETTERS = 4
    private const val MAX_SHARE = 0.2

    /** [ordered] is the list from [orderEpisodes]; [cached] the video ids whose subtitles are already in the cache. */
    fun rank(ordered: List<ClipEpisode>, hint: ClipHint, lines: List<ClipLine>, cached: Set<String> = emptySet()): List<ClipEpisode> {
        val heard = lines.flatMap { ClipText.normalize(it.text) }
            .filter { word -> word.length >= MIN_LETTERS && word.none { it.isDigit() } }
            .toSet()
        val texts = ordered.map { ClipText.normalize("${it.title.orEmpty()}\n${it.overview.orEmpty()}").toSet() }
        val counts = mutableMapOf<String, Int>()
        for (words in texts) for (word in words) if (word in heard) counts[word] = (counts[word] ?: 0) + 1
        val limit = maxOf(1.0, ordered.size * MAX_SHARE)
        val scores = texts.map { words ->
            words.sumOf { word ->
                val count = counts[word] ?: 0
                if (count == 0 || count > limit) 0.0 else 1.0 / count
            }
        }
        fun hinted(episode: ClipEpisode) =
            hint.season != null && hint.episode != null && episode.season == hint.season && episode.episode == hint.episode
        fun inSeason(episode: ClipEpisode) = hint.season != null && episode.season == hint.season
        return ordered.indices.sortedWith(
            compareBy<Int>(
                { if (hinted(ordered[it])) 0 else 1 },
                { if (ordered[it].videoId in cached) 0 else 1 },
                { if (inSeason(ordered[it])) 0 else 1 },
                { -scores[it] },
                { it },
            ),
        ).map { ordered[it] }
    }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipEpisodeRankTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.test.Test
import kotlin.test.assertEquals

/** Made-up episode summaries and heard words. */
class ClipEpisodeRankTest {
    private fun episode(season: Int, number: Int, overview: String) =
        ClipEpisode("e$season-$number", "e$season-$number", "series", season, number, title = "Episode $number", overview = overview)

    private val season1 = listOf(
        episode(1, 1, "Kora meets the neighbours."),
        episode(1, 2, "Kora and the lamp."),
        episode(1, 3, "Zibotu visits; the lamp breaks."),
        episode(1, 4, "Nesa returns. Kora alone."),
        episode(1, 5, "Nothing heard here."),
    )

    private fun ids(list: List<ClipEpisode>) = list.map { it.videoId }

    @Test
    fun `a rare heard word in a summary moves its episode up, a common one does nothing`() {
        val lines = listOf(ClipLine("zibotu brought the lamp back, kora", 0, 3_000))
        assertEquals(listOf("e1-3", "e1-1", "e1-2", "e1-4", "e1-5"), ids(ClipEpisodeRank.rank(season1, ClipHint(), lines)))
        assertEquals(ids(season1), ids(ClipEpisodeRank.rank(season1, ClipHint(), emptyList())))
    }

    @Test
    fun `the hinted episode stays first and episodes already fetched come next`() {
        val list = season1.take(4) + episode(2, 1, "A new start.")
        val lines = listOf(ClipLine("nesa is here", 0, 3_000))
        assertEquals(
            listOf("e2-1", "e1-2", "e1-4", "e1-1", "e1-3"),
            ids(ClipEpisodeRank.rank(list, ClipHint(season = 2, episode = 1), lines, cached = setOf("e1-2"))),
        )
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipPrefetch.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope

/**
 * Work done while the clip is still being listened to (listening is slow and needs no network). When
 * the page alone names a show strongly (score 90 or more: an exact hashtag, a keyword of the page, this
 * poster's last show), its episode list and the subtitles of its first 36 episodes (hinted episode and
 * season first) are fetched into the cache, 6 at a time. The search after listening then reads them
 * from the cache. The pipeline cancels this as soon as listening ends; what was fetched stays cached.
 */
class ClipPrefetch(
    private val finder: ClipShowFinder,
    private val loadEpisodes: suspend (ShowGuess) -> List<ClipEpisode>,
    private val subtitles: EpisodeSubtitleSource,
) {
    /** The show it worked on (set once its episode list is loaded), or null. */
    var show: ShowGuess? = null
        private set

    /** That show's episodes as loaded, not ordered. */
    var episodes: List<ClipEpisode> = emptyList()
        private set

    /** Video ids whose subtitles are now in the cache. */
    val fetched = mutableSetOf<String>()

    suspend fun run(clues: ClipClues) {
        val top = finder.find(clues, emptyList()).firstOrNull() ?: return
        if (top.score < STRONG) return
        val loaded = loadEpisodes(top.show)
        if (loaded.isEmpty()) return
        episodes = loaded
        show = top.show
        val ordered = orderEpisodes(loaded, ClipNames.hint(clues, emptyList())).take(MAX_EPISODES)
        for (batch in ordered.chunked(IN_FLIGHT)) {
            val done = coroutineScope {
                batch.map { episode ->
                    async { episode.videoId.takeIf { subtitles.cues(top.show.metaId, episode) != null } }
                }.awaitAll()
            }
            fetched += done.filterNotNull()
        }
    }

    companion object {
        const val STRONG = 90
        const val MAX_EPISODES = 36
        private const val IN_FLIGHT = 6
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipShowSearch.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.coroutines.CoroutineContext
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

/** How the show search ended: answers best first, or why there are none ([failure], plain English). */
data class ClipShowOutcome(val answers: List<ClipAnswer> = emptyList(), val failure: String? = null)

/**
 * Searching episodes from the clues and the heard lines: suspects ([ClipShowFinder]), the name check when
 * there are many, then the subtitles of up to 3 shows. Moved out of the pipeline as it was, with three
 * additions: episodes in [ClipEpisodeRank] order, the episode list and subtitles fetched while listening
 * ([ClipPrefetch]) reused, and a "Match" note with the numbers behind the confidence.
 */
class ClipShowSearch(
    private val finder: ClipShowFinder,
    private val loadEpisodes: suspend (ShowGuess) -> List<ClipEpisode>,
    private val subtitles: EpisodeSubtitleSource,
    private val now: () -> Long,
    private val work: CoroutineContext,
) {
    suspend fun run(
        clues: ClipClues,
        lines: List<ClipLine>,
        prefetch: ClipPrefetch?,
        timings: ClipTimings,
        note: (String, String) -> Unit,
        progress: (String) -> Unit,
    ): ClipShowOutcome {
        var suspects = finder.find(clues, lines, onNote = note)
        timings.lap("guess")
        val hint = ClipNames.hint(clues, lines)
        val cached: Set<String> = prefetch?.fetched.orEmpty()
        val episodeLists = mutableMapOf<String, List<ClipEpisode>>()
        val early = prefetch?.show
        if (prefetch != null && early != null) episodeLists[early.metaId] = prefetch.episodes
        suspend fun episodesOf(show: ShowGuess): List<ClipEpisode> {
            val loaded = episodeLists.getOrPut(show.metaId) { quietly { loadEpisodes(show) }.orEmpty() }
            return ClipEpisodeRank.rank(orderEpisodes(loaded, hint), hint, lines, cached)
        }

        // Many suspects: one subtitle file of each tells which show has the people named in the clip.
        val names = ClipNameCheck.names(lines)
        if (ClipNameCheck.needed(suspects, names)) {
            progress("Checking which show has the names heard")
            note("Names heard", names.joinToString())
            val ranked = withTimeoutOrNull(ClipFinderPipeline.NAME_CHECK_MS) {
                ClipNameCheck.rank(suspects, names) { show ->
                    episodesOf(show).firstOrNull()?.let { episode -> subtitles.cues(show.metaId, episode) }
                }
            }
            if (ranked != null) {
                note("Name check", ranked.joinToString { "${it.first.show.name} ${it.second}" }.take(300))
                suspects = ranked.map { it.first }
            }
            timings.lap("names")
        }
        val chosen = suspects.take(ClipNameCheck.KEEP)
        note("Show guesses", chosen.joinToString { "${it.show.name} (${it.why})" }.ifBlank { "none" })
        if (chosen.isEmpty()) return ClipShowOutcome(failure = if (clues.typed.isBlank()) ClipMessages.NO_SHOW else ClipMessages.NO_TYPED_SHOW)
        val deadline = now() + ClipFinderPipeline.SEARCH_BUDGET_MS
        val owners = mutableMapOf<String, Pair<ShowGuess, ClipEpisode>>()
        var best = emptyList<EpisodeCues>()
        var candidates = emptyList<ClipCandidate>()
        var tried = 0
        var withSubtitles = 0
        for (guess in chosen.map { it.show }) {
            if (now() >= deadline) break
            progress("Loading the episode list of ${guess.name}")
            val episodes = episodesOf(guess)
            timings.lap("episode list")
            if (episodes.isEmpty()) continue
            for (episode in episodes) owners[episode.videoId] = guess to episode
            val showDeadline = minOf(deadline, now() + ClipFinderPipeline.SHOW_BUDGET_MS)
            val result = withContext(work) {
                subtitles.search(guess.metaId, episodes, lines, showDeadline, best) { done, total, found ->
                    progress("Searching ${guess.name}: $done of $total episodes, $found with subtitles")
                }
            }
            timings.lap("subtitles", "${result.tried} episodes")
            best = result.best
            candidates = result.candidates
            tried += result.tried
            withSubtitles += result.withSubtitles
            if (result.decisive) break
            if (result.tried < episodes.size) note("Search", "stopped at the time limit in ${guess.name}")
        }
        note("Subtitles", "$withSubtitles of $tried episodes")
        if (tried == 0) return ClipShowOutcome(failure = ClipMessages.NO_EPISODES)
        if (withSubtitles == 0) return ClipShowOutcome(failure = ClipMessages.NO_SUBTITLES)
        note("Match", matchNote(lines, candidates))
        val answers = candidates.filter { it.hits >= ClipMatcher.MIN_HITS }.mapNotNull { candidate ->
            owners[candidate.videoId]?.let { (show, episode) -> ClipAnswer(candidate, show, episode.title, episode.thumbnail) }
        }
        note("Candidates", answers.size.toString())
        return if (answers.isEmpty()) ClipShowOutcome(failure = ClipMessages.NO_MATCH) else ClipShowOutcome(answers)
    }

    /** "41 shared phrases of 160 heard (25%), next best 3": the numbers behind the confidence, to tune it on real clips. */
    private fun matchNote(lines: List<ClipLine>, candidates: List<ClipCandidate>): String {
        val heard = ClipText.triples(lines.flatMap { ClipText.normalize(it.text) }).toSet().size
        val top = candidates.firstOrNull() ?: return "nothing shared with $heard heard phrases"
        val share = if (heard == 0) 0 else top.hits * 100 / heard
        return "${top.hits} shared phrases of $heard heard ($share%), next best ${candidates.getOrNull(1)?.hits ?: 0}"
    }

    private suspend fun <T> quietly(block: suspend () -> T): T? =
        try {
            block()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            null
        }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderState.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.math.roundToInt

enum class ClipStage { ReadingLink, Listening, Searching, Done }

/** One diagnostic line on the screen ("Audio: 312 s"). Real data from the run, so a screenshot shows where it broke. */
data class ClipNote(val label: String, val value: String)

data class ClipAnswer(
    val candidate: ClipCandidate,
    val show: ShowGuess,
    val episodeTitle: String? = null,
    val thumbnail: String? = null,
)

data class ClipFinderState(
    val source: String = "",
    /** The stage that runs now, or the one that failed when [failed] is true. */
    val stage: ClipStage = ClipStage.ReadingLink,
    val failed: Boolean = false,
    val message: String = "",
    val showFileHint: Boolean = false,
    val progress: String = "",
    val notes: List<ClipNote> = emptyList(),
    val lines: List<ClipLine> = emptyList(),
    /** What is known about the clip besides its sound; kept so a typed show name can search again. */
    val clues: ClipClues = ClipClues(),
    val answers: List<ClipAnswer> = emptyList(),
    /** YouTube videos that hold the clip (their captions match what was heard), best first. */
    val youtube: List<ClipVideoAnswer> = emptyList(),
    /** Open the first YouTube video by itself, once: it is the only sure answer. */
    val openYouTube: Boolean = false,
    /** Shows to open when the clip itself could not be heard (no video address, or no speech). */
    val shows: List<ShowGuess> = emptyList(),
    /** The clip could not be heard: a typed name can only find the show, not the moment. */
    val noClip: Boolean = false,
) {
    /** A note with the same label is replaced where it stands; a new label goes to the end. */
    fun withNote(label: String, value: String): ClipFinderState {
        val note = ClipNote(label, value)
        val index = notes.indexOfFirst { it.label == label }
        return copy(notes = if (index < 0) notes + note else notes.toMutableList().also { it[index] = note })
    }
}

internal const val CLIP_LEAD_IN_MS = 10_000L

internal object ClipMessages {
    const val NO_BRIDGE = "Clip finder only works in the iPhone app."
    const val PAGE_TIMEOUT = "Reading the link took longer than 45 s."
    const val PAGE_FAILED = "The page could not be read."
    const val NO_VIDEO = "Nuvio could not find the video's address on the page. The site may have asked for a login or changed its page."
    const val LISTEN_TIMEOUT = "Listening took longer than 7 minutes and was stopped."
    const val NO_SPEECH = "No speech was heard in this clip (music only, or not in English)."
    const val NO_SHOW = "Nuvio could not work out the show from the caption, the hashtags, the poster or the text on screen. Type its name below."
    const val NO_TYPED_SHOW = "No show or movie in your catalogs has that name. Check the spelling and try again."
    const val NO_EPISODES = "The episode list of the guessed shows could not be loaded."
    const val NO_SUBTITLES = "No English subtitles were found. Check that a subtitle add-on (OpenSubtitles) is switched on in Nuvio."
    const val NO_MATCH = "No match: what was heard does not line up with the subtitles of the guessed shows. If you know the show, type its name below."
    const val OPEN_SHOW = "The caption names the show below: open it to pick the episode yourself."
    const val OPEN_TYPED_SHOW = "The clip could not be heard, so Nuvio cannot find the moment. Open the show below to pick the episode yourself."
    const val FILE_HINT = "Other way: save the video to your iPhone, then in the Files app hold it, tap Share and pick Nuvio."
    fun unexpected(error: Throwable): String = "Something went wrong: " + (error.message ?: error.toString()).take(200)
}

/**
 * The type-the-show box is shown once there is something heard to search with, and after a clip that
 * could not be heard (then a typed name only finds the show to open).
 */
internal fun clipCanType(state: ClipFinderState): Boolean =
    (state.noClip && state.failed) ||
        (state.lines.isNotEmpty() && (state.stage == ClipStage.Searching || state.stage == ClipStage.Done))

/** Where playback starts: 10 s before the matched moment, or right after it. */
internal fun clipStartMs(candidate: ClipCandidate, afterClip: Boolean): Long =
    if (afterClip) candidate.endMs else maxOf(0L, candidate.startMs - CLIP_LEAD_IN_MS)

/** "4:07" or "1:02:09". */
internal fun clipClock(ms: Long): String {
    val total = maxOf(0L, ms) / 1000
    val hours = total / 3600
    val minutes = (total % 3600) / 60
    val seconds = (total % 60).toString().padStart(2, '0')
    return if (hours > 0) "$hours:${minutes.toString().padStart(2, '0')}:$seconds" else "$minutes:$seconds"
}

/** "South Park, season 14 episode 2: Title" or just the movie's name. */
internal fun clipAnswerTitle(answer: ClipAnswer): String {
    val season = answer.candidate.season
    val episode = answer.candidate.episode
    if (season == null || episode == null) return answer.show.name
    val title = answer.episodeTitle?.takeIf { it.isNotBlank() }?.let { ": $it" }.orEmpty()
    return "${answer.show.name}, season $season episode $episode$title"
}

/** "at 4:07 to 9:30, 86% sure" or "..., 31% (weak)". */
internal fun clipAnswerDetail(answer: ClipAnswer): String = clipMatchDetail(answer.candidate)

/** "Made Up Interview (Sample Channel)", or "YouTube video" when its name is not known. */
internal fun clipVideoTitle(answer: ClipVideoAnswer): String {
    val name = answer.video.title.ifBlank { "YouTube video" }
    return if (answer.video.channel.isBlank()) name else "$name (${answer.video.channel})"
}

/** The matched span and how sure the match is, for an episode or a YouTube video. */
internal fun clipMatchDetail(c: ClipCandidate): String {
    val percent = (c.confidence * 100).roundToInt()
    return "at ${clipClock(c.startMs)} to ${clipClock(c.endMs)}, " + if (c.confident) "$percent% sure" else "$percent% (weak)"
}

/** "done", "now", "failed" or "" for stage number [index] (0..2) of CLIP_FINDER_STAGES. */
internal fun clipStageMark(state: ClipFinderState, index: Int): String = when {
    index < state.stage.ordinal -> "done"
    index > state.stage.ordinal -> ""
    state.failed -> "failed"
    else -> "now"
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderPipeline.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.coroutines.CoroutineContext
import kotlin.coroutines.resume
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull

/**
 * The whole run for one shared clip: read the link (for Instagram also the post's other pages), listen,
 * then search episodes; YouTube is searched beside it. While the clip is listened to, the show the page
 * names is already fetched ([ClipPrefetch]) and YouTube already searched. Everything that touches the
 * phone or the network is passed in, so this is tested with fakes. Call [run] from the main thread;
 * [emit] may be called from another thread.
 */
class ClipFinderPipeline(
    private val native: ClipFinderNative?,
    private val finder: ClipShowFinder,
    private val loadEpisodes: suspend (ShowGuess) -> List<ClipEpisode>,
    private val subtitles: EpisodeSubtitleSource,
    private val memory: ClipMemory,
    private val now: () -> Long,
    private val work: CoroutineContext = Dispatchers.Default,
    private val youtube: ClipYouTubeFinder? = null,
    private val webGet: suspend (String, Map<String, String>) -> ClipWebReply = { _, _ -> ClipWebReply(0, "") },
) {
    private val showSearch = ClipShowSearch(finder, loadEpisodes, subtitles, now, work)

    private class NativeResult(
        val page: String? = null,
        val lines: List<ClipLine> = emptyList(),
        val screenText: List<String> = emptyList(),
        val error: String? = null,
        val failedStage: String = "",
    )

    suspend fun run(source: String, emit: (ClipFinderState) -> Unit) =
        guarded(Run(ClipFinderState(source = source), emit)) { it.stages() }

    /**
     * Searches again with a show name the user typed. [previous] is the state of the finished (or
     * stopped) run: what was heard and the other clues are reused, nothing is read or listened to again.
     * YouTube answers found before stay. After a clip that could not be heard it only finds the show.
     */
    suspend fun runTyped(previous: ClipFinderState, typed: String, emit: (ClipFinderState) -> Unit) {
        val start = previous.copy(
            stage = if (previous.noClip) previous.stage else ClipStage.Searching,
            failed = false,
            message = "",
            showFileHint = false,
            progress = "",
            notes = previous.notes.filter { it.label !in SEARCH_NOTES },
            answers = emptyList(),
            openYouTube = false,
            shows = emptyList(),
            clues = previous.clues.copy(typed = typed.trim().take(MAX_TYPED)),
        )
        guarded(Run(start, emit)) { it.search(null, null) }
    }

    private suspend fun guarded(run: Run, block: suspend (Run) -> Unit) {
        try {
            block(run)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            run.fail(ClipMessages.unexpected(e))
        }
    }

    private inner class Run(start: ClipFinderState, private val emit: (ClipFinderState) -> Unit) {
        private val state = MutableStateFlow(start)
        private val source = start.source
        private val isFile = source.startsWith("file:", ignoreCase = true)
        private val timings = ClipTimings(now)
        private var lastPart = ""

        fun change(block: (ClipFinderState) -> ClipFinderState) {
            state.update(block)
            emit(state.value)
        }

        fun note(label: String, value: String) = change { it.withNote(label, value) }

        fun fail(message: String, fileHint: Boolean = false) = change {
            it.copy(failed = true, message = message, showFileHint = fileHint, progress = "").withNote("Timings", timings.line())
        }

        suspend fun stages() {
            emit(state.value)
            val phone = this@ClipFinderPipeline.native ?: return fail(ClipMessages.NO_BRIDGE)

            // 1. Reading link
            var pageClues = ClipClues()
            var mediaUrls = listOf(source)
            var pageUrl = ""
            if (!isFile) {
                val read = withTimeoutOrNull(PAGE_TIMEOUT_MS) { call { phone.readPage(source, it) } }
                    ?: return fail(ClipMessages.PAGE_TIMEOUT, fileHint = true)
                val pageJson = read.page ?: return fail(read.error ?: ClipMessages.PAGE_FAILED, fileHint = true)
                timings.lap("page")
                val page = ClipPageParser.parse(pageJson)
                mediaUrls = page.videoUrls
                pageUrl = page.pageUrl.ifBlank { source }
                pageClues = ClipClues(
                    caption = page.caption,
                    author = page.author.ifBlank { ClipNames.authorInLink(pageUrl) },
                    sound = page.sound,
                    keywords = page.keywords,
                    hashtags = page.hashtags,
                )
                val code = ClipInstagram.shortcode(pageUrl).ifBlank { ClipInstagram.shortcode(source) }
                if (mediaUrls.isEmpty() && code.isNotEmpty()) {
                    change { it.copy(progress = "Trying Instagram's other pages of this post") }
                    val first = "page: " + ClipInstagram.describe(pageJson)
                    val other = ClipInstagram.findVideo(code, webGet, { url -> readOtherPage(phone, url) }, first) { note("Instagram", it) }
                    timings.lap("Instagram pages")
                    change { it.copy(progress = "") }
                    if (other != null) {
                        mediaUrls = other.videoUrls
                        if (pageClues.caption.isBlank()) pageClues = pageClues.copy(caption = other.caption)
                        if (pageClues.author.isBlank()) pageClues = pageClues.copy(author = other.author)
                    }
                }
                note("Caption", pageClues.caption.ifBlank { "none" }.take(120))
                if (pageClues.author.isNotBlank()) note("Author", pageClues.author)
                if (pageClues.sound.isNotBlank()) note("Sound", pageClues.sound.take(100))
                if (pageClues.keywords.isNotEmpty()) note("Keywords", pageClues.keywords.joinToString().take(160))
                note("Video address found", if (mediaUrls.isEmpty()) "no" else "yes (${mediaUrls.size})")
                if (mediaUrls.isEmpty()) return offerShows(pageClues, ClipMessages.NO_VIDEO, fileHint = true)
            } else {
                change { it.copy(stage = ClipStage.Listening) }
            }
            coroutineScope { listenAndSearch(this, phone, mediaUrls, pageUrl, pageClues) }
        }

        /** 2. Listening (for a link the download still counts as reading the link), with the prefetch and YouTube beside it. */
        private suspend fun listenAndSearch(
            scope: CoroutineScope,
            phone: ClipFinderNative,
            mediaUrls: List<String>,
            pageUrl: String,
            pageClues: ClipClues,
        ) {
            val prefetch = if (isFile) null else ClipPrefetch(finder, loadEpisodes, subtitles)
            val early = prefetch?.let { pre -> scope.launch { beside("prefetch", { "${pre.fetched.size} files" }) { pre.run(pageClues) } } }
            var tube = if (isFile) null else startTube(scope, pageClues)
            try {
                val heard = withTimeoutOrNull(LISTEN_TIMEOUT_MS) { call { phone.listen(mediaUrls, pageUrl, it) } }
                early?.cancelAndJoin()
                val fetchedShow = prefetch?.show
                if (prefetch != null && fetchedShow != null) {
                    note("Fetched while listening", "${fetchedShow.name}: ${prefetch.fetched.size} subtitle files")
                }
                if (heard == null) return fail(ClipMessages.LISTEN_TIMEOUT, fileHint = !isFile)
                if (heard.error != null) {
                    if (heard.failedStage == CLIP_FINDER_STAGES[1]) change { it.copy(stage = ClipStage.Listening) }
                    return fail(heard.error, fileHint = !isFile)
                }
                val lines = heard.lines
                val clues = pageClues.copy(screenText = heard.screenText)
                change { it.copy(stage = ClipStage.Listening, lines = lines, clues = clues).withNote("Lines heard", lines.size.toString()) }
                note("Text on screen", clues.screenText.joinToString(" | ").ifBlank { "none" }.take(200))
                if (lines.sumOf { ClipText.normalize(it.text).size } < MIN_WORDS) return offerShows(clues, ClipMessages.NO_SPEECH)
                if (tube == null) tube = startTube(scope, clues)
                search(prefetch, tube)
            } finally {
                early?.cancel()
                tube?.cancel()
            }
        }

        /** 3. Searching episodes (and checking the YouTube videos), from the clues and lines in the state. */
        suspend fun search(prefetch: ClipPrefetch?, tube: Deferred<List<ClipVideo>>?) {
            val clues = state.value.clues
            val lines = state.value.lines
            if (clues.typed.isNotBlank()) note("Show typed", clues.typed)
            if (state.value.noClip) return showsOnly(clues)
            change { it.copy(stage = ClipStage.Searching, progress = "Working out the show") }
            val outcome = showSearch.run(clues, lines, prefetch, timings, { label, value -> note(label, value) }) { text ->
                change { it.copy(progress = text) }
            }
            var videos = state.value.youtube
            if (tube != null) {
                change { it.copy(progress = "Checking the YouTube videos") }
                val found = tube.await()
                timings.lap("YouTube wait")
                videos = ClipYouTube.verify(found, lines)
                if (found.isNotEmpty()) note("YouTube match", ClipYouTube.matchNote(videos, found.count { it.cues.isNotEmpty() }))
            }
            val answers = outcome.answers
            if (answers.isEmpty() && (videos.isEmpty() || clues.typed.isNotBlank())) {
                change { it.copy(youtube = videos) }
                return fail(outcome.failure ?: ClipMessages.NO_MATCH)
            }
            val open = videos.isNotEmpty() && answers.none { it.candidate.confident }
            change {
                it.copy(stage = ClipStage.Done, answers = answers, youtube = videos, openYouTube = open, progress = "")
                    .withNote("Timings", timings.line())
            }
            // A confident match is remembered (show and poster only), so the next clip of this show or poster starts there.
            val top = answers.firstOrNull()
            if (top != null && top.candidate.confident) runCatching { memory.remember(clues.author, top.show) }
        }

        /** The clip cannot be heard (no video address, or no speech): the show named by the other clues can still be opened. */
        private suspend fun offerShows(clues: ClipClues, message: String, fileHint: Boolean = false) {
            change { it.copy(progress = "Looking for the show in the caption") }
            val found = quietly { withTimeoutOrNull(OFFER_MS) { finder.find(clues, emptyList()) } }.orEmpty()
                .filter { it.score >= OFFER_SCORE }
                .take(ClipNameCheck.KEEP)
            if (found.isNotEmpty()) note("Show from the caption", found.joinToString { "${it.show.name} (${it.why})" })
            change { it.copy(shows = found.map { suspect -> suspect.show }, noClip = true) }
            fail(if (found.isEmpty()) message else "$message ${ClipMessages.OPEN_SHOW}", fileHint)
        }

        /** A name typed after a clip that could not be heard: find the show to open, nothing more. */
        private suspend fun showsOnly(clues: ClipClues) {
            change { it.copy(progress = "Looking up the show") }
            val found = finder.find(clues, emptyList()) { label, value -> note(label, value) }.take(ClipNameCheck.KEEP)
            change { it.copy(shows = found.map { suspect -> suspect.show }) }
            fail(if (found.isEmpty()) ClipMessages.NO_TYPED_SHOW else ClipMessages.OPEN_TYPED_SHOW, fileHint = !isFile)
        }

        private suspend fun readOtherPage(phone: ClipFinderNative, url: String): String? =
            withTimeoutOrNull(PAGE_TIMEOUT_MS) { call { phone.readPage(url, it) } }?.page

        /** YouTube is searched and its captions read while the rest goes on; checked against what was heard at the end. */
        private fun startTube(scope: CoroutineScope, clues: ClipClues): Deferred<List<ClipVideo>>? {
            val tubeFinder = youtube ?: return null
            return scope.async {
                val started = now()
                val found = quietly { withTimeoutOrNull(YOUTUBE_MS) { tubeFinder.collect(clues) { label, value -> note(label, value) } } }.orEmpty()
                timings.beside("YouTube", now() - started, "${found.size} videos")
                found
            }
        }

        /** Runs [block] and writes its time down as work beside the stages, also when it is stopped. */
        private suspend fun beside(stage: String, extra: () -> String, block: suspend () -> Unit) {
            val started = now()
            try {
                quietly { block() }
            } finally {
                timings.beside(stage, now() - started, extra())
            }
        }

        /** Starts one native call and waits for its end. Cancelling (or a time-out) stops the native work. */
        private suspend fun call(start: (ClipNativeListener) -> Unit): NativeResult =
            suspendCancellableCoroutine { continuation ->
                val lines = mutableListOf<ClipLine>()
                val screen = mutableListOf<String>()
                var ended = false
                fun end(result: NativeResult) {
                    if (ended) return
                    ended = true
                    continuation.resume(result)
                }
                continuation.invokeOnCancellation {
                    ended = true
                    native?.cancel()
                }
                start(object : ClipNativeListener {
                    override fun onNote(label: String, value: String) {
                        if (ended) return
                        when (label) {
                            "Download" -> if (value.startsWith("HTTP")) timings.lap("download")
                            "Speech" -> timings.lap("frames")
                            "Audio" -> {
                                timings.lap("sound")
                                change { it.copy(stage = ClipStage.Listening) }
                            }
                            "Listening" -> lastPart = value
                        }
                        note(label, value)
                    }

                    override fun onPage(pageJson: String) = end(NativeResult(page = pageJson))

                    override fun onScreenText(text: String) {
                        if (ended) return
                        screen += text.lines().map { it.trim().take(MAX_TYPED) }.filter { it.isNotEmpty() }.take(maxOf(0, MAX_SCREEN_LINES - screen.size))
                    }

                    override fun onLine(text: String, startMs: Long, endMs: Long) {
                        if (!ended) lines += ClipLine(text, startMs, endMs)
                    }

                    override fun onDone() {
                        if (!ended) timings.lap("listen", lastPart)
                        end(NativeResult(lines = lines.toList(), screenText = screen.toList()))
                    }

                    override fun onFailed(stage: String, message: String) =
                        end(NativeResult(error = message, failedStage = stage))
                })
            }

        private suspend fun <T> quietly(block: suspend () -> T): T? =
            try {
                block()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                null
            }
    }

    companion object {
        const val PAGE_TIMEOUT_MS = 45_000L
        const val LISTEN_TIMEOUT_MS = 420_000L
        const val SEARCH_BUDGET_MS = 240_000L
        const val SHOW_BUDGET_MS = 120_000L
        /** Fewer recognised words than this cannot be matched: "no speech". */
        const val MIN_WORDS = 6
        const val MAX_TYPED = 80
        const val NAME_CHECK_MS = 45_000L
        const val MAX_SCREEN_LINES = 40
        /** YouTube gets this long from its start (it starts before listening for a link). */
        const val YOUTUBE_MS = 60_000L
        /** Looking for the show to open when the clip cannot be heard. */
        const val OFFER_MS = 20_000L
        /** A show is offered to open only when a clue names it this clearly (its name in the caption: 85). */
        const val OFFER_SCORE = 85
        /** Notes of a search; removed when a typed show name starts a new search. */
        private val SEARCH_NOTES = setOf(
            "Show typed", "Known titles", "Searches", "Names heard", "Name check", "Show guesses", "Search", "Subtitles",
            "Match", "Candidates", "Show from the caption", "Timings",
        )
    }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipFinderPipelineWebTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.coroutines.EmptyCoroutineContext
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.add
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put

/** The pipeline with YouTube, Instagram's other pages and the work done while listening. Everything is made up. */
@OptIn(ExperimentalCoroutinesApi::class)
class ClipFinderPipelineWebTest {
    private val link = "https://clips.example.test/@sample.user/video/7000000000000000001"
    private val element = "https://v16.example.test/element.mp4"
    private val show = ShowGuess("tt001", "series", "Made Up Show")
    private val episodes = (1..2).flatMap { season ->
        (1..6).map { number -> ClipEpisode("tt001:$season:$number", "tt001:$season:$number", "series", season, number, "Title $season-$number") }
    }
    private val texts = episodes.associate { it.videoId to ClipTestText.cueTexts(it.season!! * 100 + it.episode!!) }
    private val clipLines = ClipTestText.linesFrom(texts.getValue("tt001:2:5"), 20..31)
    private val interview = ClipTestText.cueTexts(501)

    private fun pageJson(caption: String, videos: List<String> = listOf(element)): String = buildJsonObject {
        put("url", link)
        put("title", "")
        put("metas", buildJsonObject {})
        put("videos", buildJsonArray { videos.forEach { add(it) } })
        put(
            "scripts",
            buildJsonArray {
                add(
                    buildJsonObject {
                        put(
                            "item",
                            buildJsonObject {
                                put("desc", caption)
                                put("author", buildJsonObject { put("uniqueId", "sample.user") })
                                put("video", buildJsonObject {})
                            },
                        )
                    }.toString(),
                )
            },
        )
    }.toString()

    /** The phone: reads pages from [pages] (by address), and listens at once, or only on [release] when [hold]. */
    private class Phone(val pages: Map<String, String>, val lines: List<ClipLine>, val hold: Boolean = false) : ClipFinderNative {
        var readLinks = 0
        var listenCalls = 0
        var listenMedia: List<String>? = null
        private var waiting: ClipNativeListener? = null

        override fun readPage(link: String, listener: ClipNativeListener) {
            readLinks++
            val page = pages[link]
            if (page != null) listener.onPage(page) else listener.onFailed("Reading link", "The page did not load.")
        }

        override fun listen(mediaUrls: List<String>, pageUrl: String, listener: ClipNativeListener) {
            listenCalls++
            listenMedia = mediaUrls
            listener.onNote("Audio", "41 s")
            if (hold) waiting = listener else finish(listener)
        }

        fun release() = waiting?.let { finish(it) }

        private fun finish(listener: ClipNativeListener) {
            lines.forEach { listener.onLine(it.text, it.startMs, it.endMs) }
            listener.onDone()
        }

        override fun cancel() = Unit

        override fun cacheRead(key: String): String? = null

        override fun cacheWrite(key: String, text: String) = Unit

        override fun settingRead(key: String): String? = null

        override fun settingWrite(key: String, text: String) = Unit

        override fun askModel(prompt: String, listener: ClipModelListener) = listener.onAnswer(null, "not in tests")
    }

    private inner class Harness(
        val phone: Phone,
        val tube: FakeTube = FakeTube(),
        val webGet: suspend (String, Map<String, String>) -> ClipWebReply = { _, _ -> ClipWebReply(404, "") },
        val search: suspend (String) -> List<ShowGuess> = { query -> if (query == "Made Up Show") listOf(show) else emptyList() },
        val popular: suspend () -> List<ShowGuess> = { emptyList() },
    ) {
        val addon = FakeSubtitleAddon(texts)
        val states = mutableListOf<ClipFinderState>()
        val last: ClipFinderState get() = states.last()
        var loads = 0
        private val memory = ClipMemory({ null }, { }, { 1_000L })
        private val subtitles = EpisodeSubtitleSource({ _, id -> addon.list(id) }, { url -> addon.download(url) }, MapSubtitleCache(), { 0L })
        private val pipeline = ClipFinderPipeline(
            phone, ClipShowFinder(search, popular, memory), { loads++; episodes }, subtitles, memory, { 0L }, EmptyCoroutineContext,
            youtube = tube.finder(), webGet = webGet,
        )

        suspend fun run(source: String = link) = pipeline.run(source) { states += it }

        suspend fun typed(name: String) = pipeline.runTyped(last, name) { states += it }

        fun note(label: String): String = last.notes.first { it.label == label }.value
    }

    /** YouTube serving one full upload whose captions are [captions]. */
    private fun tubeWith(captions: List<String>) = FakeTube(
        searchIds = listOf("FULLvideo01"),
        players = mapOf("FULLvideo01" to ClipTubeSamples.playerJson("FULLvideo01", "Made Up Interview", 3_600)),
        captions = mapOf("https://www.youtube.com/api/timedtext?v=FULLvideo01&lang=en" to ClipTubeSamples.captionXml(captions)),
    )

    @Test
    fun `a clip that is on YouTube only opens the YouTube video by itself`() = runTest {
        val phone = Phone(mapOf(link to pageJson("Made up interview with a sample guest")), ClipTestText.linesFrom(interview, 20..31))
        val h = Harness(phone, tube = tubeWith(interview), search = { emptyList() })
        h.run()
        assertEquals(ClipStage.Done, h.last.stage)
        assertFalse(h.last.failed)
        assertEquals(emptyList(), h.last.answers)
        assertEquals(listOf("FULLvideo01"), h.last.youtube.map { it.video.id })
        assertTrue(h.last.openYouTube)
        assertTrue(h.note("YouTube match").startsWith("Made Up Interview: "))
        assertTrue(h.note("Timings").endsWith(" s"))
    }

    @Test
    fun `an episode and the YouTube video are both shown and nothing opens by itself`() = runTest {
        val phone = Phone(mapOf(link to pageJson("Made Up Show S2E5 the lamp scene")), clipLines)
        val h = Harness(phone, tube = tubeWith(texts.getValue("tt001:2:5")))
        h.run()
        assertEquals(ClipStage.Done, h.last.stage)
        assertEquals("tt001:2:5", h.last.answers.first().candidate.videoId)
        assertTrue(h.last.answers.first().candidate.confident)
        assertEquals(listOf("FULLvideo01"), h.last.youtube.map { it.video.id })
        assertFalse(h.last.openYouTube)
        assertTrue(h.note("Match").contains(" shared phrases of "))
    }

    @Test
    fun `an Instagram reel without a video address gets it from the embed page`() = runTest {
        val reel = "https://www.instagram.com/reel/DAbc123xyz/?igsh=c2FtcGxl"
        val page = buildJsonObject {
            put("url", "https://www.instagram.com/reel/DAbc123xyz/")
            put("title", "")
            put(
                "metas",
                buildJsonObject {
                    put("og:description", "585K likes, 550 comments - sample.user on December 15, 2025: \"Made Up Show S2E5 the lamp scene\". ")
                },
            )
            put("videos", buildJsonArray {})
            put("scripts", buildJsonArray {})
        }.toString()
        val embed = """<html><script>window.__additionalDataLoaded('extra',{"shortcode_media":{"video_url":"https://cdn.example.test/reel.mp4"}});</script></html>"""
        val asked = mutableListOf<String>()
        val phone = Phone(mapOf(reel to page), clipLines)
        val h = Harness(phone, webGet = { url, _ ->
            asked += url
            ClipWebReply(200, embed)
        })
        h.run(reel)
        assertEquals(listOf("https://www.instagram.com/p/DAbc123xyz/embed/captioned/"), asked.filter { "instagram.com" in it })
        assertEquals(listOf("https://cdn.example.test/reel.mp4"), phone.listenMedia)
        assertEquals(1, phone.readLinks)
        assertEquals("page: 0 KB, video key no; embed download: HTTP 200, 0 KB, video key yes", h.note("Instagram"))
        assertEquals("Made Up Show S2E5 the lamp scene", h.note("Caption"))
        assertEquals("sample.user", h.note("Author"))
        assertEquals(ClipStage.Done, h.last.stage)
        assertEquals("tt001:2:5", h.last.answers.first().candidate.videoId)
    }

    @Test
    fun `without a video the show named in the caption is offered, and a typed name only finds the show`() = runTest {
        val phone = Phone(mapOf(link to pageJson("Made Up Show S2E5 the lamp scene", videos = emptyList())), clipLines)
        val h = Harness(phone)
        h.run()
        assertTrue(h.last.failed)
        assertEquals(ClipMessages.NO_VIDEO + " " + ClipMessages.OPEN_SHOW, h.last.message)
        assertEquals(listOf(show), h.last.shows)
        assertTrue(h.last.noClip)
        assertTrue(clipCanType(h.last))
        h.typed("Made Up Show")
        assertTrue(h.last.failed)
        assertEquals(ClipMessages.OPEN_TYPED_SHOW, h.last.message)
        assertEquals(listOf(show), h.last.shows)
        assertEquals(ClipStage.ReadingLink, h.last.stage)
        assertEquals(0, phone.listenCalls)
    }

    @Test
    fun `while the clip is listened to the named show's subtitles are fetched and YouTube is searched`() = runTest {
        val phone = Phone(mapOf(link to pageJson("lol #madeupshow")), clipLines, hold = true)
        val tube = FakeTube()
        val h = Harness(phone, tube = tube, search = { emptyList() }, popular = { listOf(show) })
        val job = launch { h.run() }
        runCurrent()
        assertEquals(1, phone.listenCalls)
        assertEquals(12, h.addon.downloaded.size, "all 12 episodes are fetched before listening ends")
        assertTrue(tube.asked.isNotEmpty(), "YouTube is searched before listening ends")
        phone.release()
        job.join()
        assertEquals(12, h.addon.downloaded.size, "nothing is downloaded twice")
        assertEquals(1, h.loads)
        assertEquals(ClipStage.Done, h.last.stage)
        assertEquals("tt001:2:5", h.last.answers.first().candidate.videoId)
        assertEquals("Made Up Show: 12 subtitle files", h.note("Fetched while listening"))
        assertTrue("prefetch 0.0 s (12 files) beside" in h.note("Timings"))
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderSession.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import com.nuvio.app.features.addons.AddonRepository
import com.nuvio.app.features.addons.enabledAddons
import com.nuvio.app.features.addons.httpGetTextWithHeaders
import com.nuvio.app.features.addons.httpPostJsonWithHeaders
import com.nuvio.app.features.addons.httpRequestRaw
import com.nuvio.app.features.catalog.fetchCatalogPage
import com.nuvio.app.features.details.MetaDetailsRepository
import com.nuvio.app.features.player.addonSubtitleRequests
import com.nuvio.app.features.player.loadAddonSubtitles
import com.nuvio.app.features.streams.epochMs
import kotlin.coroutines.resume
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull

/**
 * The one running Clip finder search. It lives outside the screen so that going to the stream list
 * and back does not start the search again.
 */
object ClipFinderSession {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val _state = MutableStateFlow(ClipFinderState())
    val state: StateFlow<ClipFinderState> = _state.asStateFlow()
    private var job: Job? = null
    private var runId = 0
    private var pipeline: ClipFinderPipeline? = null

    /** Starts the search for [source]. Does nothing when that clip is already running or shown, unless [restart]. */
    fun start(source: String, restart: Boolean = false) {
        if (!restart && _state.value.source == source) return
        job?.cancel()
        val id = ++runId
        _state.value = ClipFinderState(source = source)
        val native = ClipFinderBridge.current()
        val cache = object : ClipSubtitleCache {
            override fun read(key: String): String? = native?.cacheRead(key)
            override fun write(key: String, text: String) {
                native?.cacheWrite(key, text)
            }
        }
        val memory = ClipMemory(
            read = { native?.settingRead(ClipMemory.KEY) },
            write = { text -> native?.settingWrite(ClipMemory.KEY, text) },
            now = ::epochMs,
        )
        val created = ClipFinderPipeline(
            native = native,
            finder = ClipShowFinder(::clipSearchShows, ::clipPopularShows, memory) { prompt -> clipAskModel(native, prompt) },
            loadEpisodes = ::clipLoadEpisodes,
            subtitles = EpisodeSubtitleSource(::clipListSubtitles, ::clipDownloadText, cache, ::epochMs),
            memory = memory,
            now = ::epochMs,
            youtube = ClipYouTubeFinder(::clipWebGet, ::clipWebPost),
            webGet = ::clipWebGet,
        )
        pipeline = created
        job = scope.launch {
            created.run(source) { if (id == runId) _state.value = it }
        }
    }

    /** Searches again with a show name the user typed, reusing what was heard. Stops a search that still runs. */
    fun searchTyped(name: String) {
        val current = _state.value
        val active = pipeline ?: return
        if (name.isBlank() || !clipCanType(current)) return
        job?.cancel()
        val id = ++runId
        job = scope.launch {
            active.runTyped(current, name) { if (id == runId) _state.value = it }
        }
    }

    /** The screen opened the YouTube video by itself: it must not do so again when Mo comes back. */
    fun youTubeOpened() {
        _state.value = _state.value.copy(openYouTube = false)
    }
}

private const val MODEL_TIMEOUT_MS = 12_000L

/** One question to Apple's on-device model through the bridge; a missing bridge or no answer in 12 s is a problem text. */
internal suspend fun clipAskModel(native: ClipFinderNative?, prompt: String): ClipModelAnswer {
    val phone = native ?: return ClipModelAnswer(problem = "only in the iPhone app")
    return withTimeoutOrNull(MODEL_TIMEOUT_MS) {
        suspendCancellableCoroutine { continuation ->
            phone.askModel(
                prompt,
                object : ClipModelListener {
                    override fun onAnswer(text: String?, problem: String?) {
                        if (continuation.isActive) continuation.resume(ClipModelAnswer(text.orEmpty(), problem.orEmpty()))
                    }
                },
            )
        }
    } ?: ClipModelAnswer(problem = "no answer in 12 s")
}

private var popularShows: List<ShowGuess> = emptyList()

/**
 * Well-known titles to compare hashtags and handles with: the first page of every plain catalog
 * (series and movies, no required filter) of the switched-on add-ons, for example Cinemeta's
 * "Popular". Fetched once per app start; an empty answer is asked for again next time.
 */
internal suspend fun clipPopularShows(): List<ShowGuess> {
    if (popularShows.isNotEmpty()) return popularShows
    AddonRepository.initialize()
    val catalogs = AddonRepository.uiState.value.addons.enabledAddons().mapNotNull { it.manifest }.flatMap { manifest ->
        manifest.catalogs
            .filter { catalog -> (catalog.type == "series" || catalog.type == "movie") && catalog.extra.none { it.isRequired } }
            .map { manifest to it }
    }.take(8)
    val pages = coroutineScope {
        catalogs.map { (manifest, catalog) ->
            async {
                quietly(8_000L) { fetchCatalogPage(manifest.transportUrl, catalog.type, catalog.id, maxItems = 100).items }.orEmpty()
            }
        }.awaitAll()
    }
    val shows = pages.flatten().filter { it.name.isNotBlank() }.map { ShowGuess(it.id, it.type, it.name, it.poster) }.distinctBy { it.metaId }
    popularShows = shows.filter { it.metaId.startsWith("tt") }.ifEmpty { shows }
    return popularShows
}

private suspend fun <T> quietly(timeoutMs: Long, block: suspend () -> T): T? =
    withTimeoutOrNull(timeoutMs) {
        try {
            block()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            null
        }
    }

/** Nuvio's own search: every search catalog (series and movies) of the switched-on add-ons, results mixed by rank. */
internal suspend fun clipSearchShows(query: String): List<ShowGuess> = coroutineScope {
    AddonRepository.initialize()
    val catalogs = AddonRepository.uiState.value.addons.enabledAddons().mapNotNull { it.manifest }.flatMap { manifest ->
        manifest.catalogs
            .filter { catalog ->
                (catalog.type == "series" || catalog.type == "movie") &&
                    catalog.extra.any { it.name == "search" } &&
                    catalog.extra.none { it.isRequired && it.name != "search" }
            }
            .map { manifest to it }
    }.take(6)
    val pages = catalogs.map { (manifest, catalog) ->
        async {
            quietly(8_000L) {
                fetchCatalogPage(manifest.transportUrl, catalog.type, catalog.id, search = query, maxItems = 8).items
            }.orEmpty()
        }
    }.awaitAll()
    val mixed = (0 until 8).flatMap { rank -> pages.mapNotNull { it.getOrNull(rank) } }
        .map { ShowGuess(it.id, it.type, it.name, it.poster) }
        .distinctBy { it.metaId }
    // Subtitle add-ons only know IMDb ids ("tt..."), so those results go first when there are any.
    mixed.filter { it.metaId.startsWith("tt") }.ifEmpty { mixed }
}

/** The episodes of a series (specials and season 0 left out), or the movie itself as one entry. */
internal suspend fun clipLoadEpisodes(show: ShowGuess): List<ClipEpisode> {
    val meta = quietly(25_000L) { MetaDetailsRepository.fetch(show.type, show.metaId) } ?: return emptyList()
    val imdbId = listOf(meta.id, meta.imdbId.orEmpty(), show.metaId).firstOrNull { it.startsWith("tt") }
    val episodes = meta.videos.filter { (it.season ?: 0) > 0 && it.episode != null }
    if (episodes.isEmpty()) {
        return listOf(ClipEpisode(videoId = meta.id, subtitleId = imdbId ?: meta.id, type = show.type))
    }
    return episodes.map { video ->
        val subtitleId = if (video.id.startsWith("tt") || imdbId == null) video.id else "$imdbId:${video.season}:${video.episode}"
        ClipEpisode(video.id, subtitleId, show.type, video.season, video.episode, video.title, video.thumbnail, video.overview)
    }
}

internal suspend fun clipListSubtitles(type: String, subtitleId: String): List<ClipSubtitleLink> =
    loadAddonSubtitles(addonSubtitleRequests(type, subtitleId)).map { ClipSubtitleLink(it.url, it.language) }

internal suspend fun clipDownloadText(url: String): String = httpGetTextWithHeaders(url, emptyMap())

/** A plain web request from Kotlin (YouTube, Instagram's embed page), at most 6 MB of answer. */
internal suspend fun clipWebGet(url: String, headers: Map<String, String>): ClipWebReply {
    val reply = httpRequestRaw("GET", url, headers, "", maxResponseBodyBytes = 6 * 1024 * 1024)
    return ClipWebReply(reply.status, reply.body)
}

/** A JSON request (YouTube's player answer); a refusal throws, which the caller treats as "failed". */
internal suspend fun clipWebPost(url: String, body: String, headers: Map<String, String>): ClipWebReply =
    ClipWebReply(200, httpPostJsonWithHeaders(url, body, headers))
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderScreen.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalUriHandler
import androidx.lifecycle.compose.collectAsStateWithLifecycle
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

/**
 * [onOpen] gets the tapped candidate and the time to start playing from, in milliseconds; [onShow] a show
 * to open (its episode list) when the clip itself could not be heard. A YouTube video opens through the
 * system (the YouTube app when installed): by itself once when it is the only sure answer, else on a tap.
 */
@Composable
fun ClipFinderScreen(
    source: String,
    onBack: () -> Unit,
    onOpen: (ClipAnswer, Long) -> Unit = { _, _ -> },
    onShow: (ShowGuess) -> Unit = {},
) {
    val colors = MaterialTheme.nuvio.colors
    val current by ClipFinderSession.state.collectAsStateWithLifecycle()
    val state = if (current.source == source) current else ClipFinderState(source = source)
    var afterClip by rememberSaveable { mutableStateOf(false) }
    val uriHandler = LocalUriHandler.current
    val openVideo: (ClipVideoAnswer, Long) -> Unit = { video, startMs ->
        runCatching { uriHandler.openUri(ClipYouTube.openUrl(video.video.id, startMs)) }
    }
    LaunchedEffect(source) { ClipFinderSession.start(source) }
    LaunchedEffect(state.openYouTube) {
        val first = state.youtube.firstOrNull()
        if (state.openYouTube && first != null) {
            ClipFinderSession.youTubeOpened()
            openVideo(first, clipStartMs(first.candidate, afterClip))
        }
    }

    NuvioScreen {
        item { NuvioScreenHeader(title = CLIP_FINDER_TITLE, onBack = onBack) }
        item {
            NuvioSurfaceCard {
                NuvioSectionLabel(if (isClipFile(source)) "Shared video" else "Shared link")
                Text(clipSourceLabel(source), style = MaterialTheme.typography.bodyMedium, color = colors.textPrimary)
            }
        }
        item { ClipStagesCard(state) }
        if (state.failed) {
            item { ClipFailureCard(state, onRetry = { ClipFinderSession.start(source, restart = true) }) }
        }
        if (state.answers.isNotEmpty()) {
            item { ClipAnswersCard(state.answers, afterClip, onAfterClip = { afterClip = it }, onOpen = onOpen) }
        }
        if (state.youtube.isNotEmpty()) {
            item { ClipYouTubeCard(state.youtube, afterClip, onOpen = openVideo) }
        }
        if (state.shows.isNotEmpty()) {
            item { ClipShowsCard(state.shows, onShow) }
        }
        if (clipCanType(state)) {
            item { ClipTypeCard(heard = !state.noClip, onSearch = { ClipFinderSession.searchTyped(it) }) }
        }
        if (state.notes.isNotEmpty()) {
            item { ClipNotesCard(state.notes) }
        }
        if (state.lines.isNotEmpty()) {
            item { ClipLinesCard(state.lines) }
        }
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderParts.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.nuvio.app.core.ui.Chip
import com.nuvio.app.core.ui.NuvioInputField
import com.nuvio.app.core.ui.NuvioPrimaryButton
import com.nuvio.app.core.ui.NuvioSectionLabel
import com.nuvio.app.core.ui.NuvioSurfaceCard
import com.nuvio.app.core.ui.nuvio

@Composable
internal fun ClipStagesCard(state: ClipFinderState) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Steps")
        CLIP_FINDER_STAGES.forEachIndexed { index, stage ->
            val mark = clipStageMark(state, index)
            Text(
                text = "${index + 1}. $stage" + if (mark.isEmpty()) "" else " ($mark)",
                style = MaterialTheme.typography.bodyMedium,
                color = if (mark == "now" || mark == "failed") colors.textPrimary else colors.textMuted,
            )
        }
        if (state.progress.isNotBlank()) {
            Text(state.progress, style = MaterialTheme.typography.bodyMedium, color = colors.textPrimary)
        }
    }
}

@Composable
internal fun ClipFailureCard(state: ClipFinderState, onRetry: () -> Unit) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Stopped at: ${CLIP_FINDER_STAGES.getOrElse(state.stage.ordinal) { "" }}")
        Text(state.message, style = MaterialTheme.typography.bodyMedium, color = colors.textPrimary)
        if (state.showFileHint) {
            Text(ClipMessages.FILE_HINT, style = MaterialTheme.typography.bodyMedium, color = colors.textMuted)
        }
        NuvioPrimaryButton(text = "Try again", modifier = Modifier.padding(top = 8.dp), onClick = onRetry)
    }
}

@Composable
internal fun ClipAnswersCard(
    answers: List<ClipAnswer>,
    afterClip: Boolean,
    onAfterClip: (Boolean) -> Unit,
    onOpen: (ClipAnswer, Long) -> Unit,
) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Found (tap one, then pick a stream)")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(vertical = 8.dp)) {
            Chip(label = "From clip start", selected = !afterClip, onClick = { onAfterClip(false) })
            Chip(label = "After the clip", selected = afterClip, onClick = { onAfterClip(true) })
        }
        answers.forEach { answer ->
            val startMs = clipStartMs(answer.candidate, afterClip)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onOpen(answer, startMs) }
                    .padding(vertical = 8.dp),
            ) {
                Text(clipAnswerTitle(answer), style = MaterialTheme.typography.titleMedium, color = colors.textPrimary)
                Text(
                    text = clipAnswerDetail(answer) + ". Plays from ${clipClock(startMs)}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = colors.textMuted,
                )
            }
        }
    }
}

/** YouTube videos whose captions hold the clip; a tap opens the YouTube app at the moment. */
@Composable
internal fun ClipYouTubeCard(videos: List<ClipVideoAnswer>, afterClip: Boolean, onOpen: (ClipVideoAnswer, Long) -> Unit) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("On YouTube (tap to open the YouTube app)")
        videos.forEach { video ->
            val startMs = clipStartMs(video.candidate, afterClip)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onOpen(video, startMs) }
                    .padding(vertical = 8.dp),
            ) {
                Text(clipVideoTitle(video), style = MaterialTheme.typography.titleMedium, color = colors.textPrimary)
                Text(
                    text = clipMatchDetail(video.candidate) + ". Opens at ${clipClock(startMs)}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = colors.textMuted,
                )
            }
        }
    }
}

/** Shows named by the caption when the clip itself could not be heard; a tap opens the show's page. */
@Composable
internal fun ClipShowsCard(shows: List<ShowGuess>, onShow: (ShowGuess) -> Unit) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Open the show and pick the episode")
        shows.forEach { show ->
            Text(
                text = show.name,
                style = MaterialTheme.typography.titleMedium,
                color = colors.textPrimary,
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onShow(show) }
                    .padding(vertical = 8.dp),
            )
        }
    }
}

/**
 * The show name typed here is searched with what was already heard: nothing is read or listened to again.
 * When nothing could be heard ([heard] false) it only finds the show to open.
 */
@Composable
internal fun ClipTypeCard(heard: Boolean, onSearch: (String) -> Unit) {
    val colors = MaterialTheme.nuvio.colors
    var name by rememberSaveable { mutableStateOf("") }
    NuvioSurfaceCard {
        NuvioSectionLabel("Know the show? Type its name")
        Text(
            text = if (heard) "Nuvio searches it with what it already heard. Nothing is listened to again." else "Nuvio finds the show so you can open it.",
            style = MaterialTheme.typography.bodySmall,
            color = colors.textMuted,
        )
        NuvioInputField(
            value = name,
            onValueChange = { name = it.take(80) },
            placeholder = "Show or movie name",
            modifier = Modifier.padding(vertical = 8.dp),
        )
        NuvioPrimaryButton(text = "Search this show", enabled = name.isNotBlank(), onClick = { onSearch(name) })
    }
}

@Composable
internal fun ClipNotesCard(notes: List<ClipNote>) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Details (for a screenshot if something fails)")
        notes.forEach { note ->
            Text("${note.label}: ${note.value}", style = MaterialTheme.typography.bodySmall, color = colors.textMuted)
        }
    }
}

@Composable
internal fun ClipLinesCard(lines: List<ClipLine>) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Heard (first lines)")
        lines.take(6).forEach { line ->
            Text("${clipClock(line.startMs)}  ${line.text}", style = MaterialTheme.typography.bodySmall, color = colors.textMuted)
        }
    }
}
```

##### File: `iosApp/iosApp/ClipFinder/ClipPageReader.swift`
```swift
import Foundation
import UIKit
import WebKit

struct ClipPageResult {
    let pageJson: String?
    let error: String?
    let cookies: [HTTPCookie]
    let userAgent: String
}

/// Loads the shared link in an off-screen web view (the normal iOS web view, nothing faked) and hands
/// back what the page says about itself as JSON text; Kotlin (ClipPageParser) reads it. Any script that
/// names "video_url" or "video_versions" (Instagram) is also handed back whole under "raw", whatever its
/// type, so Kotlin can find the video address in it.
/// One reader per link. Call it on the main thread only; it answers on the main thread, once.
final class ClipPageReader {
    private static let maxPolls = 25
    private static let script = #"""
    (function () {
      var out = { url: location.href, title: document.title || '', metas: {}, videos: [], scripts: [], raw: [] };
      var known = false;
      if (location.protocol !== 'http:' && location.protocol !== 'https:') { return ''; }
      try {
        var metas = document.querySelectorAll('meta[property], meta[name]');
        for (var i = 0; i < metas.length; i++) {
          var key = metas[i].getAttribute('property') || metas[i].getAttribute('name') || '';
          if (key.indexOf('og:') === 0 || key.indexOf('twitter:') === 0 || key === 'description') {
            out.metas[key] = metas[i].getAttribute('content') || '';
          }
        }
      } catch (e) {}
      try {
        var videos = document.querySelectorAll('video, video source');
        for (var j = 0; j < videos.length; j++) {
          var list = [videos[j].currentSrc, videos[j].src];
          for (var k = 0; k < list.length; k++) {
            var address = list[k];
            if (address && address.indexOf('http') === 0 && out.videos.indexOf(address) < 0) {
              out.videos.push(address);
              known = true;
            }
          }
        }
      } catch (e) {}
      try {
        var scripts = document.querySelectorAll('script');
        var total = 0;
        var rawTotal = 0;
        for (var s = 0; s < scripts.length; s++) {
          var type = (scripts[s].type || '').toLowerCase();
          var id = scripts[s].id || '';
          var named = id === '__UNIVERSAL_DATA_FOR_REHYDRATION__' || id === 'SIGI_STATE' || id === '__NEXT_DATA__';
          var text = scripts[s].textContent || '';
          var media = text.indexOf('video_url') >= 0 || text.indexOf('video_versions') >= 0;
          if (media && rawTotal + text.length <= 2000000) {
            rawTotal += text.length;
            out.raw.push(text);
            continue;
          }
          if (!named && type.indexOf('json') < 0) { continue; }
          if (text.length < 20 || total + text.length > 3000000) { continue; }
          total += text.length;
          out.scripts.push(text);
          if (named) { known = true; }
        }
      } catch (e) {}
      var state = known ? '1' : (document.readyState === 'complete' ? '2' : '0');
      return state + JSON.stringify(out);
    })()
    """#

    private var webView: WKWebView?
    private var polls = 0
    private var lastPayload: String?
    private var finished = false
    private var note: ((String, String) -> Void)?
    private var completion: ((ClipPageResult) -> Void)?

    func read(link: String, note: @escaping (String, String) -> Void, completion: @escaping (ClipPageResult) -> Void) {
        self.note = note
        self.completion = completion
        guard let url = URL(string: link), let scheme = url.scheme?.lowercased(), scheme == "http" || scheme == "https" else {
            finish(page: nil, error: "This is not a web link.", cookies: [], userAgent: "")
            return
        }
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = WKWebsiteDataStore.nonPersistent()
        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = .all
        let view = WKWebView(frame: CGRect(x: 0, y: 0, width: 390, height: 844), configuration: configuration)
        view.isUserInteractionEnabled = false
        view.alpha = 0.01
        if let window = ClipPageReader.keyWindow() {
            window.insertSubview(view, at: 0)
        }
        webView = view
        view.load(URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 20))
        schedulePoll()
    }

    func cancel() {
        finished = true
        completion = nil
        note = nil
        closeWebView()
    }

    private static func keyWindow() -> UIWindow? {
        var fallback: UIWindow?
        for scene in UIApplication.shared.connectedScenes {
            guard let windowScene = scene as? UIWindowScene else { continue }
            for window in windowScene.windows {
                if window.isKeyWindow { return window }
                if fallback == nil { fallback = window }
            }
        }
        return fallback
    }

    private func schedulePoll() {
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { [weak self] in
            self?.poll()
        }
    }

    private func poll() {
        guard !finished, let view = webView else { return }
        polls += 1
        view.evaluateJavaScript(ClipPageReader.script) { [weak self] value, _ in
            let text = value as? String
            DispatchQueue.main.async {
                self?.handle(text)
            }
        }
    }

    private func handle(_ text: String?) {
        guard !finished else { return }
        if let text = text, text.count > 1 {
            lastPayload = String(text.dropFirst())
            let state = String(text.prefix(1))
            if (state == "1" && polls >= 3) || (state == "2" && polls >= 6) {
                finishWithPage()
                return
            }
        }
        if polls >= ClipPageReader.maxPolls {
            finishWithPage()
            return
        }
        schedulePoll()
    }

    private func finishWithPage() {
        guard let payload = lastPayload, let view = webView else {
            note?("Page loaded", "no")
            finish(page: nil, error: "The page did not load. Check the connection; the site may also have blocked the request.", cookies: [], userAgent: "")
            return
        }
        note?("Page loaded", "yes, after \(polls) s")
        view.evaluateJavaScript("navigator.userAgent") { [weak self] value, _ in
            let agent = (value as? String) ?? ""
            view.configuration.websiteDataStore.httpCookieStore.getAllCookies { cookies in
                DispatchQueue.main.async {
                    self?.finish(page: payload, error: nil, cookies: cookies, userAgent: agent)
                }
            }
        }
    }

    private func finish(page: String?, error: String?, cookies: [HTTPCookie], userAgent: String) {
        guard !finished else { return }
        finished = true
        let done = completion
        completion = nil
        note = nil
        closeWebView()
        done?(ClipPageResult(pageJson: page, error: error, cookies: cookies, userAgent: userAgent))
    }

    private func closeWebView() {
        webView?.stopLoading()
        webView?.removeFromSuperview()
        webView = nil
    }
}
```

#### I. On the phone (after the Mac build), risks, and what the screen shows
Try it (no new permission prompt):
1. A clip cut from a YouTube interview or podcast (not a show). Expected: "Done", the YouTube app opens by itself
   at about the clip's moment; back in Nuvio the YouTube card stays. Details: `YouTube searches`, `YouTube captions`,
   `YouTube match`, `Timings`.
2. A show clip that is also on YouTube: episode cards first, YouTube card below, nothing opens by itself.
3. The Instagram reel that failed: Details `Instagram: page: ... ; embed download: ...` shows each try. Either it
   listens, or the message offers the show named in the caption; tapping it opens the show's page.
4. The Modern Family clip: `Fetched while listening: Modern Family: N subtitle files` (if its hashtag scores 90+),
   `Match: ...`, and `Timings` with `prefetch ... beside`. Compare `subtitles` with the build-3 run.
5. A saved video from Files, no caption: type the show; "Listening" does not run again (7a's open check).
Send a screenshot of the whole screen including Details for each.

Top ways it can fail, and what the screen then shows:
1. `YouTube captions: <id> failed` or `unreadable` for every video: YouTube refused the "ANDROID" player request
   (the 65% row of decision 5). Fix in Kotlin only: change `ANDROID_CLIENT_VERSION` or the client name to what
   youtube-transcript-api uses then (check its current source first).
2. `captions need YouTube's token` for every video: YouTube now asks for a token on all captions; the route is dead
   until another one is found (Later). Episode search is unaffected.
3. `YouTube searches: "...": 0` everywhere: the results page shape changed (`ytInitialData` or the consent cookie).
   Check the HTTP status in the same line first.
4. The YouTube app does not open (Safari does, or nothing): the universal link was not handed to the app. A tap on
   the card still opens the video in Safari at the moment.
5. Instagram: all three tries `video key no`: logged-out reels no longer carry the address anywhere we look; the
   show offer (decision 9) is what remains. GraphQL route is under Later.
6. A wrong YouTube video can only appear if its captions share the clip's phrases (the same rule as episodes). If
   one appears, send its `YouTube match` line.

ASSUMPTIONS (cannot be checked from here)
- D1 The Kotlin compiles; it uses only what 7a uses plus `io.ktor.http.encodeURLParameter` (Ktor, already a
  dependency) and the upstream `httpRequestRaw` / `httpPostJsonWithHeaders`.
- D2 `httpRequestRaw` with `maxResponseBodyBytes = 6 MB` either returns the first 6 MB or throws on a larger answer;
  a throw is a "failed" line. YouTube results pages were about 1 MB when yt-dlp's tests were written (not measured).
- D3 The key names and confidences of decisions 5 and 7, read from tool sources, not from live pages.
- D4 Reading YouTube's pages without its app is, like reading TikTok's (SPEC A2), against the site's terms on paper;
  nothing is downloaded but captions and pages, nothing is stored but the subtitle cache.
- D5 `LocalUriHandler.openUri` on iOS hands an https link to `UIApplication.open` (CMP 1.13), so the universal link
  reaches the YouTube app.
- D6 The prefetch's extra requests during listening do not slow the clip's own download noticeably (listening
  starts after the download).

- [ ] **7f. Speed-ups (PR #6, 2026-11-18)** Fable ideas, Sonnet built, Opus reviewed. Search while listening
  (warms caches), sliding window of 6 subtitle files, parallel show guesses, answer shown before YouTube, stop listening
  early on a decisive match whose start is in the first 8 s, disk-cached subtitles matched first, episode lists cached
  1 day and "no English file" 7 days, top shows interleaved, Instagram embed beside the page read, iOS 26
  SpeechAnalyzer with the old engine as fallback. Tick after Mo's phone check (Timings line, Modern Family still found).

- [ ] **7g. Cut-up clips (2026-11-18)** Mo: still find the show when parts in the middle are cut out.
  `ClipMatcher` also counts the longest run of hits in clip order (hops up to 3 min) as a scene; no
  extra network or audio work, about 2 ms more per 24 episodes on a laptop. Tests: single lines a
  minute apart, middle cut out, wrong order, too far apart, stray opener, scattered lines in a wrong
  episode. Tick after Mo's phone check with a cut-up clip.

- [ ] **8. Arabic** (after v1 ships; Mo wants it). Speech locale picked from the show's
  language or a setting; Arabic subtitles from OpenSubtitles; Arabic text normalising
  (diacritics, letter forms). Test clip: Love Is Blind: Habibi (on Mo's Mac).

### Milestone 7e implementation notes (written 2026-11-16)
Checked against the work tree as it is on TestFlight (7c-7d, PR #3 head de8c2cd). Same rules as the 7c-7d notes:
paths are inside `../nuvio-work` unless they start with `fork/` or `docs/`; `K` = `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder`,
`T` = the same package under `commonTest`. Where these notes differ from older text, these notes win. One Mac build
(build 5). These notes sit after milestone 8 on purpose: the 7c script reads up to "- [ ] **8." and must still find
exactly its 20 blocks.

Not checked here: nothing below was compiled or run (no Kotlin or Gradle in the cloud workspace). The alignment
numbers of `ClipAlignTest` and the release names of `ClipStreamRankTest` were run as a Python copy; every other test
value was traced by hand. The edit script of section G was run on copies of the 10 files it edits (all 24 texts found
exactly once). Kotlin errors show in "Fork check".

#### A. Decisions
1. What the subtitles carry (checked 2026-11-16 in the source of open-source Stremio clients and add-on code read
   from raw.githubusercontent.com; opensubtitles-v3.strem.io itself answers 403 from the cloud workspace): OpenSubtitles
   v3, Mo's add-on (SPEC A1), answers `{"subtitles":[{"id","url","lang"}]}`, sometimes with `SubEncoding`, and marks a
   file found by the video's hash with `"m":"h"`. No release name, no file name, no frame rate (about 80% sure).
   Nuvio's own reader (`loadAddonSubtitles`) keeps only id, url and lang, and on iOS `computeVideoHash` returns null,
   so Nuvio never sends a hash it worked out itself; only a hash the stream add-on gives (`behaviorHints.videoHash`)
   is sent. Clip finder now reads the add-on answers itself (`ClipSubtitleList`): url, language, a release name under
   any of six common keys, and the hash mark. Details `Matched subtitle` shows on the phone what was really sent;
   "OpenSubtitles v3: no release name given" is the expected line.
2. Best-match streams, only in a list opened from Clip finder (`launch.clipStartMs != null`, not a download):
   - With a release name for the matched file: same source family (web, bluray, hdtv, dvd) 4, same group 3, same
     resolution family 1; a stream needs 3. That is the "same release" rule Mo asked for.
   - Without one (the expected case, decision 1), nothing tells which release a stream lines up with, and a guess
     dressed as "same release" would be dishonest. The honest alternative: prefer the streams whose start the player
     can check exactly, its own English subtitles 3 (the check reads them, decision 3) and a file hash 2 (the add-ons
     can find a file by hash, `"m":"h"`); a stream needs 2. `Stream order` then says "own subtitles or a file hash
     (the matched subtitle has no release name)", or "order unchanged" and why.
   - The best stream is pinned in the slot a party guest's shared stream uses (`LocalSharedStream`, header "Best match
     for the clip"; a real party stream still wins) and up to 5 best streams are tagged "Best match" through
     `LocalStreamHighlight` (the party's own label still wins). Nothing is reordered: a full reorder needs an edit
     inside `StreamsScreen` (Later). Other stream lists get null and look exactly as before.
3. The play-time check (`ClipPlayCheck`), the hook and when it may seek:
   - Data: on a tap, the answer is kept in memory (`ClipPlayTargets.arm`): the episode, up to 12 anchor lines (4+
     words, from 30 s before to 30 s after the matched span, spread evenly), the matched file's url and release.
   - Hook: one call after `runtime.BindPlayerRuntimeEffects()` in `PlayerScreenContent.kt`, the narrowest place that
     sees the args, the position, the player's own first seek and `seekTo`. Everything else is in clipfinder/. It runs
     only for the player launch whose title, season, episode and start time equal the armed answer, once per launch.
   - Which file is "this video's": the stream's own English subtitles (http), else the add-ons' English file found by
     this file's hash, else their first English file when asked with this file's name, size and hash. When that is
     the file the clip was matched with, the times already agree: no seek. When it is just the add-on's usual first
     file (the answer without the file's details), the add-on ignored the details: no seek ("the add-ons gave their
     usual list, not one for this file"). No name, size or hash: "Kept the clip time: no subtitles for this video".
   - Alignment (`ClipAlign`, pure): each anchor is found in this video's file by the matcher's word triples (a
     subtitle line split differently still counts); a line found more than 10 s apart is a repeated line and is
     skipped. Speeds tried: same, 23.976 frames a second played at 25 (4.3% faster) and back; the speed with the most pairs within
     2.5 s of each other wins, the same speed wins a tie; at least 2 pairs and half of all. The new time is the
     median of what the pairs say. Seek only when the shift is 1 s to 5 min.
   - Seeking: it waits until the player has done its own first seek, is not loading, plays the stream it opened and
     is near the clip time (3 s before to 20 s after). Then it seeks once. A jump of more than 3 s back, or forward
     more than twice the time passed plus 3 s (hold-to-speed plays at 2x), before that moment means Mo moved: no
     seek. After 60 s it gives up. Every outcome is a 4 s toast plus `Player` and `Player subtitles` in Details.
4. Lead-in 15 s (was 10 s): releases differ by a few seconds and sometimes 5-10 s (SPEC A3); with 10 s, a video whose
   lines come 8 s earlier than in the matched file started 2 s before the line, too little to catch the scene; the first line heard is often a
   moment into the scene; 15 s still puts the scene on screen within SPEC 5's 20 s, and more makes Mo wait. Where the
   check works it moves to the same 15 s before the matching line, so the two do not add up.
5. Pick list (`ClipShowPicker`): from 2 letters, 350 ms after the last key (the effect restarts on each key, so an
   older ask is cancelled), known titles (shows of earlier clips, popular catalog titles, fetched once per app start)
   scored with `ClipNames.typedScore`, plus up to 8 results of `clipSearchShows` (the finder's own search) scored
   `max(typedScore, 80 - rank)` as in `ClipShowFinder`; one entry per id, the catalog's (poster, year) kept; 8 shown.
   A tap runs `searchTyped(name, show)`: `ClipClues.picked` makes `ClipShowFinder` return that show alone (score 110,
   "picked"), so nothing else is searched. After a clip that could not be heard a tap opens the show (as before).
   The button "Search this show" stays for when the catalogs do not answer.
6. Honest Details: `Matched subtitle` says "<add-on>: <release or no release name given>", or "from an earlier run's
   cache (add-on and release not known)" for cues cached before 7e (no record line); the cache now starts with one
   line `R<TAB>url<TAB>release<TAB>add-on`, which the old cue reader skips. A new typed search clears `Matched
   subtitle`, `Stream order`, `Player` and `Player subtitles`.

#### B. Contract
No Swift, no `ClipFinderNative.kt` change (still 17 functions). Upstream calls added: `addonSubtitleRequests` with
`extras` and `fetchAddonResponseText` (both internal, same module) instead of `loadAddonSubtitles`;
`PlayerScreenRuntime` fields `playbackSnapshot`, `initialSeekApplied`, `activeSourceUrl`, `playerController`;
`PlayerScreenArgs.launchId/parentMetaId/seasonNumber/episodeNumber/initialPositionMs/subtitleExtras/externalSubtitles`;
`LocalSharedStream`, `LocalStreamHighlight`, `SharedStream`. New Details lines: `Matched subtitle`, `Stream order`,
`Player`, `Player subtitles`.

#### C. Files
| Worker | File | What |
|---|---|---|
| 1 | new `K/ClipAlign.kt`, `T/ClipAlignTest.kt` | anchors, pairs, speeds, median (decision 3) |
| 1 | new `K/ClipPlayCheck.kt`, `T/ClipPlayCheckTest.kt` | `ClipPlayTarget(s)`, `ClipSeekWatch`, file choice, decide, notes |
| 1 | new `K/ClipSubtitleList.kt`, new `K/ClipStreamRank.kt`, `T/ClipStreamRankTest.kt` | add-on answer reader; release names and ranking (decisions 1, 2) |
| 1 | new `K/ClipShowPicker.kt`, `T/ClipShowPickerTest.kt` | pick list, `clipYear`, `clipPickDetail` (decision 5) |
| 1 | edited `ShowGuesser.kt`, `ClipNames.kt`, `ClipShowFinder.kt`, `EpisodeSubtitleSource.kt`, `ClipFinderState.kt`, `T/ClipFinderStateTest.kt` | section G "models" |
| 2 | rewritten `K/ClipShowSearch.kt` | answers carry episode, anchors, file; `Matched subtitle` |
| 2 | rewritten `K/ClipFinderSession.kt` | `searchTyped(name, picked)`, `pickShows`, `note`, year, `clipListSubtitles` with extras |
| 2 | rewritten `K/ClipFinderScreen.kt`, `K/ClipFinderParts.kt` | arm on tap; pick list in the type card |
| 2 | new `K/ClipPlayerHooks.kt` | the player and stream-list hooks |
| 2 | edited `ClipFinderPipeline.kt`, `T/ClipFinderPipelineTest.kt`, upstream `PlayerScreenContent.kt`, `StreamDestination.kt` | section G "pipeline", "tests", "player", "streams" |

14 blocks in section H. Every new or rewritten file is under 300 lines; `ClipFinderPipeline.kt` grows from 345 to 347
(already under Later).

#### D. Steps, one worker after the other in the same work tree
Never hand-type the files. This script copies the "File:" blocks of THIS section only (from its header to
"## Later"). Paste as it stands:
```bash
cat > /tmp/clip7e_files.py <<'PY'
import re, sys, os
mode, plan, tree = sys.argv[1], sys.argv[2], sys.argv[3].rstrip("/")
only = sys.argv[4:]                                    # optional: path fragments to limit to
text = open(plan, encoding="utf-8").read()
text = text[text.index("### Milestone 7e implementation notes"):text.index("\n## Later")]
blocks = re.findall(r"^##### File: `([^`]+)`\n```[a-z]*\n(.*?)\n```$", text, re.M | re.S)
assert len(blocks) == 14, "expected 14 file blocks, found %d" % len(blocks)
bad = 0
for path, body in blocks:
    if only and not any(o in path for o in only): continue
    full, body = os.path.join(tree, path), body + "\n"
    if mode == "write":
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w", encoding="utf-8").write(body)
        print("wrote", path)
    elif not os.path.exists(full) or open(full, encoding="utf-8").read() != body:
        bad += 1; print("DIFFERENT", path)
if mode == "check": print("all files match the plan" if not bad else "%d files differ" % bad); sys.exit(1 if bad else 0)
PY
```
0. Everyone: `fork/dev-tree.sh` (the work tree must hold 7c-7d: `grep -c "Fetched while listening" ../nuvio-work/composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/*.kt | grep -v ":0"`
   lists at least one file), save the two scripts (this one and `/tmp/clip7e_edits.py` of section G), and
   `git -C ../nuvio-work status --porcelain > /tmp/clip7e_before.txt`.
1. Worker 1 (pure logic, models, tests): `python3 /tmp/clip7e_files.py write docs/PLAN.md ../nuvio-work ClipAlign ClipPlayCheck ClipSubtitleList ClipStreamRank ClipShowPicker`
   (9 files: each name also matches its test), then `python3 /tmp/clip7e_edits.py ../nuvio-work models`. Read the
   five Kotlin files against decisions 1-5 and follow each `assertEquals` of the four test files by hand once. Report
   any value you cannot reproduce; do not "fix" a test. The tree does not compile between worker 1 and worker 2
   (`ClipShowSearch` and the session still use the old shapes): fine.
2. Worker 2 (glue, screen, hooks): `python3 /tmp/clip7e_files.py write docs/PLAN.md ../nuvio-work ClipShowSearch ClipFinderSession ClipFinderScreen ClipFinderParts ClipPlayerHooks`
   (5 files), then `python3 /tmp/clip7e_edits.py ../nuvio-work pipeline tests player streams`. Then run the
   pre-flight (F) and `fork/dev-tree.sh save`.
3. Lead: commit `fork/nuvio-share-resume.patch` + docs, push, wait for "Fork check". Kotlin errors are fixed in the
   work tree (then save again); a test is never weakened: if a traced value was wrong, find out which side is wrong
   first. Then `gh workflow run TestFlight --ref clip-finder-share` (one Mac build, about 70 min).
4. When green on the phone: tick 7e; `docs/ARCHITECTURE.md`: data flow gets "play-time check: the add-ons' file for
   this video, the clip's lines found in it, one seek"; decisions log: "Lead-in 15 s", "Re-anchor at play time with
   the matched lines, once, never after Mo seeks", "Best match by release name when the add-on sends one, else by
   what the player can check (OpenSubtitles v3 sends no release name)", "Pick list from search plus known titles".

#### E. Tests (all four new test files are given in full in section H; all data made up)
- `ClipAlignTest` (6): anchors (12 of 24 lines with 4+ words, 72 s to 168 s, a 2-word line left out; 9 near the
  start); offset (a release 3.2 s later: 12 pairs, same speed, 85 s -> 88.2 s); speed (lines 60-280 s, PAL speed and
  5 s later: PAL wins with 12 pairs, 45 s -> 48.157 s); a short span keeps the same speed; other words give null;
  a repeated line far away is skipped, an echo 1 s later counts once (earliest), and 2 anchors with 1 repeated give null.
- `ClipPlayCheckTest` (9, virtual time): one seek to 88.2 s after the player reached the clip time, note
  "+3.2 s", detail "Sample Subs: picked for this file (release: none given)", both lists asked; Mo moves first:
  no seek; own subtitles 0.4 s off: "agree (+0.4 s)", no seek; no file details: no download, no seek; the matched
  file comes back: "are the file Nuvio matched with"; other words: "not in this video's subtitles"; the player never
  arrives: given up after 60 s; the file choice rules one by one; signed seconds, speed note, a 6:40 shift refused;
  `ClipPlayTargets` once per launch and only for its own launch.
- `ClipStreamRankTest` (7): release names (web/GRP/hd, bluray, hdtv/XYZ, DDP5.1 H.264-GRP, 4K, digits only, empty);
  ranking with a release name (the same release pinned and alone tagged; without it, same source family and
  resolution next), no stream of that release (order unchanged), without a release name (own subtitles first, two
  tagged, hash next, French or file:// subtitles do not count, none: unchanged), at most 5 tagged; the add-on answer
  reader (hash mark, `releaseName`, entry without url, not an object, not JSON); the cache's file record (tab taken
  out, cues still read, older entries give null).
- `ClipShowPickerTest` (6): "modernfam" gives the known show with the catalog's poster and year, then a search
  result; fewer than 2 letters ask nothing; a failing search or failing known list still lists the other; at most 8,
  stable order; a picked show is the finder's only suspect with no search; year and kind text.
- Changed (section G, nothing removed): `ClipFinderPipelineTest` labels gain `"Matched subtitle"` after
  `"Candidates"`; new test "a show picked in the list is searched alone, and the answer carries what the player
  checks" (no new search, listened once, episode `tt001:2:5`, 1-12 anchors within 30 s of the match, file url,
  `add-on: no release name given`). `ClipFinderStateTest`: the lead-in test expects 235 000 (250 000 - 15 000).
`ClipFinderPipelineWebTest`, `EpisodeSubtitleSourceTest`, `ClipShowFinderTest` and the rest stay green unchanged
(traced: new constructor parameters all come last with defaults; `runTyped(last, name) { }` still compiles with
`picked` defaulted; the old cue reader skips the record line).

#### F. Pre-flight before pushing
```bash
W=../nuvio-work; K=$W/composeApp/src/commonMain/kotlin/com/nuvio/app
python3 /tmp/clip7e_files.py check docs/PLAN.md $W                    # all files match the plan
git -C $W status --porcelain | diff /tmp/clip7e_before.txt -            # exactly one line: > M .../features/player/PlayerScreenContent.kt
grep -c "ClipPlayerCheck(" $K/features/player/PlayerScreenContent.kt    # 1
grep -c "clipPick" $K/StreamDestination.kt                              # 3
grep -rn "Dispatchers.IO\|AIza\|api[_-]key" $K/features/clipfinder/     # prints nothing
wc -l $K/features/clipfinder/*.kt | awk '$1 > 300 && $2 != "total"'     # only ClipFinderPipeline.kt
python3 - $K <<'PY'                                                   # the bridge is unchanged
import re, sys
k = open(sys.argv[1] + "/features/clipfinder/ClipFinderNative.kt").read()
assert len(re.findall(r"^\s*fun ", k, re.M)) == 17, "ClipFinderNative.kt must still declare exactly 17 functions"
print("contract OK")
PY
fork/dev-tree.sh save
```
What each check proves: Fork check = all Kotlin compiles and the tests pass; nothing about the live add-ons or the
player. Mac build = the app builds. Phone = section I.

#### G. Edits to existing files
Run after writing the files. Exact replacements; the script stops if a text is not found exactly once:
```bash
cat > /tmp/clip7e_edits.py <<'PY'
import sys, os
tree, parts = sys.argv[1].rstrip("/"), set(sys.argv[2:])
A = "composeApp/src/commonMain/kotlin/com/nuvio/app"
K = A + "/features/clipfinder"
T = "composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder"
picked_test = '''    @Test
    fun `a show picked in the list is searched alone, and the answer carries what the player checks`() = runTest {
        val fake = FakeNative(lines = clipLines)
        val asked = mutableListOf<String>()
        val h = Harness(fake, search = { query -> asked += query; emptyList() })
        h.run("file:///x/clip.mp4")
        assertFailed(h, ClipStage.Searching, ClipMessages.NO_SHOW, fileHint = false)
        val searches = asked.size
        h.picked(ShowGuess("tt001", "series", "Made Up Show (picked)"))
        assertEquals(ClipStage.Done, h.last.stage)
        val top = h.last.answers.first()
        assertEquals("Made Up Show (picked)", top.show.name)
        assertEquals(searches, asked.size)
        assertEquals(1, fake.listenCalls)
        assertEquals("tt001:2:5", top.episode?.subtitleId)
        assertTrue(top.anchors.isNotEmpty() && top.anchors.size <= ClipAlign.MAX_ANCHORS)
        assertTrue(top.anchors.all { it.startTimeMs in (top.candidate.startMs - 30_000)..(top.candidate.endMs + 30_000) })
        assertEquals("https://subs.example.test/tt001:2:5.srt", top.subtitle?.url)
        assertEquals("add-on: no release name given", h.last.notes.first { it.label == "Matched subtitle" }.value)
    }

'''
edits = {
  "models": [
    (K + "/ShowGuesser.kt",
     "data class ShowGuess(val metaId: String, val type: String, val name: String, val poster: String? = null)",
     "data class ShowGuess(val metaId: String, val type: String, val name: String, val poster: String? = null, val year: String? = null)"),
    (K + "/ClipNames.kt",
     "    val typed: String = \"\",\n",
     "    val typed: String = \"\",\n    /** The show tapped in the pick list under \"Know the show?\": searched alone. */\n    val picked: ShowGuess? = null,\n"),
    (K + "/ClipShowFinder.kt",
     "    private suspend fun pick(clues: ClipClues, lines: List<ClipLine>, max: Int, onNote: (String, String) -> Unit): List<ClipSuspect> {\n",
     "    private suspend fun pick(clues: ClipClues, lines: List<ClipLine>, max: Int, onNote: (String, String) -> Unit): List<ClipSuspect> {\n"
     "        // Mo tapped the show in the pick list: no clue can know better.\n"
     "        clues.picked?.let { return listOf(ClipSuspect(it, PICKED_SCORE, \"picked\")) }\n"),
    (K + "/ClipShowFinder.kt",
     "        const val MAX_SHOWS = ClipNameCheck.MAX_SUSPECTS\n",
     "        const val MAX_SHOWS = ClipNameCheck.MAX_SUSPECTS\n        /** A show tapped in the pick list. */\n        const val PICKED_SCORE = 110\n"),
    (K + "/EpisodeSubtitleSource.kt",
     "data class ClipSubtitleLink(val url: String, val language: String)",
     "/**\n * One subtitle file an add-on lists. [source]: the add-on's name; [release]: its release name, when the add-on sends\n"
     " * one ([ClipSubtitleList]); [hashMatch]: the add-on found it by the video file's hash.\n */\n"
     "data class ClipSubtitleLink(\n    val url: String,\n    val language: String,\n    val source: String = \"\",\n"
     "    val release: String = \"\",\n    val hashMatch: Boolean = false,\n)"),
    (K + "/EpisodeSubtitleSource.kt",
     "runCatching { cache.write(key, encodeCues(cues)) }",
     "runCatching { cache.write(key, linkLine(link) + encodeCues(cues)) }"),
    (K + "/EpisodeSubtitleSource.kt",
     "    /** Null on a time-out or any failure; cancelling the search still cancels. */\n",
     "    /** The file an episode's cached cues came from; null for cues cached before 7e. */\n"
     "    fun usedLink(showId: String, videoId: String): ClipSubtitleLink? =\n"
     "        runCatching { cache.read(\"$showId/$videoId\") }.getOrNull()?.let { decodeLink(it) }\n\n"
     "    /** Null on a time-out or any failure; cancelling the search still cancels. */\n"),
    (K + "/EpisodeSubtitleSource.kt",
     "        }.toList()\n",
     "        }.toList()\n\n"
     "        /** The first line of a cache entry: R, url, release, add-on (tabs taken out). [decodeCues] skips it. */\n"
     "        fun linkLine(link: ClipSubtitleLink): String =\n"
     "            listOf(\"R\", link.url, link.release, link.source).joinToString(\"\\t\") { it.replace('\\t', ' ').replace('\\n', ' ') } + \"\\n\"\n\n"
     "        fun decodeLink(text: String): ClipSubtitleLink? {\n"
     "            val parts = text.lineSequence().firstOrNull()?.split('\\t') ?: return null\n"
     "            if (parts.size < 4 || parts[0] != \"R\" || parts[1].isBlank()) return null\n"
     "            return ClipSubtitleLink(parts[1], \"eng\", source = parts[3], release = parts[2])\n"
     "        }\n"),
    (K + "/ClipFinderState.kt",
     "import kotlin.math.roundToInt\n",
     "import com.nuvio.app.features.player.SubtitleSyncCue\nimport kotlin.math.roundToInt\n"),
    (K + "/ClipFinderState.kt",
     "    val thumbnail: String? = null,\n)\n\ndata class ClipFinderState(",
     "    val thumbnail: String? = null,\n"
     "    /** The episode the answer is in; the player's check asks the subtitle add-ons for it ([ClipPlayCheck]). */\n"
     "    val episode: ClipEpisode? = null,\n"
     "    /** Up to 12 lines around the match, from the file it was matched with ([ClipAlign.anchors]). */\n"
     "    val anchors: List<SubtitleSyncCue> = emptyList(),\n"
     "    /** That file; null when its cues came from an older cache. */\n"
     "    val subtitle: ClipSubtitleLink? = null,\n)\n\ndata class ClipFinderState("),
    (K + "/ClipFinderState.kt",
     "internal const val CLIP_LEAD_IN_MS = 10_000L\n",
     "/**\n * Playback starts this long before the matched moment. Releases differ by a few seconds, sometimes 5-10, and the\n"
     " * first line heard is often a moment into the scene; 15 s still shows the scene within SPEC 5's 20 s. Where this\n"
     " * video's subtitles allow it, the player's check ([ClipPlayCheck]) moves to the matching line, keeping the 15 s.\n */\n"
     "internal const val CLIP_LEAD_IN_MS = 15_000L\n"),
    (K + "/ClipFinderState.kt",
     "/** Where playback starts: 10 s before the matched moment, or right after it. */",
     "/** Where playback starts: 15 s before the matched moment, or right after it. */"),
    (T + "/ClipFinderStateTest.kt",
     "    fun `playback starts ten seconds before the moment or right after it`() {\n        val found = candidate(250_000, 400_000)\n        assertEquals(240_000L,",
     "    fun `playback starts fifteen seconds before the moment or right after it`() {\n        val found = candidate(250_000, 400_000)\n        assertEquals(235_000L,"),
  ],
  "pipeline": [
    (K + "/ClipFinderPipeline.kt",
     "     * YouTube answers found before stay. After a clip that could not be heard it only finds the show.\n     */\n"
     "    suspend fun runTyped(previous: ClipFinderState, typed: String, emit: (ClipFinderState) -> Unit) {",
     "     * YouTube answers found before stay. After a clip that could not be heard it only finds the show.\n"
     "     * [picked]: the show tapped in the pick list; then only that show is searched.\n     */\n"
     "    suspend fun runTyped(previous: ClipFinderState, typed: String, picked: ShowGuess? = null, emit: (ClipFinderState) -> Unit) {"),
    (K + "/ClipFinderPipeline.kt",
     "            clues = previous.clues.copy(typed = typed.trim().take(MAX_TYPED)),",
     "            clues = previous.clues.copy(typed = typed.trim().take(MAX_TYPED), picked = picked),"),
    (K + "/ClipFinderPipeline.kt",
     "            \"Match\", \"Candidates\", \"Show from the caption\", \"Timings\",\n",
     "            \"Match\", \"Candidates\", \"Matched subtitle\", \"Show from the caption\", \"Timings\", \"Stream order\", \"Player\",\n"
     "            \"Player subtitles\",\n"),
  ],
  "tests": [
    (T + "/ClipFinderPipelineTest.kt",
     "\"Known titles\", \"Searches\", \"Show guesses\", \"Subtitles\", \"Match\", \"Candidates\", \"Timings\",",
     "\"Known titles\", \"Searches\", \"Show guesses\", \"Subtitles\", \"Match\", \"Candidates\", \"Matched subtitle\", \"Timings\","),
    (T + "/ClipFinderPipelineTest.kt",
     "        suspend fun typed(name: String) = pipeline().runTyped(last, name) { states += it }\n",
     "        suspend fun typed(name: String) = pipeline().runTyped(last, name) { states += it }\n\n"
     "        suspend fun picked(show: ShowGuess) = pipeline().runTyped(last, show.name, show) { states += it }\n"),
    (T + "/ClipFinderPipelineTest.kt",
     "    @Test\n    fun `no bridge`() = runTest {\n",
     picked_test + "    @Test\n    fun `no bridge`() = runTest {\n"),
  ],
  "player": [
    (A + "/features/player/PlayerScreenContent.kt",
     "import com.nuvio.app.core.ui.LocalFold\n",
     "import com.nuvio.app.core.ui.LocalFold\nimport com.nuvio.app.features.clipfinder.ClipPlayerCheck\n"),
    (A + "/features/player/PlayerScreenContent.kt",
     "        runtime.BindPlayerRuntimeEffects()\n",
     "        runtime.BindPlayerRuntimeEffects()\n"
     "        ClipPlayerCheck(\n"
     "            args,\n"
     "            position = { runtime.playbackSnapshot.positionMs },\n"
     "            ready = { runtime.initialSeekApplied && !runtime.playbackSnapshot.isLoading && runtime.activeSourceUrl == args.sourceUrl },\n"
     "        ) { runtime.playerController?.seekTo(it) }\n"),
  ],
  "streams": [
    (A + "/StreamDestination.kt",
     "import com.nuvio.app.features.streams.LocalStreamHighlight\n",
     "import com.nuvio.app.features.streams.LocalStreamHighlight\n"
     "import com.nuvio.app.features.clipfinder.clipPinned\n"
     "import com.nuvio.app.features.clipfinder.rememberClipHighlight\n"
     "import com.nuvio.app.features.clipfinder.rememberClipStreamPick\n"),
    (A + "/StreamDestination.kt",
     "            ?.let { SharedStream(label = sharedLabel, stream = it.toStreamItem()) }\n    }\n",
     "            ?.let { SharedStream(label = sharedLabel, stream = it.toStreamItem()) }\n    }\n"
     "    val clipPick = rememberClipStreamPick(\n"
     "        fromClip = launch.clipStartMs != null && !launch.downloadIntent,\n"
     "        groups = streamsUiState.takeIf { it.requestToken == expectedStreamsRequestToken }?.groups.orEmpty(),\n"
     "    )\n"),
    (A + "/StreamDestination.kt",
     "            LocalStreamHighlight provides streamHighlight,\n            LocalSharedStream provides sharedStream,\n",
     "            LocalStreamHighlight provides rememberClipHighlight(clipPick, streamHighlight),\n"
     "            LocalSharedStream provides (sharedStream ?: clipPinned(clipPick)),\n"),
  ],
}
for part in sorted(parts):
    for path, old, new in edits[part]:
        full = os.path.join(tree, path)
        text = open(full, encoding="utf-8").read()
        assert text.count(old) == 1, "%s: expected the old text once, found %d" % (path, text.count(old))
        open(full, "w", encoding="utf-8").write(text.replace(old, new))
        print("edited", path)
PY
```
Upstream files: `PlayerScreenContent.kt` gets one import and one call right after `runtime.BindPlayerRuntimeEffects()`
(nothing reformatted; the call does nothing unless the player was opened from a Clip finder answer).
`StreamDestination.kt` is already the fork's (it passes the clip start): 3 imports, one `val clipPick`, and the two
provider lines wrap the party values (party first, so a party behaves exactly as before). `ClipFinderStateTest` and
`ClipFinderPipelineTest` are the fork's own tests.

#### H. The files
Write them with the script of section D. The block header is the path inside the work tree.

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipAlign.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import com.nuvio.app.features.player.SubtitleSyncCue
import kotlin.math.abs
import kotlin.math.roundToLong

/**
 * Lines up two subtitle files of one episode: the file the clip was matched with, and a file made for the
 * video Mo plays, which may come from another release (a recap more or less, other cuts, ads, or 25 instead
 * of 23.976 frames a second). Lines are compared with [ClipText]'s words, like the matcher. Pure, no network.
 */
object ClipAlign {
    /** Lines shorter than this ("Yeah.", "What?") are said everywhere and are not used. */
    const val MIN_WORDS = 4
    const val MAX_ANCHORS = 12
    /** Anchors are taken from this long before the matched span to this long after it. */
    const val AROUND_MS = 30_000L
    /** Pairs whose offsets differ by at most this much agree with each other. */
    const val AGREE_MS = 2_500L
    /** A line found at places further apart than this is a repeated line ("previously on", a catch phrase): skipped. */
    const val SAME_PLACE_MS = 10_000L
    const val MIN_PAIRS = 2
    /** Speeds tried, same speed first: 23.976 played at 25 frames a second (the PAL speed-up, about 4%), and back. */
    val RATIOS = listOf(1.0, 23.976 / 25.0, 25.0 / 23.976)

    /** One line found in both files (a pair): its time in the matched file and in the video's file. */
    data class Hit(val anchorMs: Long, val targetMs: Long)

    /** The pairs that agree on one offset at one speed. [ratio] is video time per matched-file time. */
    data class Alignment(val pairs: List<Hit>, val ratio: Double) {
        /** A time of the matched file as a time of the video: the middle of what each agreeing pair says. */
        fun map(timeMs: Long): Long {
            val guesses = pairs.map { it.targetMs + ((timeMs - it.anchorMs) * ratio).roundToLong() }.sorted()
            return guesses[(guesses.size - 1) / 2]
        }
    }

    /** Up to 12 cues of 4+ words from 30 s before the matched span to 30 s after it, spread evenly over it. */
    fun anchors(cues: List<SubtitleSyncCue>, startMs: Long, endMs: Long): List<SubtitleSyncCue> {
        val near = cues.filter {
            it.startTimeMs in (startMs - AROUND_MS)..(endMs + AROUND_MS) && ClipText.normalize(it.text).size >= MIN_WORDS
        }
        if (near.size <= MAX_ANCHORS) return near
        return List(MAX_ANCHORS) { near[it * (near.size - 1) / (MAX_ANCHORS - 1)] }
    }

    /**
     * Where the [anchors] are in [target], or null when fewer than 2 lines are found or they do not agree.
     * The speed that lets the most pairs agree wins; on a tie the same speed wins (short clips cannot tell).
     */
    fun align(anchors: List<SubtitleSyncCue>, target: List<SubtitleSyncCue>): Alignment? {
        val found = pairs(anchors, target)
        if (found.size < MIN_PAIRS) return null
        var best: Alignment? = null
        for (ratio in RATIOS) {
            val agreeing = agreeing(found, ratio)
            val enough = agreeing.size >= MIN_PAIRS && agreeing.size * 2 >= found.size
            if (enough && (best == null || agreeing.size > best.pairs.size)) best = Alignment(agreeing, ratio)
        }
        return best
    }

    /**
     * Each anchor's place in [target]: the cue holding most of the anchor's word triples (at least half, and 2),
     * counting triples that run on into the next cue, since releases split lines differently. An anchor whose
     * best cues are more than 10 s apart is a repeated line and is skipped; close copies give the earliest.
     */
    fun pairs(anchors: List<SubtitleSyncCue>, target: List<SubtitleSyncCue>): List<Hit> {
        val words = target.map { ClipText.normalize(it.text) }
        val cuesOf = HashMap<String, MutableSet<Int>>()
        for (index in target.indices) {
            val run = words[index] + words.getOrElse(index + 1) { emptyList() }.take(2)
            for (triple in ClipText.triples(run)) cuesOf.getOrPut(triple) { mutableSetOf() } += index
        }
        return anchors.mapNotNull { anchor ->
            val triples = ClipText.triples(ClipText.normalize(anchor.text)).toSet()
            val votes = HashMap<Int, Int>()
            for (triple in triples) for (index in cuesOf[triple].orEmpty()) votes[index] = (votes[index] ?: 0) + 1
            val best = votes.values.maxOrNull() ?: return@mapNotNull null
            if (best < 2 || best * 2 < triples.size) return@mapNotNull null
            val times = votes.filterValues { it == best }.keys.map { target[it].startTimeMs }
            if (times.max() - times.min() > SAME_PLACE_MS) return@mapNotNull null
            Hit(anchor.startTimeMs, times.min())
        }
    }

    /** The pairs within 2.5 s of the middle offset, at [ratio]. */
    private fun agreeing(pairs: List<Hit>, ratio: Double): List<Hit> {
        fun offset(pair: Hit): Long = pair.targetMs - (pair.anchorMs * ratio).roundToLong()
        val offsets = pairs.map(::offset).sorted()
        val middle = offsets[(offsets.size - 1) / 2]
        return pairs.filter { abs(offset(it) - middle) <= AGREE_MS }
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipPlayCheck.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import com.nuvio.app.features.player.PlayerSubtitleCueParser
import com.nuvio.app.features.player.SubtitleRequestExtras
import com.nuvio.app.features.player.SubtitleSyncCue
import com.nuvio.app.features.streams.StreamSubtitle
import kotlin.coroutines.CoroutineContext
import kotlin.math.abs
import kotlin.math.roundToInt
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

/** A Clip finder answer as the player needs it. Times are times of the subtitle file the clip was matched with. */
data class ClipPlayTarget(
    val metaId: String,
    val season: Int?,
    val episode: Int?,
    val type: String,
    val subtitleId: String,
    val startMs: Long,
    val anchors: List<SubtitleSyncCue>,
    /** The file the clip was matched with; "" when its cues came from an older cache. */
    val matchedUrl: String,
    /** Its release name; "" when the add-on gives none. */
    val release: String,
)

/** The answer tapped last, in memory only. The stream list and the player look it up. */
object ClipPlayTargets {
    private var target: ClipPlayTarget? = null
    private val checked = mutableSetOf<Long>()

    fun arm(answer: ClipAnswer, startMs: Long) {
        target = ClipPlayTarget(
            metaId = answer.show.metaId,
            season = answer.candidate.season,
            episode = answer.candidate.episode,
            type = answer.episode?.type ?: answer.show.type,
            subtitleId = answer.episode?.subtitleId ?: answer.candidate.videoId,
            startMs = startMs,
            anchors = answer.anchors,
            matchedUrl = answer.subtitle?.url.orEmpty(),
            release = answer.subtitle?.release.orEmpty(),
        )
    }

    fun current(): ClipPlayTarget? = target

    /** The target when this player was started from it (same title, episode and start time); once per player launch. */
    fun forPlayer(launchId: Long?, metaId: String, season: Int?, episode: Int?, startMs: Long): ClipPlayTarget? {
        val armed = target ?: return null
        if (launchId == null || launchId in checked) return null
        if (armed.metaId != metaId || armed.season != season || armed.episode != episode || armed.startMs != startMs) return null
        checked += launchId
        return armed
    }
}

/** Where to seek (null: stay), the note for the screen and Details, and which subtitles were used ([detail]). */
data class ClipPlayPlan(val seekToMs: Long?, val note: String, val detail: String = "")

/**
 * Sees whether Mo moved himself after the player reached the clip time: a jump of more than 3 s backwards, or
 * forwards beyond twice the time passed (hold-to-speed plays at 2x) plus 3 s.
 */
class ClipSeekWatch(private val startMs: Long) {
    var landed = false
        private set
    var moved = false
        private set
    private var lastPositionMs = 0L
    private var lastWallMs = 0L

    fun sample(positionMs: Long, wallMs: Long) {
        if (moved) return
        if (!landed) {
            if (positionMs in (startMs - LAND_BEFORE_MS)..(startMs + LAND_AFTER_MS)) {
                landed = true
                lastPositionMs = positionMs
                lastWallMs = wallMs
            }
            return
        }
        val passed = maxOf(0L, wallMs - lastWallMs)
        if (positionMs > lastPositionMs + 2 * passed + JUMP_MS || positionMs < lastPositionMs - JUMP_MS) moved = true
        lastPositionMs = positionMs
        lastWallMs = wallMs
    }

    companion object {
        const val LAND_BEFORE_MS = 3_000L
        const val LAND_AFTER_MS = 20_000L
        const val JUMP_MS = 3_000L
    }
}

/**
 * The play-time check of a stream opened from Clip finder. The subtitle file the clip was matched with may come
 * from another release than the video, so the time can be off. While the player starts, the subtitle add-ons are
 * asked what the player asks them (with this stream's file name, size and hash); when they give a file made for
 * this video, the clip's lines are found in it ([ClipAlign]) and the player is moved there, once, and never
 * after Mo moved himself. Otherwise the clip time stays and the note says why.
 */
class ClipPlayCheck(
    private val listSubtitles: suspend (type: String, subtitleId: String, extras: SubtitleRequestExtras?) -> List<ClipSubtitleLink>,
    private val download: suspend (url: String) -> String,
    private val now: () -> Long,
    private val work: CoroutineContext = Dispatchers.Default,
) {
    /** Waits until the player is at the clip time and the plan is ready, then seeks at most once. */
    suspend fun run(
        target: ClipPlayTarget,
        extras: SubtitleRequestExtras?,
        own: List<StreamSubtitle>,
        position: () -> Long,
        ready: () -> Boolean,
        seek: (Long) -> Unit,
    ): ClipPlayPlan = coroutineScope {
        val planned = async { quietly { plan(target, extras, own) } ?: ClipPlayPlan(null, KEPT + "the check failed") }
        val watch = ClipSeekWatch(target.startMs)
        val started = now()
        while (!(planned.isCompleted && watch.landed)) {
            if (ready()) watch.sample(position(), now())
            if (watch.moved || now() - started > LATE_MS) {
                val why = when {
                    watch.moved -> "you moved yourself"
                    planned.isCompleted -> "the player did not reach the clip time within 60 s"
                    else -> "the check did not finish within 60 s"
                }
                planned.cancel()
                return@coroutineScope ClipPlayPlan(null, KEPT + why)
            }
            delay(POLL_MS)
        }
        val plan = planned.await()
        plan.seekToMs?.let(seek)
        plan
    }

    /** Picks this video's subtitle file, finds the clip's lines in it and decides where to start. */
    suspend fun plan(target: ClipPlayTarget, extras: SubtitleRequestExtras?, own: List<StreamSubtitle>): ClipPlayPlan = coroutineScope {
        val ownLinks = own.filter { it.url.startsWith("http", ignoreCase = true) }.map { ClipSubtitleLink(it.url, it.language, it.name.orEmpty()) }
        val forFile = if (extras == null) null else async { listed(target, extras) }
        val bare = async { listed(target, null) }
        val choice = choose(ownLinks, forFile?.await(), bare.await(), target.matchedUrl)
        val link = choice.link ?: return@coroutineScope ClipPlayPlan(null, KEPT + choice.why, choice.detail)
        val text = quietly { withTimeoutOrNull(FILE_MS) { download(link.url) } }
        val cues = text?.let { body -> runCatching { PlayerSubtitleCueParser.parse(body, link.url) }.getOrDefault(emptyList()) }.orEmpty()
        if (cues.isEmpty()) return@coroutineScope ClipPlayPlan(null, KEPT + "this video's subtitles could not be read", choice.detail)
        val alignment = withContext(work) { ClipAlign.align(target.anchors, cues) }
            ?: return@coroutineScope ClipPlayPlan(null, KEPT + "the clip's lines are not in this video's subtitles", choice.detail)
        decide(target.startMs, alignment, choice.detail)
    }

    private suspend fun listed(target: ClipPlayTarget, extras: SubtitleRequestExtras?): List<ClipSubtitleLink> =
        quietly { withTimeoutOrNull(LIST_MS) { listSubtitles(target.type, target.subtitleId, extras) } }.orEmpty()

    private suspend fun <T> quietly(block: suspend () -> T): T? =
        try {
            block()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            null
        }

    /** The file to line up with ([link] null: none), [why] for the note, [detail] for the "Player subtitles" line. */
    data class Choice(val link: ClipSubtitleLink?, val why: String, val detail: String)

    companion object {
        const val MOVED = "Moved to the matching line in this video's subtitles"
        const val KEPT = "Kept the clip time: "
        const val NONE = "no subtitles for this video"
        const val POLL_MS = 250L
        const val LATE_MS = 60_000L
        const val LIST_MS = 12_000L
        const val FILE_MS = 15_000L
        /** A smaller shift is not worth a seek (and a rebuffer). */
        const val MIN_SHIFT_MS = 1_000L
        /** A larger shift is more likely a wrong line than another release. */
        const val MAX_SHIFT_MS = 300_000L

        /**
         * This video's file, in order: the stream's own English subtitles; an English file the add-on found by this
         * file's hash; the add-on's first English file for this file, if it is not the one the clip was matched with
         * and not simply the add-on's usual first file ([bare]: the list without the file's name, size and hash).
         * [forFile] is null when the stream gives no file name, size or hash.
         */
        fun choose(own: List<ClipSubtitleLink>, forFile: List<ClipSubtitleLink>?, bare: List<ClipSubtitleLink>, matchedUrl: String): Choice {
            own.firstOrNull { EpisodeSubtitleSource.isEnglish(it.language) }?.let { return Choice(it, "", "this stream's own English subtitles") }
            if (forFile == null) return Choice(null, NONE, "the stream gives no file name, size or hash")
            val english = forFile.filter { EpisodeSubtitleSource.isEnglish(it.language) }
            english.firstOrNull { it.hashMatch }?.let { return Choice(it, "", "${sourceOf(it)}: found by this file's hash") }
            val first = english.firstOrNull() ?: return Choice(null, NONE, "the add-ons list no English subtitles for this file")
            val usual = bare.firstOrNull { EpisodeSubtitleSource.isEnglish(it.language) }?.url.orEmpty()
            if (first.url == matchedUrl.ifBlank { usual }) {
                return Choice(null, "this video's subtitles are the file Nuvio matched with", "the add-ons' first English file is the matched one")
            }
            if (first.url == usual) return Choice(null, NONE, "the add-ons gave their usual list, not one for this file")
            return Choice(first, "", "${sourceOf(first)}: picked for this file (release: ${first.release.ifBlank { "none given" }})")
        }

        /** Seek to the corrected start unless the shift is under 1 s or over 5 min. */
        fun decide(startMs: Long, alignment: ClipAlign.Alignment, detail: String): ClipPlayPlan {
            val mapped = maxOf(0L, alignment.map(startMs))
            val shift = mapped - startMs
            return when {
                abs(shift) < MIN_SHIFT_MS -> ClipPlayPlan(null, KEPT + "this video's subtitles agree (${signedSeconds(shift)})", detail)
                abs(shift) > MAX_SHIFT_MS -> ClipPlayPlan(null, KEPT + "the matching lines are ${clipClock(abs(shift))} away, too far to trust", detail)
                else -> ClipPlayPlan(mapped, "$MOVED (${signedSeconds(shift)}${speedNote(alignment.ratio)})", detail)
            }
        }

        /** "+3.2 s", "-0.4 s" (rounded to a tenth). */
        fun signedSeconds(ms: Long): String {
            val tenths = (abs(ms) + 50) / 100
            return (if (ms < 0) "-" else "+") + "${tenths / 10}.${tenths % 10} s"
        }

        /** "; this video plays 4.3% faster" for a speed other than the same one, else "". */
        fun speedNote(ratio: Double): String {
            if (ratio == 1.0) return ""
            val tenths = (abs(1.0 / ratio - 1.0) * 1000).roundToInt()
            return "; this video plays ${tenths / 10}.${tenths % 10}% " + if (ratio < 1.0) "faster" else "slower"
        }

        private fun sourceOf(link: ClipSubtitleLink): String = link.source.ifBlank { "the add-on" }
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipSubtitleList.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject

/**
 * One subtitle add-on answer (`{"subtitles":[{"id","url","lang",...}]}`) read with every field Clip finder can
 * use. Nuvio's own reader keeps only id, url and language; this one also keeps a release name and the hash mark
 * when the add-on sends them. OpenSubtitles v3 is believed to send only id, url and lang (and maybe "m": "h" for
 * a match by the video's hash): the "Matched subtitle" and "Player subtitles" lines in Details show what it sends.
 */
object ClipSubtitleList {
    private val languageKeys = listOf("lang", "language", "languageCode", "locale", "label")
    private val releaseKeys = listOf("releaseName", "release", "subtitleFileName", "fileName", "SubFileName", "MovieReleaseName")

    /** The answer of the add-on named [source]; anything that is not this shape gives an empty list. */
    fun parse(json: String, source: String): List<ClipSubtitleLink> {
        val items = runCatching { Json.parseToJsonElement(json).jsonObject["subtitles"]?.jsonArray }.getOrNull() ?: return emptyList()
        return items.mapNotNull { element ->
            val item = element as? JsonObject ?: return@mapNotNull null
            val url = item.text("url") ?: return@mapNotNull null
            ClipSubtitleLink(
                url = url,
                language = languageKeys.firstNotNullOfOrNull { item.text(it) } ?: "unknown",
                source = source,
                release = releaseKeys.firstNotNullOfOrNull { item.text(it) }.orEmpty(),
                hashMatch = item.text("m") == "h",
            )
        }
    }

    private fun JsonObject.text(name: String): String? =
        (this[name] as? JsonPrimitive)?.contentOrNull?.trim()?.takeIf { it.isNotEmpty() }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipStreamRank.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import com.nuvio.app.features.streams.StreamItem

/** What a file or stream name says about its release: source family (web, bluray, hdtv, dvd), group, resolution family. */
data class ClipRelease(val source: String? = null, val group: String? = null, val resolution: String? = null) {
    val known: Boolean get() = source != null || group != null

    /** "web, GRP, hd": what is known, for Details. */
    fun describe(): String = listOfNotNull(source, group, resolution).joinToString()

    companion object {
        private val sources = mapOf(
            "bluray" to "bluray", "bdrip" to "bluray", "brrip" to "bluray", "bdremux" to "bluray", "remux" to "bluray",
            "web" to "web", "webdl" to "web", "webrip" to "web", "amzn" to "web", "nf" to "web", "dsnp" to "web", "hmax" to "web",
            "hdtv" to "hdtv", "pdtv" to "hdtv",
            "dvd" to "dvd", "dvdrip" to "dvd", "dvd5" to "dvd", "dvd9" to "dvd",
        )
        private val resolutions = mapOf(
            "2160p" to "uhd", "4k" to "uhd", "uhd" to "uhd", "1080p" to "hd", "1080i" to "hd", "720p" to "hd", "576p" to "sd", "480p" to "sd",
        )
        /** Last pieces after a dash that are not a group: "WEB-DL", "Blu-Ray", codecs, languages. */
        private val notGroups = setOf("dl", "rip", "ray", "web", "x264", "x265", "h264", "h265", "hevc", "avc", "aac", "ac3", "dts", "eng", "srt")
        private val extension = Regex("\\.(mkv|mp4|avi|m4v|ts|webm|srt|sub|ass|ssa|vtt)$", RegexOption.IGNORE_CASE)
        private val groupAtEnd = Regex("-([A-Za-z0-9]{2,15})$")
        private val splitter = Regex("[^a-z0-9]+")

        /** "Made.Up.Show.S02E05.720p.WEB-DL.x264-GRP.srt" -> web, GRP, hd. */
        fun of(name: String): ClipRelease {
            val base = name.trim().replace(extension, "")
            val tokens = base.lowercase().split(splitter).filter { it.isNotEmpty() }
            var source: String? = null
            for ((index, token) in tokens.withIndex()) {
                val next = tokens.getOrNull(index + 1)
                val joined = if ((token == "web" || token == "blu") && next in setOf("dl", "rip", "ray")) token + next else token
                source = sources[joined] ?: continue
                break
            }
            val group = groupAtEnd.find(base)?.groupValues?.get(1)?.takeIf { it.lowercase() !in notGroups }
            return ClipRelease(source, group, tokens.firstNotNullOfOrNull { resolutions[it] })
        }

        /** A stream's release: its file name, else the first line of its title, description or name that names a source or group. */
        fun ofStream(stream: StreamItem): ClipRelease =
            listOfNotNull(stream.behaviorHints.filename, stream.title, stream.description, stream.name)
                .flatMap { it.lines() }
                .map { of(it) }
                .firstOrNull { it.known } ?: ClipRelease()
    }
}

/** For a stream list opened from Clip finder: the stream pinned on top, the streams tagged "Best match", and why. */
data class ClipStreamPick(val pinned: StreamItem?, val tagged: Set<StreamItem>, val note: String)

/**
 * Which streams most likely line up with the subtitle file the clip was matched with. With a release name for that
 * file: same source family 4, same group 3, same resolution family 1; a stream needs 3 to be tagged. Without one
 * (OpenSubtitles v3 gives none as far as known), nothing says which release a stream lines up with, so the streams
 * the player can check exactly go first: its own English subtitles 3, a file hash for the subtitle add-ons 2; a
 * stream needs 2. The best score is pinned (the first such stream) and tagged (at most 5); nothing else moves.
 */
object ClipStreamRank {
    const val TAG = "Best match"
    const val HEADER = "Best match for the clip"
    const val RELEASE_BAR = 3
    const val CHECK_BAR = 2
    const val MAX_TAGS = 5

    fun pick(streams: List<StreamItem>, matchedRelease: String): ClipStreamPick {
        val wanted = ClipRelease.of(matchedRelease)
        val scored = streams.map { it to if (wanted.known) sameRelease(ClipRelease.ofStream(it), wanted) else canCheck(it) }
        val top = scored.maxOfOrNull { it.second } ?: 0
        val bar = if (wanted.known) RELEASE_BAR else CHECK_BAR
        if (top < bar) {
            val note = if (wanted.known) {
                "no stream has the matched subtitle's release (${wanted.describe()}); order unchanged"
            } else {
                "the matched subtitle has no release name and no stream has its own subtitles or a file hash; order unchanged"
            }
            return ClipStreamPick(null, emptySet(), note)
        }
        val best = scored.filter { it.second == top }.map { it.first }
        val why = if (wanted.known) "same release as the matched subtitle (${wanted.describe()})" else "own subtitles or a file hash (the matched subtitle has no release name)"
        return ClipStreamPick(best.first(), best.take(MAX_TAGS).toSet(), "best match: ${best.size} of ${streams.size} streams, $why")
    }

    fun sameRelease(stream: ClipRelease, wanted: ClipRelease): Int =
        (if (wanted.source != null && stream.source == wanted.source) 4 else 0) +
            (if (wanted.group != null && stream.group.equals(wanted.group, ignoreCase = true)) 3 else 0) +
            (if (wanted.resolution != null && stream.resolution == wanted.resolution) 1 else 0)

    fun canCheck(stream: StreamItem): Int =
        (if (stream.externalSubtitles.any { it.url.startsWith("http", ignoreCase = true) && EpisodeSubtitleSource.isEnglish(it.language) }) 3 else 0) +
            (if (!stream.behaviorHints.videoHash.isNullOrBlank()) 2 else 0)
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipShowPicker.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlinx.coroutines.CancellationException

/**
 * The pick list under "Know the show?": shows and movies whose name fits what was typed, from the titles Nuvio
 * knows ([known]: shows of earlier clips, popular catalog titles) and the catalogs' search, best first. Names are
 * compared squashed ([ClipNames.typedScore]), so "modernfam" or "Modern  family!" still find "Modern Family".
 */
class ClipShowPicker(
    private val search: suspend (query: String) -> List<ShowGuess>,
    private val known: suspend () -> List<ShowGuess>,
) {
    /** Never throws (except when cancelled); fewer than 2 letters list nothing and ask nothing. */
    suspend fun pick(typed: String): List<ShowGuess> {
        val text = typed.trim().take(ClipFinderPipeline.MAX_TYPED)
        if (ClipNames.key(text).length < MIN_LETTERS) return emptyList()
        val picks = LinkedHashMap<String, Pair<ShowGuess, Int>>()
        fun add(show: ShowGuess, score: Int) {
            if (score <= 0 || show.metaId.isBlank()) return
            val old = picks[show.metaId]
            // The catalog's entry has the poster and year; the remembered one has neither.
            val shown = if (old == null || (old.first.poster == null && show.poster != null)) show else old.first
            picks[show.metaId] = shown to maxOf(score, old?.second ?: 0)
        }
        for (show in quietly { known() }.orEmpty()) add(show, ClipNames.typedScore(show.name, text))
        for ((rank, show) in quietly { search(text) }.orEmpty().take(MAX_SEARCHED).withIndex()) {
            add(show, maxOf(ClipNames.typedScore(show.name, text), SEARCH_SCORE - rank))
        }
        return picks.values.sortedByDescending { it.second }.take(MAX_PICKS).map { it.first }
    }

    private suspend fun <T> quietly(block: suspend () -> T): T? =
        try {
            block()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            null
        }

    companion object {
        const val MIN_LETTERS = 2
        /** Typing pauses this long before the list is asked for. */
        const val PAUSE_MS = 350L
        const val MAX_PICKS = 8
        const val MAX_SEARCHED = 8
        /** A search result's score by its rank when its name does not hold what was typed (as in [ClipShowFinder]). */
        const val SEARCH_SCORE = 80
    }
}

/** "2009" from a catalog's release text ("2009-2020", "2009"), else null. */
internal fun clipYear(releaseInfo: String?): String? = releaseInfo?.let { Regex("\\d{4}").find(it)?.value }

/** The second line of a pick: "2009 · Series", "Movie". */
internal fun clipPickDetail(show: ShowGuess): String =
    listOfNotNull(show.year, if (show.type == "movie") "Movie" else "Series").joinToString(" · ")
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipShowSearch.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.coroutines.CoroutineContext
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

/** How the show search ended: answers best first, or why there are none ([failure], plain English). */
data class ClipShowOutcome(val answers: List<ClipAnswer> = emptyList(), val failure: String? = null)

/**
 * Searching episodes from the clues and the heard lines: suspects ([ClipShowFinder]), the name check when
 * there are many, then the subtitles of up to 3 shows. Moved out of the pipeline as it was, with three
 * additions: episodes in [ClipEpisodeRank] order, the episode list and subtitles fetched while listening
 * ([ClipPrefetch]) reused, and a "Match" note with the numbers behind the confidence. Each answer carries
 * what the player needs to check its time in the video Mo picks ([ClipPlayCheck]): the episode, a few
 * matched lines ([ClipAlign.anchors]) and the subtitle file they came from.
 */
class ClipShowSearch(
    private val finder: ClipShowFinder,
    private val loadEpisodes: suspend (ShowGuess) -> List<ClipEpisode>,
    private val subtitles: EpisodeSubtitleSource,
    private val now: () -> Long,
    private val work: CoroutineContext,
) {
    suspend fun run(
        clues: ClipClues,
        lines: List<ClipLine>,
        prefetch: ClipPrefetch?,
        timings: ClipTimings,
        note: (String, String) -> Unit,
        progress: (String) -> Unit,
    ): ClipShowOutcome {
        var suspects = finder.find(clues, lines, onNote = note)
        timings.lap("guess")
        val hint = ClipNames.hint(clues, lines)
        val cached: Set<String> = prefetch?.fetched.orEmpty()
        val episodeLists = mutableMapOf<String, List<ClipEpisode>>()
        val early = prefetch?.show
        if (prefetch != null && early != null) episodeLists[early.metaId] = prefetch.episodes
        suspend fun episodesOf(show: ShowGuess): List<ClipEpisode> {
            val loaded = episodeLists.getOrPut(show.metaId) { quietly { loadEpisodes(show) }.orEmpty() }
            return ClipEpisodeRank.rank(orderEpisodes(loaded, hint), hint, lines, cached)
        }

        // Many suspects: one subtitle file of each tells which show has the people named in the clip.
        val names = ClipNameCheck.names(lines)
        if (ClipNameCheck.needed(suspects, names)) {
            progress("Checking which show has the names heard")
            note("Names heard", names.joinToString())
            val ranked = withTimeoutOrNull(ClipFinderPipeline.NAME_CHECK_MS) {
                ClipNameCheck.rank(suspects, names) { show ->
                    episodesOf(show).firstOrNull()?.let { episode -> subtitles.cues(show.metaId, episode) }
                }
            }
            if (ranked != null) {
                note("Name check", ranked.joinToString { "${it.first.show.name} ${it.second}" }.take(300))
                suspects = ranked.map { it.first }
            }
            timings.lap("names")
        }
        val chosen = suspects.take(ClipNameCheck.KEEP)
        note("Show guesses", chosen.joinToString { "${it.show.name} (${it.why})" }.ifBlank { "none" })
        if (chosen.isEmpty()) return ClipShowOutcome(failure = if (clues.typed.isBlank()) ClipMessages.NO_SHOW else ClipMessages.NO_TYPED_SHOW)
        val deadline = now() + ClipFinderPipeline.SEARCH_BUDGET_MS
        val owners = mutableMapOf<String, Pair<ShowGuess, ClipEpisode>>()
        var best = emptyList<EpisodeCues>()
        var candidates = emptyList<ClipCandidate>()
        var tried = 0
        var withSubtitles = 0
        for (guess in chosen.map { it.show }) {
            if (now() >= deadline) break
            progress("Loading the episode list of ${guess.name}")
            val episodes = episodesOf(guess)
            timings.lap("episode list")
            if (episodes.isEmpty()) continue
            for (episode in episodes) owners[episode.videoId] = guess to episode
            val showDeadline = minOf(deadline, now() + ClipFinderPipeline.SHOW_BUDGET_MS)
            val result = withContext(work) {
                subtitles.search(guess.metaId, episodes, lines, showDeadline, best) { done, total, found ->
                    progress("Searching ${guess.name}: $done of $total episodes, $found with subtitles")
                }
            }
            timings.lap("subtitles", "${result.tried} episodes")
            best = result.best
            candidates = result.candidates
            tried += result.tried
            withSubtitles += result.withSubtitles
            if (result.decisive) break
            if (result.tried < episodes.size) note("Search", "stopped at the time limit in ${guess.name}")
        }
        note("Subtitles", "$withSubtitles of $tried episodes")
        if (tried == 0) return ClipShowOutcome(failure = ClipMessages.NO_EPISODES)
        if (withSubtitles == 0) return ClipShowOutcome(failure = ClipMessages.NO_SUBTITLES)
        note("Match", matchNote(lines, candidates))
        val cuesOf = best.associateBy { it.videoId }
        val answers = candidates.filter { it.hits >= ClipMatcher.MIN_HITS }.mapNotNull { candidate ->
            owners[candidate.videoId]?.let { (show, episode) ->
                val cues = cuesOf[candidate.videoId]?.cues.orEmpty()
                val link = runCatching { subtitles.usedLink(show.metaId, episode.videoId) }.getOrNull()
                ClipAnswer(candidate, show, episode.title, episode.thumbnail, episode, ClipAlign.anchors(cues, candidate.startMs, candidate.endMs), link)
            }
        }
        note("Candidates", answers.size.toString())
        if (answers.isEmpty()) return ClipShowOutcome(failure = ClipMessages.NO_MATCH)
        note("Matched subtitle", matchedNote(answers.first().subtitle))
        return ClipShowOutcome(answers)
    }

    /** "OpenSubtitles v3: no release name given": which file the best answer was matched with (the stream list ranks by its release). */
    private fun matchedNote(link: ClipSubtitleLink?): String {
        if (link == null) return "from an earlier run's cache (add-on and release not known)"
        return link.source.ifBlank { "add-on" } + ": " + link.release.ifBlank { "no release name given" }
    }

    /** "41 shared phrases of 160 heard (25%), next best 3": the numbers behind the confidence, to tune it on real clips. */
    private fun matchNote(lines: List<ClipLine>, candidates: List<ClipCandidate>): String {
        val heard = ClipText.triples(lines.flatMap { ClipText.normalize(it.text) }).toSet().size
        val top = candidates.firstOrNull() ?: return "nothing shared with $heard heard phrases"
        val share = if (heard == 0) 0 else top.hits * 100 / heard
        return "${top.hits} shared phrases of $heard heard ($share%), next best ${candidates.getOrNull(1)?.hits ?: 0}"
    }

    private suspend fun <T> quietly(block: suspend () -> T): T? =
        try {
            block()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            null
        }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderSession.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import com.nuvio.app.features.addons.AddonRepository
import com.nuvio.app.features.addons.enabledAddons
import com.nuvio.app.features.addons.fetchAddonResponseText
import com.nuvio.app.features.addons.httpGetTextWithHeaders
import com.nuvio.app.features.addons.httpPostJsonWithHeaders
import com.nuvio.app.features.addons.httpRequestRaw
import com.nuvio.app.features.catalog.fetchCatalogPage
import com.nuvio.app.features.details.MetaDetailsRepository
import com.nuvio.app.features.player.SubtitleRequestExtras
import com.nuvio.app.features.player.addonSubtitleRequests
import com.nuvio.app.features.streams.epochMs
import kotlin.coroutines.resume
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull

/**
 * The one running Clip finder search. It lives outside the screen so that going to the stream list
 * and back does not start the search again.
 */
object ClipFinderSession {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val _state = MutableStateFlow(ClipFinderState())
    val state: StateFlow<ClipFinderState> = _state.asStateFlow()
    private var job: Job? = null
    private var runId = 0
    private var pipeline: ClipFinderPipeline? = null
    private var memory: ClipMemory? = null

    /** Starts the search for [source]. Does nothing when that clip is already running or shown, unless [restart]. */
    fun start(source: String, restart: Boolean = false) {
        if (!restart && _state.value.source == source) return
        job?.cancel()
        val id = ++runId
        _state.value = ClipFinderState(source = source)
        val native = ClipFinderBridge.current()
        val cache = object : ClipSubtitleCache {
            override fun read(key: String): String? = native?.cacheRead(key)
            override fun write(key: String, text: String) {
                native?.cacheWrite(key, text)
            }
        }
        val memory = ClipMemory(
            read = { native?.settingRead(ClipMemory.KEY) },
            write = { text -> native?.settingWrite(ClipMemory.KEY, text) },
            now = ::epochMs,
        ).also { this@ClipFinderSession.memory = it }
        val created = ClipFinderPipeline(
            native = native,
            finder = ClipShowFinder(::clipSearchShows, ::clipPopularShows, memory) { prompt -> clipAskModel(native, prompt) },
            loadEpisodes = ::clipLoadEpisodes,
            subtitles = EpisodeSubtitleSource({ type, id -> clipListSubtitles(type, id) }, ::clipDownloadText, cache, ::epochMs),
            memory = memory,
            now = ::epochMs,
            youtube = ClipYouTubeFinder(::clipWebGet, ::clipWebPost),
            webGet = ::clipWebGet,
        )
        pipeline = created
        job = scope.launch {
            created.run(source) { if (id == runId) _state.value = it }
        }
    }

    /**
     * Searches again with a show name the user typed, or the show [picked] in the pick list (then exactly that
     * show), reusing what was heard. Stops a search that still runs.
     */
    fun searchTyped(name: String, picked: ShowGuess? = null) {
        val current = _state.value
        val active = pipeline ?: return
        if (name.isBlank() || !clipCanType(current)) return
        job?.cancel()
        val id = ++runId
        job = scope.launch {
            active.runTyped(current, name, picked) { if (id == runId) _state.value = it }
        }
    }

    /** The pick list for what was typed so far ([ClipShowPicker]): the catalogs' search and the titles Nuvio knows. */
    suspend fun pickShows(typed: String): List<ShowGuess> {
        val remembered = memory
        return ClipShowPicker(::clipSearchShows) {
            runCatching { remembered?.shows() }.getOrNull().orEmpty() + clipPopularShows()
        }.pick(typed)
    }

    /** A line for Details from outside the search (the stream list, the player); the screen shows it when Mo comes back. */
    fun note(label: String, value: String) {
        _state.value = _state.value.withNote(label, value)
    }

    /** The screen opened the YouTube video by itself: it must not do so again when Mo comes back. */
    fun youTubeOpened() {
        _state.value = _state.value.copy(openYouTube = false)
    }
}

private const val MODEL_TIMEOUT_MS = 12_000L

/** One question to Apple's on-device model through the bridge; a missing bridge or no answer in 12 s is a problem text. */
internal suspend fun clipAskModel(native: ClipFinderNative?, prompt: String): ClipModelAnswer {
    val phone = native ?: return ClipModelAnswer(problem = "only in the iPhone app")
    return withTimeoutOrNull(MODEL_TIMEOUT_MS) {
        suspendCancellableCoroutine { continuation ->
            phone.askModel(
                prompt,
                object : ClipModelListener {
                    override fun onAnswer(text: String?, problem: String?) {
                        if (continuation.isActive) continuation.resume(ClipModelAnswer(text.orEmpty(), problem.orEmpty()))
                    }
                },
            )
        }
    } ?: ClipModelAnswer(problem = "no answer in 12 s")
}

private var popularShows: List<ShowGuess> = emptyList()

/**
 * Well-known titles to compare hashtags and handles with: the first page of every plain catalog
 * (series and movies, no required filter) of the switched-on add-ons, for example Cinemeta's
 * "Popular". Fetched once per app start; an empty answer is asked for again next time.
 */
internal suspend fun clipPopularShows(): List<ShowGuess> {
    if (popularShows.isNotEmpty()) return popularShows
    AddonRepository.initialize()
    val catalogs = AddonRepository.uiState.value.addons.enabledAddons().mapNotNull { it.manifest }.flatMap { manifest ->
        manifest.catalogs
            .filter { catalog -> (catalog.type == "series" || catalog.type == "movie") && catalog.extra.none { it.isRequired } }
            .map { manifest to it }
    }.take(8)
    val pages = coroutineScope {
        catalogs.map { (manifest, catalog) ->
            async {
                quietly(8_000L) { fetchCatalogPage(manifest.transportUrl, catalog.type, catalog.id, maxItems = 100).items }.orEmpty()
            }
        }.awaitAll()
    }
    val shows = pages.flatten().filter { it.name.isNotBlank() }
        .map { ShowGuess(it.id, it.type, it.name, it.poster, clipYear(it.releaseInfo)) }
        .distinctBy { it.metaId }
    popularShows = shows.filter { it.metaId.startsWith("tt") }.ifEmpty { shows }
    return popularShows
}

private suspend fun <T> quietly(timeoutMs: Long, block: suspend () -> T): T? =
    withTimeoutOrNull(timeoutMs) {
        try {
            block()
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            null
        }
    }

/** Nuvio's own search: every search catalog (series and movies) of the switched-on add-ons, results mixed by rank. */
internal suspend fun clipSearchShows(query: String): List<ShowGuess> = coroutineScope {
    AddonRepository.initialize()
    val catalogs = AddonRepository.uiState.value.addons.enabledAddons().mapNotNull { it.manifest }.flatMap { manifest ->
        manifest.catalogs
            .filter { catalog ->
                (catalog.type == "series" || catalog.type == "movie") &&
                    catalog.extra.any { it.name == "search" } &&
                    catalog.extra.none { it.isRequired && it.name != "search" }
            }
            .map { manifest to it }
    }.take(6)
    val pages = catalogs.map { (manifest, catalog) ->
        async {
            quietly(8_000L) {
                fetchCatalogPage(manifest.transportUrl, catalog.type, catalog.id, search = query, maxItems = 8).items
            }.orEmpty()
        }
    }.awaitAll()
    val mixed = (0 until 8).flatMap { rank -> pages.mapNotNull { it.getOrNull(rank) } }
        .map { ShowGuess(it.id, it.type, it.name, it.poster, clipYear(it.releaseInfo)) }
        .distinctBy { it.metaId }
    // Subtitle add-ons only know IMDb ids ("tt..."), so those results go first when there are any.
    mixed.filter { it.metaId.startsWith("tt") }.ifEmpty { mixed }
}

/** The episodes of a series (specials and season 0 left out), or the movie itself as one entry. */
internal suspend fun clipLoadEpisodes(show: ShowGuess): List<ClipEpisode> {
    val meta = quietly(25_000L) { MetaDetailsRepository.fetch(show.type, show.metaId) } ?: return emptyList()
    val imdbId = listOf(meta.id, meta.imdbId.orEmpty(), show.metaId).firstOrNull { it.startsWith("tt") }
    val episodes = meta.videos.filter { (it.season ?: 0) > 0 && it.episode != null }
    if (episodes.isEmpty()) {
        return listOf(ClipEpisode(videoId = meta.id, subtitleId = imdbId ?: meta.id, type = show.type))
    }
    return episodes.map { video ->
        val subtitleId = if (video.id.startsWith("tt") || imdbId == null) video.id else "$imdbId:${video.season}:${video.episode}"
        ClipEpisode(video.id, subtitleId, show.type, video.season, video.episode, video.title, video.thumbnail, video.overview)
    }
}

/**
 * Every subtitle the switched-on subtitle add-ons list for [subtitleId], in add-on order, with the release name
 * and hash mark when an add-on sends them ([ClipSubtitleList]). [extras] names the video file (name, size,
 * hash), as the player sends it. 10 s per add-on; a failed add-on lists nothing.
 */
internal suspend fun clipListSubtitles(type: String, subtitleId: String, extras: SubtitleRequestExtras? = null): List<ClipSubtitleLink> =
    coroutineScope {
        addonSubtitleRequests(type, subtitleId, extras).map { request ->
            async { quietly(10_000L) { ClipSubtitleList.parse(fetchAddonResponseText(request.url), request.addonName) }.orEmpty() }
        }.awaitAll().flatten()
    }

internal suspend fun clipDownloadText(url: String): String = httpGetTextWithHeaders(url, emptyMap())

/** A plain web request from Kotlin (YouTube, Instagram's embed page), at most 6 MB of answer. */
internal suspend fun clipWebGet(url: String, headers: Map<String, String>): ClipWebReply {
    val reply = httpRequestRaw("GET", url, headers, "", maxResponseBodyBytes = 6 * 1024 * 1024)
    return ClipWebReply(reply.status, reply.body)
}

/** A JSON request (YouTube's player answer); a refusal throws, which the caller treats as "failed". */
internal suspend fun clipWebPost(url: String, body: String, headers: Map<String, String>): ClipWebReply =
    ClipWebReply(200, httpPostJsonWithHeaders(url, body, headers))
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderScreen.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalUriHandler
import androidx.lifecycle.compose.collectAsStateWithLifecycle
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

/**
 * [onOpen] gets the tapped candidate and the time to start playing from, in milliseconds; the answer is kept
 * first ([ClipPlayTargets]) so the stream list and the player can check it. [onShow] gets a show to open (its
 * episode list) when the clip itself could not be heard. A YouTube video opens through the system (the
 * YouTube app when installed): by itself once when it is the only sure answer, else on a tap.
 */
@Composable
fun ClipFinderScreen(
    source: String,
    onBack: () -> Unit,
    onOpen: (ClipAnswer, Long) -> Unit = { _, _ -> },
    onShow: (ShowGuess) -> Unit = {},
) {
    val colors = MaterialTheme.nuvio.colors
    val current by ClipFinderSession.state.collectAsStateWithLifecycle()
    val state = if (current.source == source) current else ClipFinderState(source = source)
    var afterClip by rememberSaveable { mutableStateOf(false) }
    val uriHandler = LocalUriHandler.current
    val openAnswer: (ClipAnswer, Long) -> Unit = { answer, startMs ->
        ClipPlayTargets.arm(answer, startMs)
        onOpen(answer, startMs)
    }
    val openVideo: (ClipVideoAnswer, Long) -> Unit = { video, startMs ->
        runCatching { uriHandler.openUri(ClipYouTube.openUrl(video.video.id, startMs)) }
    }
    LaunchedEffect(source) { ClipFinderSession.start(source) }
    LaunchedEffect(state.openYouTube) {
        val first = state.youtube.firstOrNull()
        if (state.openYouTube && first != null) {
            ClipFinderSession.youTubeOpened()
            openVideo(first, clipStartMs(first.candidate, afterClip))
        }
    }

    NuvioScreen {
        item { NuvioScreenHeader(title = CLIP_FINDER_TITLE, onBack = onBack) }
        item {
            NuvioSurfaceCard {
                NuvioSectionLabel(if (isClipFile(source)) "Shared video" else "Shared link")
                Text(clipSourceLabel(source), style = MaterialTheme.typography.bodyMedium, color = colors.textPrimary)
            }
        }
        item { ClipStagesCard(state) }
        if (state.failed) {
            item { ClipFailureCard(state, onRetry = { ClipFinderSession.start(source, restart = true) }) }
        }
        if (state.answers.isNotEmpty()) {
            item { ClipAnswersCard(state.answers, afterClip, onAfterClip = { afterClip = it }, onOpen = openAnswer) }
        }
        if (state.youtube.isNotEmpty()) {
            item { ClipYouTubeCard(state.youtube, afterClip, onOpen = openVideo) }
        }
        if (state.shows.isNotEmpty()) {
            item { ClipShowsCard(state.shows, onShow) }
        }
        if (clipCanType(state)) {
            item {
                ClipTypeCard(
                    heard = !state.noClip,
                    onSearch = { ClipFinderSession.searchTyped(it) },
                    // A clip that could not be heard has no moment to find: a picked show just opens.
                    onPick = { show -> if (state.noClip) onShow(show) else ClipFinderSession.searchTyped(show.name, show) },
                )
            }
        }
        if (state.notes.isNotEmpty()) {
            item { ClipNotesCard(state.notes) }
        }
        if (state.lines.isNotEmpty()) {
            item { ClipLinesCard(state.lines) }
        }
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipFinderParts.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import com.nuvio.app.core.ui.Chip
import com.nuvio.app.core.ui.NuvioInputField
import com.nuvio.app.core.ui.NuvioPrimaryButton
import com.nuvio.app.core.ui.NuvioSectionLabel
import com.nuvio.app.core.ui.NuvioSurfaceCard
import com.nuvio.app.core.ui.nuvio
import kotlinx.coroutines.delay

@Composable
internal fun ClipStagesCard(state: ClipFinderState) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Steps")
        CLIP_FINDER_STAGES.forEachIndexed { index, stage ->
            val mark = clipStageMark(state, index)
            Text(
                text = "${index + 1}. $stage" + if (mark.isEmpty()) "" else " ($mark)",
                style = MaterialTheme.typography.bodyMedium,
                color = if (mark == "now" || mark == "failed") colors.textPrimary else colors.textMuted,
            )
        }
        if (state.progress.isNotBlank()) {
            Text(state.progress, style = MaterialTheme.typography.bodyMedium, color = colors.textPrimary)
        }
    }
}

@Composable
internal fun ClipFailureCard(state: ClipFinderState, onRetry: () -> Unit) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Stopped at: ${CLIP_FINDER_STAGES.getOrElse(state.stage.ordinal) { "" }}")
        Text(state.message, style = MaterialTheme.typography.bodyMedium, color = colors.textPrimary)
        if (state.showFileHint) {
            Text(ClipMessages.FILE_HINT, style = MaterialTheme.typography.bodyMedium, color = colors.textMuted)
        }
        NuvioPrimaryButton(text = "Try again", modifier = Modifier.padding(top = 8.dp), onClick = onRetry)
    }
}

@Composable
internal fun ClipAnswersCard(
    answers: List<ClipAnswer>,
    afterClip: Boolean,
    onAfterClip: (Boolean) -> Unit,
    onOpen: (ClipAnswer, Long) -> Unit,
) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Found (tap one, then pick a stream)")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(vertical = 8.dp)) {
            Chip(label = "From clip start", selected = !afterClip, onClick = { onAfterClip(false) })
            Chip(label = "After the clip", selected = afterClip, onClick = { onAfterClip(true) })
        }
        answers.forEach { answer ->
            val startMs = clipStartMs(answer.candidate, afterClip)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onOpen(answer, startMs) }
                    .padding(vertical = 8.dp),
            ) {
                Text(clipAnswerTitle(answer), style = MaterialTheme.typography.titleMedium, color = colors.textPrimary)
                Text(
                    text = clipAnswerDetail(answer) + ". Plays from ${clipClock(startMs)}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = colors.textMuted,
                )
            }
        }
    }
}

/** YouTube videos whose captions hold the clip; a tap opens the YouTube app at the moment. */
@Composable
internal fun ClipYouTubeCard(videos: List<ClipVideoAnswer>, afterClip: Boolean, onOpen: (ClipVideoAnswer, Long) -> Unit) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("On YouTube (tap to open the YouTube app)")
        videos.forEach { video ->
            val startMs = clipStartMs(video.candidate, afterClip)
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onOpen(video, startMs) }
                    .padding(vertical = 8.dp),
            ) {
                Text(clipVideoTitle(video), style = MaterialTheme.typography.titleMedium, color = colors.textPrimary)
                Text(
                    text = clipMatchDetail(video.candidate) + ". Opens at ${clipClock(startMs)}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = colors.textMuted,
                )
            }
        }
    }
}

/** Shows named by the caption when the clip itself could not be heard; a tap opens the show's page. */
@Composable
internal fun ClipShowsCard(shows: List<ShowGuess>, onShow: (ShowGuess) -> Unit) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Open the show and pick the episode")
        shows.forEach { show ->
            Text(
                text = show.name,
                style = MaterialTheme.typography.titleMedium,
                color = colors.textPrimary,
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onShow(show) }
                    .padding(vertical = 8.dp),
            )
        }
    }
}

/**
 * As Mo types, matching shows and movies are listed after a short pause ([ClipShowPicker]): poster, name,
 * year and type. A tap ([onPick]) searches exactly that show with what was already heard: nothing is read or
 * listened to again; when nothing could be heard ([heard] false) it opens the show. The button searches the
 * typed name as before (the list can stay empty when the catalogs do not answer).
 */
@Composable
internal fun ClipTypeCard(heard: Boolean, onSearch: (String) -> Unit, onPick: (ShowGuess) -> Unit) {
    val colors = MaterialTheme.nuvio.colors
    var name by rememberSaveable { mutableStateOf("") }
    var picks by remember { mutableStateOf<List<ShowGuess>>(emptyList()) }
    LaunchedEffect(name) {
        if (ClipNames.key(name).length < ClipShowPicker.MIN_LETTERS) {
            picks = emptyList()
            return@LaunchedEffect
        }
        delay(ClipShowPicker.PAUSE_MS)
        picks = ClipFinderSession.pickShows(name)
    }
    NuvioSurfaceCard {
        NuvioSectionLabel("Know the show? Type its name")
        Text(
            text = if (heard) "Tap it in the list: Nuvio searches it with what it already heard. Nothing is listened to again." else "Tap it in the list to open it.",
            style = MaterialTheme.typography.bodySmall,
            color = colors.textMuted,
        )
        NuvioInputField(
            value = name,
            onValueChange = { name = it.take(80) },
            placeholder = "Show or movie name",
            modifier = Modifier.padding(vertical = 8.dp),
        )
        picks.forEach { show ->
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onPick(show) }
                    .padding(vertical = 6.dp),
            ) {
                AsyncImage(
                    model = show.poster,
                    contentDescription = null,
                    modifier = Modifier
                        .size(width = 40.dp, height = 60.dp)
                        .clip(RoundedCornerShape(4.dp)),
                    contentScale = ContentScale.Crop,
                )
                Column(modifier = Modifier.weight(1f)) {
                    Text(show.name, style = MaterialTheme.typography.titleMedium, color = colors.textPrimary)
                    Text(clipPickDetail(show), style = MaterialTheme.typography.bodySmall, color = colors.textMuted)
                }
            }
        }
        NuvioPrimaryButton(text = "Search this show", enabled = name.isNotBlank(), onClick = { onSearch(name) })
    }
}

@Composable
internal fun ClipNotesCard(notes: List<ClipNote>) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Details (for a screenshot if something fails)")
        notes.forEach { note ->
            Text("${note.label}: ${note.value}", style = MaterialTheme.typography.bodySmall, color = colors.textMuted)
        }
    }
}

@Composable
internal fun ClipLinesCard(lines: List<ClipLine>) {
    val colors = MaterialTheme.nuvio.colors
    NuvioSurfaceCard {
        NuvioSectionLabel("Heard (first lines)")
        lines.take(6).forEach { line ->
            Text("${clipClock(line.startMs)}  ${line.text}", style = MaterialTheme.typography.bodySmall, color = colors.textMuted)
        }
    }
}
```

##### File: `composeApp/src/commonMain/kotlin/com/nuvio/app/features/clipfinder/ClipPlayerHooks.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import com.nuvio.app.core.ui.NuvioToastController
import com.nuvio.app.features.player.PlayerScreenArgs
import com.nuvio.app.features.streams.AddonStreamGroup
import com.nuvio.app.features.streams.SharedStream
import com.nuvio.app.features.streams.StreamItem
import com.nuvio.app.features.streams.epochMs

private const val NOTE_MS = 4_000L

/**
 * The player's one Clip finder hook (one line in PlayerScreenContent): when this player was opened from a Clip
 * finder answer, its start time is checked against this video's subtitles once ([ClipPlayCheck]). The note shows
 * as a toast and in Details. [ready]: the player's own first seek is done and the stream is the one it opened.
 */
@Composable
internal fun ClipPlayerCheck(args: PlayerScreenArgs, position: () -> Long, ready: () -> Boolean, seek: (Long) -> Unit) {
    val target = remember(args.launchId) {
        ClipPlayTargets.forPlayer(args.launchId, args.parentMetaId, args.seasonNumber, args.episodeNumber, args.initialPositionMs)
    } ?: return
    LaunchedEffect(target, args.launchId) {
        val check = ClipPlayCheck({ type, id, extras -> clipListSubtitles(type, id, extras) }, ::clipDownloadText, ::epochMs)
        val plan = check.run(target, args.subtitleExtras, args.externalSubtitles, position, ready, seek)
        NuvioToastController.show(plan.note, NOTE_MS)
        ClipFinderSession.note("Player", plan.note)
        if (plan.detail.isNotBlank()) ClipFinderSession.note("Player subtitles", plan.detail)
    }
}

/**
 * The stream list's Clip finder hook (StreamDestination): for a list opened from Clip finder ([fromClip]) the
 * best match is worked out from the streams loaded so far; null for any other list, which stays as it is.
 */
@Composable
internal fun rememberClipStreamPick(fromClip: Boolean, groups: List<AddonStreamGroup>): ClipStreamPick? {
    val pick = remember(fromClip, groups) {
        if (fromClip) ClipStreamRank.pick(groups.flatMap { it.streams }, ClipPlayTargets.current()?.release.orEmpty()) else null
    }
    LaunchedEffect(pick?.note) {
        pick?.note?.let { ClipFinderSession.note("Stream order", it) }
    }
    return pick
}

/** The best match, shown above the list under "Best match for the clip" (the slot a party's shared stream uses). */
internal fun clipPinned(pick: ClipStreamPick?): SharedStream? =
    pick?.pinned?.let { SharedStream(label = ClipStreamRank.HEADER, stream = it) }

/** The stream list's highlight: the party's own label first, then "Best match" on the tagged streams. */
@Composable
internal fun rememberClipHighlight(pick: ClipStreamPick?, other: (StreamItem) -> String?): (StreamItem) -> String? =
    remember(pick, other) {
        val tagged = pick?.tagged.orEmpty()
        val highlight: (StreamItem) -> String? = { stream -> other(stream) ?: if (stream in tagged) ClipStreamRank.TAG else null }
        highlight
    }
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipAlignTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import com.nuvio.app.features.player.SubtitleSyncCue
import kotlin.math.abs
import kotlin.math.roundToLong
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** Made-up lines only ([ClipTestText]); one cue every 4 s in the file the clip was matched with. */
class ClipAlignTest {
    private val texts = ClipTestText.cueTexts(205, count = 80)

    /** The matched file's lines as another release has them: [shiftMs] later and at [ratio] of the time. */
    private fun cues(shiftMs: Long = 0, ratio: Double = 1.0, lines: List<String> = texts) =
        lines.mapIndexed { index, text ->
            val start = (index * 4_000L * ratio).roundToLong() + shiftMs
            SubtitleSyncCue(start, start + 3_000, text)
        }

    @Test
    fun `anchors are up to twelve lines of four or more words around the match, spread evenly`() {
        val withShort = cues().toMutableList().also { it[20] = it[20].copy(text = "Yeah. What?") }
        val anchors = ClipAlign.anchors(withShort, 100_000, 140_000)
        assertEquals(12, anchors.size)
        assertTrue(anchors.none { it.text == "Yeah. What?" })
        assertEquals(72_000, anchors.first().startTimeMs)
        assertEquals(168_000, anchors.last().startTimeMs)
        assertEquals(9, ClipAlign.anchors(cues(), 0, 4_000).size)
    }

    @Test
    fun `a release that starts 3_2 s later moves every line by 3_2 s`() {
        val anchors = ClipAlign.anchors(cues(), 100_000, 140_000)
        val alignment = assertNotNull(ClipAlign.align(anchors, cues(shiftMs = 3_200)))
        assertEquals(1.0, alignment.ratio)
        assertEquals(12, alignment.pairs.size)
        assertEquals(88_200, alignment.map(85_000))
    }

    @Test
    fun `a video playing 4 percent faster is found from lines far apart`() {
        val pal = 23.976 / 25.0
        val anchors = ClipAlign.anchors(cues(), 60_000, 280_000)
        val alignment = assertNotNull(ClipAlign.align(anchors, cues(shiftMs = 5_000, ratio = pal)))
        assertEquals(pal, alignment.ratio)
        assertEquals(12, alignment.pairs.size)
        // 45 s of the matched file is 45 x 0.95904 + 5 = 48.157 s of this video.
        assertTrue(abs(alignment.map(45_000) - 48_157) <= 1, "mapped to ${alignment.map(45_000)}")
    }

    @Test
    fun `lines close together cannot tell the speed, so the same speed is kept`() {
        val anchors = ClipAlign.anchors(cues(), 100_000, 110_000)
        val alignment = assertNotNull(ClipAlign.align(anchors, cues(shiftMs = 5_000, ratio = 23.976 / 25.0)))
        assertEquals(1.0, alignment.ratio)
    }

    @Test
    fun `other words give no alignment`() {
        val anchors = ClipAlign.anchors(cues(), 100_000, 140_000)
        assertNull(ClipAlign.align(anchors, cues(lines = ClipTestText.cueTexts(999, count = 80))))
    }

    @Test
    fun `a line said again far away is skipped and a line said again close by counts once`() {
        val anchors = cues().subList(25, 28) // at 100, 104 and 108 s
        val recap = (cues(shiftMs = 3_200) + SubtitleSyncCue(10_000, 13_000, texts[26])).sortedBy { it.startTimeMs }
        assertEquals(listOf(ClipAlign.Hit(100_000, 103_200), ClipAlign.Hit(108_000, 111_200)), ClipAlign.pairs(anchors, recap))
        assertEquals(103_200, assertNotNull(ClipAlign.align(anchors, recap)).map(100_000))
        val echo = (cues(shiftMs = 3_200) + SubtitleSyncCue(109_000, 110_000, texts[26])).sortedBy { it.startTimeMs }
        assertEquals(
            listOf(ClipAlign.Hit(100_000, 103_200), ClipAlign.Hit(104_000, 107_200), ClipAlign.Hit(108_000, 111_200)),
            ClipAlign.pairs(anchors, echo),
        )
        // Two lines, one of them repeated: one pair is not enough to move anything.
        assertNull(ClipAlign.align(cues().subList(25, 27), recap))
    }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipPlayCheckTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import com.nuvio.app.features.player.SubtitleRequestExtras
import com.nuvio.app.features.player.SubtitleSyncCue
import com.nuvio.app.features.streams.StreamSubtitle
import kotlin.coroutines.EmptyCoroutineContext
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.delay
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.runTest

/** Made-up lines and addresses only. The clip was matched at 100-140 s of matched.srt and starts at 85 s (15 s before). */
@OptIn(ExperimentalCoroutinesApi::class)
class ClipPlayCheckTest {
    private val texts = ClipTestText.cueTexts(205, count = 80)
    private val matched = "https://subs.example.test/matched.srt"
    private val forFile = "https://subs.example.test/for-file.srt"
    private val own = "https://cdn.example.test/own.srt"
    private val start = 85_000L
    private val extras = SubtitleRequestExtras(filename = "Made.Up.Show.S02E05.720p.WEB-DL-GRP.mkv")

    private fun cues(shiftMs: Long = 0, lines: List<String> = texts) =
        lines.mapIndexed { index, text -> SubtitleSyncCue(index * 4_000L + shiftMs, index * 4_000L + shiftMs + 3_000, text) }

    private fun srt(cues: List<SubtitleSyncCue>): String = cues.mapIndexed { index, cue ->
        "${index + 1}\n${stamp(cue.startTimeMs)} --> ${stamp(cue.endTimeMs)}\n${cue.text}\n\n"
    }.joinToString("")

    private fun stamp(ms: Long): String {
        fun two(n: Long) = n.toString().padStart(2, '0')
        return "${two(ms / 3_600_000)}:${two(ms / 60_000 % 60)}:${two(ms / 1_000 % 60)},${(ms % 1_000).toString().padStart(3, '0')}"
    }

    private fun link(url: String, hash: Boolean = false) = ClipSubtitleLink(url, "eng", "Sample Subs", hashMatch = hash)

    private val target = ClipPlayTarget("tt001", 2, 5, "series", "tt001:2:5", start, ClipAlign.anchors(cues(), 100_000, 140_000), matched, "")

    /** The subtitle add-ons ([forFileList] when asked with the file's name, else the usual list) and the files they serve. */
    private inner class Fake(
        val files: Map<String, String>,
        val forFileList: List<ClipSubtitleLink> = listOf(link(forFile), link(matched)),
        val downloadMs: Long = 0,
    ) {
        val asked = mutableListOf<SubtitleRequestExtras?>()
        val downloads = mutableListOf<String>()
        val seeks = mutableListOf<Long>()

        fun check(now: () -> Long) = ClipPlayCheck(
            listSubtitles = { _, _, given -> asked += given; if (given == null) listOf(link(matched)) else forFileList },
            download = { url -> downloads += url; delay(downloadMs); files.getValue(url) },
            now = now,
            work = EmptyCoroutineContext,
        )
    }

    /** The player reaches the clip time 1 s after it opens and plays on. */
    private fun TestScope.playing(): Long = if (testScheduler.currentTime < 1_000) 0L else start + testScheduler.currentTime - 1_000

    @Test
    fun `a release 3_2 s later moves the player once, after it reached the clip time`() = runTest {
        val fake = Fake(mapOf(forFile to srt(cues(shiftMs = 3_200))))
        val plan = fake.check { testScheduler.currentTime }.run(target, extras, emptyList(), { playing() }, { true }) { fake.seeks += it }
        assertEquals(listOf(88_200L), fake.seeks)
        assertEquals("Moved to the matching line in this video's subtitles (+3.2 s)", plan.note)
        assertEquals("Sample Subs: picked for this file (release: none given)", plan.detail)
        assertEquals(listOf(forFile), fake.downloads)
        assertEquals(listOf(extras, null), fake.asked.sortedBy { it == null })
    }

    @Test
    fun `when Mo moves himself first nothing is moved`() = runTest {
        val fake = Fake(mapOf(forFile to srt(cues(shiftMs = 3_200))), downloadMs = 5_000)
        fun position(): Long {
            val now = testScheduler.currentTime
            return when {
                now < 1_000 -> 0L
                now < 3_000 -> start + now - 1_000
                else -> 400_000 + now - 3_000
            }
        }
        val plan = fake.check { testScheduler.currentTime }.run(target, extras, emptyList(), { position() }, { true }) { fake.seeks += it }
        assertTrue(fake.seeks.isEmpty())
        assertEquals("Kept the clip time: you moved yourself", plan.note)
    }

    @Test
    fun `the stream's own subtitles come first and a tiny difference is not worth a seek`() = runTest {
        val fake = Fake(mapOf(own to srt(cues(shiftMs = 400))))
        val ownSubtitles = listOf(StreamSubtitle(own, "en"), StreamSubtitle("file:///local/own.srt", "en"))
        val plan = fake.check { testScheduler.currentTime }.run(target, extras, ownSubtitles, { playing() }, { true }) { fake.seeks += it }
        assertTrue(fake.seeks.isEmpty())
        assertEquals("Kept the clip time: this video's subtitles agree (+0.4 s)", plan.note)
        assertEquals("this stream's own English subtitles", plan.detail)
        assertEquals(listOf(own), fake.downloads)
    }

    @Test
    fun `no file made for this video keeps the clip time and downloads nothing`() = runTest {
        val noName = Fake(emptyMap())
        val plan = noName.check { testScheduler.currentTime }.run(target, null, emptyList(), { playing() }, { true }) { noName.seeks += it }
        assertEquals("Kept the clip time: no subtitles for this video", plan.note)
        assertEquals("the stream gives no file name, size or hash", plan.detail)
        assertEquals(listOf<SubtitleRequestExtras?>(null), noName.asked)
        val same = Fake(emptyMap(), forFileList = listOf(link(matched), link(forFile)))
        val samePlan = same.check { testScheduler.currentTime }.run(target, extras, emptyList(), { playing() }, { true }) { same.seeks += it }
        assertEquals("Kept the clip time: this video's subtitles are the file Nuvio matched with", samePlan.note)
        assertTrue(noName.downloads.isEmpty() && same.downloads.isEmpty() && noName.seeks.isEmpty() && same.seeks.isEmpty())
    }

    @Test
    fun `lines that are not in this video's subtitles keep the clip time`() = runTest {
        val fake = Fake(mapOf(forFile to srt(cues(lines = ClipTestText.cueTexts(999, count = 80)))))
        val plan = fake.check { testScheduler.currentTime }.run(target, extras, emptyList(), { playing() }, { true }) { fake.seeks += it }
        assertEquals("Kept the clip time: the clip's lines are not in this video's subtitles", plan.note)
        assertTrue(fake.seeks.isEmpty())
    }

    @Test
    fun `a player that never reaches the clip time is left alone after 60 s`() = runTest {
        val fake = Fake(mapOf(forFile to srt(cues(shiftMs = 3_200))))
        val plan = fake.check { testScheduler.currentTime }.run(target, extras, emptyList(), { 0L }, { true }) { fake.seeks += it }
        assertEquals("Kept the clip time: the player did not reach the clip time within 60 s", plan.note)
        assertTrue(fake.seeks.isEmpty())
    }

    @Test
    fun `which file is this video's`() {
        val usual = link(matched)
        val other = link("https://subs.example.test/other.srt")
        val hashed = link("https://subs.example.test/hashed.srt", hash = true)
        val french = ClipSubtitleLink("https://subs.example.test/fr.srt", "fre")
        fun choose(forFile: List<ClipSubtitleLink>?, matchedUrl: String = matched) =
            ClipPlayCheck.choose(emptyList(), forFile, listOf(usual, other), matchedUrl)
        assertEquals(hashed, choose(listOf(other, hashed)).link)
        assertEquals("Sample Subs: found by this file's hash", choose(listOf(other, hashed)).detail)
        assertEquals(other, choose(listOf(french, other, usual)).link)
        assertEquals("this video's subtitles are the file Nuvio matched with", choose(listOf(usual, other)).why)
        // From an older cache the matched file is not known: the add-on's usual first file stands in for it.
        assertNull(choose(listOf(usual, other), matchedUrl = "").link)
        assertEquals("the add-ons gave their usual list, not one for this file", choose(listOf(usual), matchedUrl = other.url).detail)
        assertEquals("the add-ons list no English subtitles for this file", choose(listOf(french)).detail)
        assertEquals("the stream gives no file name, size or hash", choose(null).detail)
    }

    @Test
    fun `the time, the speed and the shift limits in the note`() {
        assertEquals("+3.2 s", ClipPlayCheck.signedSeconds(3_200))
        assertEquals("-0.4 s", ClipPlayCheck.signedSeconds(-449))
        assertEquals("; this video plays 4.3% faster", ClipPlayCheck.speedNote(23.976 / 25.0))
        assertEquals("", ClipPlayCheck.speedNote(1.0))
        val far = ClipAlign.Alignment(listOf(ClipAlign.Hit(100_000, 500_000), ClipAlign.Hit(104_000, 504_000)), 1.0)
        assertEquals(
            ClipPlayPlan(null, "Kept the clip time: the matching lines are 6:40 away, too far to trust", "d"),
            ClipPlayCheck.decide(85_000, far, "d"),
        )
    }

    @Test
    fun `the player checks an answer once per launch, and only the launch it opened`() {
        val answer = ClipAnswer(
            ClipCandidate("tt001:2:5", 2, 5, 100_000, 140_000, 0.9, 20, true),
            ShowGuess("tt001", "series", "Made Up Show"),
            episode = ClipEpisode("tt001:2:5", "tt001:2:5", "series", 2, 5),
            anchors = target.anchors,
            subtitle = link(matched),
        )
        ClipPlayTargets.arm(answer, start)
        assertEquals(target, ClipPlayTargets.forPlayer(7L, "tt001", 2, 5, start))
        assertNull(ClipPlayTargets.forPlayer(7L, "tt001", 2, 5, start))
        assertNull(ClipPlayTargets.forPlayer(8L, "tt001", 2, 5, 600_000))
        assertNull(ClipPlayTargets.forPlayer(9L, "tt001", 2, 6, start))
        assertNull(ClipPlayTargets.forPlayer(null, "tt001", 2, 5, start))
    }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipStreamRankTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import com.nuvio.app.features.player.SubtitleSyncCue
import com.nuvio.app.features.streams.StreamBehaviorHints
import com.nuvio.app.features.streams.StreamItem
import com.nuvio.app.features.streams.StreamSubtitle
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** Made-up release names, groups and addresses only. */
class ClipStreamRankTest {
    private val englishSubs = listOf(StreamSubtitle("https://cdn.example.test/own.srt", "eng"))

    private fun stream(name: String, title: String? = null, file: String? = null, hash: String? = null, subs: List<StreamSubtitle> = emptyList()) =
        StreamItem(
            name = name,
            title = title,
            addonName = "Sample",
            addonId = "sample",
            behaviorHints = StreamBehaviorHints(videoHash = hash, filename = file),
            externalSubtitles = subs,
        )

    @Test
    fun `a release name gives its source family, group and resolution`() {
        assertEquals(ClipRelease("web", "GRP", "hd"), ClipRelease.of("Made.Up.Show.S02E05.720p.WEB-DL.x264-GRP.srt"))
        assertEquals(ClipRelease("bluray", null, "hd"), ClipRelease.of("made up show 2x05 BluRay 1080p"))
        assertEquals(ClipRelease("hdtv", "XYZ", null), ClipRelease.of("Made Up Show S02E05 HDTV-XYZ"))
        assertEquals(ClipRelease("web", "GRP", "hd"), ClipRelease.of("Made Up Show S02E05 720p WEB-DL DDP5.1 H.264-GRP"))
        assertEquals(ClipRelease(null, null, "uhd"), ClipRelease.of("Sample 4K"))
        assertFalse(ClipRelease.of("12345678").known)
        assertFalse(ClipRelease.of("").known)
    }

    private val bluray = stream("Sample 1080p", file = "Made.Up.Show.S02E05.1080p.BluRay.x264-OTHER.mkv")
    private val sameRelease = stream("Sample 720p", title = "Made Up Show S02E05 720p WEB-DL DDP5.1 H.264-GRP\n1.2 GB")
    private val noName = stream("Sample 4K")
    private val otherWeb = stream("Sample 1080p", title = "Other", file = "Made.Up.Show.S02E05.1080p.WEB.h264-NEW.mkv")

    @Test
    fun `with the matched subtitle's release name the same release is pinned and tagged`() {
        val pick = ClipStreamRank.pick(listOf(bluray, sameRelease, noName, otherWeb), "Made.Up.Show.S02E05.720p.WEB-DL.x264-GRP")
        assertEquals(sameRelease, pick.pinned)
        assertEquals(setOf(sameRelease), pick.tagged)
        assertEquals("best match: 1 of 4 streams, same release as the matched subtitle (web, GRP, hd)", pick.note)
        // Without it, the same source family and resolution are the next best thing.
        assertEquals(otherWeb, ClipStreamRank.pick(listOf(bluray, noName, otherWeb), "Made.Up.Show.S02E05.720p.WEB-DL.x264-GRP").pinned)
    }

    @Test
    fun `no stream of the matched subtitle's release leaves the list as it is`() {
        val pick = ClipStreamRank.pick(listOf(bluray, sameRelease, noName, otherWeb), "Made Up Show S02E05 HDTV-XYZ")
        assertNull(pick.pinned)
        assertTrue(pick.tagged.isEmpty())
        assertEquals("no stream has the matched subtitle's release (hdtv, XYZ); order unchanged", pick.note)
    }

    @Test
    fun `without a release name the streams the player can check go first`() {
        val ownSubs = stream("Sample A", subs = englishSubs)
        val ownSubsToo = stream("Sample B", subs = englishSubs)
        val hashed = stream("Sample C", hash = "0123456789abcdef")
        val frenchOrLocal = stream("Sample D", subs = listOf(StreamSubtitle("https://cdn.example.test/fr.srt", "fre"), StreamSubtitle("file:///own.srt", "eng")))
        val pick = ClipStreamRank.pick(listOf(noName, ownSubs, hashed, frenchOrLocal, ownSubsToo), "")
        assertEquals(ownSubs, pick.pinned)
        assertEquals(setOf(ownSubs, ownSubsToo), pick.tagged)
        assertEquals("best match: 2 of 5 streams, own subtitles or a file hash (the matched subtitle has no release name)", pick.note)
        assertEquals(hashed, ClipStreamRank.pick(listOf(noName, hashed, frenchOrLocal), "").pinned)
        val none = ClipStreamRank.pick(listOf(noName, frenchOrLocal), "")
        assertNull(none.pinned)
        assertEquals("the matched subtitle has no release name and no stream has its own subtitles or a file hash; order unchanged", none.note)
        assertNull(ClipStreamRank.pick(emptyList(), "").pinned)
    }

    @Test
    fun `at most five streams are tagged`() {
        val many = List(7) { stream("Sample $it", subs = englishSubs) }
        assertEquals(ClipStreamRank.MAX_TAGS, ClipStreamRank.pick(many, "").tagged.size)
    }

    @Test
    fun `a subtitle add-on's answer keeps the release name and the hash mark when they are sent`() {
        val json = """
            {"subtitles":[
              {"id":"1","url":"https://subs.example.test/a.srt","lang":"eng","m":"h","SubEncoding":"UTF-8"},
              {"id":"2","url":"https://subs.example.test/b.srt","lang":"fre","releaseName":"Made.Up.Show.S02E05.720p.WEB-DL-GRP"},
              {"id":"3","lang":"eng"},
              "not an entry"
            ]}
        """.trimIndent()
        assertEquals(
            listOf(
                ClipSubtitleLink("https://subs.example.test/a.srt", "eng", source = "Sample Subs", hashMatch = true),
                ClipSubtitleLink("https://subs.example.test/b.srt", "fre", source = "Sample Subs", release = "Made.Up.Show.S02E05.720p.WEB-DL-GRP"),
            ),
            ClipSubtitleList.parse(json, "Sample Subs"),
        )
        assertTrue(ClipSubtitleList.parse("not json", "Sample Subs").isEmpty())
        assertTrue(ClipSubtitleList.parse("""{"streams":[]}""", "Sample Subs").isEmpty())
    }

    @Test
    fun `the subtitle cache remembers which file the cues came from, and older entries say nothing`() {
        val link = ClipSubtitleLink("https://subs.example.test/a.srt", "eng", source = "Sample\tSubs", release = "Made.Up.Show.S02E05")
        val cues = listOf(SubtitleSyncCue(0, 1_000, "made up words here"))
        val entry = EpisodeSubtitleSource.linkLine(link) + EpisodeSubtitleSource.encodeCues(cues)
        assertEquals(link.copy(source = "Sample Subs"), EpisodeSubtitleSource.decodeLink(entry))
        assertEquals(cues, EpisodeSubtitleSource.decodeCues(entry))
        assertNull(EpisodeSubtitleSource.decodeLink(EpisodeSubtitleSource.encodeCues(cues)))
    }
}
```

##### File: `composeApp/src/commonTest/kotlin/com/nuvio/app/features/clipfinder/ClipShowPickerTest.kt`
```kotlin
package com.nuvio.app.features.clipfinder

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlin.test.assertTrue
import kotlinx.coroutines.test.runTest

/** Names, ids and addresses here are made up, except "Modern Family" as in the other Clip finder tests. */
class ClipShowPickerTest {
    private val remembered = ShowGuess("tt100", "series", "Modern Family")
    private val family = ShowGuess("tt100", "series", "Modern Family", "https://img.example.test/mf.jpg", year = "2009")
    private val tides = ShowGuess("tt777", "movie", "Modern Tides", year = "1990")
    private val other = ShowGuess("tt003", "series", "Other Thing")
    private val asked = mutableListOf<String>()

    private fun picker(search: (String) -> List<ShowGuess> = { listOf(family, tides) }, known: () -> List<ShowGuess> = { listOf(other, remembered) }) =
        ClipShowPicker({ query -> asked += query; search(query) }, { known() })

    @Test
    fun `a squashed name lists the known title with the catalog's poster and year, then other search results`() = runTest {
        assertEquals(listOf(family, tides), picker().pick("  modernfam "))
        assertEquals(listOf("modernfam"), asked)
    }

    @Test
    fun `fewer than two letters list nothing and ask nothing`() = runTest {
        assertTrue(picker().pick("m").isEmpty())
        assertTrue(picker().pick(" ?! ").isEmpty())
        assertTrue(asked.isEmpty())
    }

    @Test
    fun `a failing search still lists the known titles`() = runTest {
        assertEquals(listOf(remembered), picker(search = { error("offline") }).pick("Modern family"))
        assertEquals(listOf(family, tides), picker(known = { error("broken") }).pick("modern"))
    }

    @Test
    fun `at most eight picks, best first`() = runTest {
        val many = List(12) { ShowGuess("tt2$it", "series", "Made Up Show $it") }
        val picks = picker(search = { many }, known = { emptyList() }).pick("made up")
        assertEquals(ClipShowPicker.MAX_PICKS, picks.size)
        assertEquals("tt20", picks.first().metaId)
    }

    @Test
    fun `a picked show is the only suspect and nothing is searched`() = runTest {
        val searched = mutableListOf<String>()
        val finder = ClipShowFinder({ query -> searched += query; listOf(other) }, { listOf(other) }, ClipMemory({ null }, {}, { 0L }))
        val found = finder.find(ClipClues(typed = "modernfam", picked = family), emptyList())
        assertEquals(listOf(ClipSuspect(family, ClipShowFinder.PICKED_SCORE, "picked")), found)
        assertTrue(searched.isEmpty())
    }

    @Test
    fun `the year and the kind under the name`() {
        assertEquals("2009", clipYear("2009-2020"))
        assertEquals("2009", clipYear("2009–"))
        assertNull(clipYear(""))
        assertNull(clipYear(null))
        assertEquals("2009 · Series", clipPickDetail(family))
        assertEquals("Movie", clipPickDetail(ShowGuess("tt9", "movie", "Made Up Film")))
    }
}
```

#### I. On the phone (after the Mac build), risks, and what the screen shows
Try it (no new permission prompt):
1. Share the Modern Family clip. When it asks, or after it answers, type "modern fam" in "Know the show?": within a
   second the list shows Modern Family with poster and "2009 · Series". Tap it: "Searching" runs, "Listening" does
   not. Details: `Matched subtitle: OpenSubtitles v3: no release name given` (expected, decision 1).
2. Tap the answer, then look at the stream list: `Stream order` in Details (open Clip finder again to read it); a
   "Best match for the clip" card on top only when that line starts "best match". A show opened from Home: no card.
3. Tap a stream. Within about 20 s a toast: "Moved to the matching line ... (+x s)" or "Kept the clip time: <why>".
   Details: `Player` (the same text) and `Player subtitles` (which file, or why none).
4. Again, but seek away in the first seconds: no jump back; toast "Kept the clip time: you moved yourself".
Send a screenshot of Details after each.

Top ways it can fail, and what the screen then shows:
1. `Player subtitles: the add-ons gave their usual list, not one for this file` every time: OpenSubtitles v3 ignores
   the file name without a hash (iOS sends no hash of its own). The check then never moves; nothing is wrong, the
   15 s lead-in carries it. Next step (Later): compute the OpenSubtitles hash on iOS, or test each stream's own file.
2. A jump to a wrong place: the `Player` line shows the shift (refused above 5 min). Send it with the episode; the
   anchors (4+ words, 2 agreeing pairs, half of all) are the tuning knob, in `ClipAlign` only.
3. No toast at all: the player was not opened from the answer (another episode, "Resume" elsewhere) or the toast
   host is behind the player; Details still has `Player`. No `Player` line either: the launch did not match (start
   time changed on the way), see `ClipPlayTargets.forPlayer`.
4. "the player did not reach the clip time within 60 s": the player started somewhere else (its own resume) or
   buffered for a minute; nothing was moved.
5. The pick list stays empty: the catalogs did not answer; the "Search this show" button still works as before.

ASSUMPTIONS (cannot be checked from here)
- E1 The Kotlin compiles; it only uses what is listed in section B.
- E2 OpenSubtitles v3's answer shape of decision 1 (about 80% sure); `Matched subtitle` and `Player subtitles` show
  the truth on the phone.
- E3 `initialSeekApplied` turns true once the player's own first seek is done and `playbackSnapshot.positionMs`
  follows playback (read in `PlayerScreenRuntimeState.kt`, not run).
- E4 `NuvioToastController` toasts show above the player.
- E5 `StreamsScreen` shows any non-null `LocalSharedStream` as a header and a card on top (read, not run).
- E6 With an external player (VLC, Infuse) Nuvio's player does not open, so nothing is checked: the 15 s lead-in only.

## Later (parked, not v1)
- "Listen" mode: Nuvio records ~10 s of any app's sound through iOS screen broadcast. Works
  for every app and never breaks when a site changes, but takes more taps.
- ShazamKit: recognise the show's theme song or soundtrack in the clip (needs a new app capability and a
  signing change). Parked by Mo 2026-11-16.
- Candidates from Continue Watching and the library, and episodes near Mo's watch progress first: dropped by Mo
  on 2026-11-16 (what TikTok shows him is not what he watches).
- Clip finder memory: a "forget" button; counting shows per poster instead of keeping the last one.
- More popular titles (second catalog page, more catalogs); the poster's display name as a clue; the sound
  title as a search phrase when it is not "original sound".
- The new iOS 26 SpeechAnalyzer for listening; more or smarter frame times for the text on screen.
- A list of past clips. Android. Other languages. Mirrored caption reading.
- Fold the three older patches and this one into fewer, smaller patches.
- From 7c-7d (each comes back when the named Details line shows the need): stop listening early once a match is
  confident (`listen` over half of `total`); a sliding window of 6 subtitle files instead of batches (`subtitles`
  long with few episodes); reading frames while the clip downloads (`frames` over 3 s); Instagram's GraphQL route
  (all three `Instagram` tries say `video key no`); another YouTube captions route if every video says `captions
  need YouTube's token`; YouTube captions in other languages (with milestone 8); split `ClipFinderPipeline.kt`
  (341 lines) by moving the native `call` into its own file.
- From 7e: compute the OpenSubtitles file hash on iOS (`computeVideoHash` returns null there), so the add-ons can
  name this video's own subtitle file (when `Player subtitles` keeps saying "their usual list"); check each stream's own
  subtitle file before playing instead of after; a real reorder of the stream list by best match (needs a
  `StreamsScreen` edit).
