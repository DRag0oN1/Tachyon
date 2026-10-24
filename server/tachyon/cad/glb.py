"""Read mesh bounds/hierarchy to check actual exported GLB units and frames."""
import json
import struct

import numpy as np

from ..errors import TachyonError


def normalize_mm_to_m(path):
    """Add the one explicit unit transform to a newly exported CadQuery GLB.

    CadQuery 2.8's tested exporter changes axes but retains millimetre numbers.
    Preserve every mesh, native child identity and relative assembly transform.
    This is unit conversion, never a resized SKU or an engineering edit.
    """
    data = path.read_bytes()
    size, kind = struct.unpack_from("<II", data, 12)
    doc = json.loads(data[20:20 + size])
    extras = doc["asset"].setdefault("extras", {})
    if extras.get("tachyonUnitNormalization"):
        raise TachyonError("DOUBLE_UNIT_CONVERSION", "This mesh already has a unit conversion receipt")
    extras["tachyonUnitNormalization"] = "mm_to_m_v1"
    for scene in doc["scenes"]:
        root = len(doc["nodes"])
        doc["nodes"].append({"name": "tachyon_unit_mm_to_m", "scale": [0.001, 0.001, 0.001],
                             "children": scene["nodes"]})
        scene["nodes"] = [root]
    encoded = json.dumps(doc, separators=(",", ":")).encode()
    encoded += b" " * (-len(encoded) % 4)
    body = struct.pack("<II", len(encoded), kind) + encoded + data[20 + size:]
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, len(body) + 12) + body)


def inspect_glb(path):
    data = path.read_bytes()
    if len(data) < 20 or struct.unpack_from("<4sII", data) != (b"glTF", 2, len(data)):
        raise TachyonError("INVALID_MESH", "The converter did not produce a valid binary glTF")
    size, kind = struct.unpack_from("<II", data, 12)
    if kind != 0x4e4f534a:
        raise TachyonError("INVALID_MESH", "GLB has no JSON scene")
    doc = json.loads(data[20:20 + size])
    if any(b.get("uri") for b in doc.get("buffers", [])) or any(i.get("uri") for i in doc.get("images", [])):
        raise TachyonError("EXTERNAL_MESH_RESOURCE", "Local meshes must not reference external files or services")
    nodes = doc.get("nodes", [])
    hierarchy = []
    low, high = np.full(3, np.inf), np.full(3, -np.inf)
    point_count = 0
    binary_offset = 20 + size
    binary_size, binary_kind = struct.unpack_from("<II", data, binary_offset)
    if binary_kind != 0x004e4942 or binary_offset + 8 + binary_size != len(data):
        raise TachyonError("INVALID_MESH", "Local GLB requires one embedded geometry buffer")
    binary = data[binary_offset + 8:]

    def positions(index):
        accessor = doc["accessors"][index]
        view = doc["bufferViews"][accessor["bufferView"]]
        if accessor["componentType"] != 5126 or accessor["type"] != "VEC3" or accessor.get("sparse"):
            raise TachyonError("INVALID_MESH", "Unsupported local mesh position format")
        count = accessor["count"]
        offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        stride = view.get("byteStride", 12)
        if view.get("buffer", 0) != 0 or count < 1 or offset < 0 or stride < 12 or offset + (count-1)*stride + 12 > len(binary):
            raise TachyonError("INVALID_MESH", "Invalid local mesh position buffer")
        return np.ndarray((count, 3), dtype="<f4", buffer=binary, offset=offset, strides=(stride, 4))

    def visit(index, parent, transform, ancestors=frozenset()):
        nonlocal low, high, point_count
        if index in ancestors:
            raise TachyonError("INVALID_MESH", "The mesh hierarchy contains a cycle")
        node = nodes[index]
        if "matrix" in node:
            local = np.array(node["matrix"]).reshape(4, 4, order="F")
        else:
            x, y, z, w = node.get("rotation", [0, 0, 0, 1])
            rot = np.array([[1-2*y*y-2*z*z, 2*x*y-2*w*z, 2*x*z+2*w*y],
                            [2*x*y+2*w*z, 1-2*x*x-2*z*z, 2*y*z-2*w*x],
                            [2*x*z-2*w*y, 2*y*z+2*w*x, 1-2*x*x-2*y*y]])
            local = np.eye(4)
            local[:3, :3] = rot @ np.diag(node.get("scale", [1, 1, 1]))
            local[:3, 3] = node.get("translation", [0, 0, 0])
        world = transform @ local
        hierarchy.append({"id": f"node-{index}", "name": node.get("name", f"Body {index}"),
                          "parentId": parent, "matrix": world.flatten(order="F").tolist(),
                          "hasMesh": "mesh" in node})
        if "mesh" in node:
            for primitive in doc["meshes"][node["mesh"]]["primitives"]:
                vertices = positions(primitive["attributes"]["POSITION"])
                transformed = vertices @ world[:3, :3].T + world[:3, 3]
                if not np.isfinite(transformed).all():
                    raise TachyonError("EMPTY_MESH", "The imported source produced nonfinite display geometry")
                low, high = np.minimum(low, transformed.min(axis=0)), np.maximum(high, transformed.max(axis=0))
                point_count += len(transformed)
        for child in node.get("children", []):
            visit(child, f"node-{index}", world, ancestors | {index})

    for root in doc.get("scenes", [{}])[doc.get("scene", 0)].get("nodes", []):
        visit(root, None, np.eye(4))
    if not point_count:
        raise TachyonError("EMPTY_MESH", "The imported source produced no finite display geometry")
    return {"boundsM": {"min": low.tolist(), "max": high.tolist()},
            "hierarchy": hierarchy, "meshCount": len(doc.get("meshes", []))}
