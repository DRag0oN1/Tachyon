# Production integration verification — 2026-10-24

`5-build` remains active in fast mode. This record describes executed software,
not full-robot or physical-match acceptance. No policy was retrained, no existing
checkpoint replaced, and no private robotics implementation incorporated.

## Actual sequence and implementation

The app/source inspector and its uncommitted CAD, assembly and binding foundations
already existed when production integration began. This increment preserves and
saves those dependencies with the new production wiring. The PPO experiment
(`ac1aa01`) and structured bridge (`eb1265c`) preceded this integration. Planning
and earlier experimental records have not been rewritten as prior production
implementation. The learner explicitly requested saved-policy integration and
independent engineering progress while external component gates remain open.

The running app now connects the verified v2 specification, fresh frozen neural
inference, saved architecture proposals, measured-port realization service,
source-mesh renderer, revision-specific strategy links and bounded assistant
commands. [Assembly contracts](../assembly-realization.md) document the routes,
private recipe schema and invariants. Only the existing bounded Override v2.1
scenario is supported. Other competitions are explicitly unavailable to PPO.

The production rollout used saved seed-17 weights and fixed episode seed
`5000000001`: **59 decisions, 43 abstract modeled points**. Repeating Generate
executes the policy again with that seed; it is not a newly discovered strategy
or a new experiment. Parameter hashes before/after agree. This single rollout
does not replace the preserved held-out evaluation or establish physical scores.

## Executed checks

| Check | Result and boundary |
| --- | --- |
| `.venv/bin/python -m pytest server/tests -q` | **528 passed**; source/native/rights, graph/joint/binding, real frozen inference, API/revision/persistence and refusal cases |
| `npm run test --prefix web -- --run` | **86 passed**, 17 files; strategy/architecture UI, actual-matrix renderer contract, assistant intent/response validation, native picking/hierarchy and source controls |
| `.local/rl-venv/bin/python -m pytest research/strategy_rl/tests -q` | **102 passed**; frozen research interfaces preserved; no production training |
| `npm run build --prefix web` | Passed TypeScript and Vite; shared Three/GLB chunk ~953 kB minified (~257 kB gzip) produces a size warning |
| `@authentic-reference` | **2 passed**; actual V5 motor GLB, desktop Chromium and mobile WebKit, SNAP and SHIFT, multiple native-part selections, focus/reset/up-axis and dimension checks |
| `@production-strategy` | **2 passed**; live policy, human-readable strategy and playbook, two actual proposals, real motor reference retained, truthful realization gaps and unsupported height edit, assistant states |
| `@production-revision` | **2 passed**; real newly authored STEP mechanism, geometry rendering/raycast, forward/reverse strategy selection, actual Preview/Discard/Apply/Undo and stable links on desktop/mobile |

Final production browser runs used the built app and real HTTP/GLB responses,
not mocked generation or a static screenshot. The strategy run took ~1.4 minutes;
the separate mechanism run ~32 seconds. No uncaught browser errors were observed.
The strategy test also rejects unexpected remote requests. No CAD was uploaded.
Mobile means Playwright's WebKit phone viewport, not a physical phone/LAN test.

Review found and repaired three edit defects before this final verification:
unsupported target requests could trigger scorer edits; extra unrelated joint
changes could pass qualification; and swapped lower/raised labels could lower
the anchor. Regression tests now reject all three. One new negative test initially
failed because its test recipe omitted its drive-role mapping; the fixture was
corrected and the complete 528-test suite passed. A prior browser assertion raced
the accepted/candidate transition; it now waits for confirmed accepted state.

The connected browser plugin could not start its Node runtime (OS error 2).
Verification used the repository's existing Playwright setup instead. No browser
session or public service was used to obtain geometry.

## Two separate evidence boundaries

**Authentic source inspection:** V5 motor 276-4840 has 23 source solids and 28
display hierarchy nodes. Clawbot 276-6009 has 450 solids, 515 display nodes and
435 geometry occurrences. Its aggregate BRep is invalid, although all 48 unique
leaf definitions passed native validation. Current browser evidence uses the
smaller motor, not a complete-Clawbot mobile performance claim. Original/native
and browser bounds are compared through the existing conversion receipts and
render checks. Native importer transforms/labels are preserved; source identity
does not turn CAD hierarchy into a mechanical attachment graph.

The current VEX entries are reference-only, with no measured generation ports
or qualified part-role mapping. Their source hashes and scoped operation status
are recorded in [CAD source status](../cad-source-status.md). No conversion,
display or redistribution grant was invented by this integration.

**Original mechanism proof:** `tools/verification/seed_mechanism.py` newly authors
a guide, carriage and fixed tool bracket/jaws as three native STEP sources in a
separate ignored workspace. Real imported source meshes are placed through a
prismatic guide joint and fixed descendant mount. The lower/raised change moves
carriage and tool **+100 mm**, leaves the guide fixed and moves the same tool
anchor from **80 to 180 mm**. Preview leaves accepted matrices/hash unchanged;
Discard restores the displayed accepted pose; Apply accepts the exact candidate;
Undo restores previous engineering content in a new history revision. Source,
instance, action and anchor IDs persist; revision/binding hashes are rederived.

