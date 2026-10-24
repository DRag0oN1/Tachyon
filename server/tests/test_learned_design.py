"""SYNTHETIC StrategySpec v2 contract tests, never learned-policy evidence.

Fixtures are authored test data, with deliberately fake checkpoint hashes and
paths. They do not demonstrate training, real rollouts, CAD or robot capability.
The real learned-export integration is a separate CLI verification.
"""

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tachyon.design import StrategySpecError, architecture_proposals, design_requirements, emit


ROOT = Path(__file__).resolve().parents[2]
TARGETS = (
    "driveSpeedMps", "turnSeconds", "reachM", "acquisitionSeconds", "placementSeconds",
    "acquisitionSuccessProbability", "placementSuccessProbability", "cycleSeconds",
)


@pytest.fixture
def synthetic_spec():
    """Minimal SYNTHETIC contract: no optional exporter metadata is required."""
    return {
        "schemaVersion": 2, "kind": "tachyon.strategy_spec", "id": "synthetic-contract-low-cycle",
        "performanceDomain": "abstract_simulation_only",
        "competition": {"id": "synthetic-competition-v2", "environmentId": "synthetic-scenario-v2"},
        "policy": {"experimentId": "synthetic-not-trained", "checkpoint": {
            "path": "SYNTHETIC_NOT_A_REAL_CHECKPOINT.pt", "sha256": "a" * 64, "parameterHash": "b" * 64}},
        "strategyFamily": "low_quadrant_cycles",
        "objectives": [{"objective": "alliance_pin_halves", "description": "Synthetic low quadrant scoring"},
                       {"id": "synthetic-midfield", "objective": "terminal_midfield"}],
        "behavior": {"representation": "frozen_neural_policy_plus_observed_contexts",
                     "conditionalPreferences": [
                         {"when": {"pinCarried": False}, "meanNeuralActionProbabilities": {
                             "acquire_alliance": .7, "move_to_supply0": .3}, "selectedActionCounts": {"acquire_alliance": 7}},
                         {"when": {"cupCarried": True}, "preferredActions": ["place_cup", "place_alliance", "unknown_synthetic_action"]}],
                     "inference": {"runtime": "synthetic_contract_only"}},
        "capabilityRequirements": {
            "hardMinimums": {"reachM": .352, "pinCapacity": 1, "cupCapacity": 1},
            "targets": {"driveSpeedMps": 1.15, "turnSeconds": .575, "reachM": .352,
                        "acquisitionSeconds": 2.0, "placementSeconds": 1.6,
                        "acquisitionSuccessProbability": .868, "placementSuccessProbability": .871, "cycleSeconds": 12.0},
            "basis": "SYNTHETIC scalar targets for contract verification only; not measured or learned",
            "evidenceRefs": ["synthetic-analysis.json#/not-real"]},
        "mechanicalRequirements": [
            {"id": "drive", "supports": ["move_to_supply0"], "requirements": ["speed_target", "turn_time_target"]},
            {"id": "scorer", "supports": ["place_alliance", "place_cup"], "requirements": ["reach_floor", "cup_interface_preparation"]}],
        "evidence": {"origin": "SYNTHETIC_CONTRACT_TEST_NOT_LEARNED_DATA"},
        "limitations": ["Synthetic test contract; not training, simulation, CAD or physical performance evidence"],
    }


def by_id(rows, identity):
    return next(row for row in rows if row["id"] == identity)


def set_field(spec, path, value):
    fields = path.split(".")
    owner = spec
    for field in fields[:-1]:
        owner = owner[field]
    owner[fields[-1]] = value


def run_cli(strategy, output, *python_options):
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, *python_options, "-m", "tachyon.design", "--strategy", str(strategy), "--output", str(output)],
        cwd=ROOT, env=environment, text=True, capture_output=True, timeout=30,
    )


