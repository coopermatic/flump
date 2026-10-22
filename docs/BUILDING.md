# Building and validating Flump

This procedure preserves the application source, SWF version 30, AIR descriptor namespace
21.0, bundled libraries, UI and export formats. New files go in `exporter/build/`.
**Do not overwrite `exporter/dist/`: it contains the previous release for comparison.**
See [AUDIT.md](AUDIT.md) for evidence and the current validation status. These instructions
include Mac steps that still need execution on a Mac; they are not a compatibility certification.
These are developer instructions. Use [MAC-DISTRIBUTION.md](MAC-DISTRIBUTION.md) for
GitHub-hosted Mac builds from Windows and [INSTALL-MAC.txt](INSTALL-MAC.txt) for the designer.
The designer must not compile, sign, package or rebuild the application.

## Toolchain

| Component | Baseline | Notes |
| --- | --- | --- |
| Java | 17, matching the build host architecture | Java 17.0.19 is available inside Animate on the audit PC. A standalone JDK 17 is preferable for other developers. |
| Apache Ant | 1.10.15 | Download the binary ZIP/TAR from Apache; no Maven installation is needed for the exporter. |
| Apache Flex | 4.16.1, build 20171115 | Matches the ProductInfo compiler metadata in the tracked Flump SWF. Do not use the obsolete README recommendation of Flex 4.6 for this baseline. |
| AIR SDK | 51.4.1.2 tested on Windows; minimum 51.3.3.1 for the documented `air4mac` route | Install the desktop components for the host OS through the official SDK Manager. Pin the full version actually validated. Later versions require a fresh regression pass. |
| AIR overlay | Same AIR version as the packaging SDK | In SDK Manager, use the installed SDK's cog menu > Flex SDK Overlay on a **copy** of Flex 4.16.1. Keep the original compiler and Flex framework. |
| Python | 3.9+ (optional) | Only needed for the export-comparison helper. |
| macOS packaging | macOS, Xcode command-line tools, existing Developer ID Application identity | Use an ARM64 JDK on M-series Macs. Windows cannot validate macOS execution or perform Apple's native signing. |

