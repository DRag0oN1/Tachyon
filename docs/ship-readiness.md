# Shipping readiness audit

**Publication update:** the learner subsequently authorized public source release.
The reviewed repository and baseline tag are now public and anonymously accessible:
<https://github.com/DRag0oN1/Tachyon>. The reviewed video is upload-ready. See the
[final publication audit](publication.md) for the current status and timestamps;
the preparation-time findings below remain a historical record, not a current
authorization blocker. Full engineering criteria and learner submission remain open.

Audit date: 2026-10-26. Git baseline: `143d6b5` (`main`), 15 reachable
commits, plus the current uncommitted stabilization candidate. This is a factual technical record for an authorized **partial-demo
preparation**, not submission copy, publication approval or full-product sign-off.

The official [6-ship skill](../.agents/skills/6-ship/SKILL.md) normally requires
completed `5-build` reviews and the learning wrap-up/app map before shipping.
The learner explicitly authorized this bounded preparation while those gates
remain open. The approved scope, PRD, specification and checklist remain in force;
this audit changes none of their completion states.

**Current public-audit status: private review recording complete; public release
and formal shipping completion pending.** Final backend, frontend and isolated RL
results and clean-launch browser checks are recorded below. Learner readiness
review and publication approval remain pending.

| Required planning artifact | Presence / recorded status |
| --- | --- |
| [Scope](../devpost/scope.md) | Present; `status: approved` |
| [PRD](../devpost/prd.md) | Present; `status: approved` |
| [Specification](../devpost/spec.md) | Present; `status: approved` |

