# Generated assembly demonstration — 2026-10-25

**A generated architecture-A assembly is visible in the production Tachyon viewer.
It remains a partial, independently authored non-VEX development robot.**
The complete authentic-VEX robot requirement has not passed. No factory Clawbot
or imported gripper is used as proof of generated robot output.

## What now works

Create Robot runs the preserved PPO policy, presents the actual StrategySpec v2
architecture proposals and realizes A through the existing pipeline:

`architecture → recipe → qualified local STEP definitions → placement graph →
prepared GLB instances → production viewer`.

PPO supplies the learned objectives/capability requirements; a deterministic
engineering recipe constructs this bounded architecture. PPO does not predict
BRep geometry.

Every placement is instantiated; geometry is shared by component definition
rather than silently truncated. The viewer reports requested, resolved and loaded
counts separately and refuses missing geometry. Camera controls, hierarchy,
selection, subsystem colors, forward/reverse strategy links and the existing
SNAP/SHIFT workspace are preserved. The assistant uses real assembly revisions;
it does not merely reply that geometry changed.

| Evidence | Result |
| --- | --- |
| Requested / resolved / loaded placements | 494 / 494 / 494 in the last full desktop/mobile run |
| Unique robot geometry assets | 35 |
| Drawn meshes | 925; these are not 925 independently placed components |
| Assembly relationships | 631, including closure/support constraints |
| Root-connected instances | 494; no isolated/unreachable graph nodes |
| Populated roles | chassis 104; drive 78; scorer 193; Pin intake 74; Cup cradle 39; Pin transfer 1; stack alignment 5 |
| Height-edit coupling | 30 actual scalar joint coordinates |
| Strategy bindings | 14, tied to the exact revision |
| Whole authentic/complete robot | **Not passed** |

The drive has two geared motors rather than four independent direct drives.
Paired four-bars, supported shafts, transmission gears, roller intake, tool,
Cup clamp, static handoff/alignment guides, supporting hardware and control/power
geometry are generated from the selected architecture. The static Pin tool and
guides do not establish powered acquisition/transfer/release or scoring support.
Alternative B remains a distinct bridge proposal, not a realized complete robot.
There is one learned strategy family, not two claimed PPO discoveries.

## Cup sequence: actual joints, incomplete mechanical operation

A 14-second **prescribed kinematic preview** approaches a modeled Cup, closes
the two jaws, raises the actual linked carrier, translates the robot, aligns over
an assumed preplaced Pin on a 120 mm development fixture, nests the Cup, opens
and retracts. The released object's world pose remains fixed. Root travel is
prescribed with rolling drive-joint coordinates; no traction or physics is solved.

The browser computes forward kinematics from joint scalars and attachment frames,
not interpolated member matrices. The backend validates 33 sampled poses; the
frontend/backend cross-check compares all nine keyframes and sampled object
poses. Browser checks compare the **drawn** Cup/jaw world matrices, run continuous
playback with the panel dismissed, and check Preview/Discard/Apply/Undo against
actual scoring-frame transforms and revision-bound links. Delayed preparation
responses cannot replace a newer revision or pending preview.

This does **not** demonstrate a mechanically successful competition operation.
Known body/shaft intersections remain; the UI and model limitations identify
unqualified assembly clearance. Screw threads, gear contact, forces, grip friction,
compliance, object stability, wiring and independent Cup tilt are unverified.
Powered Pin handoff/release and the full learned scoring cycle remain unsupported.

