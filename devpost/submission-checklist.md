# Submission preparation checklist

Status: authorized partial-demo source published; video upload and learner submission pending.
Updated 2026-10-26. Reviewed source `2d86280`; application baseline `667fd90`.

The reviewed application is preserved at `667fd90` under local tag
`submission-baseline-2026-10-26`, with a verified private Git bundle. The learner's
favorable demo review and fixed-two-design concern are recorded in the build
checklist. Following the explicit deadline fallback, [additional design generation
and management](../docs/next-design-generation.md) is the first post-hackathon
milestone, not a feature claimed in the existing recording. Public source release
is now explicitly authorized and complete; the application and review video are
unchanged. The learner will complete and submit the Devpost entry themselves.

This is a factual technical checklist, not learner-authored submission copy.
The learner authorized honest partial-demo preparation while the approved full
build is unfinished. Scope, acceptance requirements and existing review checkboxes
are unchanged. See [the shipping audit](../docs/ship-readiness.md) for evidence,
history/privacy checks and exact publication blockers.

Current authorization covers public code/documentation/history at
`DRag0oN1/Tachyon` and preparation of the reviewed **1–3 minute video** for public
sharing. It uses original Tachyon development CAD from `.local/generated-robot-a-v6`.
Manufacturer VEX reference assets are excluded. All source geometry and meshes
remain private and out of Git; manufacturer redistribution rights are unchanged.
The learner approved publishing the reviewed partial demonstration, not completion
of its remaining full engineering criteria. See [publication](../docs/publication.md).
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
- [x] Learner reviewed the demo favorably and explicitly approved public source
  publication and video preparation for the partial application. Retained failed
  attempts and passing retries; no application changes were made for publication.

The remaining full-build/learning gates stay open. They do not prevent the learner's
explicitly authorized publication of this truthfully labeled partial demo.

## Required links

| Deliverable | Link | Verification |
| --- | --- | --- |
| Public GitHub repository | [DRag0oN1/Tachyon](https://github.com/DRag0oN1/Tachyon) | Public source, required scope/PRD/spec and baseline tag verified anonymously with HTTP 200. |
| Short demo video | **Upload-ready:** `.local/final-demo/Tachyon-demo-review.mp4`, approximately 2:05 | Reviewed file unchanged; classification/privacy check complete. Learner uploads it and verifies reviewer access; public URL pending. |
| Live application | Optional; not selected | Deployment is not required and does not replace either link above. |

## Public repository and asset release

- [x] Received explicit learner authorization; created public `DRag0oN1/Tachyon`,
  configured `origin`, and pushed reviewed `main` plus the preserved baseline tag.
- [x] Reviewed the exact files and all 17 pre-release commits before pushing:
  credentials, owner-session material, private profiles/rights, CAD, meshes, media
  and caches are excluded. The final publication record documents the audit scope.
- Optional: choose an application reuse license. No root application license is
  currently present; this is not a challenge requirement or submission gate.
  The curriculum's MIT license is a separate notice.
- [x] Preserve dependency/curriculum notices and the provenance of retained
  authored RL results; do not label tooling licenses as CAD redistribution permission.
- [x] Learner approved publishing Tachyon and preparing the already-reviewed
  original-development-CAD video for public sharing. This is not a manufacturer
  CAD license; no original/converted geometry is distributed. Manufacturer
  references remain excluded with their unresolved scopes.
- [x] Keep restricted geometry and meshes out of Git/Git LFS, release downloads,
  public static assets and public hosting. Review any proposed change to that scope
  against its own actual rights evidence first.
- [x] Verify and record the public repository URL without authentication.

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
- [x] Learner reviewed the demonstration favorably and explicitly authorized
  source publication plus preparation of this reviewed video for public sharing.
- [x] Record the already-defined demonstration sequence. Narration is optional;
  the completed export is silent. Any narration or personal submission answers
  remain learner-authored.
- [x] Complete technical classification review: actual A partial non-VEX CAD,
  B schematic, authored recipe, abstract PPO and abbreviated processing waits
  remain identified; no physical or competition-scoring result is claimed.
- [x] Complete technical recording privacy review by the main owner: actual
  home/playbook/B/CAD/highlight/mobile/edit frames inspected; no credentials,
  address bar or private windows on screen. Only original Tachyon CAD is shown.
- [ ] Learner uploads the prepared video and verifies anonymous reviewer access.
  Source CAD and meshes remain outside Git; no public media URL is claimed yet.
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

The authorized public repository now exists and is anonymously readable at
<https://github.com/DRag0oN1/Tachyon>. Initial push was 17:03:21 Eastern, after the
stated 17:00 deadline; no timely-publication or Devpost submission claim is made.
The learner must check whether their submission form remains available. No root
reuse license has been selected; that optional choice is not a submission gate,
and the curriculum's MIT license is not an application or CAD license grant.
