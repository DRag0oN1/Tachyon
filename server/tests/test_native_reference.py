"""Actual native XCAF occurrence regression, using original non-VEX geometry.

The STEP writer can resolve a top-level reference during serialization. Inject
its valid native document at the importer boundary instead; exercise real
CadQuery document import and BReps against independently calculated matrices.
This is not a complete robot, a file-import demo, or manufacturer CAD evidence.
"""
from itertools import product

import numpy as np


def test_native_root_reference_keeps_hierarchy_and_world_placements(monkeypatch):
    import cadquery as cq
    from cadquery.occ_impl.assembly import toCAF
    from cadquery.occ_impl.importers.assembly import _importDoc
    from OCP.TDF import TDF_LabelSequence
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    from tachyon.cad.native import _load_source_document

    def location(translation, axis, degrees):
        return cq.Location(cq.Vector(*translation), cq.Vector(*axis), degrees)

    def matrix(translation, axis, degrees):
        x, y, z = axis
        cross = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
        angle = np.deg2rad(degrees)
        result = np.eye(4)
        result[:3, :3] = (np.cos(angle)*np.eye(3) + (1-np.cos(angle))*np.outer(axis, axis) + np.sin(angle)*cross)
        result[:3, 3] = translation
        return result

    outer = ((100, -40, 25), (0, 0, 1), 37)
    group_pose = ((13, 9, -4), (1, 0, 0), 90)
    a_pose = ((3, 5, 7), (0, 0, 1), -21)
    b_pose = ((-9, 4, -2), (0, 1, 0), 29)
    source = cq.Assembly(name="fixture_definition", loc=location(*outer))
    source.add(cq.Workplane().box(4, 6, 8, centered=False), name="fixture_A", loc=location(*a_pose))
    group = cq.Assembly(name="fixture_group")
    group.add(cq.Workplane().box(2, 3, 5, centered=False), name="fixture_B", loc=location(*b_pose))
    source.add(group, loc=location(*group_pose))
    _, document = toCAF(source, True)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(document.Main())
    roots = TDF_LabelSequence()
    tool.GetFreeShapes(roots)
    assert roots.Length() == 1 and tool.IsReference_s(roots.Value(1))

    def load_same_native_document(path, **kwargs):
        assert kwargs == {"importType": "STEP", "unit": "MM"}
        loaded = cq.Assembly()
        _importDoc(document, loaded)
        return loaded

    monkeypatch.setattr(cq.Assembly, "load", load_same_native_document)
    imported = _load_source_document("native-document-regression.step", document)
    expected = {"fixture_A": matrix(*outer) @ matrix(*a_pose),
                "fixture_B": matrix(*outer) @ matrix(*group_pose) @ matrix(*b_pose)}
    points = []
    for name, dimensions in (("fixture_A", (4, 6, 8)), ("fixture_B", (2, 3, 5))):
        for corner in product(*[(0, dimension) for dimension in dimensions]):
            points.append((expected[name] @ [*corner, 1])[:3])
    bb = imported.toCompound().BoundingBox()
    np.testing.assert_allclose([bb.xmin, bb.ymin, bb.zmin], np.min(points, axis=0), atol=1e-7)
    np.testing.assert_allclose([bb.xmax, bb.ymax, bb.zmax], np.max(points, axis=0), atol=1e-7)
    assert len(imported.toCompound().Solids()) == 2
    seen = set()
    for _, path, pose, _ in imported:
        name = path.rsplit("/", 1)[-1]
        if name in expected:
            transform = pose.wrapped.Transformation()
            actual = np.eye(4)
            actual[:3, :4] = [[transform.Value(i, j) for j in range(1, 5)] for i in range(1, 4)]
            np.testing.assert_allclose(actual, expected[name], atol=1e-10)
            seen.add(name)
    assert seen == set(expected)
