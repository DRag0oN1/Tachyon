# Tachyon

A mobile-first robotics design studio connecting competition rules, learned
strategies, real component assemblies and contextual design changes.

**Complicatedly Simple.** CAD fills the workspace. SNAP and SHIFT share engineering
data and controls; the top-left core expands inside the assistant.

## Build status

Scope, PRD, specification and checklist are approved. `5-build` remains active in
fast mode; final hands-on review and `6-ship` have not occurred.

The app runs the saved Override PPO policy and presents conditional StrategySpec v2
with objectives, annotated playbooks and simulation evidence. Generate Strategy and
Create Robot are independent entry points. Two mechanically distinct architecture
proposals from the verified bridge implement **one learned family**. They are
engineering proposals, not generated CAD or two discovered strategies.

The full-screen CAD workspace displays authentic locally supplied STEP geometry,
with native hierarchy, part selection, camera controls, source identity,
SNAP/SHIFT, Simple/Advanced details and saved preferences. The tested V5 motor and
Clawbot remain imported references. No manufacturer geometry is bundled or publicly
hosted. Local-use qualification is a scoped terms interpretation, not a manufacturer
redistribution license.

Private measured-port recipes construct connected partial assemblies from qualified
components. Scoring-height previews update actual joint poses, descendant placements,
anchors, sketches and revision-specific action bindings. Apply accepts the exact
candidate, Discard retains the accepted assembly, and Undo creates a compensating
revision. Browser verification uses a separately authored **non-VEX STEP mechanism**,
explicitly labeled as a partial computational fixture. This proves the revision
pipeline, not VEX robot or physical mechanism functionality.

**The complete authentic robot journey remains incomplete.** A new measured-source
compiler creates architecture A's geared drive, paired powered four-bars, mounted
Claw Kit tool, roller intake and control/power layout: 449 outer instances and 576
relationships. Both endpoint graphs and 12 strategy bindings pass metadata checks;
this does not establish a rendered or complete robot. Gated transfer, independent
Cup handling, stack alignment, full mount/transmission qualification and physical
task/clearance checks remain unfinished. Assembly-placement rights remain
unverified in the supplied source records. Realization reports these gaps.
The [generation increment](docs/verification/robot-generation.md) documents exact
boundaries and preparation commands. Other-competition PDF ingestion, broader editing and full
workspace layouts remain unfinished. See the
[production verification](docs/verification/production-integration.md),
[CAD source status](docs/cad-source-status.md) and
[44-criterion acceptance record](docs/verification/acceptance-status.md).

## Saved strategy-first RL

The independent [PyTorch PPO experiment](research/strategy_rl/README.md) completed
786,432 simulated decisions and 12,288 gradient updates. Its
[preserved report](research/strategy_rl/results/override-ppo-v1/REPORT.md) contains
checkpoints, held-out random/heuristic controls and reproducible traces. The
[design bridge](docs/strategy-design-interface.md) exports structured mechanical
requirements and two engineering alternatives for the same family.

Production inference uses those saved weights in a separate Python environment
through a bounded subprocess. The CAD server and browser never import Torch, and
Generate performs no training. Results are **abstract simulated strategy performance**,
not physical robot or match predictions. Only the authored Override v2.1 environment
is supported by PPO. Arbitrary uploaded rulebooks do not acquire RL support.

## Install and run locally

Requires Python 3.12 and Node >=22.12. Verified on macOS arm64; other platforms
have not been runtime-verified. Install the two isolated environments:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r server/requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e ./server
npm ci --prefix web
npm run licenses --prefix web
npm run build --prefix web
python3.12 -m venv .local/rl-venv
.local/rl-venv/bin/python -m pip install -r research/strategy_rl/requirements.lock
.local/rl-venv/bin/python -m pip install --no-deps --no-build-isolation -e research/strategy_rl
.venv/bin/python -m uvicorn tachyon.app:app --host 127.0.0.1 --port 8000
```

Open the **owner launch URL printed by that serving process**. The app removes
its session fragment from the address bar and authorizes local requests. A plain
URL without the owner session shows a connection error. Keep this URL out of
public demos. Restarting invalidates the session. No provider key is needed for
the saved PPO path. An unavailable isolated runtime produces a retryable
availability/error view rather than mock inference.

STEP originals default to `~/Documents/TachyonCAD/step/`; source and permission
records use `~/Documents/TachyonCAD/rights/`. These stay outside the repository.
Private caches, recipes and the database use ignored `.local/`. No CAD library
is installed automatically and no CAD bytes/renders are sent to a remote service.

For frontend development, run the API with
`TACHYON_UI_ORIGIN=http://127.0.0.1:5173`, start
`npm run dev --prefix web -- --host 127.0.0.1` separately, then use its printed
owner URL. Vite proxies `/api` to port 8000. Physical-phone access requires an
explicit trusted LAN origin and separately qualified LAN display rights.
Loopback browser emulation does not establish physical-phone support.