The authorized P0 recording target was an actual **1–3 minute local recording**
using the existing original Tachyon development CAD in the private
`.local/generated-robot-a-v6` profile. Manufacturer VEX reference assets are
excluded from that recording scope. This is authorization to prepare a private
video artifact; no public upload, asset redistribution or new public CAD rights
are granted. Keep the source assets and meshes out of Git. The completed private
review export is `.local/final-demo/Tachyon-demo-review.mp4`, **124.54 seconds
(about 2:05)**, as confirmed by the main implementation owner. The official
[challenge overview](https://learn-ai-basics.devpost.com/) also requires a 1–3 minute
demo, a public source-repository URL and the generated scope/PRD/spec in that
repository. No public video or repository has been released by this work.

## Working evidence and its limits

| Check | Observed result | Evidence / scope |
| --- | --- | --- |
| Complete backend suite | **699 passed**, one dependency deprecation warning, 83.23 s | Read `.local/final-demo/backend-final.log`; command `.venv/bin/python -m pytest server/tests -q`. This supersedes the 698-test run before the extra launch test and the earlier 689-test baseline. No failing backend/catalog tests were reported. |
| Isolated RL suite | **102 passed**, 4.42 s | Read `.local/final-demo/rl-tests.log`; command `.local/rl-venv/bin/python -m pytest research/strategy_rl/tests -q`. The suite's small training fixtures use pytest temporary directories; no saved experiment was retrained or edited. |
| Complete frontend suite | **186 passed** across 21 files | Read `.local/final-demo/frontend-tests.log`; supersedes the 165-test studio snapshot. |
| Launch unit tests | 10 passed | Read `.local/final-demo/launch-tests.log`; these are included in backend coverage, not additional tests to add to the full-suite total. |
| Clean-launch browsers | **2 passed**, desktop/mobile, 19.8 s | Read `.local/final-demo/launch-browser.log`; loopback browser coverage, not a physical-phone/LAN claim. |
| Browser operation / recording | Private real-app recording completed | Main owner confirms actual CAD/edit frames and home/playbook/B/mobile screenshots, genuine matrix/hash checks, no API mocks and no browser errors. Local recording evidence is detailed below; this audit did not replay or operate the browser. |

The current command/results and private media evidence are consolidated in the
[final demo-stabilization report](verification/demo-stabilization.md).

The current development snapshot contains **494 placements, 35 geometry assets,
631 relationships and 14 revision-bound action bindings**. These are independently
authored, non-VEX development parts, rendered through the existing local CAD
pipeline. They must retain that identity in a demonstration. The earlier 474-part
snapshot is historical, not the current count.

These results belong to their recorded verification runs and the current
uncommitted candidate. Review any subsequent edits against those results before
publication. No heavy tests, frontend build or browser run was repeated by this
final documentation/history audit.

### Private recording and reproducible launch

The retained raw recording is `.local/final-demo/recording/raw-demo.webm`.
The main owner reports a **233.84-second raw media duration**; the recording's
`evidence.json` records **232.051 seconds of wall time**. These are different
measurements. Evidence records 494 placements, 631 relationships,
`completeRobot: false`, `physicalPerformanceVerified: false`, no browser errors,
and passing Preview/Apply/Undo/Discard checks. The main owner confirms those
checks compare the actual drawn matrices and revision hashes.

The private MP4 export abbreviates only the interiors of measured processing
waits. Its persistent caption identifies the actual app, partial non-VEX CAD,
abstract PPO and abbreviated waits. Main-owner visual review confirms CAD/edit
frames and the home, playbook, B schematic and mobile views. Technical
classification and recording privacy review are complete: the main owner confirms
no credentials, address bar or private windows are on screen, and the recording
uses only original Tachyon development CAD. The predefined demo sequence has
already been recorded; narration is optional. The raw capture is
retained; no timed physical-performance claim is derived from the edited video.
Learner review of the export and authorization to share it remain pending.

For an already running port-8019 server, the documented fresh-terminal command is:

```sh
.venv/bin/tachyon launch --port 8019
```

No `TACHYON_DATA_DIR` selection is needed to recover that running server. The
launcher uses the canonical project-local `.local/runtime/owner-launch-8019.json`
handoff and validates against the protected API before opening the browser.
Read-only inspection confirmed the handoff exists with mode `0600` and is not a
symlink; its credential content was not read or printed. See [README](../README.md)
and the [launch implementation](../server/tachyon/launch.py). The handoff, private
media, geometry and logs stay ignored; none belongs in the public Git tree.

The working bounded features include the saved PPO/StrategySpec handoff, the
four-bar/roller A proposal, the separate elevator/jaw B schematic, A's authored
component recipe, per-design revision retention, metadata-only saved-build
discovery, requalification on open, strategy links, and Preview/Apply/Discard/Undo.
The prescribed Cup preview uses real assembly joints; it does not verify contact,
friction, physical retention, stability or competition scoring. B has no complete
assembly recipe. These are two architectures for one learned strategy family.

Whole authentic-robot acceptance remains **unpassed**. The current
[44-criterion matrix](verification/acceptance-status.md) records 8 passing,
1 failing, 9 blocked and 26 unimplemented criteria. Among 22 P0 criteria, 8 pass,
1 fails, 9 are blocked and 4 are unimplemented. Automated application tests do
not change those statuses.

The [generation report](verification/robot-generation.md) records 51 lower and
37 raised major-body overlaps above 1 mm³, plus a separately audited nonmating
shaft/link interference. Powered Pin handoff/release, complete hardware/task
qualification and authentic source assembly-placement rights remain unresolved.
The formal complete-robot gate is distinct from exhaustive physics simulation;
passing graph checks or a kinematic animation does not remove these concrete
hardware failures.

## Repository and history audit

Final supplemental browser evidence: two missing-owner desktop/mobile checks and
one desktop generated-development check pass. The latter confirms 494 rendered
placements, 35 geometry assets, 925 meshes, 631 relationships, 14 bindings, full
33-sample modeled Cup playback and exact revision/matrix restoration. The private
evidence is copied under `.local/final-demo/generated-desktop-browser/`; this does
not pass authentic-VEX or physical-performance criteria.

Read-only checks covered the tracked tree, all reachable history, ignore rules,
source references and recorded notices. No remote was configured and no public
repository URL was available to verify. No push, visibility change, history
rewrite, release, deployment or submission was performed.

| Area | Finding at the audited snapshot |
| --- | --- |
| Tracked files | 290; no tracked source CAD or mesh files, private data/cache roots, generated frontend bundle, or credential files. `.env.example` is the tracked configuration template. |
| Learner profile | Exists locally, is explicitly ignored, and is absent from the tracked tree and reachable history. Its private content is not reproduced here. |
| Ignore rules | `.local/`, actual `.env` files, private key extensions, uploaded/CAD/cache directories, generated geometry, dependencies and build outputs are excluded. Ignoring is separate from checking history. |
| Reachable history | 15 commits; no historical CAD/mesh paths, learner-profile path, private/generated roots or credential-like file paths were found. No remediation or history rewrite was indicated by these checks. |
| Secret-pattern inspection | 419 reachable text-blob versions and 33 current changed/new text files inspected for private-key headers, common provider/GitHub/AWS token forms and embedded owner launch tokens; no matches. Values were not printed. This bounded scan is not a guarantee against every possible secret. |
| Uncommitted publication candidate | 21 changed tracked files and 12 non-ignored untracked files at scan time; no learner profile, geometry/mesh, private-root or credential-file paths. No matching secret patterns; no current files skipped. This includes the reference app map, launch/session changes, tests, recorder, verification documentation and these checklists. |
| Excluded binary/compressed content | 20 blob versions skipped by that text scan. Tracked model/data files are confined to the authored RL experiment: 8 `.pt`, 9 `.gz`, 4 `.jsonl` paths. Their existence is documented; this is not an independent audit of every binary or compressed payload. |
| Git staging | Nothing staged at audit start. Recheck the exact intended publication diff and history immediately before an authorized push. |

Runtime owner-session URLs, session files, server logs, screenshots, uploaded
documents, source geometry and private rights evidence must stay out of a public
repository and recording. The private verification logs referenced above are
local evidence, not files to add to the publication set.

## Source identities and publication scope

The [CAD source-status record](cad-source-status.md) separates manufacturer
references from original development geometry. The Clawbot source is pinned to
`d291e70cf6ccd5260983193ab07d9f824b965b1c5f7e2ef298e961e7e7768fb7`;
the V5 motor reference to
`3399374de417a5b403619e9e475d616e0cc1c3196324b4ba15d4fd0049ab9cec`.
They are reference-inspection inputs, not a generated authentic robot.
Their narrow private-inspection interpretation is not a manufacturer
redistribution license. Assembly placement, public depiction, redistribution,
public hosting and LAN scopes remain separate/unverified for those references.

The audited private studio development profile has 41 original-part/object rights
records covering acquisition/storage, conversion, assembly placement and loopback
display. Those records did not contain additional publication grants. The chosen
recording shows only original Tachyon CAD: its depiction release can be included
in the learner's **single explicit repository/video publication approval**.
No separate manufacturer-license gate is imposed on this recording, since
manufacturer geometry is excluded. Private preparation is not that release
approval, and geometry/mesh redistribution remains outside the publication set.
No permission records were created or changed by this audit.

Dependency/curriculum provenance is retained in
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md),
[Python dependency inventory](python-dependencies.md),
[frontend notices](../web/THIRD_PARTY_NOTICES.md),
[frontend license texts](../web/public/THIRD_PARTY_NOTICES.txt), and the
[isolated RL notices](../research/strategy_rl/THIRD_PARTY_NOTICES.md).
The official curriculum's MIT text and PyTorch/NumPy notices are present.
Software licenses confer no manufacturer geometry rights. No root application
`LICENSE` is present; choosing an application reuse license is optional, not a
challenge submission gate.
The curriculum's MIT license must not be presented as an application or CAD license.
No new external licensing determination was made here.

