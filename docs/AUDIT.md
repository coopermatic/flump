# Flump audit and validation record

Audit date: **22 October 2026**. Repository: `coopermatic/flump`.
Starting revision: `987c277` on `master`. Work branch: `codex/native-air-build`.
Host: Windows; no macOS execution/signing environment is available in this session.

## Conclusion and evidence boundaries

There is no evidence requiring an application rewrite or a change to PNG/JSON serialization.
Native Apple Silicon is principally a **runtime and packaging** task for this application.
A current AIR SDK can package universal macOS bundles; the source uses no native extensions.
The Windows rebuild and export smoke test now pass. The Mac route is viable, **not a completed native-compatibility result**. The currently
tracked conventional `.air` is not sufficient evidence of native ARM64 operation.

HARMAN's 51.3.3.1 notes say older `.air` packages installed by that shared runtime are reduced
to x64; its new `air4mac` target supplies Apple-signed native installation files. The vendor
continues to recommend a signed captive `bundle`. This audit therefore provides both a rebuild
path and `repackage-macos`, which wraps the existing release without recompilation, preserving
its SWF byte for byte while isolating the runtime/packaging change.

Apple documents general Rosetta availability through macOS 27, with limited legacy-game use
thereafter. This motivates the native work; it is not a basis for claiming future macOS support.
See the primary sources in [BUILDING.md](BUILDING.md#primary-references).

## How the application works

- `Flump.mxml` is a Flex/Spark entry point; `FlumpApp` and the export controllers provide the
  desktop UI, configuration, previews and publishing.
- `FlaLoader` reads modern ZIP-based FLA contents through the vendored FZip library.
  `XflLoader` reads an uncompressed XFL document directory. Both load an associated published
  AS3 SWF. The exporter does not compile or publish an Animate document itself.
- `XflLibrary`, movie/layer/keyframe classes and the XFL XML describe animation structure,
  transforms, labels, easing and linkage. Instantiated SWF symbols supply artwork to rasterise.
  This is why a well-formed FLA with the expected Flump construction and a matching SWF matters.
- `TexturePacker` and its packers assemble atlases. `AtlasUtil` uses as3corelib's `PNGEncoder`.
  `PublishFormat` builds runtime model objects and JSON serialization; JSON, JSONZip and XML
  formats are selectable. JSON output includes `library.json` and atlas PNGs; JSONZip packages
  the export for the existing runtime. No serializer or packing algorithm was changed.
- Starling supplies GPU previews/runtime playback. All six vendored SWCs are ActionScript
  libraries. No `.ane`, `ExtensionContext`, `NativeProcess`, `HTMLLoader` or `StageWebView`
  dependency was found in exporter application source. This removes several common native
  migration blockers, but GPU/rasterisation behaviour still needs execution testing.

### Dependencies kept exactly as supplied

| Library | Supplied version |
| --- | --- |
| flump-runtime | 1.5.5 |
| as3corelib | 0.93 |
| aspire | 1.2.3 |
| fzip | a5430bd |
| react-as3 | 1.2.2 |
| starling-framework | 2.4 |

The supplied SWF's ProductInfo tag reports Flex **4.16**, build **20171115**. Apache Flex 4.16.1's
SDK description reports that exact build. Its SWF header reports version **30**. The README's
Flex 4.6 advice is therefore not an accurate description of the recent compiled release.
The six SWC files are preserved; individual SHA-256 sidecars provide a rebuild check.

The SWF embedded in the tracked AIR and the standalone tracked SWF have different file hashes.
Inspection of all 1,320 decompressed SWF tags found only the ProductInfo compilation timestamp
differs; no other tag differs. The packaging-only target deliberately uses the AIR's own payload.

## Fork history

The local history after upstream v1.5.5 (`f5655da`, 2018-08-18) contains:

| Commit | Date | Observed change and interpretation |
| --- | --- | --- |
| `4933c6c` | 2019-11-28 | Added a runtime link to README; no exporter change. |
| `4a61301` | 2026-04-15 | Message: "Update build files to run with latest flex/air". Replaced the exporter application's old compiler macro with direct `mxmlc.jar`, used local SWCs instead of Maven resolution, changed the timestamp endpoint, supplied compiled AIR/SWF and six SWCs, changed a signing file and changed the exporter POM's runtime version from a snapshot to 1.5.5. These are consistent with restoring a usable modern build, without altering application source. |
| `987c277` | 2026-04-27 | Replaced the developer's fixed SDK paths with home-relative Flex and AIR 51.3.1 paths. This is portability work, but still assumes machine-specific installation locations. |

`git diff f5655da..987c277` shows no changes to exporter application source or runtime source.
The bundled Starling 2.4 agrees with the existing runtime POM; it is not an upgrade introduced
by this audit. Commit messages describe intent; they do not establish which OS combinations
were tested or the actual AIR SDK version that signed the tracked release.

## Confirmed build problems and changes

1. **Unneeded remote bootstrap:** exporter `build.xml` ran `etc/bootstrap.xml` and imported a
   home-directory ooo-build installation even though the new application compiler no longer
   used it. The exporter now calls Java tools directly and consumes only the pinned local SWCs.
   Runtime/demo legacy builds remain untouched.
2. **Broken test task registration:** the fork removed `maventaskdef`, but `test-swf` still
   invoked `amxmlc`. Tests now use the same direct Flex compiler as the application.
3. **Release overwrite/deletion risk:** default compilation and `clean` targeted tracked
   `exporter/dist`. New output is `exporter/build`; no cleanup target removes old releases.
   A test-harness output-path adjustment keeps generated test exports there too. Fixtures are unchanged.
4. **Mixed SDK selection:** packaging invoked `adt.jar` from Flex, while ADL used a different
   AIR path. Packaging and execution now use the explicit `AIR_HOME`; compilation uses the
   explicitly selected Flex overlay. Instructions require matching AIR versions.
5. **Missing native packaging:** only a conventional shared-runtime `.air` target existed.
   New targets prepare optional AIRI, sign/package Windows x64 output directly from files, and create a Developer ID signed
   macOS bundle. `repackage-macos` can also preserve the existing release's bytecode verbatim.
6. **Implicit signing material:** old targets defaulted to the repository keystore and had a
   key-generation action. New targets have no default credential and do not generate keys. Windows signing requires
   explicit environment configuration and sends the password through stdin. The local candidate
   reused the existing signing material without altering it or exposing its password. Mac signing
   uses an existing Keychain identity. Historical signing files are preserved; new private-key files are ignored.
7. **Poor failure visibility:** ADL did not propagate failure through Ant and used a fixed `dist`
   argument. Tests now fail on errors/timeouts, use the correct OS executable name, and use the
   generated build directory. Windows tests select `adl64.exe`, matching the x64 bundle.
   The test descriptor now uses `flump.tests`, because its old `flump` ID caused invocations to
   be forwarded to a running real application. Missing tool/overlay errors are explicit.
8. **Outdated instructions:** README pointed to Adobe AIR and the upstream binary as the build
   solution. Dedicated build, signing, comparison and M4 verification instructions now replace it.

The application's descriptor stays at namespace 21.0, version 1.5.3 and ID `flump`, despite the
POM being 1.5.5. That pre-existing metadata mismatch is recorded, not silently "fixed": changing
identity/version can affect installed-app upgrades and preferences. Choose a release version
when a validated replacement is approved. The interface, production AS/MXML, runtime source,
FLA/XFL/SWF fixtures, SWCs, existing compiled releases and signing files remain unchanged. Only the test descriptor ID and test-output path change in the test harness.

## Obsolete or fragile components retained outside the build path

- `bin/asbuild` and `bin/localrepobuild.py` use Python 2 syntax, Unix path assumptions and a
  Nailgun/ooo-build workflow. They are not required to build the exporter now.
- Runtime/demo Maven tasks and remote repositories are legacy infrastructure. Rebuilding the
  exporter does not require redeploying the runtime; no game-engine changes were made.
- Flex 4.16.1 and its precompiled dependencies are old. The new procedure pins them for
  compatibility instead of upgrading them speculatively.
- Conventional `.air` installation depends on a mutable shared runtime and on the original AIR
  signing identity for some update scenarios. The portable/native bundle path changes that
  installation model; verify preference access, file opening and side-by-side installs.
- Graphics drivers, font availability, bitmap rendering and floating-point behaviour can differ
  across runtimes/architectures. These are regression-test concerns, not confirmed output bugs.

## Malformed-document reporting: recommendation only

Existing parsing already reports errors with library/movie/layer/frame context and distinguishes
warning/critical severities. Tests explicitly expect warnings in `bella.fla`; a warning does not
prove an AIR/ARM incompatibility.

There is a concrete diagnostic weakness in `FlaLoader.listLibrary`: it assumes
`DOMDocument.xml` and each referenced library ZIP entry exist before accessing their content.
Corrupt/unsupported archives can therefore surface low-level exceptions. A small, separate
future change could validate required entries, report the affected FLA and symbol path, and
ensure failed asynchronous parsing always settles the load future. Also distinguish a missing
or stale matching SWF from unsupported Animate content. Add malformed-input fixtures only as
part of that follow-up. **No error-reporting/application changes were implemented here.**
The colleague's problem file was not supplied, so its cause remains unverified.

## Validation record

| Check | Result in this session |
| --- | --- |
| Separate branch | Created `codex/native-air-build`; no merge, push or release publication. |
| Source/history and package inspection | Completed; traditional AIR archive has SWF/resources/AIR signature, no native Mac-signing payload. |
| Tool archives | Ant 1.10.15 and Flex 4.16.1 downloaded locally; Apache published checksums match. |
| Java / Ant execution | Java 17.0.19 and Ant 1.10.15 run on this Windows host. |
| `ant verify-libs` | PASS: all six pinned SWC hashes match. |
| Fixture static integrity | 39 nonempty XML files parse; seven MobileSettings XML files are empty and are not exporter inputs. All four FLAs' local ZIP entries pass CRC/size checks, their document and referenced symbol XML parses, and matching SWFs exist. This is not an import/export execution test. |
| Application and test compilation | PASS with Flex 4.16.1 + AIR 51.4.1.2. Initial missing-overlay preflight was resolved after SDK installation. |
| AIR setup | User installed `C:\Coopermatic\sdks\AIR\AIRSDK_51.4.1`; ADT reports 51.4.1.2. SDK Manager flow completed by the user; no download bypass. |
| Windows packaging | PASS: direct descriptor/file packaging using existing AIR signing material; native EXE and embedded AIR DLL are PE AMD64 (`0x8664`). Candidate is not Authenticode-signed. |
| ADL integration suite | 13 passed, 3 failed on AIR 51.4.1.2 x86/x64 and installed AIR 51.3.1.2 x86. Import/publish/load checks pass; looping-label assertions fail. No test suppression or runtime changes. |
| Packaged application smoke test | PASS: copied squaredance project exported JSON and JSONZip; process exits zero and exporter log confirms publishing completed. UI shows Valid = Yes and displays the red/blue-square animation preview. |
| macOS target on Windows | Correctly rejected with "Build and sign the macOS bundle on macOS." |
| macOS package, signing, notarisation, ARM64 process | Not performed; requires a Mac and the organisation's existing signing setup. |
| Export comparator | Seven focused checks passed: JSON equality/difference, strict byte mode, PNG difference, ZIP metadata and content differences. Three additional checks confirm key-order equivalence and rejection of boolean/number and integer/decimal differences. This tests the helper, not Flump export compatibility. |
| Mac verification helper | Bash syntax checked on Windows; actual `lipo`/`codesign` checks await a Mac artifact. |
| Old/new export comparison | PASS for copied squaredance: old tracked SWF on installed AIR 51.3.1.2 vs rebuilt x64 executable on AIR 51.4.1.2. PNG bytes and canonical JSON (including number representation) match; JSON member order and ZIP container bytes differ. Strict byte-exact whole-output check therefore FAILS. |
| Current Animate publish workflow / game consumer | Pending a copied known-good production project and actual runtime smoke test. |
| Preservation / whitespace | Production source, runtime/demo, fixtures, application descriptor, old releases and SWCs are unchanged; test descriptor ID/output path are the only test-harness changes. `git diff --check` passes. |

Static ZIP-reader caveat: Python's standard `zipfile` rejects `flump.fla`, `potion_simple.fla`
and `rotate_test2.fla` because their recorded central-directory sizes exceed the available
directory data by 54 bytes. Reading local ZIP headers independently validates their entries and
XML. This is **not** evidence that Flump/FZip or Animate cannot load them; leave the fixtures
unchanged and use `squaredance` plus `bella` for the established automated baseline. Static
results are saved in `exporter/build/audit/static-evidence.json` and
`fla-local-entry-validation.json`.

Produced Windows artifacts:

- `exporter/build/windows/Flump/Flump.exe` and its complete captive-runtime folder.
- `exporter/build/packages/Flump-windows-x64-AIR-51.4.1.2.zip` (portable candidate, not an MSI installer), plus SHA-256 sidecar.
- `exporter/build/flump-exporter.swf` and `exporter/build/flump-test.swf`.
- Baseline/candidate exports and configs under `exporter/build/smoke/`.

No macOS app was built or executed. The SDK's Mac framework was inspected statically and contains
both x86_64 (`0x01000007`) and ARM64 (`0x0100000c`) slices; this is not a signed app or running-process test.
Existing releases remain at `exporter/dist/flump-exporter.air` and `exporter/dist/flump-exporter.swf`.
Local downloaded tools are under ignored `.tools/`; build logs/check evidence go under
`exporter/build/audit/`. New build targets specify their expected artifact paths in BUILDING.md;
Mac expected paths must not be mistaken for generated artifacts.
`exporter/build/audit/build-manifest.json` records the tested tool versions, Windows artifact
hashes and export-comparison results. The packaged ZIP's integrity check passes.

## Reproduced issues discovered during execution

- **Pre-existing looping labels:** `Play when added`, `Play, stop, loop` and `Pause while removed`
  fail with `Should've passed flump.movie.FIRST_FRAME`. All three reproduce with the same test
  SWF on the installed AIR 51.3.1.2 runtime as well as AIR 51.4.1.2 (32/64-bit). In unchanged
  `runtime/src/main/as/flump/display/Movie.as`, `updateFrame` sets `_frame = newFrame`, then
  tests `newFrame < _frame` to detect wraparound; that comparison cannot be true. This explains
  the observed missed loop label in the source. The vendored library was not rebuilt or edited.
  Recommend a separately approved runtime fix with deterministic label tests; this is outside
  this task's scope because game-runtime changes were explicitly excluded.
- **ADT 51.4.1.2 Windows conversion bug:** converting the old signed AIR with `-target bundle`
  throws a null `ApplicationDescriptor` exception in `WinBundlePackager.useDirectDrawFonts`.
  Unsigned AIRI conversion is also rejected because it lacks signing options. Direct packaging
  from the descriptor/files **with existing AIR signing credentials** succeeds and is now the
  build target. Mac conversion remains untested; if `repackage-macos` fails, use the direct
  `bundle-macos` rebuild instead. No SDK binary was patched.
- **Sandbox launch limitation:** sandboxed ADL timed out without test output; running the same
  suite on the interactive desktop produced real results. This is a host execution limitation,
  not an animation failure.
- **Legacy config example:** `src/test/testconfig.flump` lacks the `scaleFactors` array required
  by the current reader. It was preserved; generated smoke configs include the required field.
- **Byte identity:** JSON object-key order differs between the old x86 baseline and current x64
  output. Canonical JSON including numeric representation and PNG bytes match. Consumers must
  parse JSON structurally; applications that depend on raw JSON byte hashes need explicit review.

## Remaining acceptance gates

1. Retain the Windows candidate for validation; run a representative current Animate/production-project regression and existing-game consumer test. The repository-fixture smoke test is complete, but the full suite remains red for the established looping-label bug.
2. The build owner must produce the Mac package on the GitHub macOS runner, following
   MAC-DISTRIBUTION.md. Validate universal binaries, signing, native ARM64 export and
   notarisation there. The designer's M4 is for installation, **Kind = Apple**, import/export
   and preview acceptance only; it is not a development machine.
3. Confirm output compatibility using both repository fixtures and a copied known-good Peek &
   Poke project with matching SWF, plus a smoke test in an existing game without modifying it.
4. With release approval, notarise the selected app/installer, test the distributed artifact
   under Gatekeeper, and agree the application version/update path before replacing installations.
5. Save the verified SDK installers/tool hashes and test evidence. Retest AIR changes narrowly;
   keep error-reporting improvements as a separate maintenance task.

Native ARM64 operation and successful Windows export are acceptance criteria, not assumptions.
No assertion is made about untested future macOS releases.
