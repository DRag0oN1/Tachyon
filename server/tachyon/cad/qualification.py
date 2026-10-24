"""Permission-gated native measurement, before catalog bounds are declared.

This emits metadata only. It creates neither a display mesh nor a robot, and
cannot certify manufacturer identity, mates, actuation or task suitability.
"""
from ..config import MAX_SOURCE_BYTES, Settings
from ..errors import TachyonError
from ..models import Operation, RightsManifest
from .catalog import read_json
from .rights import RightsPolicy, sha256_file


def measure_source(settings: Settings, source_path: str, rights_path: str | None = None):
    source = settings.source_path(source_path)
    if source.suffix.lower() not in (".step", ".stp"):
        raise TachyonError("UNSUPPORTED_CAD_FORMAT", "Supply an original STEP file")
    if source.stat().st_size > MAX_SOURCE_BYTES:
        raise TachyonError("CAD_TOO_LARGE", "This local importer supports files up to 256 MiB")
    with source.open("rb") as stream:
        if not stream.read(4096).lstrip().startswith(b"ISO-10303-21;"):
            raise TachyonError("INVALID_STEP", "The supplied source is not an ISO STEP document")
    source_hash = sha256_file(source)
    default_rights = (settings.rights_dir / "rights.json") if settings.rights_dir else (settings.data_dir / "catalog/rights.json")
    permissions = read_json(settings.rights_path(rights_path or str(default_rights)), RightsManifest)
    # Measurement invokes the native converter. A download receipt alone cannot
    # authorize that processing. Fail before importing any CAD implementation.
    RightsPolicy(settings, permissions).require(source_hash, [Operation.acquisition_storage, Operation.conversion])
    try:
        from .native import import_source
        assembly = import_source(source)
        shape = assembly.toCompound()
        solids = shape.Solids()
        if not solids or not shape.isValid():
            raise TachyonError("INVALID_GEOMETRY", "Source must contain valid solid component geometry")
        bounds = shape.BoundingBox()
        nodes = []

        def visit(node, parent_id=None):
            node_id = f"native-{len(nodes)}"
            transform = node.loc.wrapped.Transformation()
            matrix = [transform.Value(row + 1, col + 1) if row < 3 else float(col == 3)
                      for col in range(4) for row in range(4)]
            nodes.append({"id": node_id, "name": node.name, "parentId": parent_id,
                          "matrixMmZUp": matrix, "hasGeometry": node.obj is not None})
            for child in node.children:
                visit(child, node_id)

        visit(assembly)
        if sha256_file(source) != source_hash:
            raise TachyonError("SOURCE_HASH_MISMATCH", "The source changed during native measurement")
        return {"schemaVersion": 1, "kind": "native_source_measurement", "sourceSha256": source_hash,
                "boundsMm": {"min": [bounds.xmin, bounds.ymin, bounds.zmin],
                             "max": [bounds.xmax, bounds.ymax, bounds.zmax]},
                "solidCount": len(solids), "nativeHierarchy": nodes,
                "frame": "Millimetres, native source axes; matrices are local to parent, column-major",
                "geometryIncluded": False, "convertedMesh": False, "completeRobot": False,
                "limitations": ["Measured geometry is not independent dimensional certification",
                                "Names do not certify manufacturer identity or part numbers",
                                "Native hierarchy is not mechanical connection or joint evidence"]}
    except TachyonError:
        raise
    except Exception:
        raise TachyonError("CAD_MEASUREMENT_FAILED", "Native STEP measurement failed; check the source and root selection") from None