Selecting Place an alliance Pin highlights carrier/tool, focuses the camera and
shows the current coordinate/anchor sketch. A real raycast on the source tool
exposes the reverse action. Links remain correct through all revision operations.
This fixture is **non-VEX, partial, below the learned 352 mm target and not a
powered or physically validated mechanism**. It does not pass complete-authentic-
robot, real game-object scoring or physical-reach criteria.

## Current product status

| Category | Actual state |
| --- | --- |
| Working | Saved-policy inference, conditional StrategySpec v2 UI, objectives/priorities/decision contexts, sequences, abstract annotated playbook, capability/mechanism requirements, advanced evidence, actual bridge comparison, independent entry points, authentic local source inspection, SNAP/SHIFT and assistant states |
| Working on qualified private partial recipes | Connected placement/joint graph, source identity, exact world transforms, mesh rendering, forward/reverse selection, derived anchor sketch, Preview/Apply/Discard/Undo, persisted design revisions and requalification |
| Partial | Architecture-to-CAD: accepts real recipes and reports exact gaps, but current authentic catalog produces no robot. Simple/Advanced and panel resizing work; complete Focus/Split/Studio/Custom behavior and recovery are unfinished. Strategy results are held in the current tab; saved design sessions have APIs but are not automatically restored in the UI. |
| Blocked inputs/rights | Qualified authentic role components, measured full frames/ports and appropriate assembly-placement scope. Public geometry hosting, redistribution and rendered-depiction rights remain unverified. No physical-phone/LAN verification. |
| Unimplemented | Full authentic robot BOM/builders and actuation/control hardware, whole-robot task/clearance validation, second-rulebook ingestion/non-RL model path, continuous mechanism operation, broad CAD edits, Fusion/simulator integrations, automatic capability feedback/co-optimization |
| Failing | No failing executed check remains. The full requested end-to-end authentic robot journey has **not passed**; component blockers and unimplemented operations are not test successes. |

Required roles still missing from the authentic generation catalog: chassis,
drive, Pin intake, Pin transfer, scorer, independent Cup cradle and stack interface,
with their support/fastening/actuation/control hardware. Even with permission,
whole-file reference imports cannot supply these roles without actual part
selection, measured mounts, engineered recipes and task validation. See the
[criterion matrix](acceptance-status.md); all 22 P0 obligations remain required.

## Reproduction commands

Install the two environments and build the app as described in the README.
For actual source-catalog verification, start:

```sh
TACHYON_UI_ORIGIN=http://127.0.0.1:8008 .venv/bin/python -m uvicorn tachyon.app:app --host 127.0.0.1 --port 8008
```

Use that process's printed owner URL in a browser. Put only its session value in
an ignored mode-600 file `.local/verification/production-session`; never commit
or publish it. From the repository root, with that file's absolute path:

```sh
TACHYON_E2E_BASE_URL=http://127.0.0.1:8008 \
TACHYON_E2E_SESSION_FILE="$PWD/.local/verification/production-session" \
TACHYON_E2E_REFERENCE_ID=v5_motor_reference \
npm run test:e2e --prefix web -- --grep @authentic-reference --output ../.local/verification/production-motor-inspection

TACHYON_E2E_BASE_URL=http://127.0.0.1:8008 \
TACHYON_E2E_SESSION_FILE="$PWD/.local/verification/production-session" \
npm run test:e2e --prefix web -- --grep @production-strategy --output ../.local/verification/production-browser-final
```

For the original mechanism, seed a **new** separate workspace (refuses overwrite),
then start its server and use its separate private owner session file:

```sh
.venv/bin/python tools/verification/seed_mechanism.py
TACHYON_DATA_DIR=.local/mechanism-verification TACHYON_UI_ORIGIN=http://127.0.0.1:8009 \
.venv/bin/python -m uvicorn tachyon.app:app --host 127.0.0.1 --port 8009
```

```sh
TACHYON_E2E_BASE_URL=http://127.0.0.1:8009 \
TACHYON_E2E_SESSION_FILE="$PWD/.local/verification/mechanism-session" \
TACHYON_E2E_MECHANISM_FIXTURE=1 \
npm run test:e2e --prefix web -- --grep @production-revision --output ../.local/verification/mechanism-browser-final
```

Current local owner launch URLs are stored privately in
`.local/verification/production-launch-url` and `mechanism-launch-url`. They are
ephemeral and invalid after a server restart. Existing unrelated serving processes
were left running. No asset rights records were broadened for these tests.

## Evidence and remaining review

Private screenshots are in `.local/verification/production-motor-inspection/`,
`production-browser-final/` and `mechanism-browser-final/`. They show actual CAD,
strategy panels, source restrictions and candidate/applied poses. Desktop SNAP,
mobile SHIFT and the updated mobile sketches were visually inspected.
[Evidence hashes](production-evidence.json) identify files without publishing
geometry depictions. Manufacturer screenshots remain local, unpublished and
subject to separate depiction rights. Browser videos/traces are disabled.

The formal checklist revision records the learner-directed saved-PPO substitution
and dependency sequencing; it does not waive complete robots or change the P0
boundary. Full P0 hands-on review, final review, learning wrap-up and shipping
remain incomplete. This increment is a usable production connection with explicit
engineering gaps, not completion of the full Tachyon product.