def test_requirements_map_every_target_and_independent_possession(synthetic_spec):
    result = design_requirements(synthetic_spec)
    drive = by_id(result["requirements"], "drive_motion")
    assert drive["driveSpeedTargetMps"] == 1.15
    assert drive["turnTimeTargetSeconds"] == .575
    assert drive["acceleration"]["represented"] is False
    assert drive["acceleration"]["learnedRequirement"] is None
    possession = by_id(result["requirements"], "independent_possession")
    assert (possession["pinCapacity"], possession["cupCapacity"]) == (1, 1)
    assert possession["simultaneousIndependentRetention"] is True
    assert by_id(result["requirements"], "single_pin_transfer")["pinCapacityAcrossPath"] == 1
    acquisition = by_id(result["requirements"], "oriented_pin_acquisition")
    assert acquisition["acquisitionTimeTargetSeconds"] == 2
    assert acquisition["successProbabilityTarget"] == .868
    assert acquisition["orientationIntent"]
    reach = by_id(result["requirements"], "reach_and_stack_interface")
    assert reach["minimumReachM"] == .352
    assert reach["preferredReachTargetM"] == .352
    assert reach["interfacePreparationIntent"]
    scorer = by_id(result["requirements"], "scorer_cycle")
    assert scorer["placementTimeTargetSeconds"] == 1.6
    assert scorer["placementSuccessProbabilityTarget"] == .871
    assert scorer["cycleTimeTargetSeconds"] == 12
    assert result["capabilityConstraints"] == synthetic_spec["capabilityRequirements"]
    assert result["sourceMechanicalRequirements"] == synthetic_spec["mechanicalRequirements"]


def test_two_mechanical_architectures_keep_the_same_policy_and_family(synthetic_spec):
    a, b = architecture_proposals(synthetic_spec)
    assert a["id"] != b["id"]
    assert a["mechanicalSignature"] != b["mechanicalSignature"]
    assert by_id(a["subsystems"], "drive")["layoutIntent"]["wheelCount"] == 4
    assert by_id(b["subsystems"], "drive")["layoutIntent"]["wheelCount"] == 6
    assert "four_bar" in by_id(a["subsystems"], "scorer")["mechanismIntent"]
    assert "linear_elevator" in by_id(b["subsystems"], "scorer")["mechanismIntent"]
    assert "rollers" in by_id(a["subsystems"], "pin_intake")["mechanismIntent"]
    assert "parallel_jaw" in by_id(b["subsystems"], "pin_intake")["mechanismIntent"]
    for proposal in (a, b):
        assert proposal["strategyFamily"] == "low_quadrant_cycles"
        assert proposal["strategyId"] == synthetic_spec["id"]
        assert proposal["source"]["policy"] == synthetic_spec["policy"]
        assert proposal["performanceDomain"] == "abstract_simulation_only"
        assert proposal["newLearnedPoliciesCreated"] == proposal["newStrategyFamiliesClaimed"] == 0
        assert proposal["completeRobot"] is proposal["cadGenerated"] is proposal["physicalPerformanceVerified"] is False
        assert len(proposal["qualificationRequired"]) >= 6
        assert proposal["source"]["checkpointBytesVerified"] is False
        drive = by_id(proposal["subsystems"], "drive")["actuationIntent"]
        assert drive["independentSides"] == 2
        assert drive["accelerationRequirementRepresented"] is False


