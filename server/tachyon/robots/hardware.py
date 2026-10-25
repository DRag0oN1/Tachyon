"""Real source fasteners, shaft adapters and retention for generated recipes."""
from __future__ import annotations

import math

from .. import assemblies as A

T = A.RigidTransform
X, Y, Z = (1., 0., 0.), (0., 1., 0.), (0., 0., 1.)


def fastener(b, pack, name, parent, parent_port, *, bolt="bolt_short", offset_m=-.0011684,
             reverse=False, nut_distances_m=(.0038862,), role=None):
    """A source bolt and individually placed nuts, with explicit shank stations.

    Distances are along the actual bolt shank, measured from its underside.
    The caller selects the plate faces and stack; no invisible fastener is used.
    """
    role = role or next(n["subsystemId"] for n in b.instances if n["id"] == parent)
    for alias in (bolt, "nut"):
        b.parts[alias] = pack.parts[alias].part()
    seat = pack.port(bolt, "under-head", (0., 0., 0.), (0., -1., 0.), X, basis="purchased_interface")
    nut = pack.port("nut", "thread-axis", (0., 0., 0.), Y, X, basis="bore_station")
    flip = T.rotation(X, math.pi) if reverse else T()
    b.attached(name, bolt, role, parent, parent_port, seat, mate=T.translation(0., 0., offset_m).compose(flip))
    ids = [name]
    for index, distance in enumerate(nut_distances_m):
        station = pack.port(bolt, f"thread-{round(distance*1e6)}", (0., -distance*1000, 0.),
                            (0., -1., 0.), X, basis="shaft_station")
        identity = f"{name}-nut-{index+1}"
        b.attached(identity, "nut", role, name, station, nut)
        ids.append(identity)
    return ids


def bearing_fasteners(b, pack, bearing, support, support_port_points, *, support_part="channel",
                      support_axis=Y, support_roll=Z, source_face=-6.35):
    """The shaft bore is never filled with a mounting screw.

    Two real flat-bearing screw holes ±12.7 mm away mount to separate measured
    structure holes; the central bore remains free for the actual drive shaft.
    """
    ids, relationships = [], []
    for index, (position, source_y) in enumerate(zip(support_port_points, (-12.7, 12.7))):
        parent = pack.port(support_part, f"{bearing}-support-{index}", position, support_axis, support_roll)
        child = pack.port("bearing", f"bolt-{source_y}", (source_face, source_y, 0.), X, Y)
        mate = b.port(support, parent).inverse().compose(b.port(bearing, child))
        relation = f"{bearing}-screw-mate-{index}"
        b.constraint(relation, support, parent, bearing, child, mate=mate)
        relationships.append(relation)
        # 6.35 mm bearing body + 1.1684 mm plate + real nut; the 12.7 mm
        # source screw retains useful thread engagement without a long spike.
        ids.extend(fastener(b, pack, f"{bearing}-bolt-{index}", support, parent,
                            bolt="bolt_mid", offset_m=-.0011684, nut_distances_m=(.0090678,)))
    return {"fastenerIds": ids, "relationshipIds": relationships}


def shaft_retention(b, pack, shaft, role, *, stations_mm, reversed_indices=()):
    """Actual 228-2500-086 collars, not the similarly named wing-nut model."""
    b.parts["collar"] = pack.parts["collar"].part()
    clamp = pack.port("collar", "shaft-axis", (0., 0., 0.), Z, X, kind="shaft", basis="bore_station")
    ids = []
    for index, station in enumerate(stations_mm):
        port = pack.port(b.nominal_world[shaft][0], f"retainer-{round(station*1000)}", (0., 0., station),
                         Z, X, kind="shaft", basis="shaft_station")
        identity = f"{shaft}-collar-{index}"
        b.attached(identity, "collar", role, shaft, port, clamp,
                   mate=T.rotation(X, math.pi) if index in reversed_indices else T())
        ids.append(identity)
    return ids


def add_drive_hardware(b, pack, drive_facts):
    """Complete the two-sided source drive's actual supports, hubs and retainers."""
    result = {"mounts": [], "retainers": {}, "adapters": {}, "spacers": {}}
    for record in drive_facts["shaftSupports"]:
        shaft = record["shaft"]
        side, station = shaft.split('-')[:2]
        sign = 1 if side == "right" else -1
        z = {"rear": -88.9, "middle": 0., "front": 88.9}[station]
        for label in ("inner", "outer"):
            bearing = record[label+"Bearing"]
            # Bearing native Y follows the rail; mirroring reverses that order.
            native_direction = -sign if label == "inner" else sign
            points = [(sign*(z+native_direction*y), 0. if label == "inner" else 1.1684, -.1) for y in (-12.7, 12.7)]
            result["mounts"].append(bearing_fasteners(b, pack, bearing, f"{side}-{label}-rail", points))
        centre = 118.65 if station == "middle" else 125.
        outer = 141.47 if station == "middle" else 170.8048
        result["retainers"][shaft] = shaft_retention(b, pack, shaft, "drive",
            stations_mm=(122.-centre, outer-centre), reversed_indices=(1,))
        gear = f"{side}-{station}-gear"
        result["adapters"][gear] = shaft_adapters(b, pack, gear, "gear84", "drive")
        if station != "middle":
            wheel = f"{side}-{station}-wheel"
            result["adapters"][wheel] = shaft_adapters(b, pack, wheel, "omni", "drive", source_axis=Y,
                                                       face_stations_mm=(-6.92, 6.92))
            ids = []
            for alias, position in (("spacer", 136.7917), ("washer", 138.7602), ("washer", 139.5222), ("washer", 140.2842)):
                b.parts[alias] = pack.parts[alias].part()
                axis = Y if alias == "spacer" else Z
                child = pack.port(alias, "shaft-seat", (0., 0., 0.), axis, X, kind="shaft", basis="bore_station")
                port = pack.port("shaft_long", f"{alias}-{round(position*1000)}", (0., 0., position-centre), Z, X,
                                 kind="shaft", basis="shaft_station")
                identity = f"{wheel}-{alias}-{len(ids)}"
                b.attached(identity, alias, "drive", shaft, port, child)
                ids.append(identity)
            result["spacers"][shaft] = ids
    # Two actual threaded motor mounts per side, not a screw through the rotor.
    for side, sign in (("right", 1), ("left", -1)):
        for index, x in enumerate((-12.7, -25.4)):
            parent = pack.port("channel", f"{side}-drive-thread-{index}", (x, 0., -.1), Y, X)
            result["mounts"].append({"fastenerIds": fastener(b, pack, f"{side}-drive-mount-bolt-{index}",
                f"{side}-inner-rail", parent, offset_m=.0011684, reverse=True, nut_distances_m=())})
    return result


