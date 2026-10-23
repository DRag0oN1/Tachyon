---
doc: checklist
status: draft
---

# Tachyon Build Checklist

Build mode: fast — selected by the learner. Verify and commit each slice;
pause for the early hands-on checkpoint and final review. Less code discussion
does not remove learner ownership or the required tests.

Scope, PRD and technical specification are approved. This is the first proposed
implementation order; no application slice is implemented or passed yet. The
existing native-CAD mount probe is pre-build source research, not a completed
slice or evidence of a working lift, robot, AI edit or browser application.

A slice stays unchecked until its usable behavior and required mechanical
verification pass. An unavailable input can be reported as blocked, but an
expected rejection or a synthetic fixture cannot substitute for that slice's
required authentic geometry, real inference or complete-assembly demonstration.
Keep the approved 22 P0 / 20 P1 / 2 P2 gates; the first working version requires
all P0 obligations, while full completion also requires the remaining criteria.

## Slices

- [ ] **1. Register local CAD and inspect its real component geometry**
  Becomes usable: Start Tachyon locally, see Home with the two independent entry actions and truthful availability, register supplied STEP through the local CLI, and inspect a permitted component in the full-screen viewer with identity/source information. Missing permission or geometry produces an actionable unavailable state instead of a substitute robot.
  Why now: Proves the critical source → permission check → conversion → authenticated asset API → actual browser rendering path before building robot or AI claims around it. Bootstrapping belongs inside this working increment.
  PRD ref: `prd.md > Home and First Use`, `CAD Workspace Composition`, `F4 — Authentic Components and Connected Conceptual Assemblies`, `F5 — Interactive CAD Inspection`, `F8 — SNAP, SHIFT, and Reduced Motion`, `F10 — Mobile, Accessibility, and Input Behavior`, `F11 — Workspace Continuity and Honest Availability`.
  Spec ref: `spec.md > Where It Runs and How Someone Tries It`, `Stack`, `Look and Feel`, `Local CAD Registration and Rights Policy`, `Authentic Component Catalog and Mesh Preparation`, `CAD Renderer and Shared Selection`, `Workspace Shell, Themes, Assistant, and Layouts`, `Geometry and Rights Classification`, `HTTP API`, `File Structure`.
  Build: Create Tachyon's own Python 3.12 environment, FastAPI package, React/TypeScript/R3F application, lockfiles and secret-free configuration; implement local registration/rights reports and content-addressed STEP-to-GLB preparation with source selection, units, source/mesh hashes and preserved identities. Keep all supplied sources, geometry and private rights evidence in ignored local storage. Add owner-session-protected APIs, explicit loopback/LAN rights handling, public role requirements, source inspection, actual scene-load/error handling, orbit/zoom/pan/select/reset, dismiss/reopen controls, basic SNAP/SHIFT, reduced motion, Simple/Advanced controls and the top-left core shell. Any not-yet-implemented core action is explicitly unavailable. Establish `docs/verification/acceptance-status.md` with all 44 PRD IDs and evidence locations; do not check off later functionality.
  Verify (mechanical): Run `python -m pytest server/tests/test_catalog.py server/tests/test_asset_api.py`, `npm run test --prefix web -- --run`, `npm run build --prefix web`, and `npm run test:e2e --prefix web -- --grep @cad-import`. Exercise genuine imported geometry when rights-qualified inputs exist, desktop and phone viewports, source-vs-mesh dimensions, selection identity and observed scene loading. Test refusal for missing/expired/wrong-scope rights, tampered hashes, invalid units, unsupported formats and unauthorized asset requests. Check no geometry enters bundles, Git, public routes or provider payloads. Clearly labeled Tachyon-authored CAD fixtures can test converter/error contracts only; they cannot pass authentic-VEX acceptance. Log permission/input-dependent rendering checks as blocked until actually run, with no claim this slice proves complete robots.
  Learner check: Open the printed local launch URL, inspect an authorized imported component, orbit and select it, switch SNAP/SHIFT, then dismiss and reopen its information. If inputs are unavailable, inspect the exact missing-input explanation; do not treat that negative case as a completed authentic-CAD demonstration. This check is available now and incorporated into the early hands-on session after slice 3.
  Commit: `Add local CAD registration and authentic component inspection`