@pytest.mark.parametrize("hard,preferred", [(.352, .80), (.80, .352), (.32, 1.22), (.5, .5)])
def test_synthetic_high_reach_changes_sizing_without_inventing_a_family(synthetic_spec, hard, preferred):
    low = architecture_proposals(synthetic_spec)
    synthetic_spec["capabilityRequirements"]["hardMinimums"]["reachM"] = hard
    synthetic_spec["capabilityRequirements"]["targets"]["reachM"] = preferred
    requirements = design_requirements(synthetic_spec)
    reach = by_id(requirements["requirements"], "reach_and_stack_interface")
    assert reach["minimumReachM"] == hard
    assert reach["preferredReachTargetM"] == preferred
    assert reach["toolSizingReachM"] == max(hard, preferred)
    high = architecture_proposals(synthetic_spec)
    for before, after in zip(low, high):
        old = by_id(before["subsystems"], "scorer")
        new = by_id(after["subsystems"], "scorer")
        assert new["layoutIntent"]["stageCountIntent"] == 2
        assert new["layoutIntent"] != old["layoutIntent"]
        assert new["layoutIntent"]["toolSizingReachM"] == max(hard, preferred)
        assert after["strategyFamily"] == before["strategyFamily"] == "low_quadrant_cycles"
    assert "cascaded" in by_id(high[0]["subsystems"], "scorer")["mechanismIntent"]


def test_speed_turn_and_handling_time_change_engineering_intents(synthetic_spec):
    before_requirements = design_requirements(synthetic_spec)
    before = architecture_proposals(synthetic_spec)
    synthetic_spec["capabilityRequirements"]["targets"].update(
        driveSpeedMps=2.1, turnSeconds=.3, acquisitionSeconds=1.2, placementSeconds=1.0, cycleSeconds=8.0)
    assert design_requirements(synthetic_spec)["requirements"] != before_requirements["requirements"]
    after = architecture_proposals(synthetic_spec)
    for old, new in zip(before, after):
        old_drive, new_drive = by_id(old["subsystems"], "drive"), by_id(new["subsystems"], "drive")
        assert old_drive["layoutIntent"]["wheelbaseM"] != new_drive["layoutIntent"]["wheelbaseM"]
        assert old_drive["actuationIntent"]["wheelToMotorSpeedRatioIntent"] != new_drive["actuationIntent"]["wheelToMotorSpeedRatioIntent"]
        for identity in ("pin_intake", "pin_transfer", "scorer", "cup_cradle"):
            assert by_id(old["subsystems"], identity)["actuationIntent"] != by_id(new["subsystems"], identity)["actuationIntent"]
        assert old["cycleBudgetIntent"] != new["cycleBudgetIntent"]


def test_drive_sizing_equation_is_an_explicit_unqualified_assumption(synthetic_spec):
    for proposal in architecture_proposals(synthetic_spec):
        drive = by_id(proposal["subsystems"], "drive")
        dimensions, actuation = drive["layoutIntent"], drive["actuationIntent"]
        speed = (math.pi * dimensions["wheelDiameterM"] * actuation["referenceMotorOutputRpmAssumption"] / 60
                 * actuation["loadedSpeedFractionAssumption"] * actuation["wheelToMotorSpeedRatioIntent"])
        assert speed == pytest.approx(1.15)
        assert drive["qualificationStatus"] == "unqualified_engineering_intent"


def test_bindings_use_source_paths_and_only_declared_semantic_subsystems(synthetic_spec):
    for proposal in architecture_proposals(synthetic_spec):
        ids = {subsystem["id"] for subsystem in proposal["subsystems"]}
        bindings = proposal["bindingIntent"]
        assert len(bindings["objectives"]) == 2
        assert bindings["actions"]
        for source in ("meanNeuralActionProbabilities", "selectedActionCounts", "supports"):
            assert any(source in row["sourcePath"] for row in bindings["actions"])
        for binding in bindings["objectives"] + bindings["actions"]:
            assert set(binding["subsystemIDs"]) <= ids
            source_value = synthetic_spec
            for field in binding["sourcePath"].strip("/").split("/"):
                field = field.replace("~1", "/").replace("~0", "~")
                source_value = source_value[int(field)] if isinstance(source_value, list) else source_value[field]
            assert binding["sourceValue"] == source_value
        cup = next(row for row in bindings["actions"] if row["sourceValue"] == "place_cup")
        assert "cup_cradle" in cup["subsystemIDs"]
        unknown = next(row for row in bindings["actions"] if row["sourceValue"] == "unknown_synthetic_action")
        assert unknown["subsystemIDs"] == []
        assert unknown["status"] == "unresolved_semantics"
        for connection in proposal["attachmentAndJointIntents"]:
            assert {connection["parentSubsystemID"], connection["childSubsystemID"]} <= ids
        serialized = json.dumps(proposal)
        for fabricated_field in ('"assemblyId"', '"componentId"', '"partId"', '"transform"', '"meshPath"'):
            assert fabricated_field not in serialized


