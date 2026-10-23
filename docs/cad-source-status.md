# CAD source qualification status

Public-source review date: 2026-10-23. This note supports the new Tachyon technical
specification. It records public source observations and unresolved acquisition
dependencies; it does not grant rights or certify geometry.

**Current state: no complete V5 component set has been qualified for Tachyon's
declared use.** No CAD assets or component library have been incorporated. The
technical specification must not represent the source or recipe gate as passed.

## Sources Checked

| Public source | What was established | What was not established |
| --- | --- | --- |
| [Official V5 Robot Brain product page](https://www.vexrobotics.com/276-4810.html) | Manufacturer component identity, dimensions, mounting description, and explicit CAD download entries exist. | This one page is not a complete robot part set or a blanket conversion/redistribution license. |
| [VEX Terms of Use](https://www.vexrobotics.com/terms-of-use), linking to [the publisher's terms](https://www.iubenda.com/terms-and-conditions/89449486) | Content rights are reserved, with a conditional personal/noncommercial download/copy/share provision where explicitly stated and with required attribution. | A blanket grant covering every desired component's conversion, public browser distribution, or commercial use was not established. Record applicable permission for the declared use; do not infer it from Download buttons. |
| [VEX-CAD Fusion repository](https://github.com/VEX-CAD/VEX-CAD-Fusion) and [its license](https://github.com/VEX-CAD/VEX-CAD-Fusion/blob/master/LICENSE) | The archived repository provides Fusion tooling and a parts-library link; its software license is MIT, copyright 2020 VEX CAD. | The license scope/rights covering every required separately supplied geometry asset, its conversion, and distribution have not been verified. The software license alone does not qualify the component set. |
| [Current public Fusion component library](https://github.com/VEX-CAD/VEX-CAD-Fusion-360-Library) | A public component library is available and identifies its purpose as VEX parts. | No asset-specific permission covering the full required Tachyon subset was established during this review. Do not classify it as licensed manufacturer geometry or ready-to-bundle assets. |

These observations are deliberately narrower than legal conclusions. A suitable
path may use asset-specific public licensing, an explicit applicable manufacturer
grant, or written permission covering the intended operations. Permission to
download and permission to redistribute may differ. Keeping files out of Git
does not, by itself, establish use/conversion/display permission.

## Minimum Geometry Roles to Resolve

Qualify an actual identity/source for each required role, with sufficient variants
for two complete architecture baselines and standard/raised configurations on
the demonstrated editable recipe. The second recipe's height edit is not a V1
requirement. Repeated instances
can share one source definition. Counts follow real connections, not a target
part-count metric.

| Assembly function | Required component roles/evidence |
| --- | --- |
| Chassis and structure | Actual structural channels/plates/braces; verified mounting frames and holes |
| Mobility | Actual wheels, V5 motors and mounts, shafts, supported transmissions, bearings, retention and fastening |
| Acquisition and retention | Real end-effector members/contact geometry, pivots/supports, actuator/transmission and retention path |
| Four-bar scoring recipe | Sourced parallel members and their mounted pivots/bearings, powered drive path, supported end-effector mounting and orientation relationship |
| Elevator scoring recipe | Actual tower, guidance/carriage, complete lift transmission and anchors, supported end effector; no floating carriage or invisible chain/path |
| Control and power | Actual required control/power components and mounting/placement; missing required geometry remains a completeness gap |
| Standard/raised alternatives | Native supported part variants or real mounting-port configurations, all changed supports/fasteners, verified joint relationships and measurable scoring-envelope delta |

Do not select exact heights, tooth counts, shaft lengths, channel variants, or
load ratings without the source/part evidence. Do not manufacture new part
lengths by scaling a mesh and claim an authentic SKU.

## Required Qualification Record

For each selected component, the later manifest must include:

- Original publisher/source URL and immutable revision or acquired content hash.
- Actual component/SKU identity and manufacturer-versus-community origin.
- Applicable permission/license, its scope, attribution, and distribution limits.
- Source file hash, file type, units, dimensions, and accepted body selection.
- Converter/version/settings, output mesh hash, and source-to-browser frame.
- Verified mounting/shaft/joint ports and known limitations.

For each baseline, map required strategy actions to sourced object interfaces,
acquisition/retention geometry, target poses, reach, and relevant clearances.
For each recipe/configuration, record actual definitions, connections, joint
members/limits and coupling, completeness, and competition-task compatibility.
For the demonstrated editable recipe, record its supported height/reach delta.
This record must
identify missing evidence rather than filling unknowns with invented facts.

## Consequence for Planning

The proposed architecture and APIs can be reviewed now. **Final engineering
specification readiness remains blocked** until a complete permitted source set
and viable configurations are identified. No blank manifest, primitive fixture,
attractive render, or AI claim substitutes for that qualification. A source-name/
public-link question has been offered to the learner; no permission request has
been sent to a third party and no acceptance is inferred from silence.
