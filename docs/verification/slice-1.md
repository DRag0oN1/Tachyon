# Source import and inspection increment — verification

Recorded 2026-10-23. `5-build` is active; the approved first slice is **partial**.
The executable software path is implemented and tested. Official Clawbot/motor
originals now exist in the external private catalog, but applicable
conversion/display evidence remains missing, so the slice checkbox
and the full P0/POC completion gates remain unchecked.

The subsequent [external catalog increment](external-catalog.md) records the
latest 205 backend / 28 frontend test results, actual original source hashes and
two real source-status browser cases. The earlier rendering results below use
only the original authored non-VEX calibration fixture.

## Implemented behavior

- Local STEP registration with source/evidence hashes, operation-specific rights,
  expiry and path checks. Registration, conversion, cached loopback/LAN display
  and future new assembly placement do not imply each other's permissions.
- Native standalone and assembly import, preserved source identities and hierarchy,
  explicit `.step`/`.stp` handling and rejection of ambiguous multiple free roots.
  Source bytes are unchanged. Original inch-declared test STEP converts correctly.
- CadQuery/OCCT-to-GLB conversion with source/code/version fingerprints, explicit
  one-time millimetre-to-metre normalization, actual binary-vertex/frame checks,
  content-addressed private meshes, typed receipts and source/mesh revalidation.
- Authenticated local asset APIs, private/no-store headers, Origin handling,
  separate LAN rights, sanitized errors and persisted source preferences.
- Full-window source CAD rendering, native-node selection/hierarchy, orbit,
  zoom/pan/reset, SNAP/SHIFT, top-left animated core shell with internal expansion
  controls, phone sheets and progressively exposed source detail. Editing and
  generation remain disabled and accurately labeled as unavailable.

The imported graph's parent relationships are **source hierarchy**, not verified
mechanical attachments or joints. No complete robot, live model generation,
strategy-mechanism linkage, powered lift or application revision lifecycle is
claimed by this increment.

## Executed checks

| Check | Result | Evidence scope |
| --- | --- | --- |
| `.venv/bin/python -m pytest server/tests -q --junitxml=.local/verification/backend-junit.xml` | **148 passed**, zero failures | Actual converter, original test STEP, independent binary-vertex decoder, native source selection, wrong units, rights scopes, tampering, API/auth/headers, preference persistence |
| `npm run test --prefix web -- --run` | **24 passed** across 7 files | Client contracts/integrity, HTTP/LAN hash fallback, reducer/draft/save behavior and source interface; renderer contract stubs are explicitly unit tests only |
| `npm run build --prefix web` | **Passed** | TypeScript and actual production build; CAD renderer is lazy-loaded |
| `npm run licenses --prefix web` | **Passed** | 271 locked dependency entries; 215 installed license/notice texts retained |
| Real `@cad-import` suite, source profile | **6 passed**, 2 profile-specific skips, zero failures/flaky cases | Actual protected GLB on desktop Chromium and mobile WebKit; the empty-source cases do not apply when this server has geometry |
| Real authenticated-empty-catalog cases, default profile | **2 passed**, zero failures | The two skipped source-profile cases were run against the actual empty built application, on both browser projects |
| Manual live API checks | **Passed** | Health/catalog/capabilities/workspace returned 200 with private/no-store; one original non-VEX fixture source, no input blockers in that isolated profile |

Raw JUnit/browser evidence is in ignored `.local/verification/`. The source-profile
JSON and output are redacted; owner tokens, source geometry and private evidence
are excluded from commits. [Structured summary](slice-1-results.json) records the
results without embedding those inputs. The package emits one Starlette/httpx
deprecation warning; the build also reports a large lazy CAD-renderer chunk.
Neither is hidden or counted as a completed mobile performance assessment.

## Geometry used for software verification

Only original **Tachyon-authored, non-VEX calibration test fixtures** were converted
and rendered. The main fixture has two native solids with named nested placement,
known asymmetric bounds and a 90-degree source transform. The browser bounds are
`(-0.039, -0.004, -0.029)` to `(0.023, 0.020, -0.003)` metres. Each rendered view
identifies it as converter proof and explicitly says it is not authentic VEX.

Tests also generate their own inch-declared part, single-root part, rotated prism
and ambiguous multi-root inputs. Those exercise real STEP parsing and real binary
mesh output; none are a VEX component, complete robot or fake successful generation.
No rights record was invented for the three existing manufacturer research files.
No VEX geometry was converted or redistributed.

## Actual browser observations

Both browser projects loaded the authenticated GLB, verified source/mesh identity,
observed correct metre bounds and actual rendered draw calls, selected native
geometry, switched themes without re-fetching/changing the mesh, reopened source
panels, retained camera/selection and kept expanded-assistant draft text. Orbit,
zoom/pan handler changes and reset were checked against the real controls' camera
and target. Reduced-motion behavior was checked in the running browser.

Desktop uses Chromium with a software WebGL backend. Mobile uses a WebKit phone
viewport and real browser tap selection. Its driver cannot send `mouse.wheel`;
the zoom handler is exercised with a dispatched WheelEvent. **This is not a
physical-phone pinch/pan test.** Real device/GPU/touch verification remains open.

Screenshots stay private under `.local/verification/source-browser/`, with filenames
including `tachyon-authored-non-vex-converter-fixture`. Desktop/mobile SNAP and
SHIFT views were captured. They illustrate the converter and interface only.

The in-app Browser runtime could not start its Node service. The approved project
Playwright browsers were used for actual rendering checks instead; no screenshot
or mocked successful CAD route substituted for those checks.

## Failures found and repaired

The first native conversion exposed a 1000× GLB unit error: the tested exporter
rotated axes but retained millimetre coordinates. The explicit one-time unit root
and independently measured binary vertices now verify metres. Tests reject a
second conversion. Import inspection also found standalone/extension limitations,
free-root truncation risk and wrapper-name collisions; each has a verified fix or
an explicit unsupported-state rejection. Rights override, malformed receipt and
cached context handling were corrected. A referenced native root now retains its
outer placement; an independent-matrix regression checks its real native solids
and member transforms. Malformed non-ASCII session headers receive a private 401. The mobile driver wheel failure was
fixed in the test with its synthetic-input limitation recorded above.

## Remaining work and blockers

The [44-criterion report](acceptance-status.md) separates passing, failing,
blocked and unimplemented items. It does not turn source-view coverage into full
application acceptance. In particular:

- Authentic VEX conversion/display and a complete, task-appropriate component set
  need applicable source-specific permission evidence and verified local inputs.
- Complete robot builders, acquisition/scoring integration, live AI strategies and
  two distinct designs, actual strategy links and scoring-height revisions are
  unimplemented. The pre-build static mount proves none of them.
- Model credentials/access are not configured and no live provider call was made.
- Additional rulebooks, accepted project/revision recovery, coupled mechanism
  operation and full workspace layout/customization remain unimplemented.
- Physical phone use and public CAD demonstration-image rights are unverified.

No early P0 hands-on checkpoint, final review, learning wrap-up or shipping stage
is marked complete. The next approved milestone remains the first complete
strategy-linked robot, followed by live two-design generation and real revisions.

The final serving process was rechecked after these fixes: both actual renderer
journeys passed again (desktop and mobile WebKit), with no skips or failures.
