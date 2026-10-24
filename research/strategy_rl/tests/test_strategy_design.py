"""Synthetic contract cases; these are not trained-policy discovery evidence."""
from copy import deepcopy
import gzip
import json

import pytest

from tachyon_strategy_rl.design import architecture_from_strategy, validate_capability_feedback, validate_strategy
from tachyon_strategy_rl.environment import Capabilities
from tachyon_strategy_rl.strategy import export_strategies


def contract(reach=.35):
    caps = Capabilities(.25, .35, .40).to_dict()
    return {"schemaVersion": 1, "id": "synthetic-contract-case", "performanceDomain": "abstract_simulation_only",
            "evidence": {"origin": "trained_neural_ppo_rollouts", "episodes": 1, "checkpointParameterHashes": ["a"*64]},
            "capabilityRequirements": {"hardMinimums": {"reachM": reach, "pinCapacity": 1, "cupCapacity": 1},
                "jointReferenceCapabilities": caps, "targets": {"reachM": reach, "driveSpeedMps": caps["drive_speed_m_s"],
                    "acquisitionSeconds": caps["acquisition_seconds"], "placementSeconds": caps["placement_seconds"]}}}


def test_learned_requirements_drive_distinct_recipes_and_numerical_geometry_intent():
    low = architecture_from_strategy(contract(.35))
    high = architecture_from_strategy(contract(.62))
    assert low["scoring"]["type"] == "four_bar_pin_gripper"
    assert high["scoring"]["type"] == "elevator_with_pin_gripper"
    assert low["transfer"]["type"] != high["transfer"]["type"]
    assert low["intake"]["type"] != high["intake"]["type"]
    assert low["geometryIntent"] != high["geometryIntent"]
    assert len(low["geometryIntent"]["wheelCentersM"]) == 4
    assert low["drivetrain"]["driveMotors"] == 2
    assert low["completeRobot"] is False
    assert low["cadStatus"] == "requires_qualified_components_and_complete_recipe"


@pytest.mark.parametrize("change", ["performance", "untrained", "illegal_possession", "mixed_budget", "unsupported_reach"])
def test_design_contract_rejects_unqualified_or_impossible_requirements(change):
    spec = contract()
    if change == "performance": spec["performanceDomain"] = "real_match"
    elif change == "untrained": spec["evidence"]["origin"] = "heuristic"
    elif change == "illegal_possession": spec["capabilityRequirements"]["hardMinimums"]["pinCapacity"] = 2
    elif change == "mixed_budget": spec["capabilityRequirements"]["targets"]["driveSpeedMps"] += 1
    else: spec["capabilityRequirements"]["targets"]["reachM"] = 5
    with pytest.raises(ValueError): validate_strategy(spec)


@pytest.mark.parametrize("compressed", [False, True])
def test_empty_or_unreplicated_rollouts_do_not_fabricate_two_architectures(tmp_path, compressed):
    source = tmp_path / "evaluation"; source.mkdir()
    (source / "evaluation.json").write_text(json.dumps({"checkpoints": [{"name": "ppo_seed_1", "parameterHash": "a"*64}]}))
    if compressed:
        (source / "ppo_seed_1.jsonl.gz").write_bytes(gzip.compress(b"", mtime=0))
    else:
        (source / "ppo_seed_1.jsonl").write_text("")
    result = export_strategies(source, tmp_path / "export")
    assert result["supportedFamilies"] == []
    assert result["twoDistinctArchitecturesSupported"] is False
    assert len(result["unsubstantiatedFamilies"]) == 2
    assert not list((tmp_path / "export").glob("*-architecture.json"))


def test_feedback_interface_keeps_future_loop_and_calibration_explicit():
    feedback = {"schemaVersion": 1, "robotDesignId": "candidate-1", "source": "estimated",
                "capabilities": {"driveSpeedMps": 1.2, "acquisitionSeconds": 2, "placementSeconds": 2, "reachM": .6}}
    result = validate_capability_feedback(feedback)
    assert result["abstractBudgetCalibrationRequired"] is True
    assert result["automaticTrainingLoopImplemented"] is False
    feedback["capabilities"]["driveSpeedMps"] = float("nan")
    with pytest.raises(ValueError): validate_capability_feedback(feedback)
