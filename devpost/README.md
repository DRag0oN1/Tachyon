# Devpost workflow

The official [Devpost Learn Skill Pack](https://github.com/challengepost/learn-ai-basics)
is available in `.agents/skills/1-start` through `.agents/skills/6-ship` with their
templates and references. `skills-lock.json` records the upstream source.
Its license is preserved in [third-party notices](../THIRD_PARTY_NOTICES.md).

## Current state

| Stage | Artifact | State |
| --- | --- | --- |
| `1-start` | `learner-profile.md`, excluded from Git | Complete |
| `2-scope` | `scope.md` | Approved by the learner |
| `3-prd` | `prd.md` | Approved by the learner; initial scoring reach/height edit confirmed |
| `4-spec` | `spec.md` | Approved by the learner; local supplied-CAD path and architecture accepted; asset/complete-recipe qualification remains a build gate |
| `5-build` | `checklist.md`, application, `app-map.html` | Active; implementation order approved with the first complete robot before live two-design generation; fast mode selected |
| `6-ship` | Working demo video, public repository, learner-authored submission | Awaits verified build and required reviews |

## Actual project sequence

On 2026-10-23, the submission workspace was initialized with a new Git repository
and the official curriculum. The learner supplied their product requirements and
technical/planning background. Onboarding was completed and the scope draft was
written before application implementation. The learner explicitly approved the
scope on 2026-10-23 and requested the full product definition. The PRD was saved
as a draft defining screens, navigation, interactions, themes, mobile behavior,
functional requirements, error states, and acceptance criteria. The proposed first
supported engineering edit was approved with the PRD on 2026-10-23. The learner
authorized technical planning with staged acceptance priorities. Specification
review became the next approval gate before implementation. The draft
technical plan defines P0/P1/P2 acceptance, the local browser/Python architecture,
real assembly revision edits and post-edit links, contracts, tests, and milestones.
The learner then requested investigation of official manufacturer and community
CAD, explicit rights separation, and an authorized local supplied-CAD fallback.
Public source/terms research and a newly authored bounded native BRep mount and
reference revision probe were performed before spec approval. The probe is not
application implementation, a complete robot, or production lifecycle evidence.
The source report records failed hardware placements as well as the final checks.
No geometry was converted to meshes, committed, deployed, or redistributed.
The finalized draft selects local supplied STEP with scoped permission checks;
complete powered recipes, game-task support and actual app verification remain
required build gates. The learner then explicitly approved `4-spec` and its
architecture on 2026-10-23 and requested `5-build`. The spec is marked approved;
the first build checklist proposes five usable increments and retains the
required early/final hands-on reviews. Execution-order approval is pending,
as required by the official skill. At that build-order checkpoint application implementation had not started. Subsequent
implementation and actual acceptance evidence are recorded below.

## Review and verification

Each planning document is saved as `status: draft` and becomes `approved` only
after the learner approves the displayed plan. Do not repeat settled product
questions or treat the number of interview turns as a quota. Fast mode reduces
routine explanations and pauses while preserving consequential approvals,
verification, useful early feedback, final review, and learning wrap-up/app map.

Maintain accurate library and asset provenance. A conceptual assembly is not
physical validation or competition certification. Demonstrate real behavior
before marking build steps complete.

Shipping requires a working video and public repository. Submission answers and
reflections remain learner-authored. Do not publish or submit without explicit
authorization.

The learner approved the build checklist and execution refinements on 2026-10-23. Application implementation begins from slice 1. Actual permissions, model access, complete robot acceptance and test evidence remain separate from planning approval.


## First implementation increment — historical checkpoint

The local source pipeline and mobile full-window inspection application are now
implemented. Actual tests pass: 148 backend, 24 frontend, production build,
6 source-profile browser cases and 2 default empty-source browser cases. Geometry
used for conversion/render verification is an original non-VEX test fixture;
authentic-VEX rights and the full component set remain unresolved. First-slice
completion is therefore still unchecked. Complete robot builders, live AI,
strategy actions and actual assembly revisions are not implemented. See
[verification](../docs/verification/slice-1.md) and
[criterion status](../docs/verification/acceptance-status.md). No hands-on review
or learner sign-off has been inferred.

## Production integration — 2026-10-24

Following the saved PPO experiment (`ac1aa01`) and bridge (`eb1265c`), the learner
requested their production integration. Existing uncommitted source-inspection,
assembly and binding foundations were preserved and integrated with the new
strategy service, strategy/architecture screens, measured-port realization,
revision-aware CAD, bidirectional action links and functional bounded core.
No training was repeated or geometry published. Actual motor source inspection
and a separate original non-VEX STEP mechanism were tested in desktop/mobile
browsers. The complete authentic robot and full P0 journey remain unmet; user
review and shipping have not occurred. See the
[current verification](../docs/verification/production-integration.md) and
[criterion status](../docs/verification/acceptance-status.md), rather than the
historical first-increment counts above.
