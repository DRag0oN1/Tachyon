# Tachyon

A new mobile-first AI robotics design application connecting competition rules,
strategy, realistic VEX assemblies, and contextual design changes.

**Complicatedly Simple.** The robot fills the workspace; strategy explanations,
components, and the top-left AI core appear when needed. SNAP and SHIFT provide
two mechanical visual identities over the same design data.

## Current status

Planning is in progress. `1-start` is complete and [scope](devpost/scope.md) is
approved. The [product requirements](devpost/prd.md) are approved, including
scoring reach/height as the first supported CAD edit. The [technical specification](devpost/spec.md)
is a final draft awaiting your approval, with staged acceptance, architecture,
data contracts, and milestones. [CAD source findings](docs/cad-source-status.md)
select user-provided STEP and local processing under applicable rights; no
manufacturer/community geometry will be bundled or publicly hosted.
Application implementation has not started. A narrow, user-requested native CAD
mount/reference-lifecycle probe was written during source qualification; it is
not the application or a complete robot demonstration.
No robot generation, model integration, or CAD asset loading is claimed working.
Installation and run instructions will accompany the first verified application
increment.

## Planned core workflow

1. Select Override or upload a supported VEX rulebook and inspect source-linked
   objectives, scoring opportunities, and constraints.
2. Generate distinct AI strategies and compare two mechanical architectures.
3. Inspect connected conceptual robot designs assembled from authentic,
   appropriately licensed VEX component geometry.
4. Select a strategy step to highlight and explain its actual mechanism.
5. Request a supported change through the AI core and inspect the changed CAD.

**Generate Strategy** and **Create Robot** remain independent entry points.
Mobile/desktop layouts, SNAP/SHIFT, Simple/Advanced modes, and collapsible panels
are part of the planned product.

## Planning and development

- [Established product vision](docs/product-vision.md)
- [Devpost progress and required order](devpost/README.md)
- [Approved scope](devpost/scope.md)
- [Approved product requirements](devpost/prd.md)
- [Technical specification draft](devpost/spec.md)
- [CAD source qualification status](docs/cad-source-status.md)
- [Bounded source/mount verification](docs/verification/scoring-mount-feasibility.json)
- [Third-party materials](THIRD_PARTY_NOTICES.md)

Use the official Devpost Learn sequence: `1-start` → `2-scope` → `3-prd` →
`4-spec` → `5-build` → `6-ship`. Fast mode retains required planning approvals,
tests, runtime verification, and learner review. Scope, PRD, and specification
must be approved in order before implementation.

## Source and asset provenance

Application code will be newly implemented for Tachyon. Third-party libraries
and assets require recorded origins, licenses, and attribution. No CAD assets
have been incorporated into the application. Actual source geometry, display
meshes, conceptual geometry, and verification levels will be identified accurately.

The learner profile and credentials are excluded from commits. Publication,
deployment, and challenge submission have not occurred.

The planned public deliverable is code and import instructions without a CAD library.
Users must supply appropriately authorized authentic STEP locally. Conversion,
assembly placement, local/LAN display, demo publication and redistribution have
separate rights checks; an upload or public download link establishes none of
these automatically. Rulebook/strategy services will operate without local CAD;
robot creation will report missing geometry or permissions honestly.