- [ ] **2. Generate competition-aware alternatives and inspect their linked assemblies**
  Becomes usable: Select default Override, use Generate Strategy without a robot or Create Robot directly, make genuine model calls, compare two mechanically different complete conceptual robot designs, and select a strategy action to highlight its real subsystem with a matching sketch and field step.
  Why now: Establishes Tachyon's signature strategy-to-CAD relationship before adding the edit workflow or wider workspace options. Two complete assemblies and real inference are validated here, rather than deferred behind decorative UI.
  PRD ref: `prd.md > The Core Journey` steps 1–6, `F1 — Competition Selection and Rulebook Review`, `F2 — Standalone Strategy Generation`, `F3 — Robot Requests, Architecture Generation, and Comparison`, `F4 — Authentic Components and Connected Conceptual Assemblies`, `F6 — Bidirectional Strategy, Mechanism, Sketch, and Field Links`.
  Spec ref: `spec.md > Competition Ingestion and Grounding`, `Strategy and Architecture Proposals`, `Assembly Recipes, Connections, and Validation`, `Strategy Binding and Derived Illustrations`, `Persistence, Operations, and Availability`, `Data Model`, `Internal Service Contracts`, `Model Provider`, `Competition Sources`, `V1 — First Working End-to-End Version`.
  Build: Pin the default rulebook's actual source/version/hash and extract page-linked competition facts. Implement the single server-side OpenAI Responses adapter with an explicitly verified model, strict schemas, source/capability validation and real provider receipts; do not send CAD bytes or renders. Implement four-bar/gripper and elevator/gripper builders from the qualified local catalog, including actual component identities, rigid placements, mounted acquisition/retention, powered scoring paths, supports/fasteners, joints and necessary control/power hardware. Verify object interfaces, target poses, reach and clearances per recipe. Deliver independent entry flows, candidate comparison/selection, operation progress and typed failures, source review, shared selection, action-to-mechanism highlights, derived sketches/playbooks and immutable accepted snapshots. An incomplete recipe or missing essential game fact stays incomplete, and an absent provider stays unavailable.
  Verify (mechanical): Run `python -m pytest server/tests/test_grounding.py server/tests/test_generation.py server/tests/test_assemblies.py server/tests/test_bindings.py`, the relevant browser/component tests, `npm run build --prefix web`, and `npm run test:e2e --prefix web -- --grep @generation-links`. Inspect real full-robot and close-up CAD, not screenshots alone. Verify both architectures' connected hardware, mounts, drive/actuation paths, task support and distinct signatures. Fault injection must reject missing supports, broken ports/links, placeholders and unsupported source facts. Execute and record a genuine provider call and browser generation through each entry point; offline provider fixtures prove contracts/errors only. Missing credentials, permitted assets or task evidence are blocked checks, never passing robot/AI criteria.
  Learner check: Generate standalone strategies, then create two designs from rules without first entering Strategy. Open each robot, compare the actual mechanical differences, and select a scoring/acquisition step to find its mechanism, source references, sketch and field explanation. This becomes part of the early hands-on session after slice 3.
  Commit: `Connect competition strategies to two complete robot assemblies`

- [ ] **3. Make a real scoring-height revision through the contextual AI core**
  Becomes usable: Ask the selected mechanism to use its supported raised configuration; inspect the actual changed assembly and diff; Apply or Discard it; Undo an accepted change. The correct strategy action, capability, sketch and displayed geometry follow each revision. The essential P0 journey can now be tried end to end.
  Why now: Proves the other half of the unique kernel while the complete generation and inspection path is already runnable. It prevents a static mount probe or a persuasive assistant response from being mistaken for a functioning design editor.
  PRD ref: `prd.md > F7 — Contextual AI Core and Real Design Changes`, `F6 — Bidirectional Strategy, Mechanism, Sketch, and Field Links`, `Navigation and Context Continuity`, `F8 — SNAP, SHIFT, and Reduced Motion`, `F10 — Mobile, Accessibility, and Input Behavior`, `F11 — Workspace Continuity and Honest Availability`.
  Spec ref: `spec.md > Scoring Configuration Edit and Revision Service`, `Strategy Binding and Derived Illustrations`, `Workspace Shell, Themes, Assistant, and Layouts`, `Persistence, Operations, and Availability`, `Data Model`, `P0 Engineering and Revision Tests`, `Browser and Live Demo Tests`, `P0, P1, and P2 Gates`.
  Build: Integrate the supported native-port remount into at least one complete recipe's scoring carrier, dependent actuator/support hardware and actual task envelope. Implement selection-aware AI intent handling, immutable candidate revisions, assembly validation/diffs, exact-candidate preview, atomic idempotent Apply, Discard and per-design compensating Undo. Rebuild all affected placements/connections/joint frames and derive new capabilities, links, explanations and sketch/playbook anchors before Apply. Reject stale bases, wrong-design targets, unavailable configurations and broken dependencies. Complete compact text input, expanded desktop panel/mobile sheet and full-screen assistant with internal expansion controls, theme-specific core motion, honest unsupported states and preserved pending proposals. Keep real assembly data separate from camera, explode and operating poses.
  Verify (mechanical): Run `python -m pytest server/tests/test_revisions.py server/tests/test_bindings.py server/tests/test_assistant.py`, relevant frontend reducer/preview tests, `npm run build --prefix web`, and `npm run test:e2e --prefix web -- --grep @revision-journey`. Against actual app APIs and rendered assemblies, compare accepted/candidate engineering and binding hashes, changed parts/ports/dependent anchors, and visibly changed geometry. Preview must not mutate accepted data; Apply must accept exactly that candidate; Discard must preserve accepted data; Undo must restore prior engineering/binding content while retaining history. Exercise repeat Undo, duplicate Apply, stale revisions, cross-candidate proposals, source changes, invalid task support and unsupported requests. Run the complete live P0 journey in desktop and mobile browser projects, including both themes, all assistant states, touch input and panel dismissal; separately verify actual phone/LAN use when its rights and device are available. The earlier headless probe is not evidence for these checks.
  Learner check: On desktop and a phone, select the scoring mechanism, request the supported higher configuration, inspect its real CAD preview, Apply and Undo it, then Preview again and Discard. Select the strategy step after each change and confirm it follows the right mechanism. Try one unsupported edit. Report what was confusing or should change before the remaining workflow and layout work.
  Commit: `Implement contextual scoring revisions with verified preview and undo`

