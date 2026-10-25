# Application acceptance status — 2026-10-25

Current build: production strategy/architecture integration, authentic local source
inspection and qualified private partial-assembly revisions. **The full product
and all 22 P0 obligations have not passed.**

Criterion status: **8 passing, 0 failing, 9 blocked, 27 unimplemented**. Partially delivered criteria stay unimplemented
or blocked; their notes identify the real working coverage. Blocked criteria have
missing authentic inputs/qualification/device evidence, sometimes alongside
explicitly unfinished whole-robot software. No failing executed software test is
carried forward. A passing UI criterion does not pass the independent authentic-
robot or full journey gates.

Latest executed checks: **655 backend, 86 frontend and 102 RL tests passed**, plus
production build and **6 desktop/mobile browser cases** across a selected authentic
factory tool, real saved-policy UI and a separate original non-VEX STEP mechanism.
The new partial architecture-A recipe has 449 outer instances/576 relationships;
its two endpoints and 12 strategy bindings pass metadata checks. This does not
pass complete-robot criteria. See the [generation increment](robot-generation.md).
See [exact commands and boundaries](production-integration.md),
[evidence hashes](production-evidence.json) and [source operation status](../cad-source-status.md).
Historical fixture/blocked-source records remain in [Slice 1](slice-1.md) and
[external catalog](external-catalog.md); their older counts/status are not current.

## Learner-directed strategy amendment

The later requests explicitly permit two engineering architectures implementing
one evidenced learned family and prohibit inventing a second learned strategy.
For this saved-PPO path, STRAT-1 therefore requires real independent generation of
the supported conditional family; a second family is shown only if evaluation
supports it. STRAT-2 applies to that supported family. This amendment is recorded
in the PRD/spec/checklist and does not waive two mechanically distinct complete
robot designs, authentic geometry or any of the 22 P0 gate identities. Other
rulebooks are not represented as PPO-supported.

## Criterion matrix

