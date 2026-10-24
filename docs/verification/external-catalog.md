# External CAD catalog increment — verification

Recorded 2026-10-23, during `5-build` Slice 1. The approved order and fast mode
are preserved. This is a verified software increment within an **incomplete
slice**, not proof of a generated robot or completed authentic-CAD acceptance.

## Source findings and execution

Two explicitly requested official manufacturer STEP downloads were saved to the
external private STEP root. Actual hashes, download/product URLs, identities,
provenance, terms observations and all ten separate operation states were
recorded in the external rights directory. See [source status](../cad-source-status.md)
for original byte counts, hashes and source links. Originals were not changed.
No VEX BRep was imported by this increment, and no VEX mesh was generated.

The source register and rights records are distinct: a download/source fact is
not permission. General terms and the footer-linked EULA did not establish an
asset-specific conversion/display grant. All VEX application operation states
remain **unverified**. Public hosting, original/mesh redistribution and public
imagery are not approved. No third party was contacted and no assets uploaded.

Actual `assets-discover` and `assets-record-source` runs recorded both originals.
`assets-source-status` returned two present sources with unverified conversion
and local display. `assets-measure` refused both with `SOURCE_NOT_QUALIFIED`
before native import. It did not produce bounds, hierarchy or conversion output.
Those refusals pass the rights-gate check, not authentic-import acceptance.

## Implemented and verified software

- Separate external STEP/rights roots, role-prefixed and absolute paths, legacy
  private-data compatibility, and rejection of public project paths, cross-role
  paths and escaping symlinks. Cache meshes/receipts remain private.
- Streamed hash discovery with bounded text observations and a 256 MiB limit,
  preserving matching-byte provenance and invalidating changes. Duplicate bytes,
  missing/unreadable inputs, malformed registers and unsafe links are covered.
- Provenance recording cannot accept permission-approval fields. Status checks
  revalidate evidence and current bytes before reporting qualified operations;
  unpermitted source bodies are not read by the status endpoint.
- Gated native measurement supplies real source bounds and local parent matrices
  before manifest authoring. Original authored calibration fixtures verify this
  processing and external-source conversion/cache loading. They are **non-VEX**.
- Owner-authenticated `/api/sources` returns metadata only, without filenames,
  absolute paths or permission text. The collapsible Components source register
  distinguishes discovered originals from prepared geometry and supports retry.
- Lower/upper/mixed-case CAD formats are ignored. No tracked original or converted
  CAD, learner profile or private rights record was introduced.

Executed results: **205 backend tests passed**, including external-root,
discovery, evidence, measurement and existing converter/API checks; **28 frontend
tests passed**; production TypeScript/Vite build passed. The existing renderer
chunk-size warning remains; this is not a large-assembly performance result.
One backend dependency deprecation warning is non-failing.

The existing real-GLB regression also passed on the updated production server
using only Tachyon's original non-VEX calibration fixture: **4 passed, 2
profile-specific empty-catalog cases skipped**. Both actual renderer journeys
loaded, verified hashes/bounds, selected geometry and retained workspace context
with `crypto.subtle` unavailable. An old development-only module-import test
failed against static hosting; its browser check was consolidated into these
actual production asset-loading journeys. The standard hash vector remains
covered by the frontend unit test. No VEX result is inferred from these passes.
Both empty-catalog cases then passed separately against the actual updated default
workspace, where the external originals exist but no geometry is qualified.

Real desktop Chromium SNAP and iPhone-13-sized mobile WebKit SHIFT tests passed
**2/2**, with zero geometry requests or page errors. They read actual external
records, refresh them, verify blocked operations, and collapse the source panel.
Both screenshots were visually inspected. They show metadata and an empty
workspace, **not Clawbot CAD**. Browser process launch initially failed within
the process sandbox; the authorized local-browser run passed outside it. The
in-app browser connection was unavailable, so installed project browsers were
used. Mobile viewport evidence is not a physical-phone gesture test.

Private evidence is retained under `.local/verification/`:
`external-catalog-backend-junit.xml`, `external-catalog-screenshots/`, and the
loopback server log/session (not for publication). No owner token is included in
this document. Screenshots are named `desktop-snap-external-register-blocked.png`
and `mobile-webkit-shift-external-register-blocked.png`.

## Requested Slice 1 checks

| Requested check | Current result |
| --- | --- |
| Import genuine VEX assembly | **Blocked:** applicable native-processing rights unverified |
| Preserve its individual identities/hierarchy | **Blocked:** authentic assembly has not been imported; software path passes original calibration tests |
| Convert/display actual source geometry | **Blocked:** conversion and display rights unverified |
| Verify scaling and part transforms | **Blocked:** authentic source measurements/rendering not executed |
| Desktop SNAP / mobile SHIFT CAD inspection | **Blocked:** source-status UI passes; it contains no CAD |
| Select multiple authentic individual parts | **Blocked:** no authentic mesh is available; prior calibration picking is not a substitute |
| Accurate screenshots/evidence | Metadata-only screenshots verified; authentic-CAD screenshots **blocked** |
| Honest source/rights restrictions | Recorded; no unverified grant marked approved |

Full acceptance remains **1 passing (STATE-3), 0 failing, 3 blocked
(CAD-1, CAD-4, VIEW-1), 40 unimplemented/partial**. CAD-4 additionally needs a
qualified component set for the submitted robot recipes; VIEW-1 also needs actual
robot inspection and physical touch evidence. A qualified Clawbot import fixture
would not prove connected new robot generation, competition task suitability,
strategy linkage, mechanism actuation or scoring revisions. These remain
unimplemented engineering work, separately tracked in the approved later slices.

Next prerequisite is applicable V5 asset-specific terms or rightsholder permission
for the intended local operations. Then measure/review the native assembly,
register it, convert it, inspect desktop/mobile geometry, and verify individual
part picking. Slice 1 must genuinely pass before the approved first complete
strategy-linked robot increment proceeds. No new planning approval is requested.
