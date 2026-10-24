"""Pure Strategy Specification -> mechanical architecture contract.

This planner makes real parameter/recipe decisions. It does not claim that its
layout envelopes are resolved VEX solids or validated robot assemblies.
"""
import hashlib
import json
import math


def validate_strategy(spec):
    if spec.get("schemaVersion") != 1 or spec.get("performanceDomain") != "abstract_simulation_only":
        raise ValueError("Strategy must carry the versioned abstract-simulation label")
    if spec.get("evidence", {}).get("origin") != "trained_neural_ppo_rollouts":
        raise ValueError("Architecture input requires trained-policy rollout evidence")
    evidence = spec["evidence"]
    if evidence.get("episodes", 0) < 1 or not evidence.get("checkpointParameterHashes"):
        raise ValueError("Missing policy evidence")
    for digest in evidence["checkpointParameterHashes"]:
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Invalid policy parameter hash")
    requirements = spec["capabilityRequirements"]
    hard, target = requirements["hardMinimums"], requirements["targets"]
    for key in ("reachM", "pinCapacity", "cupCapacity"):
        if key not in hard or not math.isfinite(hard[key]) or hard[key] < 0:
            raise ValueError("Invalid minimum capability")
    if hard["pinCapacity"] != 1 or hard["cupCapacity"] not in (0, 1):
        raise ValueError("The modeled Override scenario permits one Pin and one Cup")
    for key in ("driveSpeedMps", "reachM", "acquisitionSeconds", "placementSeconds"):
        if not math.isfinite(target.get(key, float("nan"))) or target[key] <= 0:
            raise ValueError("Invalid target capability")
    if target["reachM"] < hard["reachM"]:
        raise ValueError("Target reach cannot undershoot the demonstrated minimum")
    joint = requirements.get("jointReferenceCapabilities", {})
    allocation = joint.get("allocation", {})
    if set(allocation) != {"drive", "handling", "lift"} or any(not math.isfinite(v) or v < 0 for v in allocation.values()) or abs(sum(allocation.values())-1) > 1e-8:
        raise ValueError("Capability targets need a jointly feasible sampled budget")
    for target_key, capability_key in (("driveSpeedMps", "drive_speed_m_s"), ("acquisitionSeconds", "acquisition_seconds"), ("placementSeconds", "placement_seconds")):
        if abs(target[target_key]-joint.get(capability_key, float("inf"))) > 1e-8:
            raise ValueError("Targets must retain the demonstrated joint capability sample")
    if target["reachM"] > joint.get("max_reach_m", 0):
        raise ValueError("Requested reach exceeds the supporting capability sample")
    return spec


def architecture_from_strategy(spec):
    spec = validate_strategy(spec)
    hard, target = spec["capabilityRequirements"]["hardMinimums"], spec["capabilityRequirements"]["targets"]
    reach = target["reachM"]
    elevated = reach >= .50
    wheel_diameter = .1016  # Provisional 4-inch wheel role; authentic component unresolved.
    motor_rpm = 200.0  # Design assumption; cartridge/torque qualification remains required.
    ratio = target["driveSpeedMps"] / (math.pi*wheel_diameter*motor_rpm/60)
    width, length = (.36, .42) if elevated else (.32, .36)
    wheelbase = length*.76
    wheels = [[x, wheel_diameter/2, z] for x in (-width/2, width/2)
              for z in (-wheelbase/2, wheelbase/2)]
    scoring = {"type": "elevator_with_pin_gripper" if elevated else "four_bar_pin_gripper",
               "targetReachM": round(reach, 4),
               "minimumModeledReachM": hard["reachM"],
               "cupHandling": "independent_single_cup_cradle" if hard["cupCapacity"] else "not_required_by_this_rollout"}
    geometry = {"classification": "conceptual_layout_envelope_not_CAD", "units": "metres",
                "chassisWidthM": width, "chassisLengthM": length,
                "wheelDiameterM": wheel_diameter, "wheelCentersM": wheels,
                "scoringBaseM": [0., .10, length*.22],
                "intakeMouthWidthM": .15 if elevated else .18,
                "liftTravelM": round(max(0., reach-.10), 4) if elevated else 0.,
                "fourBarLinkLengthM": 0. if elevated else round(max(.15, (reach-.10)/.85), 4)}
    proposal = {"schemaVersion": 1, "strategyId": spec["id"],
                "performanceDomain": "abstract_simulation_only", "generationMethod": "deterministic_realization_of_learned_capability_requirements",
                "drivetrain": {"type": "linked_geared_differential", "driveMotors": 2, "drivenWheels": 4,
                               "targetSpeedMps": target["driveSpeedMps"], "nominalMotorRpmAssumption": motor_rpm,
                               "wheelToMotorSpeedRatio": round(ratio, 4), "qualification": "torque_and_traction_unverified"},
                "intake": {"type": "orientation_preserving_parallel_gripper" if elevated else "guided_opposed_rollers",
                           "targetAcquisitionSeconds": target["acquisitionSeconds"], "pinCapacity": 1},
                "transfer": {"type": "single_pin_elevator_carriage" if elevated else "single_pin_gated_handoff",
                             "independentCupPath": bool(hard["cupCapacity"])},
                "scoring": scoring, "geometryIntent": geometry,
                "requiredComponentRoles": ["structural_channels", "paired_geared_drive", "wheels", "shafts", "bearings", "fasteners",
                                           "pin_gripper", "cup_cradle"] + (["linear_rails", "lift_transmission"] if elevated else ["parallel_links", "pivot_shafts"]),
                "cadStatus": "requires_qualified_components_and_complete_recipe",
                "completeRobot": False, "physicalPerformanceValidated": False,
                "remainingChecks": ["Authentic component resolution and licenses", "Mounts and connection closure",
                                    "Actuator and transmission integration", "Object contact and cup orientation",
                                    "Collision, stability and drivetrain effort", "Full competition legality"]}
    proposal["id"] = "architecture-"+hashlib.sha256(json.dumps(proposal, sort_keys=True).encode()).hexdigest()[:20]
    return proposal


def validate_capability_feedback(data):
    """Future co-design boundary. No automatic retraining or fabricated projection."""
    if data.get("schemaVersion") != 1 or not data.get("robotDesignId"):
        raise ValueError("Feedback requires a version and generated design identity")
    if data.get("source") not in ("estimated", "measured", "abstract_simulation"):
        raise ValueError("Feedback must identify how capabilities were obtained")
    values = data.get("capabilities", {})
    for field in ("driveSpeedMps", "acquisitionSeconds", "placementSeconds", "reachM"):
        if not isinstance(values.get(field), (int, float)) or not math.isfinite(values[field]) or values[field] <= 0:
            raise ValueError("Feedback capabilities need finite positive values in documented units")
    return {**data, "abstractBudgetCalibrationRequired": True, "automaticTrainingLoopImplemented": False}
