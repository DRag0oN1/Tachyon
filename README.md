# Tachyon

A mobile-first robotics design studio connecting competition rules, learned
strategies, real component assemblies and contextual design changes.

**Complicatedly Simple.** CAD fills the workspace. SNAP and SHIFT share engineering
data and controls; the top-left core expands inside the assistant.

## Build status

Scope, PRD, specification and checklist are approved. `5-build` remains active in
fast mode. The learner authorized bounded `6-ship` publication of the partial
demo. [Public source](https://github.com/DRag0oN1/Tachyon) is available; full-build
completion, video hosting and the learner's Devpost submission remain open.

The app runs the saved Override PPO policy and presents conditional StrategySpec v2
with objectives, annotated playbooks and simulation evidence. Generate Strategy and
Create Robot are independent entry points. Two mechanically distinct architecture
proposals from the verified bridge implement **one learned family**. They are
engineering alternatives, not two discovered strategies. Architecture A now
produces an inspectable development assembly; architecture B's full CAD remains
unimplemented.

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

**The complete authentic robot journey remains incomplete.** The architecture-A
compiler now renders **494 generated placements, 35 geometry assets and 631
relationships**, with 14 strategy bindings. The development workspace uses
originally authored, explicitly **non-VEX** STEP hardware through the production
catalog/conversion/realization/viewer pipeline. It includes a two-motor geared
drive, paired four-bars, roller intake, supported Cup clamp/transmission and
control/power layout. A prescribed Cup acquisition/lift/placement/release sequence
operates its actual joints on a 120 mm development fixture; contact, forces,
scoring and physical retention are unverified. Whole-assembly solid checks found
structural interference, so it remains a partial development assembly. Powered
Pin handoff/release, full mounting/clearance qualification and architecture B
remain unfinished. No imported factory assembly is used as generated-robot proof.
The original VEX source records are unchanged; new assembly placement and public
distribution/hosting/publication rights remain unverified for those assets.
The [generation increment](docs/verification/robot-generation.md) documents exact
boundaries and preparation commands. Other-competition PDF ingestion, broader engineering edits and full
inspection/docking controls remain unfinished. See the
[production verification](docs/verification/production-integration.md),
[CAD source status](docs/cad-source-status.md) and
[44-criterion acceptance record](docs/verification/acceptance-status.md).

## Mechanical studio

Home keeps **Generate Strategy** and **Create Robot** as independent actions.
The visual playbook groups the actual rollout into phases; **Advanced Analysis**
retains its full trace, conditional evidence and capability targets. Episode points
are labeled separately from evaluation averages.

**Design 01** is the four-bar/roller proposal with a local authored assembly recipe.
**Design 02** is the distinct elevator/jaw proposal and currently shows its honest
schematic and build requirements. Switching designs changes the displayed content
and preserves each accepted assembly revision. Saved local builds recheck their
inputs when opened. This is recipe construction, not unrestricted robot synthesis.

SNAP uses perforated docking housings and modular motion; SHIFT uses articulated
shells, asymmetric panels and rail transitions. The small top-left mechanical core
contains its expansion controls. The bottom rail prioritizes Design, Strategy and
Components. Preferences provides Simple/Advanced and Focus/Split/Studio/Custom
arrangements; desktop Custom permits practical panel resizing. Phones use one
resizable task sheet. Tool rails retract, and viewport resizing refits actual CAD.
General docking, hide/isolate/explode and full two-robot realization remain unfinished.
See the [studio verification](docs/verification/mechanical-studio.md).


## Current demonstration

- Start with the authorized launch, then **Generate Strategy**. All six observed
  PPO phases are visible; full traces and experiment data stay in Advanced Analysis.
- **Create Robot** opens Design 01 and Design 02. A has a saved/authored partial
  development assembly; B is an elevator/jaw schematic, not realized CAD.
- Use **Inspect the development assembly** on Home or **Open development CAD**
  in Design. Every open rechecks its inputs; no imported reference replaces it.
- Select a phase and its Cup action to highlight actual linked geometry.
- Open the mechanical core, request a supported scoring-height configuration,
  then Preview/Apply/Undo or Preview/Discard. Collapsing the core hides the form
  and response; it does not accept an edit.
- SNAP/SHIFT and mobile layouts share the same engineering data.

This demonstrates frozen-policy inference and real changes to a **partial,
independently authored non-VEX assembly**. It does not demonstrate a complete
validated VEX robot, physical match performance, arbitrary robot synthesis or
new-rulebook PPO support. CAD files remain private; the reviewed video is prepared
for public sharing. [Publication details](docs/publication.md) and
[submission preparation](devpost/submission-checklist.md)
records the remaining user-authored fields and publication approvals.
The [demo stabilization record](docs/verification/demo-stabilization.md) contains
the launch/recovery verification, recording procedure and remaining failures.

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
.venv/bin/tachyon serve --port 8019 --open
```

The `--open` option opens a connected browser tab after the server is ready.
To reopen or recover an expired tab, run this from the Tachyon project folder:

```sh
.venv/bin/tachyon launch --port 8019
```

This works from a fresh terminal even when the server uses a separate private CAD
profile. The launcher reads a mode-600 project-local handoff, verifies it against
the real protected API, and opens the current authorized link without printing its
credential. There is no unauthenticated token endpoint or public-CAD shortcut.
A plain `http://127.0.0.1:8019/` in a fresh browser shows one connection screen,
not a broken Home/Strategy view. If automatic opening is unavailable, run
`launch --port 8019 --show-url` **privately** and paste its full output into the
connection screen. Never paste it into chat, a public recording or submission.

The app strips the credential fragment before requests, keeps it in tab-scoped
storage, and supports refresh. New independent tabs/reopened browsers need the
launch command. Restart rotates the session and invalidates the old link; saved
assemblies and server-side previews remain intact. No provider key is required
for the saved PPO path. Unavailable services are reported rather than mocked.

STEP originals default to `~/Documents/TachyonCAD/step/`; source and permission
records use `~/Documents/TachyonCAD/rights/`. These stay outside the repository.
Private caches, recipes and the database use ignored `.local/`. No CAD library
is installed automatically and no CAD bytes/renders are sent to a remote service.

For frontend development, run the API with
`TACHYON_UI_ORIGIN=http://127.0.0.1:5173`, start
`npm run dev --prefix web -- --host 127.0.0.1` separately, then use `tachyon launch --port 5173` once both are running. Vite proxies `/api` to port 8000. Physical-phone access requires an
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

For the generated architecture-A development assembly:

```sh
.venv/bin/python tools/verification/seed_generated_robot.py \
  --data-dir .local/generated-development
TACHYON_DATA_DIR=.local/generated-development \
.venv/bin/tachyon serve --port 8017 --open
```

Use `tachyon launch --port 8017` to reopen. Choose **Create Robot → Design 01 → Assemble local recipe** (or **Open development CAD** for an existing saved assembly). The accepted partial assembly opens directly in the full-screen viewer. Components can color the seven subsystems;
Strategy highlights the actual mechanisms. **Prepare Cup operation** exposes
continuous playback and individual stages. The assistant's supported height
commands operate real Preview/Apply/Discard/Undo revisions. This profile is
independently authored development CAD, not authentic VEX or validated robot
hardware. All generated STEP/GLB, recipes, sources and state stay ignored/local.
It reads no manufacturer or private-project CAD and grants no rights over those
materials. Existing output is preserved by refusing overwrite.

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
The opt-in `demo-launch.spec.ts` instead reads the private launch handoff via
`TACHYON_E2E_LAUNCH_FILE` and follows the actual launch URL from a clean browser,
including missing/expired recovery, refresh and an independent new tab.
The generated assembly uses `@generated-development` with
`TACHYON_E2E_GENERATED_DEVELOPMENT=1`; its geometry and interference results are
recorded separately in the [generation report](docs/verification/robot-generation.md).

Model-provider configuration is server-side only. No external model-provider
inference has been verified. Keep credentials out of frontend variables, browser
storage and Git. The independent PPO path needs no provider credential.

## Project documents

- [Public source, video handoff and final audit](docs/publication.md)
- [Immediate next milestone: scalable design generation](docs/next-design-generation.md)
- [Product vision](docs/product-vision.md)
- [Devpost progress](devpost/README.md)
- [Approved scope](devpost/scope.md), [PRD](devpost/prd.md), [specification](devpost/spec.md)
- [Build checklist](devpost/checklist.md)
- [Application reference map](devpost/app-map.html)
- [Submission preparation](devpost/submission-checklist.md)
- [Source restrictions](docs/cad-source-status.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

The official sequence remains `1-start` → `2-scope` → `3-prd` → `4-spec` →
`5-build` → `6-ship`. Reviews, learning wrap-up and shipping remain pending.
Source publication is complete. No live deployment or challenge submission has occurred.