## Supply permitted component geometry

[Catalog setup](data/catalog/README.md) documents source manifests, private rights
records, measured bounds, ports and registration/preparation commands. Source
hashes, rights scope, units, geometry and provenance are checked separately.
Manufacturer availability and tooling licenses do not establish asset permissions.

GLB is source-derived display geometry, not editable solid CAD. Imported hierarchy
does not establish mechanical attachments, actuation or complete-robot capability.
Source-part editing, geometry redistribution and public mesh hosting remain
unavailable. Publication of CAD imagery requires a separate applicable basis.
[Measured assembly recipes](docs/assembly-realization.md) describe the connection
between bridge architectures, parts, joints, revisions and strategy bindings.

## Reproduce geometry and revision checks without third-party CAD

The calibration seeder authors original STEP in a separate ignored workspace:

```sh
.venv/bin/python tools/verification/seed_fixture.py --prepare
```

For the three-component moving-joint workspace:

```sh
.venv/bin/python tools/verification/seed_mechanism.py
TACHYON_DATA_DIR=.local/mechanism-verification \
TACHYON_UI_ORIGIN=http://127.0.0.1:8009 \
.venv/bin/python -m uvicorn tachyon.app:app --host 127.0.0.1 --port 8009
```

Seeders refuse to overwrite existing workspaces. Their self-authorship records
apply only to their original fixtures, never manufacturer/user CAD. The main
catalog is untouched. Choose Create Robot, select alternative B, check its parts,
open Strategy and select Place an alliance Pin. In the assistant, request “Raise
scoring height,” inspect Preview, then Apply, Undo or Discard. The 80/180 mm tool
anchors are below the learned 352 mm target and are reported as such. Missing
robot subsystems and unverified hardware capabilities remain visible.

## Verification

```sh
.venv/bin/python -m pytest server/tests -q
.local/rl-venv/bin/python -m pytest research/strategy_rl/tests -q
npm run test --prefix web -- --run
npm run build --prefix web
```

Browser checks use the real backend and GLB responses. Supply its ephemeral owner
session through a private file using `TACHYON_E2E_SESSION_FILE` (absolute path).
Use `@production-strategy` for the saved-policy UI, `@authentic-reference` with
`TACHYON_E2E_REFERENCE_ID` for qualified source inspection, or
`@production-revision` with `TACHYON_E2E_MECHANISM_FIXTURE=1` only against the
separate original-mechanism workspace. Exact commands and evidence are in the
[verification record](docs/verification/production-integration.md). Missing required
inputs are skipped/blocked, never passing authentic-VEX criteria. Recordings and
traces are disabled; private CAD screenshots remain ignored and unpublished.

Model-provider configuration is server-side only. No external model-provider
inference has been verified. Keep credentials out of frontend variables, browser
storage and Git. The independent PPO path needs no provider credential.

## Project documents

- [Product vision](docs/product-vision.md)
- [Devpost progress](devpost/README.md)
- [Approved scope](devpost/scope.md), [PRD](devpost/prd.md), [specification](devpost/spec.md)
- [Build checklist](devpost/checklist.md)
- [Source restrictions](docs/cad-source-status.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

The official sequence remains `1-start` → `2-scope` → `3-prd` → `4-spec` →
`5-build` → `6-ship`. Reviews, learning wrap-up and shipping remain pending.
No publication, deployment or challenge submission has occurred.
