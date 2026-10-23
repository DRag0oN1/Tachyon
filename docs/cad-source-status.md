# CAD source qualification status

Reviewed 2026-10-23 for `4-spec`. **Official manufacturer geometry is preferred.
Neither investigated library has verified permission for Tachyon to redistribute
original CAD or converted browser meshes.** No such geometry is included in the
public project, and no geometry was deployed. No permission request was sent.

**Selected implementation approach: user-provided STEP, local processing, and
operation-specific rights qualification.** This resolves the distribution
dependency in the architecture; it does not grant permission to convert a
particular uploaded file or establish that complete robot recipes already work.
The technical specification is ready for review on this basis, with asset,
recipe, task-compatibility, and browser checks retained as build gates.

## Findings from the requested sources

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

| Operation | Current evidence | Tachyon policy for this build |
| --- | --- | --- |
| Acquire / store original | Specific manufacturer downloads, subject to terms. | User supplies lawfully obtained files; retain source identity and terms. No bulk downloader or automatic mirror. |
| Convert STEP to browser mesh | No general permission verified. | Require an applicable asset-specific basis covering conversion before preprocessing. Local storage alone is insufficient. |
| Place instances / modify assembly | No general permission verified. Placement and changing part geometry are distinct operations. | Record assembly-placement authorization separately. V1 never stretches or edits source solids. Part editing remains unavailable. |
| Local browser display | No blanket permission inferred. | Qualify local display separately; retain access-controlled local API. |
| Phone access on LAN | Additional transmission/display context. | Enable only where declared permission covers that use; owner token and explicit LAN origin required. Otherwise loopback only. |
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

Explicit manufacturer downloads were inspected as native BReps in ignored
`.local/cad-research/` for this user-requested feasibility investigation. No mesh
was generated, no original file changed, and no permission for later conversion
or publication is inferred. These are research inputs, not bundled app content
or an automatically qualified runtime catalog.

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

Some offered downloads returned HTTP 403, including the candidate 25-hole
channel, gusset, motor, and separate nut request. No restriction was bypassed.
Availability of one channel/claw does not establish a complete robot part set.

## Two scoring-mount configurations: bounded verification

The newly authored [headless probe](../tools/verification/verify_scoring_mount.py)
reads the channel and claw originals and selects native bolt/nut definitions in memory.
[Measured results](verification/scoring-mount-feasibility.json) contain native
geometry and reference revision checks, without meshes or solids. No application
UI, API, or production revision service has been built by this probe.

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
3. Convert only after local conversion/display/assembly rights are qualified.
   Cache sources/meshes locally by hash. Default to loopback; qualify LAN access
   separately for the required phone demonstration.
4. In M0/M1 qualify remaining geometry for both complete four-bar and elevator
   baselines: chassis/drive/transmissions; bearings/shafts; acquisition/retention;
   powered lift members/guides/mounts; power/control; hardware/bracing. Verify
   game-object interfaces, target poses, reach and clearances. The static fixture
   passes none of these missing whole-robot gates by implication.
5. Integrate the remount edit on at least one qualified complete recipe, rederive
   capabilities/bindings after every revision, and verify the lifecycle in the app
   and browser. Unsupported edits/recipes/integrations remain unavailable.
6. Before `6-ship`, qualify demo-image/video publication for every visible asset
   or obtain permission. Distribution/hosting stay disabled unless resolved
   separately. A private working recording is not permission to publish imagery.

This path needs no private robotics implementation or internal artifact. Complete
component-set and end-to-end evidence remain explicit delivery risks, not hidden
planning successes.
