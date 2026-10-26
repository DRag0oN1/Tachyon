# Submission preparation checklist

Status: partial-demo preparation; formal build and shipping completion pending.
Updated 2026-10-26 against Git snapshot `143d6b5`.

This is a factual technical checklist, not learner-authored submission copy.
The learner authorized honest partial-demo preparation while the approved full
build is unfinished. Scope, acceptance requirements and existing review checkboxes
are unchanged. See [the shipping audit](../docs/ship-readiness.md) for evidence,
history/privacy checks and exact publication blockers.

Current authorization covers an actual **1–3 minute private local recording**
using original Tachyon development CAD from `.local/generated-robot-a-v6`.
Manufacturer VEX reference assets are excluded. Keep all source geometry and
meshes private and out of Git. Recording preparation does not authorize public
upload or grant unverified public CAD rights. Automated auth-recovery checks now
pass and learner confirmation remains pending.
The private review export is complete at **124.54 seconds (2:05)**:
`.local/final-demo/Tachyon-demo-review.mp4`. The 233.84-second raw media is
retained; its recording evidence separately measures 232.051 seconds of wall time.
Only interiors of measured processing waits were abbreviated, with a persistent
actual-app/partial-non-VEX/abstract-PPO/waits-abbreviated caption. Main-owner review
confirms actual CAD/edit frames, matrices/hashes, and home/playbook/B/mobile views;
no API mocks or browser errors were reported. See the
[demo-stabilization evidence](../docs/verification/demo-stabilization.md).

## Recorded technical evidence

- [x] Read the official [6-ship skill](../.agents/skills/6-ship/SKILL.md) and the
  actual project statuses; [scope](scope.md), [PRD](prd.md) and [specification](spec.md)
  are present with `status: approved`. The build checklist is also approved.
- [x] Final complete backend suite: **699 passed**, one dependency deprecation
  warning, 83.23 seconds; supersedes the 698-test run before the added launch test.
  Isolated RL: **102 passed**. Exact commands/private logs are in the shipping audit.
- [x] Final frontend suite: **186 passed**; clean-launch desktop/mobile browsers:
  **2 passed**. Read existing results; this audit did not repeat heavy tests,
  build `web/dist` or change application code.
- [x] Final missing-owner desktop/mobile regression: **2 passed**. Final desktop
  generated-development regression: **1 passed**, including 494 rendered placements,
  925 meshes, whole modeled Cup playback and exact revision/matrix checks. The
  separate manufacturer-reference and three-part fixture suites were not rerun
  against this profile and are not counted here.
- [x] Record the current engineering boundary: A has an authored development
  assembly; B remains a proposal. The 494-part assembly is original non-VEX CAD,
  has known interference, and is not a complete authentic VEX robot.
- [x] Audit tracked files and 15 reachable commits for private paths, geometry,
  learner-profile inclusion and common text-secret forms, including 419 historical
  text-blob versions and 33 changed/new text files. No matches were found
  within the documented audit scope. Binary/compressed inspection remains bounded.
- [x] Confirm the learner profile and local assets/logs are excluded from Git;
  preserve existing third-party dependency and curriculum notices.

## Required build and learner gates still open

- [ ] Resolve or explicitly retain the authentic/complete-robot and other
  incomplete criteria in [the acceptance record](../docs/verification/acceptance-status.md).
  The existing record has 8 passing, 1 failing, 9 blocked and 26 unimplemented criteria.
- [ ] Complete and record the remaining learner hands-on checkpoints and final
  readiness review in [the build checklist](checklist.md). Automated tests and
  browser reports do not supply learner sign-off.
- [ ] Complete the learning wrap-up and record the actual learner activity.
  The [technical reference map](app-map.html) is now prepared; its existence does
  not establish that the learner reviewed it or completed the learning activity.
- [ ] Obtain learner review/readiness confirmation for the stabilized app and
  private review video. Retain failed attempts and passing retries locally, and
  reverify any changes made after the final recorded suite results.

These open gates keep formal `5-build`/`6-ship` completion pending. They do not
prevent the explicitly authorized preparation of a truthfully labeled partial demo.

## Required links

| Deliverable | Link | Verification |
| --- | --- | --- |
| Public GitHub repository | **Pending — no remote; candidate `DRag0oN1/Tachyon` returned 404** | Creation/push requires user approval; verify anonymous access after authorized publication. |
| Short demo video | **Public URL pending; private 124.54-second review MP4 complete** | Technical classification/privacy review complete; learner review, combined repo/video release approval and anonymous access remain pending. |
| Live application | Optional; not selected | Deployment is not required and does not replace either link above. |

## Public repository and asset release

- [ ] Confirm or choose the public repository destination; obtain explicit
  authorization to create it, change visibility or push the reviewed code/history.
  Candidate `DRag0oN1/Tachyon` was checked with a 404 response. No remote is
  configured, and no publication has occurred in this task.