def shaft_adapters(b, pack, member, alias, role, *, source_axis=Z, face_stations_mm=(-6.27, 6.27)):
    """Source 276-2250-005 inserts reduce the real purchased hub to its shaft."""
    b.parts["shaft_insert"] = pack.parts["shaft_insert"].part()
    interface = pack.port("shaft_insert", "hub-seat", (0., 0., 0.), Y, X, kind="shaft", basis="purchased_interface")
    ids = []
    for index, station in enumerate(face_stations_mm):
        sign = 1. if station < 0 else -1.
        axis = tuple(sign*v for v in source_axis)
        point = tuple(station*v for v in source_axis)
        parent = pack.port(alias, f"insert-{index}", point, axis, X, kind="shaft", basis="purchased_interface")
        identity = f"{member}-shaft-insert-{index}"
        b.attached(identity, "shaft_insert", role, member, parent, interface)
        ids.append(identity)
    return ids


def add_structural_fasteners(b, pack, four_bar, electronics):
    """Close frame clamps and mount supports using unchanged source fasteners.

    The upright foot uses an adjustable through-bolt/nut standoff. This is
    explicit hardware across the measured gap, not a resized source spacer.
    Strength, vibration resistance and tightening access remain unverified.
    """
    ids=[]
    for cross in ("front", "rear"):
        for side,sign in (("right",1),("left",-1)):
            for track,x in (("outer",127.),("inner",88.9)):
                pp=pack.port("channel",f"{cross}-clamp-{side}-{track}",(sign*(x-12.7),0.,-.1),Y,X)
                ids.extend(fastener(b,pack,f"{cross}-{side}-{track}-frame-bolt",cross+"-crossmember",pp))
    for side,sign in (("right",1),("left",-1)):
        for i,y in enumerate((sign*6.35,-sign*6.35)):
            pp=pack.port("angle",f"{side}-foot-clamp-{i}",(-152.4,y,0.),Z,X)
            ids.extend(fastener(b,pack,f"{side}-upright-standoff-bolt-{i}",side+"-lift-upright",pp,
                bolt="bolt25",offset_m=0.,nut_distances_m=(.0027178,.0111506,.0154178)))
    for station in ("front","rear"):
        for side,sign in (("right",1),("left",-1)):
            z=12.7 if station=="front" else -25.4
            pp=pack.port("channel",f"brain-stand-bolt-{station}-{side}",(sign*z,-12.7,12.8),Z,X)
            ids.extend(fastener(b,pack,f"brain-{station}-{side}-bottom-bolt",side+"-inner-rail",pp,offset_m=0.,nut_distances_m=()))
            pp=pack.port("short_channel",f"brain-stand-top-{station}-{side}",(sign*76.2,1.1684,6.35),Y,X)
            ids.extend(fastener(b,pack,f"brain-{station}-{side}-top-bolt",f"brain-{station}-mount-rail",pp,
                offset_m=0.,reverse=True,nut_distances_m=()))
    for rail in electronics["mountRails"]:
        for x in (-38.1,38.1):
            pp=pack.port("short_channel",f"{rail}-brain-bolt-{x}",(x,0.,6.35),Y,X)
            ids.extend(fastener(b,pack,f"{rail}-brain-bolt-{'left' if x<0 else 'right'}",rail,pp,offset_m=0.,nut_distances_m=()))
    for side,x in (("left",-44.45),("right",44.45)):
        for i,z in enumerate((-6.45,6.25)):
            pp=pack.port("channel",f"battery-clip-bolt-{side}-{i}",(x,0.,z),Y,X)
            ids.extend(fastener(b,pack,f"battery-{side}-clip-bolt-{i}","rear-crossmember",pp,offset_m=0.,nut_distances_m=(.0047178,)))
    # The remaining gripper carrier/tool mounting groups need measured source
    # fastener access qualification. Do not invent an OEM threaded interface.
    return dict(fastenerIds=ids,limitations=["OEM tool mount fastener access and the carrier mount groups remain unqualified"])
