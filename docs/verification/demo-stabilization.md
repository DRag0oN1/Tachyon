# Final demonstration verification — 2026-10-26

This increment repairs the reported unauthorized Home/Strategy experience and
prepares an honest demonstration of the existing partial application. It does
not complete the original authentic-robot acceptance gate or authorize publication.

## Launch and recovery

The previous entry flow depended on a tab-scoped credential that expired when
the server restarted. Opening the plain address could mount private panels and
show repeated authorization errors. The new session boundary validates the real
protected workspace before mounting those panels. Missing or expired credentials
produce one recovery screen. No unauthenticated credential endpoint was added.

From the project folder, start the intended private development profile:

```sh
TACHYON_DATA_DIR=.local/generated-robot-a-v6 \
.venv/bin/tachyon serve --port 8019 --open
```

For a fresh installation, first create a separate original development workspace
with `tools/verification/seed_generated_robot.py`, as documented in the README;
do not expect private local assets to arrive from Git.

Reopen the running application from a fresh terminal:

```sh
.venv/bin/tachyon launch --port 8019
```

The launch handoff is a mode-600 file under the project's mode-700
`.local/runtime/` directory, keyed by port and independent of the CAD profile.
The launcher verifies the current token against the protected loopback API before
opening the browser. It does not print that token. The browser strips the fragment
and keeps the credential in tab storage. Refresh works; an independent new tab
needs the authorized launch. Restart rotates credentials and retains saved data.

## Visible demo path

1. Home presents Generate Strategy, Create Robot and a direct saved-development-CAD
   action when a real matching saved assembly exists.
2. Generate Strategy loads the frozen PPO result and six rollout-derived phases.
   Full traces and evaluation metadata remain in Advanced Analysis. A representative
   episode score is explicitly separate from evaluation averages.
3. Design 01 and Design 02 show distinct four-bar/roller and elevator/jaw proposals
   for the same learned strategy family. B remains a schematic with no realized CAD.
4. Opening A requalifies the saved authored recipe against the local catalog and
   opens its partial assembly directly in the full-screen viewer.
5. The Cup action highlights actual revision-bound geometry and its anchor sketch.
6. Expand the top-left core and request a supported scoring-height change. Preview
   changes the displayed candidate and scoring-frame transform; Apply accepts that
   exact candidate. Undo restores the original engineering hash and frame. A second
   Preview/Discard retains the accepted assembly. The collapsed core contains no
   permanent input, response box or error log.
7. SNAP/SHIFT, desktop/phone layouts and contextual controls use the same data.

The recorded browser run resolved and displayed **494 placements** with **631
relationships**. The final desktop regression independently confirmed **494/494
requested/resolved/rendered placements**, **35 geometry assets**, **925 meshes**,
**14 strategy bindings** and **33 modeled operation samples**. Its source is independently authored **non-VEX development CAD**,
not a factory reference assembly. No complete robot or physical validation claim
is made. Known interference and incomplete powered Pin handling remain failures;
see [robot generation](robot-generation.md) and the unchanged
[acceptance matrix](acceptance-status.md).

## Checks

| Verification | Result |
| --- | --- |
| Complete backend suite | 699 passed; one dependency deprecation warning |
| Complete frontend suite | 186 passed across 21 files |
| Isolated RL suite | 102 passed; saved experiment/checkpoints unchanged |
| TypeScript and production build | Passed; existing bundle-size warning |
| Clean actual launch, desktop Chromium and phone WebKit | 2 passed: missing, expired, pasted current URL, refresh, independent tab |
| Missing-owner access regression, desktop and phone | 2 passed: one connection screen, no private API/asset requests or replacement geometry |
| Desktop generated-development regression | 1 passed in 4.1 minutes: actual geometry, whole modeled Cup playback, exact object/jaw matrices and Preview/Discard/Apply/Undo |
| Recorded actual WebKit journey | Passed: home, six phases, both proposals, partial CAD, highlight, all four revision decisions, desktop/mobile themes; no page errors |

Private logs and copied desktop geometry evidence are under `.local/final-demo/`.
Historical failures are retained rather than erased. Browser emulation is not a
physical-phone test. The separate three-part mechanism fixture and manufacturer
reference browser suites were not rerun against this different 41-source profile;
their opt-in requirements remain intact and are not counted as passing here.

```sh
.venv/bin/python -m pytest server/tests -q
.local/rl-venv/bin/python -m pytest research/strategy_rl/tests -q
npm run test --prefix web -- --run
npm run typecheck --prefix web
npm run build --prefix web
TACHYON_E2E_ANGLE=metal TACHYON_E2E_BASE_URL=http://127.0.0.1:8019 \
TACHYON_E2E_LAUNCH_FILE="$PWD/.local/runtime/owner-launch-8019.json" \
npm --prefix web run test:e2e -- demo-launch.spec.ts \
  --output ../.local/final-demo/launch-browser
TACHYON_E2E_ANGLE=metal TACHYON_E2E_BASE_URL=http://127.0.0.1:8019 \
npm --prefix web run test:e2e -- cad-import.spec.ts --grep 'missing owner session' \
  --output ../.local/final-demo/missing-session-browser
TACHYON_E2E_ANGLE=metal TACHYON_E2E_BASE_URL=http://127.0.0.1:8019 \
TACHYON_E2E_SESSION_FILE="$PWD/.local/final-demo/current.session" \
TACHYON_E2E_GENERATED_DEVELOPMENT=1 \
npm --prefix web run test:e2e -- generated-robot.spec.ts --project desktop \
  --output ../.local/final-demo/generated-desktop-browser
```

The last command requires a mode-600 owner-session text file supplied privately
for the running server. Never commit or print that file; the clean-launch test
and recorder use the private JSON handoff directly instead.

## Private review materials

`tools/verification/record_demo.mjs` records actual local application behavior in
a new browser context. It reads the private owner handoff, follows the real launch
URL, checks responses and visible assembly transforms, and keeps all outputs ignored.
It uses no API mocks, synthetic robot screenshots or public upload.

```sh
node tools/verification/record_demo.mjs
```

The private output directory `.local/final-demo/recording/` contains the uncut
233.84-second `raw-demo.webm`, screenshots and `evidence.json`. The review export is
`.local/final-demo/Tachyon-demo-review.mp4` (**124.54 seconds**, silent). Only interiors
of measured processing waits were removed; clicks, results and geometry remain at
recorded speed. Its persistent caption identifies the actual local app, partial
non-VEX CAD, abstract PPO simulation and abbreviated waits. The local edit receipt
and FFmpeg filter retain the exact kept intervals. No learner narration was authored.

The video and screenshots have not been uploaded. Manufacturer geometry is absent
from this recording. Source STEP, converted geometry, private credentials, rights
receipts and runtime artifacts remain outside Git. Public depiction of the exact
original development geometry and public repository creation/push still require
the learner's release approval. Do not treat private recording preparation as that
approval or as permission to redistribute CAD files.

## Remaining gates

Full authentic-robot engineering, Design B realization, general robot synthesis,
additional-rulebook PPO support and physical performance validation remain open.
The learner's hands-on readiness observations, learning wrap-up review, public
repository/video access, learner-written submission answers and final submission
remain separately tracked in [the submission checklist](../../devpost/submission-checklist.md).
No entry has been submitted.
