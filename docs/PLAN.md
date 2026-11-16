Done: 3 | Last cleanup: none | Mac builds used: 1 of about 5 (milestone 3 verified on Mo's phone 2026-11-15 from branch clip-finder-share, draft PR #3)
Next: milestones 4, 5 and 6 are built together on clip-finder-share and tested with ONE Mac build (see "Milestones 4-6 implementation notes"). Merge to cmp-rewrite only after that build passes on the phone.

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

- [ ] **7. Fallbacks, tuning, ship** (Mac build 5)
  - Build: type-the-show fallback (SPEC 7), clear failure messages (SPEC 8), 60 s stage
    limit with a message, tune matcher thresholds on Mo's real clips, add a Clip finder
    section to FORK.md.
  - Less reliance on the caption (Mo, 2026-11-16; waiting on his pick): (1) try Continue
    Watching and library shows as candidates first, (2) also use the poster's name and
    hashtags, (3) type-the-show box when nothing matches, keeping what was heard. Never stop
    at "no caption". Parked: (4) Apple Vision text on video frames ("Suits S2E5" overlays).
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