- [ ] Review the final intended files and included history immediately before
  publication. Keep credentials, owner-session material, profile content, private
  rights evidence, CAD, meshes, recordings and local caches excluded.
- Optional: choose an application reuse license. No root application license is
  currently present; this is not a challenge requirement or submission gate.
  The curriculum's MIT license is a separate notice.
- [ ] Preserve dependency/curriculum notices and the provenance of retained
  authored RL results; do not label tooling licenses as CAD redistribution permission.
- [ ] Obtain the single explicit repository/video publication approval, including
  depiction of the original Tachyon CAD shown. The private-use records remain
  unchanged until that decision; no separate manufacturer-license gate applies
  to this recording. Manufacturer references remain excluded with their existing
  unresolved scopes.
- [ ] Keep restricted geometry and meshes out of Git/Git LFS, release downloads,
  public static assets and public hosting. Review any proposed change to that scope
  against its own actual rights evidence first.
- [ ] Verify and record the public repository URL without authentication.

## Demo-video preparation

- [x] Record final automated auth-recovery evidence: 699 backend tests and two
  clean-launch desktop/mobile browser cases pass. The fresh-terminal command
  `.venv/bin/tachyon launch --port 8019` uses the canonical private
  `.local/runtime/owner-launch-8019.json` handoff; no `TACHYON_DATA_DIR` is needed
  to recover the running server. The handoff credential is not reproduced here.
- [x] Prepare the actual local review recording using original v6 development
  CAD: `.local/final-demo/Tachyon-demo-review.mp4`, 124.54 seconds. No manufacturer
  VEX geometry is in its authorized scope; no geometry/media assets enter Git.
- [x] Check the official public overview: the required demo duration is 1–3
  minutes, and the public repository must include scope/PRD/spec. The signed-in
  form and all its remaining prompts have not been operated by this audit.
- [ ] Learner reviews the private recording and stabilized app, and gives the
  explicit repo/video publication approval if ready. These remain pending.
- [x] Record the already-defined demonstration sequence. Narration is optional;
  the completed export is silent. Any narration or personal submission answers
  remain learner-authored.
- [x] Complete technical classification review: actual A partial non-VEX CAD,
  B schematic, authored recipe, abstract PPO and abbreviated processing waits
  remain identified; no physical or competition-scoring result is claimed.
- [x] Complete technical recording privacy review by the main owner: actual
  home/playbook/B/CAD/highlight/mobile/edit frames inspected; no credentials,
  address bar or private windows on screen. Only original Tachyon CAD is shown.
- [ ] After the combined explicit release approval, upload the video and verify
  anonymous reviewer access. Source CAD and meshes remain outside Git.
- [ ] Record the video link in the table above and the project's sharing instructions.

## Learner-authored form and survey

- [ ] Inspect the complete current signed-in form and record its remaining
  required fields. The public requirements are checked below; the complete
  signed-in prompts and any existing draft answers have not been reviewed here.
- [ ] Learner confirms/enters the project name; the existing project is Tachyon.
- [ ] Learner writes the short description and all other required submission
  answers themselves. No draft, paraphrase, sample narrative or rewritten copy
  is provided in these artifacts.
- [ ] Learner completes their own reflections and required exit-survey answers.
  No entry-survey repetition or agent-authored reflection is implied.
- [ ] Any requested assistance with existing prose stays within the official
  skill's spelling/grammar boundary; technical evidence and gaps may be identified.
- [ ] Check that the required public repository and video links are present and
  independently accessible, and that the entry describes the actual partial result.
- [ ] Obtain explicit authorization before posting/submitting, or have the learner
  submit directly. Record submission completion only after confirmation.

Deployment, peer feedback, comment links and Discord posts are optional. No
peer-review quota is a submission or completion requirement under the installed
skill. This checklist records outstanding work; it does not claim publication,
submission, full build completion or completion of the learner's private reflections.

## Current official submission requirements checked 2026-10-26

The [official overview](https://learn-ai-basics.devpost.com/) confirms a 1–3 minute
screen recording and a public source repository URL, plus a short description of
what the project does, who it is for and what the learner learned. This is a
verified requirement, not a newly invented duration limit.

The organizer's [form update](https://learn-ai-basics.devpost.com/updates/46821-two-new-questions-on-the-submission-form)
also requires the learner's explanation of how the Devpost Learn Skill Pack was
used and an age-of-majority checkbox. The public repository link belongs in the
**Try it out** field. These fields must be completed truthfully by the learner;
no age/eligibility answer, reflection or submission prose is supplied here. The
signed-in submission form has not been operated in this task.

GitHub authentication is available locally. Read-only inspection found that the
proposed `DRag0oN1/Tachyon` repository does not currently exist (404). It has not
been created or pushed. That concrete destination remains subject to the user's
publication approval, including review of code/history and depiction of the
original CAD in the video; these can be one explicit approval. No root reuse
license has been selected; that optional choice is not a submission gate, and
the curriculum's MIT license is not an application or CAD license grant.
