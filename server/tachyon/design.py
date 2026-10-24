"""Standalone StrategySpec v2 -> mechanical requirements -> engineering intents.

Only the standard library is used. No checkpoint is loaded, no policy is run,
and no CAD or app service is imported. Provenance is validated structurally;
checkpoint bytes, rollout claims, hardware and physical performance remain
unverified. The two proposals implement the SAME supplied strategy family.

Public interface:
    design_requirements(spec) -> JSON-compatible dict
    architecture_proposals(spec) -> list of two JSON-compatible dicts
    emit(spec, output) -> manifest dict; output must not already exist

CLI (from the repository's installed app environment):
    .venv/bin/python -m tachyon.design --strategy strategy.json --output NEWDIR

Exports design-requirements.json, architecture-proposals.json and manifest.json.
Opaque evidence/inference records are preserved, not interpreted as proof.
Objective, mechanical-requirement and evidence-reference entries may be named
strings or objects; conditional preferences must be objects. Optional explicit
action/actionId, actions/preferredActions/supports and action probability/count
entries supply binding intents. Unknown semantics remain unresolved instead of
inventing IDs.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any


class StrategySpecError(ValueError):
    """A missing, malformed or inconsistent StrategySpec contract field."""


_FAMILY = "low_quadrant_cycles"
_DOMAIN = "abstract_simulation_only"
_HASH = re.compile(r"[0-9a-fA-F]{64}\Z")
# Broad concept-planning bounds, NOT official competition or hardware limits.
# Lower endpoints are exclusive except for probabilities.
_TARGET_BOUNDS = {
    "driveSpeedMps": (0, 6),
    "turnSeconds": (.01, 30),
    "reachM": (0, 2),
    "acquisitionSeconds": (.01, 120),
    "placementSeconds": (.01, 120),
    "acquisitionSuccessProbability": (0, 1),
    "placementSuccessProbability": (0, 1),
    "cycleSeconds": (.01, 300),
}
_SUBSYSTEMS = (
    "chassis", "drive", "pin_intake", "pin_transfer", "scorer",
    "cup_cradle", "stack_interface",
)
_QUALIFICATION = [
    "Select authentic VEX geometry with source identity, units and permitted asset use.",
    "Qualify real mounting interfaces, fasteners, shaft alignment and retention.",
    "Select and verify motors, transmissions, controls and power under payload.",
    "Verify reach, stow envelope, possession, interference, stability and clearances in CAD.",
    "Physically test Pin orientation, Cup clear-side orientation, stack support and releases.",
    "Measure loaded drive, turn, acquisition, placement, reliability and full cycle performance.",
    "Check current competition constraints; supplied abstract scenario IDs are not rule validation.",
]


def _fail(path: str, message: str) -> None:
    raise StrategySpecError(f"{path}: {message}")


def _object(value: Any, path: str, *, nonempty: bool = True) -> dict:
    if not isinstance(value, dict) or (nonempty and not value):
        _fail(path, "expected a nonempty object" if nonempty else "expected an object")
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(path, "expected a nonempty string")
    return value


def _identifier(value: Any, path: str) -> str:
    value = _string(value, path)
    if any(char.isspace() or ord(char) < 32 for char in value):
        _fail(path, "identity must not contain whitespace or control characters")
    return value


def _hash(value: Any, path: str) -> str:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        _fail(path, "expected a 64-hex SHA-256/parameter hash")
    return value.lower()


def _number(value: Any, path: str, low: float, high: float, *, inclusive: bool = False) -> None:
    if type(value) not in (int, float):
        _fail(path, "expected a finite non-boolean number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or value > high or (value < low if inclusive else value <= low):
        _fail(path, f"expected a finite number in {'[' if inclusive else '('}{low}, {high}]")


def _entries(value: Any, path: str, *, strings_only: bool = False, objects_only: bool = False) -> list:
    if not isinstance(value, list) or not value:
        _fail(path, "expected a nonempty array")
    for index, entry in enumerate(value):
        location = f"{path}[{index}]"
        if strings_only or isinstance(entry, str) and not objects_only:
            _string(entry, location)
        else:
            _object(entry, location)
        if isinstance(entry, dict) and "id" in entry:
            _identifier(entry["id"], location + ".id")
    ids = [entry["id"] for entry in value if isinstance(entry, dict) and "id" in entry]
    if len(ids) != len(set(ids)):
        _fail(path, "duplicate entry identities")
    return value


def _json_tree(value: Any, path: str = "$", depth: int = 0) -> None:
    """Reject NaN anywhere, non-JSON objects and circular/excessively deep input."""
    if depth > 64:
        _fail(path, "JSON nesting exceeds 64 levels or contains a cycle")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                _fail(path, "JSON object keys must be strings")
            _json_tree(child, f"{path}.{key}", depth + 1)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _json_tree(child, f"{path}[{index}]", depth + 1)
    elif type(value) is float:
        if not math.isfinite(value):
            _fail(path, "non-finite JSON number")
    elif value is not None and type(value) not in (str, int, bool):
        _fail(path, "expected a JSON value")


def _identities(value: Any, expected: dict, checkpoint: dict, path: str = "$") -> None:
    """Validate explicit source references and hash shape, not other seed identity.

    Bare parameterHash/sha256 fields (including corroborating checkpoints) need
    valid hashes, but need not match the primary. Only explicitly named primary
    references such as policyParameterHash or checkpointSha256 must match it.
    """
    if isinstance(value, list):
        for index, child in enumerate(value):
            _identities(child, expected, checkpoint, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, child in value.items():
            location = f"{path}.{key}"
            if key in expected:
                actual = _hash(child, location) if key.endswith(("Hash", "Sha256")) else _identifier(child, location)
                if actual != expected[key]:
                    _fail(location, "identity disagrees with the source strategy/policy/scenario")
            elif key.lower().endswith(("sha256", "hash")):
                _hash(child, location)
            elif key.lower().endswith("hashes"):
                if not isinstance(child, list) or not child:
                    _fail(location, "expected a nonempty array of 64-hex hashes")
                for index, item in enumerate(child):
                    _hash(item, f"{location}[{index}]")
            if key == "checkpoint" and isinstance(child, dict):
                for field in ("path", "sha256", "parameterHash"):
                    if field in child:
                        actual = _hash(child[field], location + "." + field) if field != "path" else child[field]
                        if actual != checkpoint[field]:
                            _fail(location + "." + field, "checkpoint identity disagrees with policy.checkpoint")
            if key == "competition" and isinstance(child, dict):
                for field, reference in (("id", "competitionId"), ("environmentId", "environmentId")):
                    if field in child and child[field] != expected[reference]:
                        _fail(location + "." + field, "competition/scenario identity disagrees with source")
            _identities(child, expected, checkpoint, location)


def _validate(spec: Any) -> dict:
    _object(spec, "$")
    _json_tree(spec)
    if type(spec.get("schemaVersion")) is not int or spec["schemaVersion"] != 2:
        _fail("schemaVersion", "expected integer 2")
    for field, expected in (("kind", "tachyon.strategy_spec"), ("performanceDomain", _DOMAIN), ("strategyFamily", _FAMILY)):
        if spec.get(field) != expected:
            _fail(field, f"expected {expected!r}")
    if "learnedStrategyCount" in spec and (type(spec["learnedStrategyCount"]) is not int or spec["learnedStrategyCount"] != 1):
        _fail("learnedStrategyCount", "this contract references exactly one supplied strategy family")
    _identifier(spec.get("id"), "id")
    competition = _object(spec.get("competition"), "competition")
    for field in ("id", "environmentId"):
        _identifier(competition.get(field), "competition." + field)
    policy = _object(spec.get("policy"), "policy")
    _identifier(policy.get("experimentId"), "policy.experimentId")
    checkpoint = _object(policy.get("checkpoint"), "policy.checkpoint")
    _string(checkpoint.get("path"), "policy.checkpoint.path")
    for field in ("sha256", "parameterHash"):
        _hash(checkpoint.get(field), "policy.checkpoint." + field)
    _entries(spec.get("objectives"), "objectives")
    behavior = _object(spec.get("behavior"), "behavior")
    if behavior.get("representation") != "frozen_neural_policy_plus_observed_contexts":
        _fail("behavior.representation", "expected frozen_neural_policy_plus_observed_contexts")
    _entries(behavior.get("conditionalPreferences"), "behavior.conditionalPreferences", objects_only=True)
    _object(behavior.get("inference"), "behavior.inference")
    capability = _object(spec.get("capabilityRequirements"), "capabilityRequirements")
    hard = _object(capability.get("hardMinimums"), "capabilityRequirements.hardMinimums")
    if set(hard) != {"reachM", "pinCapacity", "cupCapacity"}:
        _fail("capabilityRequirements.hardMinimums", "expected only reachM, pinCapacity and cupCapacity")
    _number(hard["reachM"], "capabilityRequirements.hardMinimums.reachM", 0, 2)
    for field in ("pinCapacity", "cupCapacity"):
        if type(hard[field]) is not int or hard[field] != 1:
            _fail("capabilityRequirements.hardMinimums." + field, "expected integer 1 (independent one Pin and one Cup)")
    targets = _object(capability.get("targets"), "capabilityRequirements.targets")
    if set(targets) != set(_TARGET_BOUNDS):
        _fail("capabilityRequirements.targets", "expected exactly " + ", ".join(_TARGET_BOUNDS))
    for field, (low, high) in _TARGET_BOUNDS.items():
        _number(targets[field], "capabilityRequirements.targets." + field, low, high, inclusive=field.endswith("Probability"))
    _string(capability.get("basis"), "capabilityRequirements.basis")
    _entries(capability.get("evidenceRefs"), "capabilityRequirements.evidenceRefs")
    _entries(spec.get("mechanicalRequirements"), "mechanicalRequirements")
    _object(spec.get("evidence"), "evidence")
    _entries(spec.get("limitations"), "limitations", strings_only=True)
    _identities(spec, {
        "strategyId": spec["id"], "strategySpecId": spec["id"], "strategyFamily": _FAMILY,
        "competitionId": competition["id"], "environmentId": competition["environmentId"],
        "scenarioId": competition["environmentId"],
        "policyParameterHash": checkpoint["parameterHash"].lower(),
        "checkpointParameterHash": checkpoint["parameterHash"].lower(),
        "checkpointSha256": checkpoint["sha256"].lower(),
    }, {**checkpoint, "sha256": checkpoint["sha256"].lower(), "parameterHash": checkpoint["parameterHash"].lower()})
    return spec


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _digest(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _source(spec: dict) -> dict:
    return {
        "strategyId": spec["id"], "strategySpecVersion": 2, "strategySpecSha256": _digest(spec),
        "competition": deepcopy(spec["competition"]), "policy": deepcopy(spec["policy"]),
        "behavior": deepcopy(spec["behavior"]), "evidence": deepcopy(spec["evidence"]),
        "limitations": deepcopy(spec["limitations"]),
        "provenanceStatus": "declared_not_independently_verified", "checkpointBytesVerified": False,
    }


def _requirements(spec: dict) -> dict:
    capability = spec["capabilityRequirements"]
    hard, targets = capability["hardMinimums"], capability["targets"]
    rows = [
        {"id": "drive_motion", "subsystemIDs": ["drive"],
         "sourcePaths": ["/capabilityRequirements/targets/driveSpeedMps", "/capabilityRequirements/targets/turnSeconds"],
         "driveSpeedTargetMps": targets["driveSpeedMps"], "turnTimeTargetSeconds": targets["turnSeconds"],
         "acceleration": {"represented": False, "learnedRequirement": None,
                          "reason": "No acceleration is represented in this contract; speed and turn overhead do not establish learned acceleration."}},
        {"id": "independent_possession", "subsystemIDs": ["pin_intake", "pin_transfer", "scorer", "cup_cradle"],
         "sourcePaths": ["/capabilityRequirements/hardMinimums"],
         "pinCapacity": 1, "cupCapacity": 1, "simultaneousIndependentRetention": True,
         "constraint": "One Pin across intake, transfer and scorer combined; one separate Cup slot. No second buffered Pin."},
        {"id": "oriented_pin_acquisition", "subsystemIDs": ["pin_intake", "pin_transfer"],
         "sourcePaths": ["/capabilityRequirements/targets/acquisitionSeconds", "/capabilityRequirements/targets/acquisitionSuccessProbability"],
         "acquisitionTimeTargetSeconds": targets["acquisitionSeconds"],
         "successProbabilityTarget": targets["acquisitionSuccessProbability"],
         "orientationIntent": "Retain the selected Pin scoring-half orientation through pickup and transfer; verify with actual geometry and sensing."},
        {"id": "single_pin_transfer", "subsystemIDs": ["pin_intake", "pin_transfer", "scorer"],
         "sourcePaths": ["/mechanicalRequirements", "/capabilityRequirements/hardMinimums/pinCapacity"],
         "pinCapacityAcrossPath": 1, "handoffIntent": "Interlock acquisition and scoring retention; preserve orientation and prevent double feeding."},
        {"id": "reach_and_stack_interface", "subsystemIDs": ["scorer", "cup_cradle", "stack_interface"],
         "sourcePaths": ["/capabilityRequirements/hardMinimums/reachM", "/mechanicalRequirements"],
         "minimumReachM": hard["reachM"],
         "preferredReachTargetM": targets["reachM"], "toolSizingReachM": max(hard["reachM"], targets["reachM"]),
         "interfacePreparationIntent": "Prepare the next single-Pin stack interface using an independently held Cup; align its clear side and preserve existing scoring halves."},
        {"id": "scorer_cycle", "subsystemIDs": ["drive", "pin_intake", "pin_transfer", "scorer", "cup_cradle", "stack_interface"],
         "sourcePaths": ["/capabilityRequirements/targets"],
         "placementTimeTargetSeconds": targets["placementSeconds"],
         "placementSuccessProbabilityTarget": targets["placementSuccessProbability"],
         "cycleTimeTargetSeconds": targets["cycleSeconds"],
         "performanceStatus": "targets_only_not_achieved_or_physically_verified"},
    ]
    return {
        "schemaVersion": 1, "kind": "tachyon.design_requirements", "strategyId": spec["id"],
        "strategyFamily": _FAMILY, "performanceDomain": _DOMAIN, "source": _source(spec),
        "requirements": rows, "sourceMechanicalRequirements": deepcopy(spec["mechanicalRequirements"]),
        "capabilityConstraints": deepcopy(capability),
        "capabilityConstraintStatus": "Preserve all supplied hard minimums and targets together; joint hardware feasibility and any resource budget require qualification.",
        "completeRobot": False, "cadGenerated": False,
    }


def design_requirements(spec: dict) -> dict:
    """Validate the contract and return traceable mechanical requirements."""
    return _requirements(_validate(spec))


def _roles(text: str) -> list[str]:
    text = re.sub(r"[^a-z0-9]+", "_", text.lower())
    roles = set()
    for words, names in (
        (("drive", "move", "travel", "turn", "midfield", "park"), ("drive",)),
        (("acqui", "intake", "pickup", "pick_up"), ("pin_intake", "pin_transfer")),
        (("transfer", "handoff", "orient", "yellow"), ("pin_intake", "pin_transfer", "scorer")),
        (("place", "scor", "cycle", "quadrant", "reach", "stack", "alliance_pin", "yellow_pin"), ("drive", "scorer", "stack_interface")),
        (("cup", "prepar"), ("cup_cradle", "stack_interface", "scorer")),
    ):
        if any(word in text for word in words):
            roles.update(names)
    # A cup-specific pickup uses its independent cradle, not the Pin intake.
    if "cup" in text:
        roles.difference_update(("pin_intake", "pin_transfer"))
    return [role for role in _SUBSYSTEMS if role in roles]


def _binding_intents(spec: dict) -> dict:
    objectives, actions = [], []

    def binding(value: Any, path: str) -> dict:
        # Only descriptive fields guide a heuristic; source IDs remain opaque.
        description = value if isinstance(value, str) else " ".join(
            str(value.get(key, "")) for key in ("id", "objective", "name", "description", "action", "actionId")
        )
        roles = _roles(description)
        return {"sourcePath": path, "sourceValue": deepcopy(value), "subsystemIDs": roles,
                "status": "semantic_intent_requires_review" if roles else "unresolved_semantics"}

    def visit(value: Any, path: str) -> None:
        if isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}/{index}")
        elif isinstance(value, dict):
            for key, child in value.items():
                location = path + "/" + key.replace("~", "~0").replace("/", "~1")
                if key in ("action", "actionId") and isinstance(child, str):
                    actions.append(binding(child, location))
                elif key in ("actions", "preferredActions", "supports") and isinstance(child, list):
                    actions.extend(binding(entry, f"{location}/{index}") for index, entry in enumerate(child) if isinstance(entry, (str, dict)))
                elif key in ("actionProbabilities", "meanNeuralActionProbabilities", "selectedActionCounts") and isinstance(child, dict):
                    for name in child:
                        entry = binding(name, location + "/" + name.replace("~", "~0").replace("/", "~1"))
                        entry.update(action=name, sourceValue=deepcopy(child[name]))
                        actions.append(entry)
                else:
                    visit(child, location)

    for index, objective in enumerate(spec["objectives"]):
        objectives.append(binding(objective, f"/objectives/{index}"))
    visit(spec["objectives"], "/objectives")
    visit(spec["behavior"]["conditionalPreferences"], "/behavior/conditionalPreferences")
    visit(spec["mechanicalRequirements"], "/mechanicalRequirements")
    return {"kind": "subsystem_binding_intent", "resolution": "semantic_subsystem_ids_only",
            "objectives": objectives, "actions": actions,
            "qualification": "Review semantic mapping, then bind to real qualified assembly instances and joints. No assembly IDs exist here."}


def _r(value: float) -> float:
    return round(value, 8)


def _subsystem(identity: str, mechanism: str, layout: dict, actuation: dict) -> dict:
    return {"id": identity, "mechanismIntent": mechanism, "layoutIntent": layout,
            "actuationIntent": actuation, "qualificationStatus": "unqualified_engineering_intent"}


def _proposal(spec: dict, requirements: dict, alternative: str) -> dict:
    a = alternative == "A"
    hard, targets = spec["capabilityRequirements"]["hardMinimums"], spec["capabilityRequirements"]["targets"]
    reach, speed = max(hard["reachM"], targets["reachM"]), targets["driveSpeedMps"]
    acquisition, placement, cycle = targets["acquisitionSeconds"], targets["placementSeconds"], targets["cycleSeconds"]
    high = reach >= .5
    stroke = max(.08, reach + .04 - .10)
    stages = 2 if high else 1
    wheel = .1016 if a else .08255
    motor_rpm = 200 if speed <= 1.1 else 600
    loaded_fraction = .75
    wheel_rpm = speed * 60 / (math.pi * wheel)
    ratio = wheel_rpm / (motor_rpm * loaded_fraction)
    tight_turn = targets["turnSeconds"] < .5
    length = (.42 if a else .46) + max(0, reach - .5) * .12
    width = (.38 if a else .40) + max(0, reach - .5) * .08
    transport = .14 if a else .08
    transfer_stroke = .10 if a else .12
    transfer_time = acquisition * .25
    move_time = placement * .60
    scorer_speed = stroke / move_time
    link_length = stroke / (stages * .8)
    guide_length = stroke / stages + .10
    scorer = "cascaded_four_bar_gripper" if a and high else "four_bar_gripper" if a else "linear_elevator_parallel_gripper"
    subsystem_rows = [
        _subsystem("chassis", "braced_frame", {"lengthM": _r(length), "widthM": _r(width), "scorerSupportHeightM": _r(.12 if a else guide_length)},
                   {"mode": "passive_structure"}),
        _subsystem("drive", "linked_geared_four_wheel_tank" if a else "chain_linked_six_wheel_drop_center_tank",
                   {"wheelCount": 4 if a else 6, "wheelDiameterM": wheel, "trackWidthM": _r(width - .06),
                    "wheelbaseM": .24 if a and tight_turn else .30 if a else .30 if tight_turn else .36,
                    "centerDropM": 0 if a else .003},
                   {"motorCountIntent": 2 if a else 4, "independentSides": 2,
                    "transmissionIntent": "geared front/rear wheels linked per side" if a else "three wheels linked by chain per side",
                    "driveSpeedTargetMps": speed, "turnTimeTargetSeconds": targets["turnSeconds"],
                    "referenceMotorOutputRpmAssumption": motor_rpm, "loadedSpeedFractionAssumption": loaded_fraction,
                    "requiredWheelRpmIntent": _r(wheel_rpm), "wheelToMotorSpeedRatioIntent": _r(ratio),
                    "ratioConvention": "wheel rpm / motor output rpm; continuous sizing intent, no selected gears or sprockets",
                    "accelerationRequirementRepresented": False}),
        _subsystem("pin_intake", "opposed_rollers_with_orientation_guides" if a else "parallel_jaw_oriented_pin_pickup",
                   {"openingWidthM": .22 if a else .18, "transportStrokeM": transport, "pinSlotsAcrossWholePath": 1},
                   {"transportSpeedTargetMps": _r(transport / (acquisition * .60)),
                    "acquisitionTimeTargetSeconds": acquisition,
                    "acquisitionSuccessProbabilityTarget": targets["acquisitionSuccessProbability"],
                    "selectionIntent": "speed_biased_actuation" if acquisition < 1.5 else "reduction_and_control_biased_actuation",
                    "orientationControlIntent": "preserve selected scoring half; sensor/interlock qualification required"}),
        _subsystem("pin_transfer", "gated_single_pin_handoff" if a else "single_pin_linear_shuttle_with_gripper",
                   {"strokeM": transfer_stroke, "pinCapacityAcrossIntakeTransferScorer": 1},
                   {"handoffTimeBudgetSeconds": _r(transfer_time), "shuttleSpeedTargetMps": _r(transfer_stroke / transfer_time),
                    "interlockIntent": "block a second Pin while scorer or transfer holds the first"}),
        _subsystem("scorer", scorer,
                   {"minimumToolReachM": hard["reachM"], "preferredToolReachM": targets["reachM"],
                    "toolSizingReachM": reach, "toolReachEnvelopeIntentM": _r(reach + .04),
                    "verticalTravelIntentM": _r(stroke), "stageCountIntent": stages,
                    **({"linkLengthIntentM": _r(link_length), "usableVerticalTravelPerLinkFractionAssumption": .8,
                        "angularStrokeRadAssumption": 1.2} if a else
                       {"guideLengthPerStageIntentM": _r(guide_length), "railSeparationM": .16,
                        "carriageWidthM": .20, "liftDrumRadiusMAssumption": .0125})},
                   {"placementTimeTargetSeconds": placement,
                    "placementSuccessProbabilityTarget": targets["placementSuccessProbability"],
                    "motionTimeBudgetSeconds": _r(move_time), "toolVerticalSpeedTargetMps": _r(scorer_speed),
                    "referenceMotorOutputRpmAssumption": 200, "loadedSpeedFractionAssumption": .75,
                    "outputToMotorSpeedRatioIntent": _r((1.2 / move_time if a else scorer_speed / .0125) / (200 * 2 * math.pi / 60 * .75)),
                    "ratioConvention": "linkage input or lift drum angular speed / motor output angular speed",
                    "retentionIntent": "hinged scoring-half gripper" if a else "parallel jaw gripper on guided carriage",
                    "selectionIntent": "speed_biased_transmission" if placement < 1.5 else "holding_torque_biased_transmission"}),
        _subsystem("cup_cradle", "independent_tilting_cup_cradle",
                   {"cupCapacity": 1, "separateFromPinSlot": True, "cradleWidthM": .16,
                    "releaseReachEnvelopeIntentM": _r(reach + .04)},
                   {"retentionAndReleaseIntent": "independent Cup latch and tilt; retain Cup while carrying one Pin",
                    "releaseTimeBudgetSeconds": _r(placement * .20)}),
        _subsystem("stack_interface", "cup_orientation_and_single_pin_stack_alignment",
                   {"alignmentApproachM": .04, "minimumInterfaceReachM": hard["reachM"], "preferredInterfaceReachM": targets["reachM"]},
                   {"preparationIntent": "place Cup clear-side as required before next Pin; verify stack geometry and sensing",
                    "alignmentTimeBudgetSeconds": _r(placement * .20)}),
    ]
    attachment_intents = [
        {"parentSubsystemID": "chassis", "childSubsystemID": "drive", "mountZoneIntent": "left/right frame rails", "jointIntent": "revolute wheel/axle support; linked per side"},
        {"parentSubsystemID": "chassis", "childSubsystemID": "pin_intake", "mountZoneIntent": "front pickup opening", "jointIntent": "roller rotation" if a else "parallel jaw translation"},
        {"parentSubsystemID": "pin_intake", "childSubsystemID": "pin_transfer", "mountZoneIntent": "single Pin pickup-to-carrier corridor", "jointIntent": "actuated gate and handoff" if a else "prismatic shuttle"},
        {"parentSubsystemID": "chassis", "childSubsystemID": "scorer", "mountZoneIntent": "braced scoring support", "jointIntent": "synchronized four-bar revolute linkages" if a else "guided prismatic elevator stages"},
        {"parentSubsystemID": "scorer", "childSubsystemID": "pin_transfer", "mountZoneIntent": "tool pickup interface", "jointIntent": "timed retention handoff"},
        {"parentSubsystemID": "scorer", "childSubsystemID": "cup_cradle", "mountZoneIntent": "separate carrier side bay", "jointIntent": "independent latch and tilt"},
        {"parentSubsystemID": "scorer", "childSubsystemID": "stack_interface", "mountZoneIntent": "tool approach end", "jointIntent": "guided alignment intent"},
    ]
    proposal = {
        "schemaVersion": 1, "kind": "tachyon.architecture_proposal",
        "generatorVersion": 1,
        "alternative": alternative, "strategyId": spec["id"], "strategyFamily": _FAMILY,
        "performanceDomain": _DOMAIN, "source": _source(spec),
        "proposalOrigin": "deterministic_engineering_alternative_for_one_supplied_strategy",
        "newLearnedPoliciesCreated": 0, "newStrategyFamiliesClaimed": 0,
        "mechanicalSignature": [subsystem_rows[index]["mechanismIntent"] for index in (1, 2, 3, 4)],
        "requirements": deepcopy(requirements["requirements"]),
        "sourceMechanicalRequirements": deepcopy(spec["mechanicalRequirements"]),
        "capabilityConstraints": deepcopy(spec["capabilityRequirements"]),
        "subsystems": subsystem_rows, "attachmentAndJointIntents": attachment_intents,
        "bindingIntent": _binding_intents(spec),
        "cycleBudgetIntent": {"cycleTimeTargetSeconds": cycle,
                              "recurringAcquisitions": 2, "recurringPlacements": 2,
                              "recurringPinCupActionSeconds": _r(2 * acquisition + 2 * placement),
                              "remainingTravelFailureAndOtherTimeSeconds": _r(max(0, cycle - 2 * acquisition - 2 * placement)),
                              "requiresOverlapOrTargetRevision": cycle < 2 * acquisition + 2 * placement,
                              "meaning": "Recurring Pin/Cup cycle: acquire Pin and Cup, place both; first Pin may omit Cup. Nominal serial bookkeeping, not achieved physical timing."},
        "engineeringAssumptions": [
            "All dimensions are numeric layout/sizing intents in metres, not authentic part dimensions or actual transforms.",
            "Nominal wheel diameters and motor output RPM are reference sizing assumptions; no catalog part is selected.",
            "Loaded speed fraction 0.75 is assumed, not measured; speed ratios do not prove available torque or turning time.",
            "Acquisition budget: transport 60%, transfer 25%, sensing/latch 15%; placement budget: motion 60%, Cup release 20%, alignment 20%.",
            "A 0.04 m tool-reach margin is an engineering allowance, not a learned or official constraint.",
            "Reach >= 0.5 m selects a two-stage concept without changing the strategy family; stow and competition limits remain unqualified.",
            "Four-bar travel fraction and elevator guide/drum dimensions require kinematic, payload and interference checks.",
        ],
        "qualificationRequired": deepcopy(_QUALIFICATION),
        "qualificationStatus": "requires_authentic_vex_geometry_mounts_actuation_physical_and_cad_qualification",
        "completeRobot": False, "cadGenerated": False, "physicalPerformanceVerified": False,
    }
    proposal["id"] = f"{spec['id']}:architecture-{alternative.lower()}:{_digest(proposal)[:24]}"
    return proposal


def architecture_proposals(spec: dict) -> list[dict]:
    """Return two mechanically distinct, unqualified alternatives for one family."""
    spec = _validate(spec)
    requirements = _requirements(spec)
    return [_proposal(spec, requirements, alternative) for alternative in ("A", "B")]


def emit(spec: dict, output: str | Path) -> dict:
    """Write a new export directory exclusively; never reuse an existing path.

    Validation and JSON serialization finish before creating the directory.
    A manifest is written last, so an interrupted write cannot look complete.
    Checkpoint paths are provenance strings, never opened or executed.
    """
    spec = _validate(spec)
    requirements = _requirements(spec)
    proposals = [_proposal(spec, requirements, alternative) for alternative in ("A", "B")]
    payloads = {"design-requirements.json": _json(requirements), "architecture-proposals.json": _json(proposals)}
    manifest = {
        "schemaVersion": 1, "kind": "tachyon.design_export", "strategyId": spec["id"],
        "strategyFamily": _FAMILY, "performanceDomain": _DOMAIN,
        "strategySpecSha256": _digest(spec), "architectureIDs": [item["id"] for item in proposals],
        "artifacts": {name: {"sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()} for name, body in payloads.items()},
        "completeRobot": False, "cadGenerated": False, "newLearnedPoliciesCreated": 0, "newStrategyFamiliesClaimed": 0,
    }
    payloads["manifest.json"] = _json(manifest)
    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=False)
    for name, body in payloads.items():
        with (destination / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(body)
    return manifest


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("JSON", f"duplicate key {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    _fail("JSON", f"non-finite numeric constant {value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--strategy", required=True, type=Path, help="StrategySpec v2 JSON file (no checkpoint is loaded)")
    parser.add_argument("--output", required=True, type=Path, help="new export directory; existing paths are refused")
    arguments = parser.parse_args(argv)
    try:
        spec = json.loads(arguments.strategy.read_text(encoding="utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        manifest = emit(spec, arguments.output)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.exit(2, f"tachyon.design: error: {exc}\n")
    print(_json(manifest), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