| Criterion | Gate | Status | Evidence or remaining requirement |
| --- | --- | --- | --- |
| COMP-1 | P0 | passing | Default Override v2.1 is available without upload; the strategy view identifies its pinned official source/version. Production browser checks. |
| COMP-2 | P1 | unimplemented | Additional PDF ingestion and page-linked extraction are not implemented. PPO does not support arbitrary manuals. |
| COMP-3 | P1 | unimplemented | Document validation/replacement workflow remains unimplemented; unsupported competition requests are explicitly rejected by the strategy API. |
| COMP-4 | P1 | unimplemented | Only the pinned Override context is supported; competition switching and source-version migration are unfinished. |
| STRAT-1 | P0 | passing | Learner-amended saved-PPO criterion: independent Home entry runs real frozen neural inference and exposes the evidenced conditional family. No second learned family is invented; see the amendment below. |
| STRAT-2 | P0 | passing | Objectives, priorities, mechanism/capability needs, sequences, conditional decision points, evidence, trade-offs and official source are presented without raw JSON. Abstract assumptions/limits remain labeled. |
| STRAT-3 | P1 | unimplemented | Partial: actual strategy/action IDs are retained in architecture and private assembly APIs. Complete selected-strategy-to-authentic-robot handoff remains unfinished. |
| STRAT-4 | P1 | unimplemented | Partial: runtime failures and retries are truthful and retain existing UI results; cancellation/operation restoration is not implemented. |
| ROBOT-1 | P0 | unimplemented | Partial: Create Robot independently executes the policy and shows actual proposals. It does not generate a complete authentic robot from the current catalog. |
| ROBOT-2 | P0 | unimplemented | Partial: actual four-bar/roller and elevator/gripper proposals are mechanically distinct and implement one learned family. Their full component assemblies are not realized. |
| ROBOT-3 | P0 | blocked | Source-selected parts and measured ports now supply a partial A recipe. Gated transfer, Cup handling, stack alignment and full mount/transmission/task qualification remain unfinished; assembly-placement rights remain unverified. No complete authentic robot is rendered or accepted. |
| ROBOT-4 | P1 | unimplemented | Partial: source-derived proposal trade-offs, subsystem choices and strategy associations work. Switching two complete CAD alternatives is not available. |
| ROBOT-5 | P1 | unimplemented | Partial: typed realization failures preserve reference inspection and accepted revisions. Per-candidate generation retry/recovery remains incomplete. |
| CAD-1 | P0 | blocked | Authentic V5 motor native import, preserved hierarchy, real GLB geometry and browser scale checks passed. Required complete-robot components and assembled authenticity remain unqualified. |
| CAD-2 | P0 | unimplemented | Partial: measured-port component placement, rigid transforms, attachments, explicit joints, descendant updates and connectivity are implemented/tested. Full authentic robot actuation/support hardware is missing. |
| CAD-3 | P0 | unimplemented | Partial: invalid geometry/units/rights, broken ports/graphs, stale hashes and wrong bindings are refused. A source-bound hardware qualifier now checks BOM, mounts, supported shafts, transmission paths and mechanism declarations; the compiler's complete declarations, game-object/task and clearance verification remain unfinished. |
| CAD-4 | P0 | blocked | Source identities/hashes and per-operation rights checks work. Authentic generation/assembly-placement and public asset/depiction scopes remain unverified; no submitted robot asset set is qualified. |
| VIEW-1 | P0 | blocked | Actual motor desktop/mobile WebKit controls, multiple native parts and scale checks passed. Physical-phone pinch/pan and complete authentic robot inspection remain unverified. |
| VIEW-2 | P1 | unimplemented | Partial: native source hierarchy and private assembly inspector select actual instances and expose source data. Full generated robot hierarchy is not available. |
| VIEW-3 | P2 | unimplemented | Focus/reset/up-axis work; hide/isolate/explode and the full display-mode controls remain unimplemented. |
| VIEW-4 | P1 | unimplemented | Discrete joint endpoints are tested; continuous supported mechanism operation/animation and swept clearance are not implemented or claimed. |
| VIEW-5 | P0 | passing | Full-screen CAD persists while Strategy, Architectures, Components and assistant panels open/close. Actual source and original-mechanism browser journeys preserve the displayed design/camera context. |
| LINK-1 | P0 | blocked | Actual source-STEP fixture action highlights/focuses carrier/tool, derives the current anchor sketch and retains the abstract field playbook. Required authentic full-robot mechanism evidence is missing. |
| LINK-2 | P1 | unimplemented | Partial: actual fixture tool raycast and assembly hierarchy expose reverse action links, tested through the browser. Full authentic-robot coverage remains unfinished. |
| LINK-3 | P1 | unimplemented | Partial: revision-bound coordinate sketches/anchors and abstract rollout diagrams are implemented and labeled. Full mechanism-operation controls and authentic-robot illustrations remain unfinished. |
| LINK-4 | P0 | blocked | Same action/component/anchor IDs and recomputed binding/revision hashes pass fixture Preview/Apply/Discard/Undo, including visible CAD and sketches. Full authentic-robot post-edit linkage remains unverified. |
| AI-1 | P0 | passing | Top-left compact composer, side panel/mobile sheet, full-screen state, internal expansion controls and retained input work in component and real browser tests. |
| AI-2 | P0 | passing | Bounded assistant explains real source/instance/action context and opens strategy/architectures. Scoring-height intent is positively scoped; unsupported targets, negations and arbitrary dimensions do not trigger edits. |
| AI-3 | P0 | blocked | Real private STEP fixture preview and exact Apply update joint poses, descendants, anchors and visible geometry. Authentic robot scoring hardware/recipe and task qualification are missing. |
| AI-4 | P0 | blocked | Discard and compensating Undo restore actual fixture engineering content and links; API tests cover stale/duplicate/wrong-candidate/changed-source cases. Authentic-robot lifecycle proof remains missing. |
| AI-5 | P0 | blocked | The agreed height edit works on an original computational STEP mechanism, not qualified authentic VEX scoring hardware. Static mounts or fixture endpoint motion do not satisfy full mechanism functionality. |
| THEME-1 | P0 | passing | SNAP and SHIFT visibly differ in surfaces, controls and core motion while exposing the same implemented functions. Actual CAD/strategy and fixture revision journeys ran in desktop SNAP/mobile SHIFT. |
| THEME-2 | P1 | unimplemented | Partial: source theme continuity is verified and engineering revisions are separated from display preferences. Full proposal-review/theme-switch matrix remains unverified. |
| THEME-3 | P1 | unimplemented | Partial: existing core/panel reduced-motion checks pass. Full mechanism-operation and proposal interaction coverage remains incomplete. |
| LAYOUT-1 | P1 | unimplemented | Partial: Simple/Advanced progressively expose source and simulation evidence details. The full robot editing control set remains unavailable. |
| LAYOUT-2 | P2 | unimplemented | Dismiss/reopen and desktop strategy-panel width work. Complete Focus/Split/Studio/Custom maximize/restore/docking is unfinished. |
| LAYOUT-3 | P1 | unimplemented | Partial: mobile sheets and full-window CAD work with no horizontal viewport overflow in the tested journeys. Full adaptive layout matrix remains unfinished. |
| LAYOUT-4 | P1 | unimplemented | Theme/mode/source preferences persist. Full project layouts, reopened strategy sessions and all custom view preferences are not restored. |
| MOBILE-1 | P1 | unimplemented | Partial: actual mobile WebKit rendering, source part taps and full fixture revision journey pass. Physical phone and full authentic-robot journey remain unverified. |
| MOBILE-2 | P1 | unimplemented | Partial: sheet/assistant context and updated compact layout work. Device rotation, keyboard/safe-area and full project recovery matrix remain unverified. |
| MOBILE-3 | P1 | unimplemented | Named controls, touch targets and focus behavior have tests. Complete keyboard/accessibility audit is unfinished. |
| STATE-1 | P1 | unimplemented | Private design revisions persist and requalify via SQLite/API; preferences persist. Automatic design/strategy workspace reopening in the UI remains incomplete. |
| STATE-2 | P0 | unimplemented | Partial: candidate NOT APPLIED, accepted, partial and blocked states are distinct and tested. The complete two-robot candidate/theme/layout/reopening matrix is unfinished. |
| STATE-3 | P0 | passing | No mock CAD/generation/edit success is exposed. Source reference, non-VEX fixture, partial assembly, modeled performance, unsupported requests and missing qualifications are explicit. |

The original three-part fixture is a genuine STEP import/placement/revision test,
not authentic VEX CAD, a complete robot, powered hardware, game-object support,
collision validation or physical reach evidence. The actual motor and Clawbot
remain reference-only. Public redistribution/hosting/depiction and new placement
rights are not approved. Planned early/final hands-on reviews, learning wrap-up
and `6-ship` remain incomplete.
