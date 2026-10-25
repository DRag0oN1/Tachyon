# CAD source qualification status

Updated 2026-10-25 from the current implementation and private local receipts.
The historical `4-spec` investigation is retained below. **Official manufacturer
geometry is preferred; public redistribution/hosting of the investigated CAD
remains unverified.** Original CAD and converted meshes stay in private storage,
outside application bundles and commits. No new licensing research or permission
request was performed for this update.

The visible generated architecture-A development assembly now uses **35 newly
authored, non-VEX STEP definitions**, not manufacturer geometry: 494 placements
and 631 relationships through the production local pipeline. Its source records
identify self-authorship and only local storage/conversion/placement/display;
they do not fabricate manufacturer permission or qualify an authentic VEX robot.
Source STEP, GLB and screenshots remain ignored/private. This is the learner's
explicitly authorized development fallback. The VEX records and their separate
unverified placement, modification, LAN, redistribution, hosting and public
depiction scopes are unchanged. See the [actual rendering and interference
report](verification/robot-generation.md); connected graph validation does not
remove its known physical intersections.

**Selected implementation approach: user-provided STEP, local processing, and
operation-specific rights qualification.** Local inspection and public asset
redistribution are separate gates. The two sources below now have a narrow
private-inspection basis recorded; this establishes neither new assembly-placement
scope nor complete robot recipes.
The learner approved the technical specification on this basis, with asset,
recipe, task-compatibility, and browser checks retained as build gates.

## Current local sources and qualification — 2026-10-24

Created the learner-selected private roots `~/Documents/TachyonCAD/step/` and
`~/Documents/TachyonCAD/rights/`, outside Git. Explicitly requested manufacturer
originals were downloaded to the STEP root. The initial 2026-10-23 register left
processing/display unverified and correctly refused native measurement at that
time. The later `rights.json` and
`private-inspection-review-2026-10-23.json` supersede that local-inspection status:
`acquisition_storage`, `conversion`, and `loopback_display` are qualified for
these exact source hashes under `terms_interpretation` /
`private_local_inspection`. **This is not explicit manufacturer permission,
an asset-specific license, or written rightsholder permission.**