- [ ] **4. Switch rulebooks and recover work without mixing design contexts**
  Becomes usable: Upload another supported VEX rulebook through the same ingestion/AI pipeline, inspect its cited facts, switch contexts safely, retry a failed candidate without losing the other, and reopen saved designs/preferences without stale or misleading results.
  Why now: Completes the P1 workflow and recovery cases around the already demonstrated kernel, incorporating early feedback before broader inspection/layout controls are finalized.
  PRD ref: `prd.md > F1 — Competition Selection and Rulebook Review`, `F2 — Standalone Strategy Generation`, `F3 — Robot Requests, Architecture Generation, and Comparison`, `Navigation and Context Continuity`, `F9 — Simple/Advanced Modes and Customizable Layouts`, `F11 — Workspace Continuity and Honest Availability`, `States and Boundaries`.
  Spec ref: `spec.md > Competition Ingestion and Grounding`, `Competition Sources`, `Persistence, Operations, and Availability`, `HTTP API`, `Data Model`, `Important Failure Modes`, `P1/P2 Expansion`.
  Build: Complete supported PDF upload/source navigation using the historical Push Back test document, explicit uncertainty and unreadable/encrypted/scanned/unsupported handling. Reuse competition extraction without implying a new game's complete mechanical recipes exist. Complete strategy-to-robot handoff, per-candidate retry, cancellation/restart/late-result isolation, competition/version ownership, persistence/save-error recovery and preference continuity. Retain each candidate's accepted design, preview owner, command draft, selection and view context; expose honest source/asset/provider failure and available next actions.
  Verify (mechanical): Run the relevant grounding/generation/persistence/operation API tests, `npm run build --prefix web`, and `npm run test:e2e --prefix web -- --grep @context-recovery`. Process the actual second document and open cited pages; exercise invalid uploads, source switches during generation, mixed candidate success, targeted retry, cancellation, interrupted jobs, save failure and restart/reopen. Assert no late result or edit crosses competition/design boundaries and no successful candidate is overwritten. Verify retained theme/mode/layout and input context; record unsupported second-game robot generation accurately.
  Learner check: Upload the second supported PDF, inspect a source-linked fact, return to an existing Override design and verify it still identifies its original rules. Retry/cancel a generation, switch candidates and reopen the workspace; confirm accepted designs and preferences remain attached to the correct context.
  Commit: `Complete rulebook switching and workspace recovery workflows`

