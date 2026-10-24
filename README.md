# Tachyon

A mobile-first robotics design studio connecting competition rules, strategies,
real VEX component assemblies and contextual design changes.

**Complicatedly Simple.** CAD fills the workspace. SNAP and SHIFT share the same
source data, selection and controls; the top-left core expands inside the assistant.

## Build status

Scope, PRD, specification and the refined six-increment build checklist are
approved. `5-build` is active in fast mode.

The first implementation provides local STEP registration, operation-specific
rights checks, source-preserving import, GLB conversion, native hierarchy,
external catalog discovery/provenance records, permission-gated measurement,
authenticated local asset serving and a full-screen source viewer. SNAP/SHIFT,
source selection, orbit/zoom/pan/reset, assistant expansion, Simple/Advanced source
detail and persisted preferences are implemented. See the
[verification record](docs/verification/slice-1.md) and
[acceptance status](docs/verification/acceptance-status.md) for actual evidence.

**This is not the completed Tachyon workflow.** Complete robot builders, live AI
strategy/design generation, strategy-to-mechanism actions and scoring-height
revisions are unimplemented. The first slice remains unchecked because authentic
VEX conversion/display rights and a qualified component set are still missing.
No VEX geometry was converted, bundled or deployed during this increment.

The running converter/render checks use an original **Tachyon-authored non-VEX
test fixture**. It is labeled in the app and cannot count as authentic VEX CAD,
a complete robot, generated strategy or a supported mechanism edit.

## Isolated strategy-first RL

An independent [PyTorch PPO experiment](research/strategy_rl/README.md) now
discovers abstract strategies before planning robot architecture. Three training
seeds completed 786,432 simulated decisions and 12,288 gradient updates. The
[preserved report](research/strategy_rl/results/override-ppo-v1/REPORT.md) includes
checkpoints, held-out random/heuristic controls, reproducible traces and a
strategy-driven architecture proposal. The new
[strategy-to-design interface](docs/strategy-design-interface.md) also emits two
engineering alternatives for the same learned family. Generated CAD and a second
learned family are not claimed. All results are abstract simulated strategy
performance. This subsystem is separate from the app and its Python environment;
production integration remains disabled.

## Install and run locally

Requires Python 3.12 and Node >=22.12. The verified environment is macOS arm64;
other platforms have not been runtime-verified. Use this project's environment:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r server/requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e ./server
npm ci --prefix web
npm run licenses --prefix web
npm run build --prefix web
.venv/bin/python -m uvicorn tachyon.app:app --host 127.0.0.1 --port 8000
```

Open the **owner launch URL printed by that serving process**. Its session is
independent of the model-provider credential. The app removes the session fragment
from the address bar and authorizes local requests; a plain URL without the owner
session shows a connection error. Do not record the owner-console URL in a public
demo. Restarting the server invalidates the old session. STEP originals default to
`~/Documents/TachyonCAD/step/`, rights and source records to
`~/Documents/TachyonCAD/rights/`; these stay outside the repository. Private caches
and the database use ignored `.local/`. No CAD library is installed automatically.

For frontend development, run the API with
`TACHYON_UI_ORIGIN=http://127.0.0.1:5173`, start
`npm run dev --prefix web -- --host 127.0.0.1` in another terminal, and use its
printed owner URL. Vite proxies `/api` to port 8000. For a built app served on a
phone, configure the actual trusted LAN origin and separately qualified LAN
asset-display rights; loopback permission is insufficient. Physical-phone
pinch/pan and the complete phone journey remain unverified.

## Supply permitted component geometry

See [local catalog setup](data/catalog/README.md) for source manifests, private
permission records, measured bounds, ports and CLI registration/preparation.
Source paths and evidence stay in private local storage. Missing or changed rights,
wrong source hashes, invalid units and ambiguous source roots fail closed.
Manufacturer CAD is preferred, but public availability and tooling licenses do
not establish CAD conversion or redistribution permission.

GLB is source-derived display geometry, not an editable solid. An imported parent
hierarchy is not proof of mechanical attachment, actuation, task support or a
complete robot. CAD redistribution, public mesh hosting and source-part editing
are unavailable. A future public demonstration also needs applicable imagery
publication rights. See [CAD source status](docs/cad-source-status.md).

## Reproduce converter tests without third-party CAD

This optional generator creates original calibration STEP and narrowly scoped
self-authorship evidence in a **separate**, ignored verification workspace:

```sh
.venv/bin/python tools/verification/seed_fixture.py --prepare
TACHYON_DATA_DIR=.local/verification-workspace \
TACHYON_UI_ORIGIN=http://127.0.0.1:5173 \
.venv/bin/python -m uvicorn tachyon.app:app --host 127.0.0.1 --port 8000
```

The seeder refuses to replace an existing workspace. To re-prepare an existing
fixture after converter changes, set `TACHYON_DATA_DIR=.local/verification-workspace` and use
`assets-prepare --manifest` and `--rights`
with its existing private catalog files. Never apply the fixture's self-authorship
evidence to manufacturer or user CAD. The main workspace remains separate.

## Verification

```sh
.venv/bin/python -m pytest server/tests
npm run test --prefix web -- --run
npm run build --prefix web
```

Browser tests use the real running backend, source catalog and GLB responses.
Supply that process's ephemeral owner session through a private ignored file
using `TACHYON_E2E_SESSION_FILE` (an absolute path), then run
`npm run test:e2e --prefix web -- --grep @cad-import`. An absent required input is
reported as skipped/blocked; fixture tests never pass authentic-VEX acceptance.
Browser recordings/traces are disabled and screenshots are restricted to the
original calibration fixture or empty workspace. Evidence stays local.

Model configuration is server-side only. No provider credentials are currently
configured or required for source inspection. No external model-provider
inference has been verified in the application.
Keep actual credentials out of frontend variables, browser storage and Git.

## Project documents

- [Product vision](docs/product-vision.md)
- [Devpost progress](devpost/README.md)
- [Approved scope](devpost/scope.md), [PRD](devpost/prd.md), [specification](devpost/spec.md)
- [Approved build checklist and remaining work](devpost/checklist.md)
- [Source restrictions](docs/cad-source-status.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

The official Devpost sequence remains `1-start` → `2-scope` → `3-prd` → `4-spec`
→ `5-build` → `6-ship`. Early/final hands-on review and learning wrap-up remain
required. No publication, deployment or challenge submission has occurred.