@pytest.mark.parametrize("path,value", [
    ("schemaVersion", 1), ("schemaVersion", 2.0), ("schemaVersion", True),
    ("kind", "wrong"), ("id", ""), ("id", "space in id"),
    ("performanceDomain", "physical_robot"), ("strategyFamily", "elevated_quadrant_cycles"),
    ("competition", []), ("competition.id", None), ("competition.environmentId", ""),
    ("policy", []), ("policy.experimentId", False), ("policy.checkpoint", "missing"),
    ("policy.checkpoint.path", " "), ("policy.checkpoint.sha256", "z" * 64),
    ("policy.checkpoint.parameterHash", "b" * 63), ("policy.checkpoint.sha256", True),
    ("objectives", []), ("objectives", [False]), ("objectives", "objective"),
    ("behavior", []), ("behavior.representation", "fixed_action_script"),
    ("behavior.conditionalPreferences", ["unstated text"]), ("behavior.inference", []),
    ("mechanicalRequirements", {}), ("mechanicalRequirements", [0]),
    ("evidence", []), ("limitations", []), ("limitations", [False]),
    ("capabilityRequirements.hardMinimums.pinCapacity", 2), ("capabilityRequirements.hardMinimums.pinCapacity", True),
    ("capabilityRequirements.hardMinimums.cupCapacity", 0), ("capabilityRequirements.hardMinimums.cupCapacity", 1.0),
    ("capabilityRequirements.hardMinimums.reachM", True), ("capabilityRequirements.hardMinimums.reachM", -1),
    ("capabilityRequirements.hardMinimums.reachM", 4), ("capabilityRequirements.basis", ""),
    ("capabilityRequirements.evidenceRefs", []), ("learnedStrategyCount", 2), ("learnedStrategyCount", True),
])
def test_malformed_contract_rejected_by_both_interfaces(synthetic_spec, path, value):
    set_field(synthetic_spec, path, value)
    for interface in (design_requirements, architecture_proposals):
        with pytest.raises(StrategySpecError):
            interface(synthetic_spec)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("value", [True, False, float("nan"), float("inf"), -float("inf"), "1.0", None, -0.1])
def test_every_numeric_target_rejects_booleans_nonfinite_and_wrong_types(synthetic_spec, target, value):
    synthetic_spec["capabilityRequirements"]["targets"][target] = value
    with pytest.raises(StrategySpecError):
        architecture_proposals(synthetic_spec)


@pytest.mark.parametrize("target,value", [
    ("driveSpeedMps", 0), ("driveSpeedMps", 7), ("turnSeconds", 40),
    ("acquisitionSeconds", 0), ("acquisitionSeconds", 1e-300), ("placementSeconds", 121),
    ("cycleSeconds", 301), ("reachM", 0), ("reachM", 2.1),
    ("acquisitionSuccessProbability", 1.001), ("placementSuccessProbability", -0.001),
])
def test_bounds_are_planning_limits_not_hardware_certification(synthetic_spec, target, value):
    synthetic_spec["capabilityRequirements"]["targets"][target] = value
    with pytest.raises(StrategySpecError):
        design_requirements(synthetic_spec)


@pytest.mark.parametrize("probability", [0, 1])
def test_probability_endpoints_accepted_as_targets(synthetic_spec, probability):
    for key in ("acquisitionSuccessProbability", "placementSuccessProbability"):
        synthetic_spec["capabilityRequirements"]["targets"][key] = probability
    assert len(architecture_proposals(synthetic_spec)) == 2