- [ ] **5. Inspect mechanism operation and customize the finished mobile workspace**
  Becomes usable: Navigate CAD hierarchy and strategy links in both directions, operate genuinely supported mechanisms, hide/isolate/explode/reset/display components, and use Focus/Split/Studio/practical Custom layouts with progressive Simple/Advanced controls and reliable mobile/keyboard behavior.
  Why now: Completes remaining P1/P2 inspection and workspace breadth after the essential engineering workflow works. These controls extend the shared workspace instead of introducing redundant panels or delaying the first functional version.
  PRD ref: `prd.md > F5 — Interactive CAD Inspection`, `F6 — Bidirectional Strategy, Mechanism, Sketch, and Field Links`, `F8 — SNAP, SHIFT, and Reduced Motion`, `F9 — Simple/Advanced Modes and Customizable Layouts`, `F10 — Mobile, Accessibility, and Input Behavior`, `F11 — Workspace Continuity and Honest Availability`.
  Spec ref: `spec.md > Assembly Recipes, Connections, and Validation`, `CAD Renderer and Shared Selection`, `Strategy Binding and Derived Illustrations`, `Workspace Shell, Themes, Assistant, and Layouts`, `Look and Feel`, `Browser and Live Demo Tests`, `P1/P2 Expansion`, `Implementation Milestones`.
  Build: Implement recipe-specific coupled joint poses with valid member transforms/limits and loop-closure checks; disable unqualified motion rather than playing arbitrary rotations. Complete reverse mechanism-to-action navigation and revision-aware operating explanations/anchors. Add hierarchy selection, hide/show/isolate/reset, inspection-only explode, orientation/render modes and the planned practical resizing/maximize/restore controls. Complete advanced detail exposure, one-sheet phone adaptation, theme/motion continuity, safe-area/keyboard/orientation behavior, touch/keyboard/focus accessibility and persisted layouts. Produce final reproducible setup/run instructions and update dependency/asset notices; integrations remain unavailable unless actually implemented and tested.
  Verify (mechanical): Run the relevant assembly/pose/binding and frontend interaction tests, `npm run build --prefix web`, and `npm run test:e2e --prefix web -- --grep @inspection-layouts`. Check actual moving members and sampled loop closure/clearance at declared poses; label sampled checks and retain physical-validation limits. Verify all display/layout actions leave engineering hashes unchanged, selection resolves identically from hierarchy/canvas, and mobile gestures/panels do not interfere. Test SNAP/SHIFT, reduced motion, phone portrait/landscape and keyboard focus in the actual renderer. Re-run affected core-journey tests after relevant changes and classify every remaining PRD criterion from recorded evidence.
  Learner check: Select a mechanism from CAD and open its strategy action, inspect supported motion and its limits, try hide/isolate/explode/reset, then switch layouts and Simple/Advanced modes. On a phone, type in the assistant, rotate the device and dismiss/reopen sheets; confirm the same design, preview and camera remain available.
  Commit: `Complete mechanism inspection and adaptive workspace controls`

## Hands-on Checkpoints

- [ ] Early usable behavior explored — after slice 3, once the actual P0 path is mechanically verified. The learner tries generation → two complete designs → strategy highlight → supported revision/Undo on desktop and phone, including the slice 1–3 learner checks, and reports feedback. Resolve relevant findings before slice 4. If a required input prevents this path, report it as blocked and request only the missing consequential input; do not call a shell or fixture an early working demo.
- [ ] Final kick-the-tires exploration and feedback completed — after slice 5 and the final runtime/acceptance review below. The learner explores the real app freely; record observations and any agreed fixes before readiness sign-off.

Fast mode is already chosen; do not ask again. No extra middle checkpoint is
planned. Additional discussion is reserved for consequential product/architecture
changes or a failure that cannot safely be repaired. Record actual feedback and
completion rather than inferring them from passing automated tests.

## Final Review

- [ ] Reproduce the local startup from the README, execute relevant backend/frontend/build/browser checks and the complete live journey, and inspect the actual rendered geometry. Record current deviations and evidence without claiming physical validation.
- [ ] Review `docs/verification/acceptance-status.md`: all 44 criteria identified; **passing, failing, blocked and unimplemented** reported separately, with any partial coverage explained. Every authentic-CAD, complete-robot, real-inference, actual revision and phone check needs its own genuine evidence. No application test has passed at checklist creation.
- [ ] Record learner observations and agreed revision tasks here; implement, mechanically verify, commit and have the learner retry affected behavior before marking each fix complete. No fixes are presumed yet.
- [ ] Final review complete — feedback resolved and learner explicitly confirms ready to ship. If essential assets/permissions, full assemblies, live inference, actual edits or required checks remain blocked/failing/unimplemented, retain that status and keep completion unchecked.

Deployment/publication/submission are outside this build authorization. Any
eventual CAD imagery in a public demo needs separately qualified publication
rights. `6-ship` follows only the completed build, reviews and learning wrap-up.

## Code Tour and App Map

- [ ] Learning activity complete — use one actual scoring-height request to investigate how the app distinguishes engineering revisions from display changes and rederives strategy links; adapt if useful practice already occurred during implementation.
- [ ] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as actually reported, with personal reflection kept in the ignored profile.
- [ ] `devpost/app-map.html` generated from finished code, checked and shown, including a project-grounded practice to reuse.

Activity and evidence: Not performed; after final revisions use actual assembly,
revision-service, binding and browser-test references. Do not claim learner mastery.

Route and stops: Not yet established; identify the real implementation symbols
after code exists. The intended focus is command → candidate assembly → derived
bindings → Apply/Undo → rendered selection.

Edit outcome: Not offered yet; optional and not an additional approval gate.

Reflection: Not offered yet; any personal answer belongs in the ignored profile.

Activity mode: Planned focused investigation for the learner's existing technical
experience; use the finished app and real code, not a redundant introductory tour.

## Revisions
