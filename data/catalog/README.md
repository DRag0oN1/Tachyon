# Local CAD catalog

The public repository contains schemas/role requirements, not a component library.
Actual STEP, private permission evidence, manifests, meshes and receipts belong in
ignored `.local/` storage. None of the examples grants asset rights.

Create `.local/catalog/manifest.json` with `schemaVersion: 1` and `components`.
Each component needs `id`, `name`, optional `sku`, `sourceUrl`, `sourcePath`
(relative to the local data directory), `sourceSha256`, `originKind`,
`geometryClass`, measured `expectedBoundsMm: {min: [x,y,z], max: [x,y,z]}`,
and optional measured `ports`. Source bounds use the STEP importer’s millimetre
coordinates. Ports are already in the documented browser metre/Y-up frame and
require measurement evidence, unit axes and stable IDs. A label is not source
identity or geometry verification.

Create a separate private `.local/catalog/rights.json` with `schemaVersion: 1`
and `records`. Each record binds one `sourceSha256` to `attribution` and an
`operations` map. Registration requires `acquisition_storage`; preparation requires that plus
`conversion`. Rendering a prepared source requires storage and `loopback_display`
or `lan_display` for the actual context. Building new assemblies separately
requires `assembly_placement`. A grant for one operation does not imply another.

Each operation decision carries `status` (`qualified`, `unverified` or `disallowed`),
`rightsholder`, `basis` (`license`, `written_permission` or actual `self_authored`
material), `evidencePath`, `evidenceSha256`, `reviewedBy`, `reviewedOn` and optional
`expiresOn`. Evidence must exist inside the private data directory and match its
reviewed hash. These records document a real review; they do not turn an assertion
or Download button into a license. The software checks scope, identity and
currency, not legal validity. Do not create self-authorship records for third-party
VEX geometry. Unresolved operations must remain `unverified`.

Use the CLI after installing the application:

```sh
.venv/bin/python -m tachyon.cli assets-register \
  --manifest .local/catalog/manifest.json --rights .local/catalog/rights.json
.venv/bin/python -m tachyon.cli assets-prepare
```

Registration checks the supplied files and reports blockers without conversion.
Preparation only imports/converts sources after the required checks pass. It
preserves the source, source names/hierarchy, solid geometry and source hash;
output GLB is a display mesh, not an editable solid. Native STEP units normalize
to millimetres, the exporter maps Z-up to Y-up, and an explicit one-time generated
GLB root converts millimetres to metres. Actual transformed binary mesh bounds
are checked against native geometry. Version/code fingerprints invalidate old
conversion receipts. Imported parent relationships are not invented joints or
mechanical mounting evidence.

`originKind` and `geometryClass` remain separate. Manufacturer and community
source identity must be reviewed; `test_fixture`, `placeholder` and `conceptual`
geometry cannot pass authentic-VEX or complete-robot acceptance. Tachyon-authored
calibration fixtures are opt-in converter/render tests and display that status.

No CAD redistribution, public geometry hosting or source-part editing is enabled.
Public demonstration imagery also needs an applicable publication basis. See
[CAD source status](../../docs/cad-source-status.md) for investigated sources,
restrictions and the remaining whole-robot qualification work.