## Open gates and publication blockers

| Gate | Current state / action still required |
| --- | --- |
| Full approved build | Slices 2–6, early/final learner checkpoints, final readiness confirmation and the learning wrap-up remain unchecked in [the build checklist](../devpost/checklist.md). The [technical app map](../devpost/app-map.html) is now present for review; its existence does not complete the learner activity or readiness review. Formal `5-build`/`6-ship` completion is not established. |
| Authentic complete robot | Remains blocked/failing as detailed above; preserve the partial/non-VEX and unverified-performance labels. The authorized partial-demo preparation does not pass this criterion. |
| Public code repository | No remote is configured. Candidate `DRag0oN1/Tachyon` was reported as returning 404; the private repository-check record also contains status 404. No public repository or upload has been created by this work. Creating/pushing/changing visibility requires explicit user approval of the exact publication set and history. |
| Auth recovery / final candidate | Final backend and clean-launch checks pass as recorded above. Final learner confirmation of recovery and readiness remains pending. |
| Demo publication | The private 124.54-second review MP4, technical classification and privacy review are complete. Learner review, a single explicit repo/video release approval, public links and anonymous-access verification remain pending. That approval may cover depiction of the original CAD; no manufacturer VEX assets are included. |
| Submission form | Official overview and organizer update checked; full signed-in form and exit survey not operated. The [organizer update](https://learn-ai-basics.devpost.com/updates/46821-two-new-questions-on-the-submission-form) adds a required Skill Pack explanation and age-of-majority checkbox, and places the repository link in “Try it out.” Responses remain learner-authored. |
| Learner authorship | Existing project name is Tachyon. Learner-entered project name/description, other required answers, reflections and exit-survey responses remain pending/unknown. No narrative was drafted. |
| Submission action | No entry has been submitted or confirmed; no publication/submission action is authorized by this audit. |

The operational handoff is [the submission checklist](../devpost/submission-checklist.md).
Deployment and peer feedback are optional under the installed shipping skill;
neither replaces the required video or public repository. There is no peer-review
count or Discord-post gate.
