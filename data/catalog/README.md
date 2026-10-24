# Local CAD catalog

The public repository contains schemas/role requirements, not a component library.
Original STEP files belong in `~/Documents/TachyonCAD/step/`; source records,
permission evidence and manifests belong in `~/Documents/TachyonCAD/rights/`.
Both directories remain outside the public repository. Private converted meshes,
receipts and the database remain in ignored `.local/`. None of these examples
grants asset rights. No command downloads CAD or uploads it to a remote service.

`TACHYON_CAD_DIR` and `TACHYON_RIGHTS_DIR` override those external roots.
`TACHYON_DATA_DIR` selects the private cache inside this project. Role-prefixed
paths make the boundaries explicit: `cad:part.step`, `rights:rights.json`,
`data:catalog/manifest.json`. Absolute paths within the corresponding configured
root also work. Unprefixed paths inside JSON retain their legacy meaning relative
to the private data directory. Escaping a root, including through a symlink, is
rejected. The external roots cannot point into public project directories.

## Discover and record originals

Copy a lawfully supplied original `.step` or `.stp` into the external STEP root.
Files supplied directly by the user use the same path as manufacturer downloads;
their names or headers do not automatically establish manufacturer authenticity.

```sh
.venv/bin/python -m tachyon.cli assets-discover
.venv/bin/python -m tachyon.cli assets-source-status
```

Discovery streams source hashes, size and bounded literal STEP observations into
`rights:source-register.json`. It never invokes a CAD reader or generates meshes.
Unknown provenance and permissions remain unverified. Status checks do not write
the register. Missing, changed, unreadable or oversized inputs remain actionable
issues; changing bytes invalidates prior source identity and permissions.

Record known provenance for an actual discovered hash:

```sh
.venv/bin/python -m tachyon.cli assets-record-source \
  --sha256 '<actual discovered SHA-256>' \
  --component-id my_component --name 'Reviewed component identity' \
  --original-url 'https://manufacturer.example/component' \
  --origin-kind manufacturer_cad --sku '<actual SKU>' \
  --provenance 'How this exact original was obtained and identified' \
  --terms-url 'https://manufacturer.example/applicable-terms' \
  --terms 'What applies, remaining restrictions and unresolved operations' \
  --recorded-by '<actual reviewer>'
```

This records an assertion with a date, not a permission grant. Duplicate byte
copies share source provenance. File changes do not inherit old metadata.
In the app, **Components → Review source register** reads owner-authenticated,
redacted metadata separately from renderable components. It exposes no source
path, permission document or geometry. Refresh does not convert a file.

## Qualify, measure, register and prepare

Create `rights:manifest.json` with `schemaVersion: 1` and `components`.
Each component needs `id`, `name`, optional `sku`, `sourceUrl`, `sourcePath`
(for example `cad:part.step`), `sourceSha256`, `originKind`,
`geometryClass`, measured `expectedBoundsMm: {min: [x,y,z], max: [x,y,z]}`,
and optional measured `ports`. Source bounds use the STEP importer’s millimetre
coordinates. Ports are already in the documented browser metre/Y-up frame and
require measurement evidence, unit axes and stable IDs. A label is not source
identity or geometry verification.

Create a separate private `rights:rights.json` with `schemaVersion: 1`
and `records`. Each record binds one `sourceSha256` to `attribution` and an
`operations` map. Registration requires `acquisition_storage`; preparation requires that plus
`conversion`. Rendering a prepared source requires storage and `loopback_display`
or `lan_display` for the actual context. Building new assemblies separately
requires `assembly_placement`. A grant for one operation does not imply another.

Each operation decision carries `status` (`qualified`, `unverified` or `disallowed`),
`rightsholder`, `basis` (`license`, `written_permission` or actual `self_authored`
material), `evidencePath`, `evidenceSha256`, `reviewedBy`, `reviewedOn` and optional
`expiresOn`. Evidence must exist inside the configured rights root (or private
data directory for legacy fixtures) and match its
reviewed hash. These records document a real review; they do not turn an assertion
or Download button into a license. The software checks scope, identity and
currency, not legal validity. Do not create self-authorship records for third-party
VEX geometry. Unresolved operations must remain `unverified`.

Once the actual storage and conversion evidence is qualified, obtain native
measurements without creating a browser mesh:

```sh
.venv/bin/python -m tachyon.cli assets-measure \
  --source cad:part.step --rights rights:rights.json
```

The metadata report contains native millimetre bounds, source names and local
parent transforms. Compare them to known part dimensions before declaring
`expectedBoundsMm` in the manifest. Measurements alone do not certify identity,
mechanical connections or operation. Do not fabricate dimensions to bypass this
review. A missing required grant blocks this command before native import.

Use the CLI after installing the application and reviewing the manifest:

```sh
.venv/bin/python -m tachyon.cli assets-register \
  --manifest rights:manifest.json --rights rights:rights.json
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
