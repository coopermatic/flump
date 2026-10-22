# Mac distribution from Windows

The designer installs, launches and tests Flump. All development, packaging,
signing and notarisation belong to the build owner and GitHub's hosted Mac runner.
No developer tools or signing credentials belong on the designer's Mac.

## Findings and selected routes

**Preferred `.air` route is supported in principle.** AIR SDK 51.3.3.1 introduced
`air4mac`: AIR signing options precede `-target air4mac`; a **Developer ID
Application** native signature follows it. The package includes signed native
installation files. On Apple Silicon, the shared runtime **51.3.3 or later**
places them in the installed app so it can run natively. On Intel the installer
strips the ARM64 slice. Windows 51.3.3+ ignores the additional Mac files.
Use the current vendor shared runtime, not Adobe's historical runtime download.
This is supported by [the release notes, AIR-4887](https://airsdk.harman.com/api/versions/51.3.3.1/release-notes/Release_Notes_AIR_SDK_51.3.3.pdf)
and [the AIR maintainer's explanation](https://github.com/airsdk/Adobe-Runtime-Support/discussions/4256).

Native code signing and notarisation are separate. Those vendor notes do not
establish an end-to-end notarisation/stapling procedure for `air4mac`. Apple accepts
ZIP/DMG/PKG submissions, not a top-level `.air`; wrapping `.air` in ZIP does not
by itself prove Apple inspected its nested payload or that the installed app
passes Gatekeeper. The automation attempts that ZIP submission, requires Accepted
and nonempty code tickets, and labels the result **air4mac validation**. It never
pretends `.air` supports stapling. Before selecting this route for the designer,
the build owner must validate installation with the current shared runtime,
installed signatures, Gatekeeper and ARM64 launch in a clean Mac test environment.
No Mac signing credentials are currently available, so this remains unexecuted.

**Practical fallback: a notarised universal app in ZIP.** This uses Apple's
documented distribution route: build with ADT, verify both native slices and
signatures, run an explicit ARM64 export smoke test, notarise, staple the app,
check Gatekeeper, then ZIP the stapled app. The recipient extracts and drags it
to Applications. No shared runtime is required. A DMG would add another container
without simplifying these steps, so ZIP is the implemented option.

The Windows build and export code are unchanged by this automation. The application
ID/version remain `flump` / `1.5.3`, preserving the existing descriptor. In-place
AIR upgrades additionally depend on certificate identity and version handling;
do not promise an automatic upgrade from the historical installation. Agree any
version increment/certificate migration separately after testing.

## What the build owner must supply

1. **Apple Developer Program membership**, held by the organisation or an authorised
   developer. A free Apple account is insufficient for Developer ID distribution.
2. An existing **Developer ID Application certificate and its matching private key**,
   exported as password-protected PKCS12 (`.p12`). A `.cer` alone is insufficient.
   This is not an Apple Development, Apple Distribution or Developer ID Installer
   certificate. If none exists, the Account Holder must arrange certificate issuance
   in Apple's portal using a securely retained private key/CSR. This can be arranged
   by the build owner or their developer; the designer's Mac is not required.
   This task does not create, rotate, export or revoke any signing credentials.
3. Notarisation authentication. This workflow uses an existing **App Store Connect
   team API key** (`.p8`), its **Key ID**, and **Issuer ID**, with suitable notarisation
   access. An Apple ID, Team ID and app-specific password is an Apple-supported
   alternative, but is not wired into this workflow. No App Store app submission,
   App Store listing or Mac App Store distribution is required.
4. For `.air` only, an approved **AIR package signing PKCS12 and password**, plus an
   approved RFC3161 timestamp endpoint. The AIR identity can be distinct from the
   Apple identity. Retaining the historical AIR identity may preserve update
   continuity, but the repository contains old signing material: do not treat it as
   a production trust anchor without the owner's review. CI does not read it or its
   historical password. The standalone app uses the Developer ID identity at both
   ADT signing stages and therefore needs no separate AIR certificate secret.
5. Confirm the appropriate **AIR SDK licence** for Peek & Poke. The user reports the
   free tier. The vendor's pricing page currently lists a free tier below **US$50,000
   annual company turnover**, based on the preceding 12-month accounting period,
   and an injected splash screen. This is company turnover, not Flump revenue.
   Paid tiers currently list Basic $199/year/seat up to $100k, Professional $799 up
   to $500k, and Enterprise $1,199 with no turnover cap, before applicable tax.
   Recheck vendor terms before purchase; installation of the free SDK is not proof
   of eligibility. If eligibility/CI-seat coverage is unclear, the owner should
   resolve it with the vendor. No paid licence is established as a technical
   prerequisite specifically for Mac ARM64 or `air4mac` in the inspected notes.
   A paid licence's existing `adt.lic` can be supplied through the optional secret.

Apple sources: [Developer ID certificates](https://developer.apple.com/help/account/certificates/create-developer-id-certificates/),
[notarisation authentication](https://developer.apple.com/documentation/technotes/tn3147-migrating-to-the-latest-notarization-tool),
[notarisation workflow](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow).
AIR sources: [pricing](https://airsdk.wxlift.com/pricing),
[SDK licence, sections 3–4](https://airsdk.wxlift.com/assets/pdfs/HARMAN%20AIR%20SDK%20License%20Agreement.pdf).
Pricing was read from the vendor website's shipped page code on 22 October 2026
because its rendered pricing page was blank in the research browser.

There is no Developer ID Installer certificate requirement for ZIP or `.air`.
No provisioning profile is needed for Flump's current capabilities outside the
Mac App Store. A native `.pkg` installer would require Developer ID Installer.
The designer needs none of these accounts, certificates or developer licences.

## GitHub configuration (owner only, once)

Workflow: [`.github/workflows/macos.yml`](../.github/workflows/macos.yml).
The repository is public and the connected GitHub account reports admin access.
The workflow uses `macos-15`, currently an Apple Silicon standard runner, and
asserts ARM64 at execution. [GitHub runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

Create an environment named **macos-distribution** under repository Settings >
Environments. Require owner approval and restrict deployment branches to the
reviewed `codex/native-air-build` branch (and later the agreed release branch).
Never enable signing on arbitrary forks or pull-request code. Repository token
permissions are read-only; no workflow step merges, pushes or creates a release.

Configure these **environment secrets** in GitHub's UI, never in chat, YAML or Git:

| Secret | Value |
| --- | --- |
| `APPLE_DEVELOPER_ID_P12_BASE64` | Base64 of the existing Developer ID Application P12 including private key |
| `APPLE_DEVELOPER_ID_P12_PASSWORD` | Password for that P12 |
| `APPLE_NOTARY_KEY_BASE64` | Base64 of the existing team API key `.p8` |
| `APPLE_NOTARY_KEY_ID` | API key identifier |
| `APPLE_NOTARY_ISSUER_ID` | Team API issuer identifier |
| `AIR_SDK_LICENSE_BASE64` | Optional: base64 of the existing paid `adt.lic`; omit for eligible free tier |
| `AIR_SIGNING_P12_BASE64` | For the `.air` step: base64 of approved existing AIR signing P12 |
| `AIR_SIGNING_P12_PASSWORD` | For the `.air` step: password for that P12 |

Environment **variables**:

| Variable | Value |
| --- | --- |
| `APPLE_SIGNING_IDENTITY` | Exact `Developer ID Application: Organisation (TEAMID)` identity name |
| `AIR_LICENSE_CONFIRMED` | `true` once the owner confirms the applicable licence |
| `AIR_TIMESTAMP_URL` | Approved timestamp service URL for AIR package signing; not `none` |

Finally set repository variable **`FLUMP_MAC_SIGNING_READY=true`**. Leave it unset
until environment protection and credentials are ready. This flag only enables
the signing job; it does not publish or approve a release. The environment approval
authorises signing/notarisation submission to Apple for that run. Base64 is encoding,
not encryption: use GitHub Secrets and do not save encoded values in the repository.

Credentials are decoded only into a temporary runner directory with restricted
permissions. An ephemeral Keychain imports the existing identity. Its random local
unlock password is not a new signing key. The script restores the runner's Keychain
settings and deletes this Keychain and temporary files on normal completion/failure;
the hosted VM is destroyed after the job even if forcibly terminated. No keychain,
SDK licence, P12/P8 or whole SDK directory is uploaded as an artifact.

## Running the automation from Windows

Pushing the reviewed work branch runs native compilation, export comparison and
the integration suite on GitHub's Mac. Initially the signing job is skipped.
Once the configuration above is complete, another push runs the signing job after
the protected-environment approval. The workflow also supports **Run workflow**
with `signed=true`, but GitHub requires a `workflow_dispatch` workflow to exist on
the default branch before normal manual dispatch is available. Until an approved
merge, the branch-push trigger avoids needing any change to `master`.

Tool versions: AIR **51.4.1.2**, Flex **4.16.1**, Ant **1.10.15**, Java **17** on
ARM64. Apache ZIP hashes and action commit SHAs are pinned. Java's patch release
and the hosted image remain maintained inputs and are recorded in `toolchain.txt`;
this is not a bit-for-bit reproducibility claim. The AIR setup action downloads
through the vendor's current endpoint with licence acceptance; it is pinned to
an inspected source revision. Its download does not establish paid entitlement.

The native export smoke test explicitly launches through `arch -arm64`, compares
the preserved old SWF with the rebuilt SWF, and, after signing, tests a copy of the
actual packaged app. It uses copied `squaredance` inputs and structural JSON plus
byte-exact PNG comparisons. No x86 fallback is allowed. The separate full integration
suite is diagnostic and visibly retains failure logs: the Windows baseline has
13 passes and three established loop-label failures. A green compilation/smoke job
must not be presented as a clean full integration pass.

The signing job first creates the standalone fallback so its artifact remains
available even if the subsequent `air4mac` experiment fails. Missing AIR signing
secrets or an unsuccessful nested notarisation submission fail the `.air` step,
with the already validated standalone ZIP still downloadable.

Artifacts in the Actions run (14-day retention):

- `macos-build-evidence-RUNID`: compiler outputs, native smoke outputs, tool versions,
  integration results. **Not an installer.**
- `Flump-mac-universal-RUNID`: `Flump-mac-universal.zip`, SHA-256, and
  [INSTALL-MAC.txt](INSTALL-MAC.txt), only after signature/ARM64 smoke/notary/staple/
  Gatekeeper checks succeed. Owner reviews before forwarding the inner ZIP and
  instructions to the designer. Downloading the Actions artifact adds an outer ZIP.
- `Flump-air4mac-validation-RUNID`: signed `Flump.air`, SHA-256 and explicit validation
  notice, only if the experimental notarisation check succeeds. Not automatically
  approved for designer distribution.
- `macos-packaging-evidence-RUNID`: signing verification and notarisation diagnostics.

For an approved `.air` package, the designer's workflow is: update/install the
official [Mac AIR shared runtime](https://airsdk.wxlift.com/runtime), double-click
`Flump.air`, complete installation, launch and test. For the standalone ZIP, follow
INSTALL-MAC.txt. No Terminal commands or security bypasses are part of either flow.

## Current completion boundary

Apple membership/certificate availability is unconfirmed (user answered "Neither /
not sure"); no Apple signing/notary credentials have been supplied. AIR is currently
reported as free tier and company eligibility remains for the owner to confirm.
No signed Mac installer is available yet. Automation execution results are recorded
in AUDIT.md; creating these workflow files alone is not a successful Mac build.
The remaining technical work stays with the build owner/automation, not the designer.