AIR SDK download: [official download page](https://airsdk.harman.com/download)
(the vendor redirects this to its current hosting domain),
[SDK Manager releases](https://github.com/airsdk/airsdkmanager-releases/releases).
Complete the vendor licence flow and use the appropriate commercial licence for your organisation.
Do not commit SDK licence files or signing material.

[Apache Flex 4.16.1 binary archive](https://archive.apache.org/dist/flex/4.16.1/binaries/)
and [Apache Ant 1.10.15 binary archive](https://archive.apache.org/dist/ant/binaries/).
Hashes of the Windows archives inspected in this audit:

```text
apache-flex-sdk-4.16.1-bin.zip
SHA256 757aa19299c8a9c8af0901c1ae35f97fa94b7af0b0a9abc2bab04fe61d756e8b
apache-ant-1.10.15-bin.zip
SHA256 e59baf898dc5b6d1aa6cd57544715f7e0060b1fdc9e56f24f9898d56612a9e0b
```

Flex's published MD5 and Ant's published SHA-512 also matched at download time.
The six `exporter/lib/*.swc.sha256` files pin the libraries already supplied by the fork.
`ant verify-libs` checks them without using the network. Do not rebuild the game runtime or
upgrade Starling/as3corelib/aspire to rebuild the exporter.

After overlay, verify these files exist:

```text
FLEX_HOME/lib/mxmlc.jar
FLEX_HOME/frameworks/air-config.xml
FLEX_HOME/frameworks/libs/air/airglobal.swc
AIR_HOME/lib/adt.jar
AIR_HOME/bin/adl64.exe     (Windows x64; adl.exe is the 32-bit launcher)
AIR_HOME/bin/adl           (macOS)
```

Set `FLEX_HOME` to the overlaid Flex directory and `AIR_HOME` to the installed AIR SDK.
Use the **same AIR version** for compilation, ADL tests and packaging. The build explicitly
sets Flex's `airHome` token to the overlay, so an unrelated global SDK will not silently supply APIs.
`check-air` prints ADT's version; confirm it against the chosen pinned version before proceeding.
The build does not enforce a numeric SDK minimum; choosing an older SDK is outside this procedure.


### Minimal compiler overlay used in this audit

The SDK Manager overlay is the supported general setup. For this exact exporter, the tested
local overlay was narrower: retain Apache Flex's compiler and `air-config.xml`; copy AIR's
`frameworks/libs/air/*` into the same Flex subdirectory, and copy `lib/afe.jar` and
`lib/aglj40.jar` into Flex's `lib`. Do this only to a disposable Flex copy. It avoids replacing
Flex's MXML configuration with the AIR-only compiler configuration.

```powershell
Copy-Item -Path "$env:AIR_HOME/frameworks/libs/air/*" -Destination "$env:FLEX_HOME/frameworks/libs/air" -Force
Copy-Item -LiteralPath "$env:AIR_HOME/lib/afe.jar","$env:AIR_HOME/lib/aglj40.jar" -Destination "$env:FLEX_HOME/lib" -Force
```

Equivalent on macOS (still to be tested there):

```bash
cp -R "$AIR_HOME/frameworks/libs/air/." "$FLEX_HOME/frameworks/libs/air/"
cp "$AIR_HOME/lib/afe.jar" "$AIR_HOME/lib/aglj40.jar" "$FLEX_HOME/lib/"
```

## Windows build

From the repository root, in PowerShell (replace the example tool paths):

```powershell
$env:JAVA_HOME = 'C:\Tools\jdk-17'
$env:ANT_HOME = 'C:\Tools\apache-ant-1.10.15'
$env:FLEX_HOME = 'C:\Tools\flex-4.16.1-air-51.4.1.2'
$env:AIR_HOME = 'C:\Tools\AIRSDK-51.4.1.2'
$env:PATH = "$env:JAVA_HOME\bin;$env:ANT_HOME\bin;$env:PATH"
java -version
ant -version
ant -f exporter/build.xml check-air verify-libs
ant -f exporter/build.xml swf test-swf
ant -f exporter/build.xml test
ant -f exporter/build.xml run
# Populate these securely from your existing signing setup, without logging the password:
# FLUMP_SIGNING_KEYSTORE = absolute path to an approved existing PKCS12 file
# FLUMP_SIGNING_PASSWORD = its password (process environment only)
ant -f exporter/build.xml bundle-windows
```

Close the ADL application to let `run` finish. Tests use the separate `flump.tests` application ID, avoiding invocation forwarding to a running Flump.
The integration suite requires a working desktop
and Stage3D; `test` fails on a nonzero ADL exit or a two-minute timeout. A timeout is a failure,
not proof that a fixture is malformed. It can be increased explicitly with `-Dtest.timeout=240000`.

Expected outputs:

- `exporter/build/flump-exporter.swf`: application bytecode, not a standalone executable.
- `exporter/build/flump-test.swf`: integration suite.
- `exporter/build/flump-exporter.airi`: optional unsigned intermediate produced by `prepare-package`, not an installable `.air` file.
- `exporter/build/windows/Flump/Flump.exe` with the complete captive-runtime directory.

The Windows bundle is portable and does not require a separately installed AIR runtime. Copy
or ZIP the **whole** `Flump` directory, not just the EXE. Test it in a new location before using
it in production. This local bundle is not Authenticode-signed and may show Windows reputation warnings; public
code signing and an MSI/EXE installer are separate distribution tasks. File associations are
not installed merely by copying a portable folder. No new signing keys are generated. ADT still requires an **AIR package signature**, even
though the EXE is not Authenticode-signed. Supply an existing approved PKCS12 path/password
through `FLUMP_SIGNING_KEYSTORE` and `FLUMP_SIGNING_PASSWORD`. Ant passes the password to ADT's
stdin prompt, not its command-line arguments. Never run verbose/debug Ant logging while these
secrets are in the environment; clear them afterwards. The build has no default credential.
`-Dtsa=none` is the default for a local test candidate. Set an approved timestamp service explicitly
for a distribution build and validate its signature/update behaviour before release.

The audit build reused the fork's existing signing material locally, without changing it or
printing its password. Do not treat a repository-stored private key as a production trust anchor;
review release-signing ownership separately.

ADT 51.4.1.2 rejected unsigned AIRI-to-bundle conversion and threw a Windows null-descriptor
exception when converting the tracked signed `.air`. `bundle-windows` therefore signs and
packages **directly from the descriptor and compiled files**. Do not use the AIRI conversion
shortcut for this SDK. The optional `prepare-package` target is for separate signing workflows.

## macOS build and signing

For an initial **packaging-only** migration test, no Flex installation is needed. Configure
Java, Ant and the macOS `AIR_HOME`, then run:

```bash
ant -f exporter/build.xml \
  '-Dmac.signing.alias=Developer ID Application: YOUR ORGANISATION (TEAMID)' \
  repackage-macos
bash bin/verify-macos.sh exporter/build/macos-existing/Flump.app
```

This untested Mac target is intended to convert the preserved `exporter/dist/flump-exporter.air` into a captive universal bundle,
keeping its compiled SWF unchanged. Use this path instead of `macos/Flump.app` in the subsequent
signing/notarisation checks if testing that candidate. It still requires functional and native
process verification; repackaging does not prove the existing SWF has no runtime regressions.
If this conversion fails, use the direct source-build route below; AIR-to-bundle conversion
failed in ADT 51.4.1.2 on Windows, while direct descriptor/file packaging succeeded there.

On the build owner's Mac environment (normally the GitHub ARM64 runner), use the
macOS AIR SDK and an ARM64 JDK. From the repository root:

```bash
export JAVA_HOME="/path/to/arm64-jdk-17/Contents/Home"
export ANT_HOME="/path/to/apache-ant-1.10.15"
export FLEX_HOME="/path/to/flex-4.16.1-air-51.4.1.2"
export AIR_HOME="/path/to/AIRSDK-51.4.1.2"
export PATH="$JAVA_HOME/bin:$ANT_HOME/bin:$PATH"
java -version
ant -version
ant -f exporter/build.xml check-air verify-libs
ant -f exporter/build.xml swf test-swf test
ant -f exporter/build.xml \
  '-Dmac.signing.alias=Developer ID Application: YOUR ORGANISATION (TEAMID)' \
  bundle-macos
bash bin/verify-macos.sh exporter/build/macos/Flump.app
```

The signing identity must already exist, with its private key, in your Mac's Keychain. Select
its exact name locally; do not paste private keys, certificate passwords or Apple credentials
into source files or logs. The Mac build uses the Keychain identity for AIR signing before `-target bundle` and for
**native** signing after it, packaging directly from the descriptor and compiled files.
It does not require the historical repository PFX or generate credentials. ADT can then sign
the application and its embedded runtime. No `-arch x64` option is applied to macOS;
the SDK's universal runtime is retained. The verification helper requires both `arm64` and
`x86_64` in each Mach-O file and a valid bundle signature.

Inspect the signing details printed by the helper: the intended Developer ID authority,
secure timestamp and hardened runtime must be present. Inspect entitlements locally with:

```bash
codesign -d --entitlements :- exporter/build/macos/Flump.app
```

AIR's JIT needs appropriate runtime entitlements. Let the current ADT supply its AIR-specific
signing configuration; do not arbitrarily add broad entitlements or ad-hoc re-sign an app intended
for distribution. If validation/notarisation fails, inspect the exact rejected binary and the
notarisation log before changing the descriptor. The original descriptor remains at AIR 21.0;
HARMAN's 51.3.3.1 notes explicitly say its changes do not require a namespace update.

## Notarisation and installation (manual distribution gate)

These commands are for a developer with the team's existing signing/notary setup, **after** local
verification and approval to submit/distribute. No notarisation upload or release publication is
performed by Ant. `flump-notary` below is the name of an existing local Keychain credential profile,
not a password. Use Apple's current `notarytool`; old tutorials using `altool` are obsolete.

```bash
ditto -c -k --keepParent exporter/build/macos/Flump.app exporter/build/macos/Flump-notarize.zip
xcrun notarytool submit exporter/build/macos/Flump-notarize.zip \
  --keychain-profile flump-notary --wait
# Require status Accepted; inspect the returned submission ID's log, including warnings:
xcrun notarytool log SUBMISSION_ID --keychain-profile flump-notary \
  exporter/build/macos/notarization-log.json
xcrun stapler staple exporter/build/macos/Flump.app
xcrun stapler validate exporter/build/macos/Flump.app
spctl --assess --type execute --verbose=4 exporter/build/macos/Flump.app
# ZIP must be recreated after stapling; the ticket attaches to the app, not the ZIP.
ditto -c -k --keepParent exporter/build/macos/Flump.app exporter/build/macos/Flump-mac-universal.zip
```

A notarised ZIP can be unzipped and the app copied to `/Applications`. Keep the previous Flump
installation backed up until validation passes. An optional wizard installer needs a separate
**Developer ID Installer** identity:

```bash
productbuild --sign 'Developer ID Installer: YOUR ORGANISATION (TEAMID)' \
  --component exporter/build/macos/Flump.app /Applications exporter/build/macos/Flump.pkg
```

Submit that PKG with `notarytool`, require `Accepted`, then staple and validate the PKG. Test the
actual downloaded/distributed archive with Gatekeeper enabled; a locally built app has different
quarantine history. Do not disable Gatekeeper as the installation procedure.

## Why `air4mac` is different

The tracked conventional `.air` contains bytecode/resources and an AIR package signature, not
Apple-signed native launch files. With the 51.3.3.1 shared runtime, installing an old `.air` removes
the ARM64 slice and leaves an Intel application. Updating AIR alone is insufficient.

For users who must retain shared-runtime `.air` installation, SDK 51.3.3.1 added `air4mac`.
On a Mac, provide AIR signing options **before** `-target air4mac`, and native Developer ID
Application options **after** it. It requires a 51.3.3+ shared runtime for native Apple Silicon
installation. Windows 51.3.3+ ignores its extra Mac signing files. This is an optional route,
not the default build here, and has not been executed during this audit:

```bash
cd exporter
"$AIR_HOME/bin/adt" -package \
  -storetype pkcs12 -keystore /outside/repo/approved-air-signing.p12 \
  -target air4mac \
  -storetype KeychainStore -alias 'Developer ID Application: YOUR ORGANISATION (TEAMID)' \
  build/Flump-shared-mac.air etc/airdesc.xml \
  icons/icon_16.png icons/icon_32.png icons/icon_48.png icons/icon_128.png \
  -C build flump-exporter.swf
```

ADT prompts for the AIR signing password; do not add it to shell history or verbose logs.
The preferred Mac bundle route avoids shared-runtime version drift and uses the existing Keychain identity for both signing stages.
An AIR signature, a native Developer ID signature and notarisation are different steps; one
does not substitute for the others. Installing an `air4mac` package still needs its own
Gatekeeper and native-process checks; do not infer them from the file extension.

## Repeatable functional verification

1. Preserve the old app and export its outputs first. Work on a **copy** of
   `exporter/src/test/resources`, or copies of approved production assets. Create a project in
   Flump rather than relying unchanged on the old `testconfig.flump`: that legacy example lacks
   the `scaleFactors` array required by the current config reader. A working generated example
   from this audit is `exporter/build/smoke/candidate.flump`; its inputs and exports are copies. Keep a distinct output directory for each build. Publishing can delete
   the selected output's prior atlas files, so never point a candidate at production exports.
2. Run `ant -f exporter/build.xml test`. The suite loads `bella.fla` (expected warnings) and
   the known-good `squaredance` XFL directory plus adjacent `squaredance.swf`. It publishes XML,
   JSON and JSONZip, reloads the JSONZip in the bundled Starling runtime, checks corrupt-input
   rejection and verifies playback controls/labels. Require the final `Passed:` list, no
   `Failed:` list, and exit zero. Outputs are below `exporter/build/test/`.
3. Launch the candidate **packaged** application. Open the copied test config; preview
   `squaredance`, export with identical JSON and JSONZip settings, and check atlas preview,
   playback, transparent edges and file-save/reopen behaviour. Repeat with at least one
   representative Peek & Poke animation containing nested movies, alpha, easing and flips.
4. Use a copy of a known-good project in the team's current Adobe Animate: publish an AS3 SWF
   alongside its FLA, import and export it. For XFL, use the document directory with
   `DOMDocument.xml` and `LIBRARY`, with the same-stem SWF alongside the directory. HTML5 Canvas
   output is not an AS3 SWF replacement. Do not resave/re-publish the checked-in fixtures.
5. Compare the old and candidate export directories, with the same input bytes/settings:

   ```bash
   python3 bin/compare-exports.py /path/to/baseline /path/to/candidate --byte-exact
   python3 bin/compare-exports.py /path/to/baseline /path/to/candidate
   ```

   On Windows use `python` if that is the installed command. The first check requires identical
   bytes. The second ignores JSON whitespace/key order and ZIP timestamps/compression, but
   checks JSON values and member names, and still requires byte-identical PNGs. Any difference
   needs inspection; do not update the baseline merely to make a check pass. The comparator
   is not a replacement for importing the outputs into a representative existing game.
6. On the M4, run `verify-macos.sh`, launch the exact packaged app and confirm **Kind = Apple**
   in Activity Monitor. Finder's Get Info > Open using Rosetta must be unchecked if offered.
   Universal file slices prove available architectures; Activity Monitor proves the architecture
   actually running. Test on an Apple Silicon Mac without Rosetta installed if one is available;
   do not remove Rosetta from a colleague's working machine just for this test.
7. Repeat the packaged-app test on Windows. Record OS version/build, architecture, SDK version,
   app hash, fixture/settings and export comparison results. Neither this audit nor an M4 test
   establishes compatibility with an unreleased macOS version.

The code contains more fixtures than the automated suite exercises (alpha, easing, skew,
mirroring, rotation and other FLA examples); include these in a manual regression pass.
A suspected malformed FLA should be tested separately from the known-good baseline.

The current suite is **not all green**: 13 tests pass and three looping-label tests fail on both
AIR 51.3.1.2 (x86) and AIR 51.4.1.2 (x86/x64). See AUDIT.md. Do not disable these assertions to
make the build appear green. The packaged app's squaredance export and visible preview pass;
this is narrower evidence than a clean full regression suite.

## Build record and maintenance

Save the Git commit/diff, `java -version`, `ant -version`, ADT `-version`, both SDK description
XML files, archive hashes, SWC hashes, test logs and candidate artifact hashes with each build.
Keep tool archives in approved internal storage subject to their licences. Pin a newer AIR
version only after the same comparisons pass; keep Flex and SWCs unchanged unless a demonstrated
problem requires a change. SWFs embed build timestamps and may include debug paths, so this is a
repeatable toolchain, not a promise of bit-identical SWF/signature/ZIP builds.

`package` now prepares the unsigned AIRI; use the explicit platform bundle target to get an app.
Legacy `genairkeystore`, `flexserver`, `package-test` and `clean` targets are not retained in the
exporter build. They depended on removed task registration, implicit credentials or destructive
`dist` cleanup. The existing runtime/demo Maven builds and Python 2/Nailgun scripts remain in
place for historical use but are not part of this exporter procedure. No runtime sources change.

## Primary references

- [HARMAN AIR 51.3.3.1 release notes](https://airsdk.harman.com/api/versions/51.3.3.1/release-notes/Release_Notes_AIR_SDK_51.3.3.pdf), sections 1, 3.4 (AIR-4887) and 7.
- [AIR maintainer explanation of native shared-runtime packaging](https://github.com/airsdk/Adobe-Runtime-Support/discussions/4256).
- [ADT packaging command reference](https://airsdk.dev/docs/building/air-developer-tool/commands/package).
- [AIR maintainer example of native signing after the bundle target](https://github.com/airsdk/Adobe-Runtime-Support/discussions/966).
- [Apple: signing with Developer ID](https://developer.apple.com/developer-id/).
- [Apple: customising the notarisation workflow](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow).
- [Apple: Rosetta availability and native apps](https://support.apple.com/en-us/102527).