The official [Override definitions, Appendix B](https://manuals.vex.com/v5/override/v2.1/definitions/)
provide the nominal Cup/Pin envelopes. The modeled Cup divider, wall thickness and
equal halves are development assumptions. The target stand is **not an official
Goal**, and the Pin's preplaced status is assumed. Nominal nesting of the Pin is
not an [SC2 scoring validation](https://manuals.vex.com/v5/override/v2.1/game/?view=core#SC2).

## Solid geometry checks — failing

The final private v6 profile passes endpoint graph closure and preserves all
component identities/rigid transforms. Exact BRep checks find **51 lower and
37 raised major-body overlaps above 1 mm³**. A separate shaft check finds one
raised input-shaft/upper-four-bar overlap of **65.869 mm³**. The carry and release
frames also intersect that link by **65.809 / 11.510 mm³**, respectively. These counts are
reported separately, not hidden as intended joint contact.

Largest remaining findings include intake-arm/tool-carrier interference
(**608.524 mm³**), lift-upright/battery interference (**520.110 mm³**) and carrier
mounting conflicts. The original-frame connections still need mechanical
rearrangement. Moving one module cleared some pairs and exposed others; those
experiments were retained privately rather than promoted to success.

The modeled Cup has no over-threshold overlap with the audited robot bodies or
Pin/fixture at the three sampled frames; nominal carry clearance is 5 mm and
modeled nesting is 81.25 mm. Those object results do not cancel the shaft/frame
failures or establish physical grasp, stability or scoring.

The audit explicitly scopes major structural bodies and separately checks the
Cup input shaft against nonmating major bodies. Other small fasteners and
shaft/gear engagements are excluded and listed; **no exhaustive collision-free
claim is made**. Three Cup-operation keyframes are audited separately. All graph,
solid, task, competition-legality and physical-performance findings are distinct.

## Verification snapshots and evidence

- Final production snapshot: private profile `.local/generated-robot-a-v6`.
  Desktop SNAP and mobile WebKit SHIFT both pass the full generated-assembly
  journey, continuous joint playback and Preview/Discard/Apply/Undo. Each draws
  925 meshes from 494/494 resolved/loaded placements and 35 geometry assets.
- The first final desktop attempt reached Apply and hit its 540-second total
  fixture limit awaiting Undo. Its isolated rerun passed with a 900-second budget
  and unchanged assertions (9.8 minutes); mobile passed in 3.6 minutes. Mobile
  evidence now waits for the final ready callback after Undo rather than recording
  a transient loaded-count read. This is functional verification under software
  WebGL, not latency/performance acceptance.
- **678 backend, 109 frontend and 102 RL tests passed**, plus production build
  and **eight desktop/mobile browser cases**: two generated-assembly cases and
  six preserved strategy, authentic source-inspection and original STEP-revision
  cases. No PPO training or checkpoint replacement occurred.
- Native endpoint and operation BRep audits exit 1 because of the intersections
  above. The offline 33-pose operation uses the production pose engine; actual
  HTTP responses and drawn transforms are separately checked by the browser.
- Exact aggregate evidence, source and screenshot hashes are saved in
  [generated-assembly-evidence.json](generated-assembly-evidence.json). STEP, GLB,
  measured pack, source/permission records, assembly recipe, SQLite revisions and
  operating poses stay in the ignored profile. Actual desktop, subsystem,
  strategy-highlight, operation and mobile screenshots remain private under
  `.local/robot-generation/actual-robot-evidence/`.
- The earlier fully verified v4 application/profile is retained as a recovery
  point; later correction attempts and their failures were retained privately.

The earlier 449-placement/576-relationship recipe had only source-inspection
screenshots. That did not establish that its generated instances reached the
viewer. The new evidence exercises the complete placement-to-scene path, first
with 474 and then 494 original development-CAD placements. This is the actual
sequence; source imports were not retroactively called generated-robot proof.

## Provenance and rights

All 35 development definitions are authored by this project in
`tools/verification/development_parts.py` and
`server/tachyon/robots/cup_handling.py`, exported as STEP and processed normally.
They are explicitly non-VEX concepts; none is represented as authentic manufacturer
CAD. The generator reads no manufacturer CAD files and uploads no geometry. It has
no dependency on a pre-existing private robotics implementation. No CAD is bundled.
Self-authorship records qualify only these new assets for local development.
They do not fabricate third-party permission or grant a public asset license.

Original VEX STEP/catalog/rights records remain unchanged. Private storage,
conversion and authenticated loopback inspection have their existing narrow
qualification. New VEX assembly placement, source modification, LAN display,
original/mesh redistribution, public hosting and public depiction remain
unverified and unavailable without the relevant basis. No original/converted
proprietary asset or private rights evidence is staged for Git.

## Reproduce

From the installed environments in the README, choose a fresh output directory
and an unused port. The seeder refuses overwrite and reads no manufacturer CAD.

```sh
.venv/bin/python tools/verification/seed_generated_robot.py \
  --data-dir .local/generated-development
TACHYON_DATA_DIR=.local/generated-development \
TACHYON_UI_ORIGIN=http://127.0.0.1:8019 \
.venv/bin/python -m uvicorn tachyon.app:app --host 127.0.0.1 --port 8019
```

Open the printed owner launch URL, then **Create Robot → alternative A → Check
parts and realize concept**. Components exposes hierarchy and subsystem colors.
Strategy selects actual bound mechanisms and prepares the explicitly limited Cup
preview. The assistant accepts registered scoring-height requests and supports
Preview, Apply, Discard and Undo.

```sh
.venv/bin/python -m pytest server/tests -q
.local/rl-venv/bin/python -m pytest research/strategy_rl/tests -q
npm run test --prefix web -- --run
npm run build --prefix web

TACHYON_E2E_BASE_URL=http://127.0.0.1:8019 \
TACHYON_E2E_SESSION_FILE=/absolute/private/owner-session-file \
TACHYON_E2E_GENERATED_DEVELOPMENT=1 \
npm run test:e2e --prefix web -- --grep @generated-development

.venv/bin/python tools/verification/check_generated_assembly.py \
  --data-dir .local/generated-development \
  --output .local/verification/generated-assembly-audit.json
```

The final command exits **1 when intersections are found**, not zero. It must
not be reported as a passing collision test. A supplied operation-model JSON can
be checked with `--operation-model`; that check covers only the three declared
keyframes. Browser session files must use private local storage. No physical
phone pinch/LAN or dynamics test is implied by mobile viewport emulation.

Slice 2, the authentic complete-robot and remaining 22-P0 obligations, learner
hands-on/final review and `6-ship` remain open. No submission or publication has
occurred. The previous source-only report is retained below as history.

---

# Historical measured-source increment — f6cd922

This increment implements **a partial architecture-A recipe**, not a completed
robot. Slice 2 stays unchecked. There is no second generated architecture and no
claim of another learned strategy family or physical match performance.

## Implemented pipeline

- `cad.native.select_source_definition`: exact source hash, XCAF definition label
  and name; exclude original occurrence placement while retaining source BReps,
  intrinsic coordinates, child hierarchy and provenance.
- `cad.prepare.prepare_components`: checked batch conversion through the existing
  CadQuery/GLB pipeline. Reuse only current source/receipt/mesh identities and
  operation rights. Record independent failures without discarding prepared parts.
- `robots.source_pack`: native millimetre interfaces become rigid metre/Y-up
  frames. Hole position and normal must match source metrology; axial stations
  stay inside the source body; purchased interface datums stay inside its envelope.
- `robots.architecture_a.compile_architecture_a`: consume the saved A proposal;
  author placements, real component identities, relationships, joint endpoints,
  BOM declarations and strategy action links. No Clawbot layout is copied.
- `realization.build_pose` and `assemblies.validate_assembly`: the existing
  production placement/closure engine validates the recipe. `bindings` derives
  revision-exact anchors and reverse mechanism links. Existing scene loading and
  rendering services consume qualified prepared components.

The existing exporter uses **relative** tessellation deflection, not a fixed
0.05 mm surface tolerance. New conversion receipts identify this explicitly;
legacy receipts' nominal `linearDeflectionMm` field was the exporter parameter.
Actual converted world bounds still must match source geometry within 0.1 mm.
Native surface measurement explicitly excludes cached display triangulation, so
converting a purchased unit cannot change later measurements of its motor/parts.
For conservative trimmed-surface BRep boxes, six independent source-geometry
extremum solves refine the comparison, with an enclosing 0.001 mm computational
coordinate margin. The original envelope and refinement basis remain in the
receipt. No mesh is scaled or fitted to make this check pass.

## Current authoring evidence

The private metrology-only probe uses explicit original test definitions with
no mesh assets or authentic-robot qualification. It checks the compiler's measured
frames and graph mathematics against the actual saved StrategySpec handoff:

| Item | Result |
| --- | --- |
| Outer placements | 449 |
| Relationships | 576, including additional closure/support constraints |
| Populated subsystem roles | chassis 104; drive 78; scorer 193; pin intake 74 |
| Source definition identities used | 26 |
| Changed scalar joints across height endpoints | 30 |
| Lower and raised graph closure | Passing in existing engine |
| Strategy action bindings | 12 in each endpoint |
| Coupled edit metadata | Passing; drive/intake stay unchanged |
| Declared jaw reference Y | 0.146768 m lower; 0.437292 m raised |

That reference is an annotation in the source tool's working region, **not** a
measured Pin contact point or validated scoring capability. These are metadata
results, not screenshots or proof of authentic full-robot rendering.

The drive uses two motors, four purchased omni wheels and three 84-tooth gears
per side. The scoring frame uses paired source-angle four-bars, supported shafts,
two 12:84 reductions and a purchased Claw Kit v2 tool. Off-axis gear/link bolts
provide an explicit torque connection. The intake uses two purchased traction
wheel units as conceptual opposed rollers on a mounted frame, with source motor,
shaft and bearing geometry. Full hardware/fit qualification remains open.

## Source inventory and rights

The supplied Clawbot source contains 48 unique valid leaf definitions. Selected
native units include a four-solid traction wheel, a 73-solid omni wheel and an
89-solid Claw Kit v2. The last is a purchased tool in its factory pose; neither
internal jaw actuation nor game-object fit follows from its import. These counts
are separate from the outer placed-instance count.

Original STEP and rights evidence remain in the user's external directories.
Metrology, prepared meshes, receipts, generated recipes, runtime state and browser
screenshots remain ignored under `.local/` or `web/test-results/`. No proprietary
original or converted geometry is bundled, committed, uploaded or publicly hosted.

The existing records qualify storage, conversion and authenticated loopback
inspection. Assembly placement remains unverified. Software now supports a
separately recorded, narrowly scoped user attestation; **no actual attestation or
manufacturer permission has been fabricated or added**. Public redistribution,
hosting, LAN display, publication and source-part modification remain separate.

## Reproduction

Executed verification: **655 backend, 86 frontend and 102 RL tests passed**, the
production build passed, and all six desktop/mobile browser cases passed. The
normal preparation command converted all 27 selected components with no geometry
errors. Its recipe hash matches the independent compile:
`167af69e225c8ec94f3bda62fed914d43cbb56543457209020eee44eb8f61d44`.
Preparation's qualification report stops at the unverified assembly-placement
scope. The full robot also lacks the mechanisms and qualifications listed below.
Aggregate evidence and private screenshot hashes are in
[robot-generation-evidence.json](robot-generation-evidence.json).

```sh
.venv/bin/python tools/prepare_architecture_a.py \
  --data-dir .local/robot-a-new-output \
  --measurements .local/robot-generation/metrology.json
```

The explicit optional metrology file is a private measurement cache for the
pinned source. Omit `--measurements` to measure the supplied definitions afresh.
The tool checks the actual source bytes and selection names before use. It writes
a separate private catalog, source metrology, measured pack, configuration, recipe
and qualification report. Existing unrelated output or changed owned files are
preserved by refusing overwrite. A copied rights decision does not broaden its
scope. Preparation can succeed while realization correctly remains inactive.

```sh
.venv/bin/python -m pytest server/tests -q
.local/rl-venv/bin/python -m pytest research/strategy_rl/tests -q
npm test --prefix web -- --run
npm run build --prefix web
```

For an authenticated private local server, supply its session through a private
file, never through a public recording:

```sh
TACHYON_E2E_BASE_URL=http://127.0.0.1:8012 \
TACHYON_E2E_SESSION_FILE=/absolute/private/session-file \
npm run test:e2e --prefix web -- --grep @production-strategy

TACHYON_E2E_BASE_URL=http://127.0.0.1:8014 \
TACHYON_E2E_SESSION_FILE=/absolute/private/session-file \
TACHYON_E2E_MECHANISM_FIXTURE=1 \
npm run test:e2e --prefix web -- --grep @production-revision

TACHYON_E2E_BASE_URL=http://127.0.0.1:8010 \
TACHYON_E2E_SESSION_FILE=/absolute/private/session-file \
TACHYON_E2E_SELECTED_SOURCE_ID=vex_45 \
npm run test:e2e --prefix web -- --grep @selected-source
```

The first checks the preserved real-policy app. The second uses original non-VEX
STEP solely for the revision regression. The third inspects the selected factory
tool; it cannot pass complete generated-robot acceptance.

## Remaining engineering and acceptance

Gated transfer, independent Cup retention/release and stack alignment are not
generated. Tool/carrier fastener access, full transmission/mount declarations,
game-object contact, interference and real loaded capabilities are unqualified.
The BOM-only compiler contract cannot pass the hardware qualifier merely by
listing components. Architecture B remains unimplemented.

ROBOT-1/2/3, CAD-1/2/3/4, VIEW-1, LINK-1 and the authentic-robot editing/end-to-end
criteria therefore retain their existing incomplete or blocked statuses. No
planning approval, P0 obligation or hands-on review is waived by this increment.
