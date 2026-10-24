# Application acceptance status

Current build: first source-import/inspection increment, **partial**.
The approved POC and all 22 P0 obligations are not complete. Passing automated
checks do not promote fixtures, a source hierarchy or a UI shell into robots.

Criterion status: **1 passing, 0 failing, 3 blocked, 40 unimplemented**.

The unimplemented category includes partially delivered interfaces; notes identify
that coverage without marking the complete criterion passed. Blocked means the
necessary authentic inputs/device evidence are missing. No known failing software
check is carried forward; unimplemented functionality is not a passing negative test.

Latest software evidence: 205 backend tests and 28 frontend tests passed; production
build passed. Two additional real desktop/mobile external-source status cases
passed with no geometry requests. Official Clawbot and motor originals now exist
outside the repository, but native processing/display rights remain unverified.
See [external catalog evidence](external-catalog.md). The updated production
source-profile suite passed four cases with two mutually exclusive
empty-catalog cases skipped; those two cases are checked separately against the real
empty default workspace. The source uses an original Tachyon-authored **non-VEX**
calibration STEP fixture. Actual source file conversion, binary GLB vertices,
metres/axes, hierarchy, selection and camera actions were checked. Physical-phone
pinch/pan, authentic VEX geometry and complete assemblies were not verified.
See [slice evidence](slice-1.md) and [structured results](slice-1-results.json).

