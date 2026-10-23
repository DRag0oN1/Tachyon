"""Independent test decoder: measure real binary vertices, not accessor bounds.

This deliberately does not call tachyon.cad.glb.inspect_glb, so converter tests
can detect incorrect metadata, lost members, and incorrect node transforms.
"""
import json
import struct
from pathlib import Path

import numpy as np


def read_glb(path: Path):
    raw = path.read_bytes()
    assert struct.unpack_from("<4sII", raw) == (b"glTF", 2, len(raw))
    chunks = {}
    offset = 12
    while offset < len(raw):
        size, kind = struct.unpack_from("<II", raw, offset)
        assert size % 4 == 0
        chunks[kind] = raw[offset + 8:offset + 8 + size]
        offset += 8 + size
    assert offset == len(raw)
    document = json.loads(chunks[0x4E4F534A])
    binary = chunks[0x004E4942]
    assert document["asset"]["version"] == "2.0"
    assert not any(item.get("uri") for item in document.get("buffers", []))
    assert not any(item.get("uri") for item in document.get("images", []))

    def accessor_values(index):
        accessor = document["accessors"][index]
        view = document["bufferViews"][accessor["bufferView"]]
        dtype = np.dtype({5121: "u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}[accessor["componentType"]])
        dimensions = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[accessor["type"]]
        offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        stride = view.get("byteStride", dimensions * dtype.itemsize)
        assert offset + (accessor["count"] - 1) * stride + dimensions * dtype.itemsize <= len(binary)
        return np.ndarray((accessor["count"], dimensions), dtype=dtype, buffer=binary,
                          offset=offset, strides=(stride, dtype.itemsize)).copy()

    def local_matrix(node):
        if "matrix" in node:
            return np.asarray(node["matrix"]).reshape((4, 4), order="F")
        # Independent quaternion construction through scalar/vector operations.
        vector = np.asarray(node.get("rotation", [0, 0, 0, 1])[:3], dtype=float)
        scalar = node.get("rotation", [0, 0, 0, 1])[3]
        x, y, z = vector
        cross = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
        rotation = (scalar * scalar - vector @ vector) * np.eye(3) + 2 * np.outer(vector, vector) + 2 * scalar * cross
        result = np.eye(4)
        result[:3, :3] = rotation @ np.diag(node.get("scale", [1, 1, 1]))
        result[:3, 3] = node.get("translation", [0, 0, 0])
        return result

    vertices, hierarchy, triangle_count = [], [], 0

    def visit(index, parent, parent_matrix, ancestors):
        nonlocal triangle_count
        assert index not in ancestors, "GLB scene must not contain cycles"
        node = document["nodes"][index]
        world = parent_matrix @ local_matrix(node)
        hierarchy.append({"id": f"node-{index}", "name": node.get("name"),
                          "parentId": parent, "hasMesh": "mesh" in node, "matrix": world})
        if "mesh" in node:
            for primitive in document["meshes"][node["mesh"]]["primitives"]:
                assert primitive.get("mode", 4) == 4
                position_index = primitive["attributes"]["POSITION"]
                positions = accessor_values(position_index)
                assert positions.shape[1] == 3 and len(positions) > 0
                assert np.isfinite(positions).all()
                metadata = document["accessors"][position_index]
                np.testing.assert_allclose(positions.min(axis=0), metadata["min"], atol=1e-7)
                np.testing.assert_allclose(positions.max(axis=0), metadata["max"], atol=1e-7)
                indices = accessor_values(primitive["indices"]).ravel()
                assert len(indices) >= 3 and len(indices) % 3 == 0
                assert indices.min() >= 0 and indices.max() < len(positions)
                triangle_count += len(indices) // 3
                homogeneous = np.column_stack((positions, np.ones(len(positions))))
                vertices.append((world @ homogeneous.T).T[:, :3])
        for child in node.get("children", []):
            visit(child, f"node-{index}", world, ancestors | {index})

    for root in document["scenes"][document.get("scene", 0)]["nodes"]:
        visit(root, None, np.eye(4), set())
    assert vertices and triangle_count > 0
    points = np.concatenate(vertices)
    assert np.isfinite(points).all()
    return {"document": document, "hierarchy": hierarchy, "triangleCount": triangle_count,
            "boundsM": {"min": points.min(axis=0), "max": points.max(axis=0)}}


def change_glb_document(path, change):
    """Fault injection after a real native export, keeping the binary intact."""
    raw = path.read_bytes()
    size, kind = struct.unpack_from("<II", raw, 12)
    assert kind == 0x4E4F534A
    document = json.loads(raw[20:20 + size])
    change(document)
    encoded = json.dumps(document, separators=(",", ":")).encode()
    encoded += b" " * (-len(encoded) % 4)
    body = struct.pack("<II", len(encoded), kind) + encoded + raw[20 + size:]
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)
