# Mechanical studio increment — 2026-10-26

The learner requested this presentation/interaction revision after the integrated
engineering application already existed. It does not replace the CAD engine,
train PPO, add a learned family or complete the unfinished robot gates.

The shared mechanical design system supplies original SVG housings, perforated
beams, fasteners, icons, wordmark and articulated core. SNAP/SHIFT change material,
housing geometry and interaction motion. Local industrial fonts avoid font-asset
redistribution. Reduced motion disables transitions. Home has independent strategy
and design entries, a compact competition source selector and requalified saved
local builds. Unsupported competition ingestion remains identified.

The playbook groups the actual 59-event frozen-policy rollout into six observed
phases. Travel arrows use rollout coordinates, not an official field layout.
Object illustrations and proposal schematics are explicitly illustrations; exact
revision coordinates and anchors accompany realized links. Complete traces,
conditional probabilities, capability tables, hashes, uncertainty and evidence
remain in Advanced Analysis. The displayed 43 points belong to one executed
modeled episode, not a held-out average or physical robot performance.

Design 01/02 schematics read the real architecture contracts: linked four-bar and
roller acquisition versus guided elevator and jaw acquisition. Both implement one
learned family. A has an authored local recipe; B has no full assembly in the
current development catalog. Switching to B removes A's CAD, and switching back
restores A's accepted revision. Pending previews prevent unsafe cross-design
switching. GET `/api/designs/catalog` only discovers metadata; opening saved work
still requalifies local geometry, source permissions and engineering state.

The CAD canvas remains the viewport base. Compact subsystem rails, camera/world
orientation, provenance disclosure, reversible highlighting and a mechanical
assembly tree support inspection. Focus/Split/Studio/Custom are display layouts;
Custom supports desktop resizing rather than a general docking engine. The
phone has one resizable task sheet and retractable tools. Preview/Apply/Discard/
Undo keep the existing actual revision service. General hide/isolate/explode and
additional architecture generation have no misleading active controls.

## Engineering boundaries

The development recipe renders **494 resolved and loaded instances, 35 geometry
assets, 925 meshes and 631 relationships**, with 14 action bindings. Its geometry
is independently authored non-VEX development STEP, not manufacturer CAD. It is
still partial: known frame/shaft interferences, incomplete powered Pin operations,
unqualified physical retention/placement and no complete B robot. The prescribed
Cup sequence is kinematic presentation, not physics. Original manufacturer local
source inspection remains separate. Manufacturer assembly-placement and public
geometry/mesh/image redistribution rights remain unverified; no restricted assets
are added to the public repository or uploaded by this increment.

## Verification

Backend: 689 tests passed. Frontend: 165 tests passed. Isolated RL: 102 tests
passed with saved weights unchanged. TypeScript and the production build pass.
The actual port-8019 release passes the WebKit studio journey and missing-session
case. Mobile WebKit also passes the complete generated-assembly operation and
Preview/Discard/Apply/Undo journey. Desktop Chromium/Metal passes the studio
journey, including CAD, A/B switching, modes/layouts, core states and reduced motion.
The bounded desktop edit retry also passes the full operation/revision assertions. Seven distinct browser cases pass across these runs: studio on both engines, generated operation/edits on both engines, preserved source inspection on both engines, and missing-session handling. The existing complete-
product acceptance gates remain unchanged.

```sh
.venv/bin/python -m pytest server/tests -q
.local/rl-venv/bin/python -m pytest research/strategy_rl/tests -q
npm --prefix web run test -- --run --maxWorkers=2
npm --prefix web run build

# Use a running owner-local development-CAD workspace and its private session.
# These paths are ignored; they are not required public assets.
TACHYON_E2E_BASE_URL=http://127.0.0.1:8020 \
TACHYON_E2E_SESSION_FILE="$PWD/.local/studio-overhaul/preview.session" \
TACHYON_E2E_GENERATED_DEVELOPMENT=1 \
npm --prefix web run test:e2e -- mechanical-studio.spec.ts \
  --output ../.local/studio-overhaul/studio-final

TACHYON_E2E_BASE_URL=http://127.0.0.1:8020 \
TACHYON_E2E_SESSION_FILE="$PWD/.local/studio-overhaul/preview.session" \
TACHYON_E2E_GENERATED_DEVELOPMENT=1 \
npm --prefix web run test:e2e -- generated-robot.spec.ts \
  --output ../.local/studio-overhaul/generated-regression
```

Production setup and independent authored development-fixture preparation remain
in `README.md` and `docs/verification/robot-generation.md`. Existing public asset
bundles contain application code only; private CAD and screenshot reports remain
ignored. Learner hands-on readiness review, the app-map/wrap-up and `6-ship` remain
pending. No submission or public deployment is performed.

The native desktop command adds `TACHYON_E2E_ANGLE=metal` and `--project=desktop`.
Software WebGL remains the default. One early software screenshot hit its 20-second
capture budget; the studio test now permits 120 seconds for actual CAD captures.
The initial long native desktop edit run lost a Discard response and timed out;
the assistant reported failure without confirming a change. The bounded retry
records request failures and temporarily prevents idle system sleep with
`caffeinate -i`. No engineering assertions were removed. Rich SVG/evidence jsdom
checks use a 15-second file budget under concurrent WebGL load.

Reviewed production screenshots remain private in `.local/studio-overhaul/verified/`:
`desktop-snap-home.png`, `desktop-snap-designs.png`, `desktop-shift-cad.png`,
`mobile-snap-home.png`, `mobile-snap-playbook.png`, `mobile-shift-cad.png`,
`design-01.png`, `design-02.png`, and `strategy-cad.png`. This includes whole CAD,
two distinct architecture schematics and revision-linked strategy highlighting.
The reviewer inspected the actual images, repaired empty-bench hierarchy and
core/header overlap, removed irrelevant Home CAD controls and startup loading,
and checked phone overflow and primary touch targets. A physical phone and
complete adaptive/accessibility matrix remain unverified.

Final desktop edit retry: **passing**, 3.7 minutes, with 494/494 loaded instances, 925 meshes, 631 relationships, 14 bindings, all 33 modeled samples, continuous playback and Preview/Discard/Apply/Undo. No browser errors were recorded in that successful run. The earlier lost-response failure remains recorded above; its root cause is not established.

Final preserved source-viewer regression: **2 passing** (desktop Chromium/Metal
and phone WebKit), including real GLB/hash identity, metres/mm scale, native-node
selection, orbit/zoom/pan/reset, theme/camera continuity, retained assistant draft,
reduced motion and no unauthorized mesh requests. Legacy test selectors were
updated to filter/expand the actual native hierarchy and use the new core's
classes. Source inspection permits explanation commands while its engineering
Preview/Apply controls remain disabled. A more-specific old mobile CSS rule had
hidden connection state; the studio now explicitly exposes it. The inspected
source was original development CAD, not new authentic-VEX evidence.

A failed legacy-test teardown echoed an ephemeral loopback owner header into an
ignored diagnostic. That session was invalidated by restart, the diagnostic was
redacted, and the authorized review tab reopened. Teardown diagnostics now retain
the original test error and suppress the secondary disposed-request exception.
No credential, proprietary CAD or screenshots enter the public commit.
