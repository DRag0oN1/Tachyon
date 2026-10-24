"""Router contracts and genuine frozen inference, without app/auth/CAD setup.

The main app owns authentication. These tests mount only this router and supply
Settings through app.state, so they also run before main wires the router.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from tachyon.config import Settings
from tachyon import strategy_runtime as runtime
from tachyon.strategy_api import router

ROOT = Path(__file__).resolve().parents[2]


def client_for(root):
    app = FastAPI()
    app.state.settings = Settings(root, root / ".local")
    app.include_router(router)
    return TestClient(app)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def real_generation():
    interpreter = ROOT / ".local/rl-venv/bin/python"
    if not interpreter.is_file():
        pytest.skip("Genuine inference requires the isolated .local/rl-venv environment")
    protected = [ROOT / runtime.SPEC, ROOT / runtime.PROPOSALS,
                 *[ROOT / runtime.EXPERIMENT / f"runs/seed-{seed}/checkpoint.pt" for seed in (17, 29, 43)]]
    before = {path: sha(path) for path in protected}
    with client_for(ROOT) as client:
        response = client.post("/api/strategy/generate", json={"competition_id": runtime.COMPETITION_ID})
    assert response.status_code == 200, response.text
    assert {path: sha(path) for path in protected} == before
    return response.json()


@pytest.fixture
def saved_workspace(tmp_path):
    """Copy just the small runtime inputs; never rewrite the real artifacts."""
    files = [*runtime.MANIFEST_PINS, runtime.SPEC, runtime.PROPOSALS,
             runtime.HANDOFF / "design/design-requirements.json", runtime.HANDOFF / "analysis.json",
             runtime.EXPERIMENT / "strategies/low_quadrant_cycles-strategy.json",
             runtime.EXPERIMENT / "evaluation/evaluation.json",
             *[runtime.EXPERIMENT / f"runs/seed-{seed}/checkpoint.pt" for seed in (17, 29, 43)],
             *[runtime.RESEARCH / "tachyon_strategy_rl" / name for name in (
                 "__init__.py", "environment.py", "scenario.json", "ppo.py", "inference.py", "evaluate.py",
                 "handoff.py", "capability_analysis.py", "production.py")]]
    for relative in files:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    (tmp_path / ".local").mkdir()
    # A normal venv is external to the artifact checks, and its Python itself is
    # normally a symlink. This shares installed dependencies, not saved inputs.
    (tmp_path / ".local/rl-venv").symlink_to(ROOT / ".local/rl-venv", target_is_directory=True)
    return tmp_path


def test_status_is_cheap_and_does_not_launch_a_worker(monkeypatch):
    def no_worker(*args, **kwargs):
        pytest.fail("Status must not launch neural inference")
    monkeypatch.setattr(runtime.subprocess, "Popen", no_worker)
    with client_for(ROOT) as client:
        data = client.get("/api/strategy/status").json()
    assert data == {"available": True, "competitionId": runtime.COMPETITION_ID,
                    "environmentId": runtime.ENVIRONMENT_ID, "policyParameterHash": runtime.PARAMETER_HASH}
    assert "torch" not in sys.modules


def test_generate_preserves_actual_spec_proposals_and_original_trace(real_generation):
    data = real_generation
    assert set(data) == {"id", "competition", "strategyFamily", "source", "performanceDomain",
                         "spec", "architectures", "rollout", "limitations"}
    assert data["spec"] == json.loads((ROOT / runtime.SPEC).read_text())
    assert data["architectures"] == json.loads((ROOT / runtime.PROPOSALS).read_text())
    assert data["id"] == data["spec"]["id"] == runtime.SPEC_ID
    assert all(proposal["strategyId"] == data["id"] for proposal in data["architectures"])
    assert data["source"] == "trained_ppo" and data["performanceDomain"] == runtime.DOMAIN
    rollout = data["rollout"]
    assert rollout["simulationOnly"] is True
    assert rollout["summary"]["done"] is True and rollout["summary"]["elapsed"] == 105.0
    assert rollout["score"] == sum(rollout["pointsByObjective"].values())
    assert rollout["capabilities"] == data["spec"]["capabilityRequirements"]["referenceCapabilities"]
    assert len(rollout["events"]) == len(rollout["decisions"]) > 1
    assert {"action", "action_id", "start_s", "end_s", "from_xy", "to_xy", "success",
            "score_before", "score_after", "reward", "details"} <= set(rollout["events"][0])
    assert rollout["events"][0]["start_s"] == 0
    assert rollout["events"][-1]["end_s"] == 105.0
    assert sum(rollout["actionFrequencies"].values()) == pytest.approx(1)
    evidence = rollout["evidence"]
    assert evidence["runtime"] == "FrozenStrategyController"
    assert evidence["trainingPerformed"] is False and evidence["freshNeuralInference"] is True
    assert evidence["parameterHashAfter"] == rollout["policyParameterHash"] == runtime.PARAMETER_HASH
    assert len(evidence["verifiedCheckpoints"]) == 3
    for event, decision in zip(rollout["events"], rollout["decisions"]):
        assert event["action_id"] == decision["actionId"]
        assert decision["actionMask"][decision["actionId"]] is True
        assert sum(decision["probabilities"]) == pytest.approx(1)
        assert len(decision["observation"]) == len(evidence["observationNames"])
    # The episode uses the reference allocation, so it is not a canned example
    # sequence from the historical mixed-capability dataset.
    assert all(rollout["events"] != sequence["events"] for sequence in data["spec"]["representativeSequences"])
    assert "torch" not in sys.modules


def test_fresh_child_reproduces_neural_decisions_without_changing_saved_weights(real_generation):
    # Two bounded episodes prove deterministic inference, without rerunning the
    # full capability experiment or invoking any training routine.
    with client_for(ROOT) as client:
        response = client.post("/api/strategy/generate", json={"competition_id": runtime.COMPETITION_ID})
    assert response.status_code == 200, response.text
    assert response.json() == real_generation


def test_missing_runtime_and_unsupported_competition_are_explicit(tmp_path):
    with client_for(tmp_path) as client:
        status = client.get("/api/strategy/status").json()
        assert status == {"available": False, "competitionId": runtime.COMPETITION_ID,
                          "environmentId": runtime.ENVIRONMENT_ID, "reason": "RL_RUNTIME_MISSING"}
        response = client.post("/api/strategy/generate", json={"competition_id": runtime.COMPETITION_ID})
        assert response.status_code == 503 and response.json()["code"] == "RL_RUNTIME_MISSING"
        unsupported = client.post("/api/strategy/generate", json={"competition_id": "uploaded-pdf-new-game"})
        assert unsupported.status_code == 422
        assert unsupported.json()["code"] == "RL_UNSUPPORTED_COMPETITION"
        assert str(tmp_path) not in response.text + unsupported.text


@pytest.mark.parametrize("body", [{}, {"competition_id": 2}, {"competition_id": True},
                                  {"competition_id": runtime.COMPETITION_ID, "checkpoint": "other.pt"},
                                  {"competitionId": runtime.COMPETITION_ID}])
def test_request_contract_forbids_coercions_and_arbitrary_paths(body, tmp_path):
    with client_for(tmp_path) as client:
        assert client.post("/api/strategy/generate", json=body).status_code == 422


@pytest.mark.parametrize("relative", [runtime.SPEC, runtime.PROPOSALS,
    runtime.HANDOFF / "manifest.json", runtime.HANDOFF / "design/manifest.json",
    runtime.EXPERIMENT / "runs/seed-17/checkpoint.pt", runtime.EXPERIMENT / "runs/seed-29/checkpoint.pt",
    runtime.EXPERIMENT / "runs/seed-43/checkpoint.pt", runtime.HANDOFF / "analysis.json",
    runtime.RESEARCH / "tachyon_strategy_rl/environment.py",
    runtime.RESEARCH / "tachyon_strategy_rl/handoff.py"])
def test_tampered_artifacts_and_sources_fail_before_inference(saved_workspace, relative, monkeypatch):
    target = saved_workspace / relative
    target.write_bytes(target.read_bytes() + b"\n")
    monkeypatch.setattr(runtime, "_execute", lambda _: pytest.fail("Tampered artifacts must not execute"))
    with client_for(saved_workspace) as client:
        status = client.get("/api/strategy/status").json()
        assert status["available"] is False and status["reason"] == "RL_ARTIFACT_MISMATCH"
        response = client.post("/api/strategy/generate", json={"competition_id": runtime.COMPETITION_ID})
        assert response.status_code == 503 and response.json()["code"] == "RL_ARTIFACT_MISMATCH"
        assert str(target) not in response.text and "Traceback" not in response.text


def test_missing_checkpoint_and_escaping_artifact_symlink_are_unavailable(saved_workspace, tmp_path):
    checkpoint = saved_workspace / runtime.EXPERIMENT / "runs/seed-43/checkpoint.pt"
    checkpoint.unlink()
    assert runtime.status(saved_workspace)["reason"] == "RL_ARTIFACT_MISSING"
    outside = tmp_path.parent / (tmp_path.name + "-outside.pt")
    outside.write_bytes(b"not a trusted artifact")
    checkpoint.symlink_to(outside)
    assert runtime.status(saved_workspace)["reason"] == "RL_ARTIFACT_MISMATCH"


def test_subprocess_timeout_is_bounded_and_sanitized(monkeypatch):
    monkeypatch.setattr(runtime, "TIMEOUT_SECONDS", .001)
    with client_for(ROOT) as client:
        response = client.post("/api/strategy/generate", json={"competition_id": runtime.COMPETITION_ID})
    assert response.status_code == 503
    assert response.json()["code"] == "RL_RUNTIME_TIMEOUT"
    assert str(ROOT) not in response.text and "Traceback" not in response.text


def test_subprocess_output_is_bounded(monkeypatch):
    monkeypatch.setattr(runtime, "MAX_OUTPUT_BYTES", 128)
    with pytest.raises(runtime.StrategyRuntimeError) as error:
        runtime._execute(ROOT)
    assert error.value.code == "RL_RUNTIME_OUTPUT_LIMIT"


def test_subprocess_uses_fixed_argv_cwd_and_does_not_inherit_secrets(monkeypatch, real_generation):
    original = subprocess.Popen
    calls = []
    def observe(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)
    monkeypatch.setenv("OPENAI_API_KEY", "must-never-reach-inference")
    monkeypatch.setenv("PYTHONPATH", "/untrusted/import/path")
    monkeypatch.setattr(runtime.subprocess, "Popen", observe)
    result = runtime._execute(ROOT)
    assert result["id"] == real_generation["id"]
    args, kwargs = calls[0]
    assert args[0] == [str(ROOT / ".local/rl-venv/bin/python"), "-B", "-E", "-s", "-m",
                       "tachyon_strategy_rl.production", "--experiment", str(ROOT / runtime.EXPERIMENT),
                       "--spec", str(ROOT / runtime.SPEC)]
    assert kwargs["shell"] is False and kwargs["cwd"] == ROOT / runtime.RESEARCH
    assert "OPENAI_API_KEY" not in kwargs["env"] and "PYTHONPATH" not in kwargs["env"]
    assert kwargs["stderr"] is subprocess.DEVNULL


@pytest.mark.parametrize("damage", ["extra_root", "wrong_identity", "score", "masked_action", "probability",
                                    "observation", "capabilities", "checkpoint_ref", "spec"])
def test_invalid_worker_evidence_never_becomes_a_success(real_generation, monkeypatch, damage):
    result = deepcopy(real_generation)
    if damage == "extra_root":
        result["secretPath"] = "/private/should-not-be-returned"
    elif damage == "wrong_identity":
        result["id"] = "not-the-spec-id"
    elif damage == "score":
        result["rollout"]["score"] += 10
    elif damage == "masked_action":
        decision = result["rollout"]["decisions"][0]
        decision["actionMask"][decision["actionId"]] = False
    elif damage == "probability":
        result["rollout"]["decisions"][0]["probabilities"][0] = -1
    elif damage == "observation":
        result["rollout"]["decisions"][0]["observation"][0] = 2
    elif damage == "capabilities":
        result["rollout"]["capabilities"]["max_reach_m"] = 100
    elif damage == "checkpoint_ref":
        result["rollout"]["evidence"]["checkpoint"]["parameterHash"] = "0" * 64
    else:
        result["spec"]["id"] = "forged"
    monkeypatch.setattr(runtime, "_execute", lambda _: result)
    with client_for(ROOT) as client:
        response = client.post("/api/strategy/generate", json={"competition_id": runtime.COMPETITION_ID})
    assert response.status_code == 503 and response.json()["code"] == "RL_RUNTIME_OUTPUT_INVALID"
    assert "should-not-be-returned" not in response.text


def test_busy_worker_is_explicit_and_slot_is_retained():
    assert runtime._WORKER_SLOT.acquire(blocking=False)
    try:
        with pytest.raises(runtime.StrategyRuntimeError) as error:
            runtime.generate(ROOT, runtime.COMPETITION_ID)
        assert error.value.code == "RL_RUNTIME_BUSY"
    finally:
        runtime._WORKER_SLOT.release()


def test_worker_rejects_nonfixed_cli_paths_without_exposing_them():
    completed = subprocess.run(
        [str(ROOT / ".local/rl-venv/bin/python"), "-B", "-E", "-s", "-m", "tachyon_strategy_rl.production",
         "--experiment", "/private/secret-experiment", "--spec", str(ROOT / runtime.SPEC)],
        cwd=ROOT / runtime.RESEARCH, capture_output=True, timeout=5, check=False)
    assert completed.returncode == 1 and completed.stderr == b""
    assert json.loads(completed.stdout)["error"]["code"] == "RL_ARTIFACT_MISMATCH"
    assert b"secret-experiment" not in completed.stdout


@pytest.mark.parametrize("raw", [b'{"score": NaN}', b'{"score": 1e9999}', b'{"id": 1, "id": 2}', b'[]\n{}'])
def test_nonfinite_duplicate_and_multidocument_json_are_refused(raw):
    with pytest.raises(ValueError):
        runtime.decode_json(raw)
