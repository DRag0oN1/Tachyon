"""Source-bound measured part data used by the bounded robot recipe compiler.

Native geometry stays in the user's private catalog. This adapter does not
manufacture geometry, infer permissions or replace the existing STEP importer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math

from .. import assemblies as A
from ..errors import TachyonError
from .builder import Part

T = A.RigidTransform
DISPLAY = T.rotation((1., 0., 0.), -math.pi/2)


def frame(point, axis, x_axis):
    """A right-handed frame; source measurements use millimetres/native axes."""
    z, x = tuple(axis), tuple(x_axis)
    if abs(sum(a*b for a, b in zip(x, z))) > 1e-8:
        raise ValueError("Measured datum axes must be perpendicular")
    y = (z[1]*x[2]-z[2]*x[1], z[2]*x[0]-z[0]*x[2], z[0]*x[1]-z[1]*x[0])
    return T(matrix=(*x, 0, *y, 0, *z, 0, *(v/1000 for v in point), 1))


def native_pose(point_mm, x_axis=(1., 0., 0.), y_axis=(0., 1., 0.), z_axis=(0., 0., 1.)):
    return T(matrix=(*x_axis, 0, *y_axis, 0, *z_axis, 0, *(v/1000 for v in point_mm), 1)).compose(DISPLAY.inverse())


@dataclass
class MeasuredPart:
    component_id: str
    definition_label: str
    definition_name: str
    source_sha256: str
    purpose: str
    measurements: dict
    ports: dict[str, A.AttachmentPort] = field(default_factory=dict)
    catalog_fingerprint: str = "0" * 64

    def port(self, identity, point_mm, axis, x_axis, *, kind="mount", basis="hole"):
        point = tuple(point_mm)
        if basis == "hole":
            candidates = [w["center"] for face in self.measurements.get("planes", [])
                          if abs(sum(a*b for a,b in zip(face["normal"],axis))) > 1-1e-6 for w in face["wires"]
                          if max(b-a for a, b in zip(*w["bounds"])) < 15]
            if not any(math.dist(point, p) <= .02 for p in candidates):
                raise TachyonError("UNMEASURED_MOUNT", f"No source hole centre supports {self.component_id}/{identity}")
        elif basis in {"shaft_station", "bore_station"}:
            low, high = self.measurements["boundsMm"]
            if any(p < a-.0001 or p > b+.0001 for p, a, b in zip(point, low, high)):
                raise TachyonError("UNMEASURED_SHAFT_STATION", "Shaft station is outside the measured source body")
            if basis == "bore_station":
                candidates = [w["center"] for face in self.measurements.get("planes", []) for w in face["wires"]
                              if max(b-a for a, b in zip(*w["bounds"])) < 15]
                candidates.extend(c["location"] for c in self.measurements.get("cylinders", [])
                                  if abs(sum(a*b for a,b in zip(c["axis"],axis))) > 1-1e-6)
                def radial_distance(reference):
                    delta = [p-q for p,q in zip(point,reference)]
                    along = sum(a*b for a,b in zip(delta,axis))
                    return math.sqrt(sum((d-along*a)**2 for d,a in zip(delta,axis)))
                if not any(radial_distance(reference) <= .02 for reference in candidates):
                    raise TachyonError("UNMEASURED_BORE", "No measured source opening supports this axial bore station")
        elif basis == "purchased_interface":
            low, high = self.measurements["boundsMm"]
            if any(p < a-.02 or p > b+.02 for p,a,b in zip(point,low,high)):
                raise TachyonError("UNMEASURED_PURCHASED_INTERFACE", "Purchased interface lies outside the source component envelope")
        else:
            raise ValueError("Unknown measurement basis")
        measured = DISPLAY.compose(frame(point, axis, x_axis))
        port = A.AttachmentPort(id=identity, kind=kind, frame=measured,
            evidence=f"Native STEP {self.source_sha256}, definition {self.definition_label} {self.definition_name}; {basis} {point} mm, unchanged geometry")
        existing = self.ports.get(identity)
        if existing is not None and existing != port:
            raise ValueError("A measured port identity cannot change frame")
        self.ports[identity] = port
        return identity

    def part(self):
        return Part(self.component_id, self.source_sha256, self.catalog_fingerprint, self.ports, self.purpose)


class SourcePack:
    def __init__(self, measured_parts):
        self.parts = measured_parts

    def port(self, part, name, point_mm, axis, x_axis, **kwargs):
        return self.parts[part].port(name, point_mm, axis, x_axis, **kwargs)

    def builder_parts(self):
        # Port dictionaries are shared while compiling a recipe; component
        # fingerprints are installed only after the complete port set is known.
        return {key: value.part() for key, value in self.parts.items()}
