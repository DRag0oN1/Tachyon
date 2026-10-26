# Next milestone: strategy-linked design generation and management

Status: **immediate post-hackathon milestone; not implemented**.
Decision recorded 2026-10-26 at approximately 15:50 Eastern, before the 17:00 deadline.

The learner reviewed the existing demonstration favorably and requested more than
two predefined architectures. Their instruction explicitly prioritizes preserving
the working submission if the full improvement cannot be implemented and tested
without delaying publication, video preparation or submission. Use that fallback.
No Generate Another Robot control has been added to the current application.

## Preserved submission baseline

- Verified application commit: `667fd90`.
- Local annotated tag: `submission-baseline-2026-10-26`.
- Private, ignored Git backup:
  `.local/backups/tachyon-submission-baseline-2026-10-26.bundle`.
  `git bundle verify` confirms a complete, valid history bundle.
- Existing checks: 699 backend, 186 frontend, 102 isolated RL tests; five browser
  cases plus an actual WebKit recording of the demo journey. The review MP4 is 2:05.
- Preserve Design 01's partial, independently authored non-VEX CAD and Design 02's
  unrealized schematic. Preserve the trained policy, checkpoints, editing and UI.

This preservation does not authorize repository/video publication or submission.
The documentation-only milestone does not require a new recording or replace the
reviewed application baseline.

## Why this is not a safe last-minute button

The reusable requirements/proposal interface exists, but current production behavior
is deliberately narrower:

- [`design.architecture_proposals`](../server/tachyon/design.py) produces A/B from
  two engineering templates, with capability-dependent sizing. It does not accept
  mechanical preferences or maintain a growing project design library.
- [`GeneratedStrategy`](../server/tachyon/strategy_api.py) requires exactly two
  architectures. [`strategy_runtime`](../server/tachyon/strategy_runtime.py) verifies
  their pinned manifests and hashes against the saved handoff.
- [`architecture_context`](../server/tachyon/realization.py) resolves only IDs in
  that verified handoff. Recipes are keyed to A/B; architecture A's builder checks
  specific subsystem intents. A new proposal is not automatically compatible CAD.
- The workspace caches assemblies by architecture ID. Saved-realization metadata
  exists, but named independent proposals, generation preferences and comparison
  across a growing project collection need persistent contracts and browser tests.

Simply appending renamed copies would not meet the requested improvement. Loosening
the manifest checks would also weaken existing provenance guarantees. Neither is
part of this change.

## Smallest complete next increment

1. **Keep the two examples immutable.** Add a project design collection alongside
   the saved strategy response, allowing any supported number of proposals without
   changing archived policy/handoff artifacts. Give each saved design an independent
   ID and editable display name; retain an immutable architecture-content identity.
2. **Generate Another Robot.** Add the real action to the existing mechanical
   design bench once its server workflow works. Offer automatic selection or
   structured preferences for drivetrain, acquisition, transfer, scoring reach/lift
   and arrangement. Validate preferences against StrategySpec capability constraints
   and supported mechanism combinations; explain conflicts rather than ignoring them.
3. **Construct new structured proposals.** Extend the existing requirements and
   proposal functions with bounded composition/configuration choices. Include
   subsystem layouts, attachment/joint intents, capability targets and action links.
   Preserve the strategy's conditional behavior and evidence; perform no PPO training.
   Label this as engineering generation implementing the same learned family.
4. **Require meaningful novelty.** Compare subsystem intents, numeric configurations
   and arrangement against existing project designs. Changing names, colors, IDs or
   field ordering is insufficient. Record what changed. If the supported space is
   exhausted or preferences are unsupported, say so without producing a fake success.
5. **Save, reopen, inspect and compare.** Persist proposal content, user preferences,
   name, project ID, competition/environment, StrategySpec ID/hash, checkpoint reference
   and generator version. Reopening must retain the exact proposal and its originating
   strategy. Compare selected designs through their actual subsystem/requirement data
   and truthful schematics; load CAD only for a realized design.
6. **Qualify CAD separately.** Default new designs to architectural proposals. A
   server-side compatibility check must match the exact proposal to supported
   component-selection, placement, mount and joint operations before realization.
   Missing geometry/operations return explicit requirements. Never reuse A's recipe
   under an incompatible generated identity, draw fake VEX parts or upgrade readiness
   because the proposal has a plausible schematic.

Keep the first increment within the currently supported Override environment.
Every design records its competition; another rulebook does not gain PPO support
through this feature. Preserve SNAP/SHIFT, the full-screen viewer, top-left core,
mobile task sheets and current revision contracts. Add no new research subsystem.

## Verification required before exposing the action

- Create at least Design 03 and Design 04 from the actual supported StrategySpec;
  demonstrate structural/configuration differences and unchanged source strategy.
- Preference changes must alter relevant mechanical requirements. Reject unsupported
  or contradictory preferences and report exhausted combinations honestly.
- Rename, compare, refresh and restart/reopen without changing identity, losing
  proposals or replacing an existing accepted CAD revision. Failed/cancelled/retried
  generation must preserve prior work and avoid duplicate saves.
- Verify strategy-to-subsystem links for each proposal and exact revision-bound
  links for realized CAD. Pending Preview/Apply/Discard/Undo remains protected when
  switching designs or generating another one.
- Test missing/unsupported CAD as a proposal state, not a completed robot. For a
  supported realization, inspect actual geometry, attachments and viewer instances.
- Run relevant backend/frontend/build and desktop/mobile browser regressions against
  the existing examples, themes, session recovery, highlighting and editing. Capture
  evidence from the running application before treating the milestone as complete.

Public code/video release and the learner-authored Devpost entry remain tracked
separately in [the submission checklist](../devpost/submission-checklist.md).
