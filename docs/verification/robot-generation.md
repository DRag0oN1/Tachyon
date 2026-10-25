# Measured-source robot generation increment — 2026-10-25

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