@pytest.mark.parametrize("section", ["competition", "policy", "objectives", "behavior", "capabilityRequirements", "mechanicalRequirements", "evidence", "limitations"])
def test_required_sections_cannot_be_omitted(synthetic_spec, section):
    del synthetic_spec[section]
    with pytest.raises(StrategySpecError):
        design_requirements(synthetic_spec)


@pytest.mark.parametrize("target", TARGETS)
def test_all_target_fields_are_required(synthetic_spec, target):
    del synthetic_spec["capabilityRequirements"]["targets"][target]
    with pytest.raises(StrategySpecError):
        design_requirements(synthetic_spec)


def test_acceleration_cannot_sneak_into_numeric_target_contract(synthetic_spec):
    synthetic_spec["capabilityRequirements"]["targets"]["accelerationMps2"] = 2
    with pytest.raises(StrategySpecError):
        architecture_proposals(synthetic_spec)


@pytest.mark.parametrize("evidence", [
    {"strategyId": "another-strategy"}, {"environmentId": "another-scenario"},
    {"competitionId": "another-competition"}, {"policyParameterHash": "c" * 64},
    {"checkpointSha256": "d" * 64}, {"analysisSha256": "not-a-hash"},
    {"sourceStrategyParameterHashes": ["bad"]},
    {"checkpoint": {"path": "different.pt"}},
    {"competition": {"id": "another-competition"}},
])
def test_repeated_provenance_cannot_disagree(synthetic_spec, evidence):
    synthetic_spec["evidence"].update(evidence)
    with pytest.raises(StrategySpecError):
        architecture_proposals(synthetic_spec)


def test_exporter_extensions_and_other_corroborating_checkpoints_are_accepted(synthetic_spec):
    synthetic_spec["policy"]["corroboratingCheckpoints"] = [
        {"name": "synthetic-another-seed", "path": "SYNTHETIC_OTHER.pt", "sha256": "c" * 64, "parameterHash": "d" * 64}]
    synthetic_spec["evidence"].update(analysisExperimentId="different-analysis-id", sourceStrategyParameterHashes=["b" * 64, "d" * 64])
    synthetic_spec["evidence"]["corroboration"] = {"experimentId": "another-synthetic-experiment", "parameterHash": "e" * 64}
    synthetic_spec["capabilityRequirements"]["acceleration"] = {"status": "not_identified"}
    synthetic_spec["learnedStrategyCount"] = 1
    proposals = architecture_proposals(synthetic_spec)
    assert len(proposals) == 2
    assert proposals[0]["source"]["policy"]["corroboratingCheckpoints"] == synthetic_spec["policy"]["corroboratingCheckpoints"]


def test_nested_nan_and_duplicate_objective_identity_rejected(synthetic_spec):
    synthetic_spec["evidence"]["nested"] = {"value": float("nan")}
    with pytest.raises(StrategySpecError):
        design_requirements(synthetic_spec)
    del synthetic_spec["evidence"]["nested"]
    synthetic_spec["objectives"] = [{"id": "duplicate"}, {"id": "duplicate"}]
    with pytest.raises(StrategySpecError):
        design_requirements(synthetic_spec)


def test_outputs_are_deterministic_independent_and_do_not_mutate_input(synthetic_spec):
    original = deepcopy(synthetic_spec)
    first = architecture_proposals(synthetic_spec)
    assert first == architecture_proposals(synthetic_spec)
    assert synthetic_spec == original
    first[0]["source"]["policy"]["checkpoint"]["path"] = "mutated"
    first[0]["requirements"][0]["subsystemIDs"].clear()
    assert first[1]["source"]["policy"] == original["policy"]
    assert first[1]["requirements"][0]["subsystemIDs"] == ["drive"]
    assert synthetic_spec == original