| Criterion | Gate | Status | Evidence or remaining requirement |
| --- | --- | --- | --- |
| COMP-1 | P0 | unimplemented | Not implemented. A fresh workspace can select default Override without a PDF upload and inspect its source/version. |
| COMP-2 | P1 | unimplemented | Not implemented. Another supported VEX PDF produces competition facts through the same visible workflow; a fact opens its corresponding source page/section. |
| COMP-3 | P1 | unimplemented | Not implemented. Invalid, encrypted/unreadable, incomplete, or unsupported documents produce a specific status and a usable retry/replacement path; none produces invented rules. |
| COMP-4 | P1 | unimplemented | Not implemented. Switching competition or source version invalidates stale generation context while retaining existing designs under their original context. |
| STRAT-1 | P0 | unimplemented | Not implemented. Generate Strategy works from Home with no robot and returns at least two substantively different approaches. |
| STRAT-2 | P0 | unimplemented | Not implemented. Each approach exposes objectives, mechanism needs, execution sequence, rationale, tradeoffs, and relevant rule sources. |
| STRAT-3 | P1 | unimplemented | Not implemented. Creating from a selected strategy retains its competition/version and action identities through the resulting design. |
| STRAT-4 | P1 | unimplemented | Not implemented. Failure, cancel, and retry retain the user's competition and inputs; failed or example output is never labeled successful AI generation. |
| ROBOT-1 | P0 | unimplemented | Not implemented. Create Robot from a fresh workspace generates from rules without a prior strategy session or mandatory description. |
| ROBOT-2 | P0 | unimplemented | Not implemented. Both candidates have competition-aware strategies and demonstrable differences in mechanism arrangement, subsystem type, chassis/power architecture, or operational approach; cosmetic changes alone fail. |
| ROBOT-3 | P0 | unimplemented | Not implemented. Both candidates are inspectable as complete conceptual component assemblies under F4; a failed or incomplete alternative is clearly labeled and does not count toward completion. |
| ROBOT-4 | P1 | unimplemented | Not implemented. Comparison identifies the actual mechanical differences and tradeoffs; opening and switching candidates preserves the correct strategy/assembly associations. |
| ROBOT-5 | P1 | unimplemented | Not implemented. Generation failure and partial success preserve existing accepted designs and expose specific retry or revise-request actions. |
| CAD-1 | P0 | blocked | Native import/conversion validated on original non-VEX fixtures only. Official Clawbot/motor originals are present externally; applicable native-processing/display rights and actual authentic import/render checks remain unresolved. |
| CAD-2 | P0 | unimplemented | Native source parent hierarchy is preserved; new robot attachments, joints and actuation paths are not implemented. |
| CAD-3 | P0 | unimplemented | Invalid sources, rights, units and receipts are rejected; whole-robot completeness checks are not implemented. |
| CAD-4 | P0 | blocked | Rights/source/asset safeguards pass software tests; no submitted authentic robot asset set is qualified. |
| VIEW-1 | P0 | blocked | Source-component desktop controls and mobile viewport/tap work. Authentic robot inspection and physical-phone pinch/pan remain unverified. |
| VIEW-2 | P1 | unimplemented | Source-native hierarchy/canvas selection is partially verified. Robot-component hierarchy remains unimplemented. |
| VIEW-3 | P2 | unimplemented | Not implemented. Hide/show, isolate, Show all, exploded/reset, orientation, and available display controls visibly affect the intended geometry without changing accepted engineering data. |
| VIEW-4 | P1 | unimplemented | Not implemented. A supported mechanism's operation moves the correct members through declared joints/limits; unsupported operation is labeled and has no misleading enabled Play action. |
| VIEW-5 | P0 | unimplemented | Source-view panels preserve camera/selection in actual browsers; robot workflow is not implemented. |
| LINK-1 | P0 | unimplemented | Not implemented. Selecting a strategy action highlights/focuses its actual mechanism and shows the matching explanation, sketch, and field step. |
| LINK-2 | P1 | unimplemented | Not implemented. Selecting that mechanism from CAD reveals the same supported actions and allows return to their context. |
| LINK-3 | P1 | unimplemented | Not implemented. Sketch annotations and operation controls refer to actual components/joints; assumed field routes and unsupported actions are labeled accurately. |
| LINK-4 | P0 | unimplemented | Not implemented. After an accepted design change, links and illustrations reflect the new assembly or show an explicit pending/unsupported state; stale support is not silently reused. |
| AI-1 | P0 | unimplemented | Assistant compact/expanded/full-screen shell and retained expanded draft work. Compact composer and functional commands remain unimplemented. |
| AI-2 | P0 | unimplemented | Selected source context is shown. Functional strategy/mechanism intents are not implemented. |
| AI-3 | P0 | unimplemented | Not implemented. A supported request produces a preview affecting actual assembly geometry/relationships; Apply updates the accepted structured design and visible CAD. |
| AI-4 | P0 | unimplemented | Not implemented. Discard leaves the accepted design unchanged, Undo restores the preceding assembly and links, and failed changes preserve the usable accepted revision. |
| AI-5 | P0 | unimplemented | Not implemented. The guaranteed initial edit is explicitly agreed and demonstrated. Explanations, camera changes, and unsupported replacements cannot substitute for that demonstration. |
| THEME-1 | P0 | unimplemented | SNAP/SHIFT source-view appearance/core feedback work in real browsers. Full engineering workflow remains unimplemented. |
| THEME-2 | P1 | unimplemented | Source-view theme switching retains the loaded geometry, camera and draft; actual revision workflow is not implemented. |
| THEME-3 | P1 | unimplemented | Browser reduced-motion checks pass for the current core/panels. Mechanism operation/revision interactions remain unimplemented. |
| LAYOUT-1 | P1 | unimplemented | Simple/Advanced source details work. Complete robot/strategy/edit controls remain unimplemented. |
| LAYOUT-2 | P2 | unimplemented | Not implemented. Focus, Split, Studio, and practical Custom arrangements allow collapse/reopen, supported resizing, maximize/restore, and reset. |
| LAYOUT-3 | P1 | unimplemented | One phone source sheet and full-window source canvas work; complete adaptive layout matrix is unimplemented. |
| LAYOUT-4 | P1 | unimplemented | Theme/mode and active source persist. Project layout preferences are not yet implemented. |
| MOBILE-1 | P1 | unimplemented | Actual mobile WebKit viewport verified for source inspection only; no physical phone or complete journey verified. |
| MOBILE-2 | P1 | unimplemented | Source panel/assistant continuity is partially verified; full keyboard/orientation/project coverage remains unimplemented. |
| MOBILE-3 | P1 | unimplemented | Named source controls, focus handling and touch targets exist; full application accessibility audit remains unimplemented. |
| STATE-1 | P1 | unimplemented | Source preferences persist through SQLite; accepted robot project/revision persistence is unimplemented. |
| STATE-2 | P0 | unimplemented | Source rendering loading/ready/failure is truthful; engineering proposal/accepted/incomplete lifecycle remains unimplemented. |
| STATE-3 | P0 | passing | Unavailable generation and edits are disabled; source/fixture labels and capabilities are truthful. No fake successful operation is exposed. |

The pre-build static scoring mount and its copied-snapshot example are not
production modification, lift, complete-robot or live-generation evidence.
The approved next milestone is one complete strategy-linked robot, followed by
live generation of two genuinely distinct designs, then actual revision handling.
No build-slice checkbox or hands-on checkpoint is complete by inference.
