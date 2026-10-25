"""Mounted source V5 control/power hardware for the bounded robot recipe."""
from __future__ import annotations

import math

from .. import assemblies as A
from ..errors import TachyonError
from .source_pack import native_pose

T = A.RigidTransform
X, Y, Z = (1., 0., 0.), (0., 1., 0.), (0., 0., 1.)


def add_electronics(b, pack):
    required = {"brain", "battery", "battery_clip", "standoff"}
    if required - pack.parts.keys():
        raise TachyonError("ROBOT_PARTS_MISSING", "V5 control, power, retention clips and supports are required")
    for alias in required:
        b.parts[alias] = pack.parts[alias].part()
    bottom = pack.port("standoff", "bottom", (0., -11.1125, 0.), Y, X, basis="bore_station")
    top = pack.port("standoff", "top", (0., 11.1125, 0.), Y, X, basis="bore_station")
    bridges = []
    for station, z in (("front", 12.7), ("rear", -25.4)):
        stand_ids = []
        for side, sign in (("right", 1), ("left", -1)):
            parent = pack.port("channel", f"brain-{side}-{station}", (sign*z, -12.7, 13.9684), Z, X)
            stand = f"brain-{side}-{station}-standoff"
            b.attached(stand, "standoff", "chassis", f"{side}-inner-rail", parent, bottom)
            stand_ids.append(stand)
        bridge = f"brain-{station}-mount-rail"
        # The right standoff sets a horizontal plate; the left independently
        # checks its actual hole spacing instead of relying on a parent label.
        bridge_hole = pack.port("short_channel", f"brain-{station}-right-hole", (76.2, 0., 6.35), Y, X)
        world = native_pose((0., 87.0934, z-6.35))
        b.attach_at(bridge, "short_channel", "chassis", stand_ids[0], top, bridge_hole, world, angular_tolerance=math.pi)
        left_hole = pack.port("short_channel", f"brain-{station}-left-hole", (-76.2, 0., 6.35), Y, X)
        mate = b.port(stand_ids[1], top).inverse().compose(b.port(bridge, left_hole))
        b.constraint(f"{bridge}-left-tie", stand_ids[1], top, bridge, left_hole, mate=mate)
        bridges.append(bridge)
    brain = "v5-control-brain"
    parent = pack.port("short_channel", "brain-front-right", (38.1, 1.1684, 6.35), Y, X)
    mount = pack.port("brain", "front-right-mount", (38.1, -15.12608151, 19.05), Y, X)
    b.attached(brain, "brain", "chassis", bridges[0], parent, mount)
    for bridge, native_z in zip(bridges, (19.05, -19.05)):
        for x in (-38.1, 38.1):
            if bridge == bridges[0] and x > 0:
                continue
            port = pack.port("short_channel", f"{bridge}-brain-{x}", (x, 1.1684, 6.35), Y, X)
            child = pack.port("brain", f"brain-{x}-{native_z}", (x, -15.12608151, native_z), Y, X)
            mate = b.port(bridge, port).inverse().compose(b.port(brain, child))
            b.constraint(f"brain-fixing-{bridge}-{x}", bridge, port, brain, child, mate=mate)
    clips = []
    for side, x in (("left", -44.45), ("right", 44.45)):
        clip = f"battery-{side}-clip"
        parent = pack.port("channel", f"{clip}-first", (x, 1.1684, -6.45), Y, X)
        child = pack.port("battery_clip", "mount-slot-rear", (-6.35, -9., 0.), Y, (0., 0., -1.), basis="bore_station")
        world = native_pose((x, 75.0368, -88.9), Z, Y, (-1., 0., 0.))
        b.attach_at(clip, "battery_clip", "chassis", "rear-crossmember", parent, child, world, angular_tolerance=math.pi)
        front = pack.port("channel", f"{clip}-second", (x, 1.1684, 6.25), Y, X)
        slot = pack.port("battery_clip", "mount-slot-front", (6.35, -9., 0.), Y, (0., 0., -1.), basis="bore_station")
        mate = b.port("rear-crossmember", front).inverse().compose(b.port(clip, slot))
        b.constraint(f"{clip}-second-fixing", "rear-crossmember", front, clip, slot, mate=mate)
        clips.append(clip)
    # Native source seating rails are at clip y=0; y=-7 is the recessed
    # fastener pocket, not the battery contact surface.
    seat = pack.port("battery_clip", "battery-retention-seat", (0., 0., 0.), Y, (0., 0., -1.), basis="purchased_interface")
    battery_left = pack.port("battery", "retained-left", (-44.45, -7.75, 0.), Y, X, basis="purchased_interface")
    battery = "v5-power-battery"
    b.attached(battery, "battery", "chassis", clips[0], seat, battery_left)
    battery_right = pack.port("battery", "retained-right", (44.45, -7.75, 0.), Y, X, basis="purchased_interface")
    mate = b.port(clips[1], seat).inverse().compose(b.port(battery, battery_right))
    b.constraint("battery-second-retention-clip", clips[1], seat, battery, battery_right, mate=mate)
    return {"brain": brain, "battery": battery, "batteryClips": clips, "mountRails": bridges,
            "electricalStatus": "Source control/power geometry mounted; wiring harness routing is not generated"}