def test_emit_new_directory_hashes_exact_bytes_and_refuses_any_existing_path(synthetic_spec, tmp_path):
    output = tmp_path / "new-design"
    manifest = emit(synthetic_spec, output)
    assert manifest == json.loads((output / "manifest.json").read_text())
    for name, metadata in manifest["artifacts"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == metadata["sha256"]
    assert json.loads((output / "architecture-proposals.json").read_text()) == architecture_proposals(synthetic_spec)
    saved = {path.name: path.read_bytes() for path in output.iterdir()}
    with pytest.raises(FileExistsError):
        emit(synthetic_spec, output)
    assert saved == {path.name: path.read_bytes() for path in output.iterdir()}
    empty = tmp_path / "existing-empty"
    empty.mkdir()
    file = tmp_path / "existing-file"
    file.write_text("keep")
    link = tmp_path / "existing-symlink"
    link.symlink_to(tmp_path / "missing-destination", target_is_directory=True)
    for path in (empty, file, link):
        with pytest.raises(FileExistsError):
            emit(synthetic_spec, path)
    assert file.read_text() == "keep"
    assert link.is_symlink()


def test_invalid_emit_creates_no_directory(synthetic_spec, tmp_path):
    del synthetic_spec["policy"]
    output = tmp_path / "missing-parent" / "new-design"
    with pytest.raises(StrategySpecError):
        emit(synthetic_spec, output)
    assert not output.parent.exists()


def test_real_module_cli_in_app_venv_has_no_ml_cad_or_app_imports(synthetic_spec, tmp_path):
    strategy = tmp_path / "synthetic-strategy.json"
    strategy.write_text(json.dumps(synthetic_spec))
    original = strategy.read_bytes()
    output = tmp_path / "new-design"
    completed = run_cli(strategy, output, "-X", "importtime")
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["kind"] == "tachyon.design_export"
    imported = [line.rsplit("|", 1)[-1].strip() for line in completed.stderr.splitlines() if line.startswith("import time:")]
    forbidden = ("torch", "numpy", "tachyon_strategy_rl", "research", "cadquery", "OCP", "tachyon.app", "tachyon.cad", "fastapi", "uvicorn")
    assert not [name for name in imported if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden)]
    assert strategy.read_bytes() == original
    repeat = run_cli(strategy, output)
    assert repeat.returncode == 2
    assert "error:" in repeat.stderr
    assert "Traceback" not in repeat.stderr


def test_import_guard_prevents_even_attempted_ml_app_or_cad_imports():
    # A fresh interpreter also catches attempted imports that an import-time log
    # could miss if caught and suppressed inside the implementation.
    script = """
import sys
class Guard:
    def find_spec(self, fullname, path=None, target=None):
        forbidden = ('torch', 'numpy', 'tachyon_strategy_rl', 'research', 'cadquery', 'OCP', 'tachyon.app', 'tachyon.cad', 'fastapi')
        if any(fullname == name or fullname.startswith(name + '.') for name in forbidden):
            raise AssertionError('Forbidden import attempted: ' + fullname)
sys.meta_path.insert(0, Guard())
import tachyon.design
assert callable(tachyon.design.emit)
"""
    completed = subprocess.run([sys.executable, "-c", script], cwd=ROOT, text=True, capture_output=True, timeout=30)
    assert completed.returncode == 0, completed.stderr


@pytest.mark.parametrize("contents", [
    '{"schemaVersion":2,"schemaVersion":2}', '{"schemaVersion":NaN}',
    '{"schemaVersion":Infinity}', '{"schemaVersion":-Infinity}', '{"schemaVersion":', '[]',
])
def test_cli_rejects_bad_json_and_constants_without_output(contents, tmp_path):
    strategy = tmp_path / "bad.json"
    strategy.write_text(contents)
    output = tmp_path / "must-not-exist"
    completed = run_cli(strategy, output)
    assert completed.returncode == 2
    assert "error:" in completed.stderr
    assert "Traceback" not in completed.stderr
    assert not output.exists()