| Official source and offered identity | Original bytes | SHA-256 | Current application permissions |
| --- | --- | --- | --- |
| [System Bundle](https://www.vexrobotics.com/v5-system-bundle.html): [V5 Clawbot 276-6009 STEP](https://www.vexrobotics.com/cadmodels/upload/download/upload_id/0212d660-fca3-43ad-addb-bc9dc58b28e4) | 119,373,056 | `d291e70cf6ccd5260983193ab07d9f824b965b1c5f7e2ef298e961e7e7768fb7` | Private storage/conversion/authenticated loopback inspection qualified by narrow terms interpretation; new assembly placement unverified |
| [V5 Smart Motor 276-4840](https://www.vexrobotics.com/276-4840.html): [offered STEP](https://www.vexrobotics.com/cadmodels/upload/download/upload_id/4d4d0c25-ee11-41b1-a39a-97eadda19619) | 16,822,582 | `3399374de417a5b403619e9e475d616e0cc1c3196324b4ba15d4fd0049ab9cec` | Private storage/conversion/authenticated loopback inspection qualified by narrow terms interpretation; new assembly placement unverified |

The review permits only the requested personal local inspection/development run,
unchanged originals/geometry, retained attribution, and authenticated loopback
display. `assembly_placement`, `part_modification`, `lan_display`,
`public_depiction`, original/mesh redistribution and public hosting remain
unverified. The policy explicitly prevents the private-inspection interpretation
from authorizing those operations. No remote CAD processing/transmission is
authorized by these records.

Implemented discovery, source-provenance recording, permission-gated native
measurement, external manifest registration, local conversion/cache loading and
owner-authenticated source status. Files supplied by the user follow the same
workflow. Discovery only hashes bytes and samples literal text; it does not
verify dimensions, geometry, identity or mechanical connections. The importer
accepts bounded STEP sources up to 256 MiB. Both sources have native measurement
and prepared browser meshes in ignored `.local/`; source/mesh hashes and current
converter/catalog fingerprints were checked. The active registration points to
`.local/catalog/vex-local-manifest.json` and the external `rights.json`.

| Prepared inspection reference | Native solids | Display hierarchy nodes | Geometry qualification |
| --- | --- | --- | --- |
| `v5_motor_reference` | 23 | 28 | Aggregate BRep valid; reference inspection only |
| `v5_clawbot_reference` | 450 | 515 | Aggregate BRep invalid; reference inspection only |

Both receipts retain `referenceOnly: true`, `ports: []`, `completeRobot: false`
and `qualifiedForRobotGeneration: false`. A separate read-only native Clawbot
audit found 48 unique leaf definitions across 435 geometry occurrences individually
BRep-valid. That does not resolve the aggregate failure: the current receipt uses
`aggregate_only` diagnostics and `invalidDefinitionCount: null`. Native parent
relationships are not physical mates, actuator paths or joints. Source labels,
definition labels and occurrence metadata exist in the native importer; the
current display receipt is not a selected-part assembly catalog.

Actual motor rendering, native-part selection, focus/reset and SNAP/SHIFT passed
on desktop and mobile WebKit in the saved
`.local/verification/production-motor-inspection/.last-run.json`. This is browser
viewport evidence on loopback, not physical-phone/LAN or public-image permission.
The motor and Clawbot remain manufacturer inspection references, not newly
generated robots. See the [production integration evidence](verification/production-integration.md)
and its final test/command report, [historical external catalog evidence](verification/external-catalog.md)
and [catalog instructions](../data/catalog/README.md). No slice or learner-review
completion is inferred from these checks.

## Historical findings from the requested sources — `4-spec`

| Source | Verified observation | Restriction / decision |
| --- | --- | --- |
| [Official V5 Structure](https://www.vexrobotics.com/v5-structure.html) and [C-channels](https://www.vexrobotics.com/channel.html) | Explicit manufacturer STEP downloads and SKU identities. Channel specifications give a 0.500-inch hole grid. Original 276-2289 STEP was read and measured locally. | Preferred geometry provenance, not an asset license. Public mesh hosting and redistribution permission were not established. |
| [VEX terms](https://www.vexrobotics.com/terms-of-use), linked [publisher terms](https://www.iubenda.com/terms-and-conditions/89449486) | Rights reserved; conditional personal/noncommercial download/copy/share where explicitly stated, with attribution. Broader transformations/publication are restricted absent an applicable basis. | No blanket grant for conversion, part modification, redistribution, or hosting was found. This does not decide whether a specific authorized local CAD use is permitted. |
| [Current VEX-CAD Fusion 360 Library](https://github.com/VEX-CAD/VEX-CAD-Fusion-360-Library/tree/1cc3283171311d639e8e8880a6a2f322a7e15520) | Reviewed commit `1cc3283171311d639e8e8880a6a2f322a7e15520`: 1,270 `.f3d` paths in the untruncated tree; GitHub license metadata `null`; no LICENSE/COPYING/COPYRIGHT/NOTICE/TERMS file found in that tree. | Asset rights remain **unverified**, not approved or assumed public domain. No community CAD was downloaded, converted, or incorporated. |
| [Separate Fusion tooling license](https://github.com/VEX-CAD/VEX-CAD-Fusion/blob/master/LICENSE) | MIT software license in the older tooling repository. | It does not establish licensing of the current library's manufacturer/community model files. Do not propagate MIT onto those assets. |
| [CadQuery import/export documentation](https://cadquery.readthedocs.io/en/latest/importexport.html) | STEP import and assembly GLB export are documented. Native Fusion `.f3d` is not a supported input in the selected pipeline. | Require STEP supplied under applicable rights. A separately permitted Fusion export is the user's preparation step, not an implemented Tachyon integration. |

The absence of a license file is evidence of unresolved permission, not proof
about all possible grants or statutory rights. No asset-specific written grant
was obtained in this investigation.

## Rights by operation

The 2026-10-25 source-selection increment prepares 27 exact native definitions
from the hash-pinned user-supplied Clawbot file, preserving their own coordinates
and child hierarchies. The supplied rights records remain unchanged: this is
private local conversion/inspection, not an approval for assembly placement or
distribution. A bounded user-attestation schema is implemented, but no real user
attestation or new manufacturer grant has been recorded. See the
[generation evidence and remaining restrictions](verification/robot-generation.md).

| Operation | Current evidence | Tachyon policy for this build |
| --- | --- | --- |
| Acquire / store original | Qualified for the two hashes above by the narrow private-inspection terms interpretation. | Retain unchanged sources, source identity, terms and attribution. No bulk downloader or automatic mirror. |
| Convert STEP to browser mesh | Qualified for those two originals for private local inspection; not an explicit manufacturer grant. | Local conversion and content-addressed meshes are implemented. Other supplied files require their own applicable records. |
| Place instances / modify assembly | **Unverified** for both references. Placement and changing source geometry are distinct operations. | Recheck assembly placement for each design part. The production service rejects `referenceOnly` inputs; source-part editing remains unavailable. |
| Local browser display | Authenticated loopback inspection qualified for those two hashes. | Check source identity, receipt, mesh and current operation evidence before serving. |
| Phone access on LAN | **Unverified** for both references. Mobile WebKit viewport tests used loopback. | Physical-phone/LAN verification remains separate; owner authentication alone does not grant LAN scope. |
| Screenshots / public demo video | No general publication permission verified. | Qualify rendered depiction/publication separately before releasing CAD recordings. A private-use grant is insufficient by itself. |
| Redistribute original or converted files | **Unverified** for both sources. | Disabled: no Git/Git LFS, releases, app bundles, sample downloads, public storage, geometry exports, or public mesh endpoint. |
| Public hosting / deployment | **Unverified** for both sources. | Disabled for these assets. Publishing application code through an authorized shipping decision does not host the local CAD library. |

For every supplied component, a private rights record stores the covered subject
(including source hash), licensor/rightsholder, applicable terms or written
permission, evidence reference/date, allowed/excluded operations, attribution,
and any expiry. An unsupported checkbox does not become verified licensing.
Unresolved required operations keep the asset unavailable. `qualified_local`
never implies `qualified_distribution` or `qualified_demo_publication`.

Original CAD, local meshes, screenshots, geometry-bearing exports, raw source
pages, permission documents, and caches stay outside commits. The external model
receives only authorized non-geometric competition facts, symbolic capabilities,
selection, and command context; **no CAD bytes or renders** are sent to it in
this profile. Do not retain geometry in access logs.

## Original-source inspection and provenance

The following channel/claw/hardware records belong to the historical `4-spec`
native-BRep investigation in ignored `.local/cad-research/`. That investigation
generated no display meshes and changed no originals. These research inputs are
not active runtime catalog entries and are not covered by the later two-source
Clawbot/motor inspection records. Later conversion of those separate references
does not qualify these research sources or any new assembly placement.

| Identity | Offered original / source | Bytes | SHA-256 |
| --- | --- | --- | --- |
| Aluminum C-channel 1×2×1×35, 276-2289; product `276-2289-001 Rev1` | [Official STEP](https://www.vexrobotics.com/cadmodels/upload/download/upload_id/9ae4c283-1720-4741-b413-cfd5f54576e7), [product](https://www.vexrobotics.com/channel.html) | 4,313,734 | `b47702c2710611256b80b3efadd53b3c6a502602d3d0c3151f45c5bf5ad07d56` |
| Claw Kit v2, 276-6010 | [Official STEP](https://www.vexrobotics.com/cadmodels/upload/download/upload_id/27ed312a-6226-498f-95d5-7c97bcc2856c), [product](https://www.vexrobotics.com/276-6010.html) | 15,555,881 | `76ddd073429280482a4538c4750d2234d0ed173d6a8649d013c6669e96f39213` |
| #8-32 × 1/2-inch star-drive screw, 276-4992 | [Official STEP](https://www.vexrobotics.com/cadmodels/upload/download/upload_id/079f0b2e-7209-45fa-bd05-370e13346ada), [product](https://www.vexrobotics.com/all-screws.html) | 110,779 | `eaf78e1cada07124cc378b241dd3237e868e77ebbc2580b0049cec63f8ce634f` |
| Selected #8-32 × 1.5-inch screw, 276-4998, and #8-32 hex nut, 275-1028 | Native definitions `_8-32_x_1_5000_Star_Drive_Screw_276-4998_No Threads` and `_8-32_Hex_Nut_275-1028` inside the claw source; [screw identity](https://www.vexrobotics.com/all-screws.html), [nut identity](https://www.vexrobotics.com/nuts-8-32.html) | Included above | Same claw source hash; no separate file exported |

The channel source has conversion-based inch units. Import to millimetres gave
444.5 mm length, 25.4 mm width, 13.97 mm depth, and 1.5748 mm web. There are
**34 centerline web holes** on a measured 12.7 mm pitch; the catalog name does
not replace measurement of the selected row. The claw source uses millimetres
and contains 83 valid solids; that is not a claim of 83 independently editable
or correctly cataloged components.

During the earlier `4-spec` investigation, some offered downloads returned HTTP 403, including the candidate 25-hole
channel, gusset, motor, and separate nut request. No restriction was bypassed.
The later Slice 1 motor download above succeeded through its explicitly offered
link. Available originals do not establish a qualified complete robot part set.

## Historical `4-spec` scoring-mount configurations: bounded verification

The newly authored [headless probe](../tools/verification/verify_scoring_mount.py)
reads the channel and claw originals and selects native bolt/nut definitions in memory.
[Measured results](verification/scoring-mount-feasibility.json) contain native
geometry and reference revision checks, without meshes or solids. This probe did
not build or exercise the application UI/API or production revision service.
The later production STEP-fixture lifecycle below is separate evidence.

One authentic channel upright supports the claw through two existing through-holes
with two genuine 1.5-inch screw/hex-nut pairs. The selected holes have measured
4.2 mm inner bores and 4.6228 mm outer openings across a 30.525 mm claw stack.
The claw is rolled a quarter-turn so its 12.7 mm hole spacing follows the upright;
its opening orientation is vertical in this fixture. The channel web contacts
an existing outer mounting face. The two native source files stay unchanged.

| Configuration | Mount reference height above fixture origin | Centerline hole indices, zero-based | Change |
| --- | --- | --- | --- |
| `standard` | 209.55 mm | 15, 16 | Baseline static cassette |
| `raised` | 260.35 mm | 19, 20 | Four pitches / **50.8 mm higher**; mounting ports, claw/hardware placements, action/sketch anchors change |

Heights are relative to the lower channel endpoint, **not robot floor height,
maximum powered reach, or a verified Override scoring target**. This is a genuine
re-mount, not a joint pose or longer mesh. Use it only within a later complete
recipe whose object-handling, actuator, supports, envelope and competition checks
also pass. The edit stays unavailable on an unqualified recipe.

The probe checks source hashes/BRep validity, real hole alignment, hardware stack,
static non-mating intersections, and connected mount records in both configurations.
All 13 instance pairs other than the two intentional screw/nut threaded mates
were checked in each configuration. Maximum computed overlap was approximately
0.000430406 mm³, below the preselected 0.001 mm³ computational-contact threshold;
this is not a manufacturing clearance or a claim of exactly zero intersection.
The modeled screws have no thread surfaces: the 2.85014 mm projection beyond
the nut is nominal axial fit, not a thread-strength/torque check.
It exercises an independent **reference example using copied snapshots**: Preview preserves
accepted data, Discard leaves it intact, Apply takes the exact candidate and changes
transforms/ports, action/sketch anchors follow the cassette, serialization preserves
it, and Undo restores the preceding engineering/binding hash. Production service
and browser verification on complete assemblies remain mandatory in `5-build`.

Not established: powered lift/drive integration, load/torque, dynamic clearance,
object retention/scoring, legality, locking-fastener suitability, continuous
collision freedom, or physical performance. The native claw needs its separate
actuator. This fixture alone is **not a complete robot**.

Earlier side-wall mounting candidates were rejected: inward nuts intersected the
housing by about 5.13 mm³, reversed screw heads by about 0.299 mm³, and spacer
variants also failed. The final through-mount uses a different measured native
hole pair. Failed layouts are not qualified recipes, and the threshold was not
relaxed to pass them.

### Reproducing this probe

Requires lawfully supplied originals matching the two source hashes above.
The tool makes no downloads, CAD exports, or mesh conversions. Use a separate
Python 3.12 environment; this is not application installation:

```sh
python3.12 -m venv .local/verification-venv
.local/verification-venv/bin/python -m pip install cadquery-ocp==8.0.1.1.0
.local/verification-venv/bin/python tools/verification/verify_scoring_mount.py \
  --channel .local/cad-research/276-2289.step \
  --claw .local/cad-research/claw.step \
  --output .local/scoring-mount-feasibility.json
```

The recorded run used a fresh temporary Python 3.12 environment, not another
project's environment. The JSON stores the probe/source hashes, selected native
definitions, measured values, tolerance, and reference-only results. Public
evidence contains numerical findings; originals and raw inspection records stay
ignored locally. The wrapper package's software license is recorded separately
in [third-party notices](../THIRD_PARTY_NOTICES.md).

## Selected implementation and remaining build gates

1. Publish new Tachyon code, recipes, source links/provenance metadata, import
   instructions, and software notices. Install without a geometry bundle;
   rulebook/strategy functions work independently. Missing CAD remains visible.
2. Accept user-supplied STEP plus a private operation-specific rights manifest.
   Validate bytes, units, selected bodies/hierarchy, and ports locally. Do not
   accept `.f3d` as STEP or add a Fusion service dependency.
3. Convert only after acquisition/storage and conversion rights are qualified.
   Cache sources/meshes locally by hash. Check assembly placement before building
   assemblies and local display before serving meshes. Default to loopback; qualify LAN access
   separately for the required phone demonstration.
4. In M0/M1 qualify remaining geometry for both complete four-bar and elevator
   baselines: chassis/drive/transmissions; bearings/shafts; acquisition/retention;
   powered lift members/guides/mounts; power/control; hardware/bracing. Verify
   game-object interfaces, target poses, reach and clearances. The static fixture
   passes none of these missing whole-robot gates by implication.
5. The production service now constructs declared joint endpoint configurations,
   revisions and derived bindings; integrate that path with a qualified complete
   authentic recipe. The historical static remount is not the production joint
   demonstration. Task capabilities remain unverified after graph/pose checks.
6. Before `6-ship`, qualify demo-image/video publication for every visible asset
   or obtain permission. Distribution/hosting stay disabled unless resolved
   separately. A private working recording is not permission to publish imagery.

This path needs no private robotics implementation or internal artifact. Complete
component-set and end-to-end evidence remain explicit delivery risks, not hidden
planning successes.


## Production integration and remaining acceptance gates — 2026-10-24

The app now exposes fresh frozen-PPO inference from the saved seed-17 policy,
without training, and two mechanically distinct engineering alternatives for
one learned family. The learner explicitly accepts this same-family alternative
pair; it is not two learned policies or two complete robots. The real production
UI, genuine motor reference and architecture-blocked path have passed desktop
and mobile WebKit checks saved under `.local/verification/production-browser/`
and `.local/verification/production-browser-mobile/` (`.last-run.json`: passed).
No CAD bytes or renders are inputs to this local policy execution.

`realization.py` / `design_api.py` and the design renderer now exercise actual
prepared STEP component instances, explicit attachments/joints, rigid world
transforms, revision-exact action links, derived tool anchors and coordinate
sketches. Preview keeps the accepted revision intact; Discard, exact-candidate
Apply and compensating Undo are implemented with persistence/conflict checks and
current catalog/rights requalification. The current source requires positive
scoring-height intent, every changing joint to be bound to the scoring action
and move the same anchor, all affected instances within that binding, and higher
Y for the raised anchor. New regression tests are present; their final rerun
results are not presumed here.

The saved `.local/verification/mechanism-browser-complete/.last-run.json` is
passed for two desktop/mobile WebKit cases using **three instances from three
new Tachyon-authored non-VEX STEP sources**. The actual renderer, picking,
strategy highlight, 0.10 m endpoint change, Preview/Discard/Apply/Undo, derived
links/anchors and restored engineering content were checked. **This proves a
software lifecycle on original STEP fixtures, not authentic VEX, a complete
robot, powered hardware, a physically proven mechanism or continuous motion.**
Do not merge it with the historical static-mount probe or the genuine motor
inspection claim.

The existing authentic catalog cannot produce a complete robot. Qualified role
parts, measured ports, role/instance mappings and complete four-bar/elevator
recipes are missing. BOM/supporting-hardware, actuator/transmission, task and
clearance qualification are unimplemented; graph closure and endpoint checks do
not supply them. Other-competition PDF ingestion, custom layouts and broader
inspection remain incomplete/unimplemented. Physical-phone/LAN and public
depiction remain unverified. The complete authentic-robot gate stays **blocked**;
see the [44-criterion status](verification/acceptance-status.md).

The [production integration report](verification/production-integration.md) is
the forthcoming location for final commands, suite totals and rerun outcomes.
This update records existing receipts and current source, without speculative
final test counts or inferred learner sign-off.
