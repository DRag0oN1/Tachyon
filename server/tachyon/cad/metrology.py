"""Native measured interfaces for local component registration, without exports."""
from __future__ import annotations

from collections import Counter
import math


def support_bounds_mm(shape, error_mm=.001):
    """Refine a conservative BRep box using six global closest-point solves.

    A point far along each axis approaches the directional support point. If
    the shape's diameter is d and the probe distance is R, the coordinate error
    is bounded by d²/(2(R-d)). Choose R from that bound and widen by error_mm.
    This operates on the source BRep, independently of display tessellation.
    It never fits/scales the source to a mesh. OCCT must return finite global
    closest-point solutions; otherwise preparation remains blocked.
    """
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.gp import gp_Pnt
    from ..errors import TachyonError
    from .native import native_bounds_mm
    low,high=native_bounds_mm(shape)
    center=[(a+b)/2 for a,b in zip(low,high)]
    diameter=math.dist(low,high)
    if not all(math.isfinite(x) for x in (*center,diameter,error_mm)) or error_mm<=0 or diameter<=0:
        raise TachyonError("SOURCE_BOUNDS_UNAVAILABLE", "Source BRep has no bounded geometric envelope")
    distance=max(1e7,diameter+2*diameter**2/error_mm)
    result=[[],[]]
    for axis in range(3):
        for side,sign in ((0,-1),(1,1)):
            point=center.copy();point[axis]+=sign*distance
            probe=BRepBuilderAPI_MakeVertex(gp_Pnt(*point)).Vertex()
            solve=BRepExtrema_DistShapeShape(probe,shape.wrapped)
            if not solve.IsDone() or solve.NbSolution()<1:
                raise TachyonError("SOURCE_BOUNDS_UNAVAILABLE", "Source extremum solve failed; display geometry was not approved")
            coordinates=[solve.PointOnShape2(i).Coord()[axis] for i in range(1,solve.NbSolution()+1)]
            if not all(math.isfinite(x) for x in coordinates):
                raise TachyonError("SOURCE_BOUNDS_UNAVAILABLE", "Source extremum solve returned nonfinite coordinates")
            result[side].append((min(coordinates) if sign<0 else max(coordinates))+sign*error_mm)
    return result


def measure_definition(assembly):
    """Measure the selected local definition, preserving its actual native frame.

    Face-wire centres are interface candidates, not automatic physical-fit or
    hardware qualification. The robot compiler selects and records exact ones.
    """
    shape = assembly.toCompound()
    from .native import native_bounds_mm
    bounds = native_bounds_mm(shape)
    planes, cylinders = [], []
    for face in shape.Faces():
        kind = face.geomType()
        if kind == "PLANE" and face.Area() > 30:
            wires = []
            for wire in face.Wires():
                box = wire.BoundingBox()
                low, high = [box.xmin, box.ymin, box.zmin], [box.xmax, box.ymax, box.zmax]
                # Only source hole-sized candidates are needed for interface
                # lookup; never turn an outer silhouette into a mounting hole.
                if max(b-a for a, b in zip(low, high)) <= 20:
                    wires.append({"bounds": [low, high], "center": [(a+b)/2 for a, b in zip(low, high)]})
            if wires:
                planes.append({"center": list(face.Center().toTuple()), "normal": list(face.normalAt().toTuple()),
                               "area": face.Area(), "wires": wires})
        elif kind == "CYLINDER":
            from OCP.BRepAdaptor import BRepAdaptor_Surface
            cylinder = BRepAdaptor_Surface(face.wrapped).Cylinder()
            point, direction = cylinder.Location(), cylinder.Axis().Direction()
            cylinders.append({"location": [point.X(), point.Y(), point.Z()],
                              "axis": [direction.X(), direction.Y(), direction.Z()], "radius": cylinder.Radius()})
    definitions = Counter()
    def visit(node):
        if node.obj is not None:
            definitions[(node.metadata.get("definitionLabel", ""), node.metadata.get("definitionName", node.name))] += 1
        for child in node.children:
            visit(child)
    visit(assembly)
    return {"name": assembly.metadata.get("definitionName", assembly.name),
            "boundsMm": bounds,
            "solidCount": len(shape.Solids()), "planes": planes, "cylinders": cylinders,
            "sourceDefinitions": [{"definitionLabel": label, "definitionName": name, "quantity": count}
                                  for (label, name), count in sorted(definitions.items())],
            "basis": "Source-native BRep interfaces; millimetres; no physical-fit certification"}
