"""Pinned frozen-policy artifacts and a bounded, Torch-free server bridge.

The pins identify the public eb1265c handoff and its original ac1aa01 policies.
Neither availability checks nor generation modify research artifacts.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import threading
import time

COMPETITION_ID = "v5-override-v2.1"
ENVIRONMENT_ID = "override_abstract_strategy_v2_cups"
SPEC_ID = "strategy-spec-4c5452f1550499ebcd54cab6"
FAMILY = "low_quadrant_cycles"
DOMAIN = "abstract_simulation_only"
RESEARCH = Path("research/strategy_rl")
EXPERIMENT = RESEARCH / "results/override-ppo-v1"
HANDOFF = RESEARCH / "results/strategy-design-bridge-v1"
SPEC = HANDOFF / "strategy-spec-v2.json"
PROPOSALS = HANDOFF / "design/architecture-proposals.json"
PARAMETER_HASH = "b9d0ff5931f9a5c35b2fb407d5051ee08a698a83ad7cfc8537d1967bd60eb5f1"
MANIFEST_PINS = {
    EXPERIMENT / "manifest.json": "758f9f8e20a552e084f5825fa67dfa5892c1bd06099177929a5421d11811c1f6",
    HANDOFF / "manifest.json": "06168fe3431aa04ddefe3d23263dd132d49b3f589aec7b7f47002ffe1b7e1415",
    HANDOFF / "design/manifest.json": "3470599d6b5e5787ea0413b84a0b6dc56d8efe4f24645f5206d76328b367841b",
}
MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
MAX_OUTPUT_BYTES = 2 * 1024 * 1024
TIMEOUT_SECONDS = 25.0
_WORKER_SLOT = threading.BoundedSemaphore(1)

# Public messages are selected by code. Child stderr, exception strings and
# user-controlled paths never become HTTP error details.
ERRORS = {
    "RL_UNSUPPORTED_COMPETITION": (422, "Frozen strategy inference supports only V5 Override manual v2.1."),
    "RL_RUNTIME_MISSING": (503, "The isolated frozen strategy runtime is not installed."),
    "RL_ARTIFACT_MISSING": (503, "A required saved strategy artifact is missing."),
    "RL_ARTIFACT_MISMATCH": (503, "Saved strategy artifacts do not match the approved frozen handoff."),
    "RL_ENVIRONMENT_MISMATCH": (503, "The strategy environment or inference contract does not match the frozen policy."),
    "RL_RUNTIME_UNAVAILABLE": (503, "The isolated frozen strategy runtime could not execute inference."),
    "RL_RUNTIME_TIMEOUT": (503, "Frozen strategy inference exceeded its execution limit."),
    "RL_RUNTIME_OUTPUT_LIMIT": (503, "Frozen strategy inference exceeded its output limit."),
    "RL_RUNTIME_OUTPUT_INVALID": (503, "Frozen strategy inference returned invalid evidence."),
    "RL_RUNTIME_BUSY": (503, "Frozen strategy inference is already running; retry shortly."),
}


class StrategyRuntimeError(Exception):
    def __init__(self, code: str):
        if code not in ERRORS:
            code = "RL_RUNTIME_UNAVAILABLE"
        self.code = code
        self.status, self.message = ERRORS[code]
        super().__init__(self.message)

    def public(self):
        return {"code": self.code, "message": self.message,
                "retryable": self.code in {"RL_RUNTIME_BUSY", "RL_RUNTIME_TIMEOUT"}}


def _reject_constant(_):
    raise ValueError("Nonfinite JSON")


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Nonfinite JSON")
    return number


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member")
        result[key] = value
    return result


def decode_json(raw):
    return json.loads(raw, parse_constant=_reject_constant, parse_float=_finite_float,
                      object_pairs_hook=_unique_object)


def _fixed_file(root: Path, relative: Path) -> Path:
    path = root / relative
    if not path.resolve().is_relative_to(root):
        raise StrategyRuntimeError("RL_ARTIFACT_MISMATCH")
    if not path.is_file():
        raise StrategyRuntimeError("RL_ARTIFACT_MISSING")
    return path


def _read(root: Path, relative: Path, expected: str | None = None) -> bytes:
    with _fixed_file(root, relative).open("rb") as stream:
        raw = stream.read(MAX_ARTIFACT_BYTES + 1)
    if len(raw) > MAX_ARTIFACT_BYTES or (expected and hashlib.sha256(raw).hexdigest() != expected):
        raise StrategyRuntimeError("RL_ARTIFACT_MISMATCH")
    return raw


def _json_file(root, relative, expected=None):
    return decode_json(_read(root, relative, expected))


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class SavedArtifacts:
    spec: dict
    architectures: list[dict]
    scenario: dict
    checkpoints: list[dict]


def load_artifacts(root: Path) -> SavedArtifacts:
    """Check small public inputs, never load Torch or replay research datasets.

All three checkpoints are only 150 KB each. Checksums are cheap enough for
status, and are checked again in the child immediately before neural loading.
The large historical episode archive is not a runtime dependency.
"""
    root = Path(root).resolve()
    try:
        original, handoff, design = [
            _json_file(root, path, pin) for path, pin in MANIFEST_PINS.items()
        ]
        spec = _json_file(root, SPEC, handoff["files"]["strategy-spec-v2.json"])
        architectures = _json_file(root, PROPOSALS, handoff["files"]["design/architecture-proposals.json"])
        requirements = _json_file(root, HANDOFF / "design/design-requirements.json",
                                  handoff["files"]["design/design-requirements.json"])
        # The design export records a canonical JSON digest, not the file digest.
        identity = {key: value for key, value in spec.items() if key != "id"}
        content_id = "strategy-spec-" + hashlib.sha256(
            json.dumps(identity, sort_keys=True, allow_nan=False).encode()).hexdigest()[:24]
        if (spec["schemaVersion"] != 2 or spec["kind"] != "tachyon.strategy_spec"
                or spec["id"] != SPEC_ID or content_id != SPEC_ID
                or spec["competition"] != {"id": COMPETITION_ID, "environmentId": ENVIRONMENT_ID}
                or spec["strategyFamily"] != FAMILY or spec["performanceDomain"] != DOMAIN
                or spec["policy"]["experimentId"] != "override-ppo-v1"
                or spec["policy"]["sourceCommit"] != "ac1aa01"
                or design["strategySpecSha256"] != canonical_hash(spec)
                or design["strategyId"] != SPEC_ID or design["cadGenerated"] is not False
                or design["completeRobot"] is not False):
            raise StrategyRuntimeError("RL_ARTIFACT_MISMATCH")
        for name in ("architecture-proposals.json", "design-requirements.json"):
            if design["artifacts"][name]["sha256"] != handoff["files"]["design/" + name]:
                raise StrategyRuntimeError("RL_ARTIFACT_MISMATCH")
        if (not isinstance(architectures, list) or len(architectures) != 2
                or [proposal["id"] for proposal in architectures] != design["architectureIDs"]):
            raise StrategyRuntimeError("RL_ARTIFACT_MISMATCH")
        for proposal in [*architectures, requirements]:
            if (proposal["strategyId"] != SPEC_ID or proposal["strategyFamily"] != FAMILY
                    or proposal["source"]["strategySpecSha256"] != canonical_hash(spec)
                    or proposal["performanceDomain"] != DOMAIN):
                raise StrategyRuntimeError("RL_ARTIFACT_MISMATCH")

        # Validate actual saved source references, without running their analyses.
        analysis = _json_file(root, HANDOFF / "analysis.json", handoff["files"]["analysis.json"])
        _read(root, EXPERIMENT / "strategies/low_quadrant_cycles-strategy.json",
              spec["evidence"]["sourceStrategySha256"])
        _read(root, EXPERIMENT / "evaluation/evaluation.json", analysis["sourceEvaluationSha256"])
        if (spec["evidence"]["analysisSha256"] != handoff["files"]["analysis.json"]
                or spec["evidence"]["episodesSha256"] != handoff["files"]["episodes.jsonl.gz"]
                or analysis["checkpoints"] != spec["policy"]["corroboratingCheckpoints"]):
            raise StrategyRuntimeError("RL_ARTIFACT_MISMATCH")
        checkpoints = spec["policy"]["corroboratingCheckpoints"]
        if [entry["path"] for entry in checkpoints] != [f"runs/seed-{seed}/checkpoint.pt" for seed in (17, 29, 43)]:
            raise StrategyRuntimeError("RL_ARTIFACT_MISMATCH")
        for entry in checkpoints:
            if entry["sha256"] != original["files"][entry["path"]]:
                raise StrategyRuntimeError("RL_ARTIFACT_MISMATCH")
            _read(root, EXPERIMENT / entry["path"], entry["sha256"])
        primary = spec["policy"]["checkpoint"]
        if (primary != {key: checkpoints[0][key] for key in ("path", "sha256", "parameterHash")}
                or primary["parameterHash"] != PARAMETER_HASH):
            raise StrategyRuntimeError("RL_ARTIFACT_MISMATCH")
        for name in ("__init__.py", "environment.py", "scenario.json", "ppo.py", "inference.py", "evaluate.py"):
            _read(root, RESEARCH / "tachyon_strategy_rl" / name, original["sourceAtPackaging"][name])
        for name in ("handoff.py", "capability_analysis.py"):
            relative = RESEARCH / "tachyon_strategy_rl" / name
            _read(root, relative, handoff["sourceFiles"][relative.as_posix()])
        scenario = _json_file(root, RESEARCH / "tachyon_strategy_rl/scenario.json")
        if scenario["name"] != ENVIRONMENT_ID:
            raise StrategyRuntimeError("RL_ENVIRONMENT_MISMATCH")
        return SavedArtifacts(spec, architectures, scenario, checkpoints)
    except StrategyRuntimeError:
        raise
    except FileNotFoundError:
        raise StrategyRuntimeError("RL_ARTIFACT_MISSING") from None
    except (OSError, ValueError, TypeError, KeyError, IndexError, RecursionError):
        raise StrategyRuntimeError("RL_ARTIFACT_MISMATCH") from None


def _runtime(root):
    # The venv interpreter can itself be a symlink to the system Python, as in
    # a normal venv. Artifact/source paths above must stay inside the repo.
    venv = root / ".local/rl-venv"
    python = venv / "bin/python"
    if (not python.is_file() or not os.access(python, os.X_OK)
            or not (venv / "pyvenv.cfg").is_file()
            or any(not (venv / "lib/python3.12/site-packages" / name / "__init__.py").is_file()
                   for name in ("torch", "numpy"))):
        raise StrategyRuntimeError("RL_RUNTIME_MISSING")
    _fixed_file(root, RESEARCH / "tachyon_strategy_rl/production.py")
    return python


def status(root: Path):
    result = {"available": False, "competitionId": COMPETITION_ID, "environmentId": ENVIRONMENT_ID}
    try:
        _runtime(Path(root).resolve())
        load_artifacts(root)
    except StrategyRuntimeError as error:
        result["reason"] = error.code
    except (OSError, ValueError, RuntimeError):
        result["reason"] = "RL_RUNTIME_UNAVAILABLE"
    else:
        result.update(available=True, policyParameterHash=PARAMETER_HASH)
    return result


def _execute(root: Path) -> dict:
    python = _runtime(root)
    command = [str(python), "-B", "-E", "-s", "-m", "tachyon_strategy_rl.production",
               "--experiment", str(root / EXPERIMENT), "--spec", str(root / SPEC)]
    environment = {"PATH": os.defpath, "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                   "OPENBLAS_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1"}
    deadline = time.monotonic() + TIMEOUT_SECONDS
    raw = bytearray()
    try:
        with subprocess.Popen(command, cwd=root / RESEARCH, env=environment, shell=False,
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, close_fds=True) as child:
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(child.stdout, selectors.EVENT_READ)
                    while selector.get_map():
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise StrategyRuntimeError("RL_RUNTIME_TIMEOUT")
                        for key, _ in selector.select(timeout=remaining):
                            chunk = os.read(key.fileobj.fileno(), 65536)
                            if not chunk:
                                selector.unregister(key.fileobj)
                                continue
                            raw.extend(chunk)
                            if len(raw) > MAX_OUTPUT_BYTES:
                                raise StrategyRuntimeError("RL_RUNTIME_OUTPUT_LIMIT")
                child.wait(timeout=max(.001, deadline - time.monotonic()))
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait()
    except subprocess.TimeoutExpired:
        raise StrategyRuntimeError("RL_RUNTIME_TIMEOUT") from None
    except OSError:
        raise StrategyRuntimeError("RL_RUNTIME_UNAVAILABLE") from None
    try:
        payload = decode_json(raw)
        if not isinstance(payload, dict):
            raise ValueError()
    except (ValueError, TypeError, RecursionError):
        raise StrategyRuntimeError("RL_RUNTIME_OUTPUT_INVALID") from None
    if child.returncode:
        error = payload.get("error", {})
        code = error.get("code") if isinstance(error, dict) else None
        raise StrategyRuntimeError(code if code in ERRORS else "RL_RUNTIME_UNAVAILABLE")
    return payload


def generate(root: Path, competition_id: str):
    if competition_id != COMPETITION_ID:
        raise StrategyRuntimeError("RL_UNSUPPORTED_COMPETITION")
    if not _WORKER_SLOT.acquire(blocking=False):
        raise StrategyRuntimeError("RL_RUNTIME_BUSY")
    try:
        root = Path(root).resolve()
        _runtime(root)
        saved = load_artifacts(root)
        payload = _execute(root)
        if payload.get("spec") != saved.spec or payload.get("architectures") != saved.architectures:
            raise StrategyRuntimeError("RL_RUNTIME_OUTPUT_INVALID")
        return payload
    except StrategyRuntimeError:
        raise
    except (OSError, ValueError, RuntimeError):
        raise StrategyRuntimeError("RL_RUNTIME_UNAVAILABLE") from None
    finally:
        _WORKER_SLOT.release()
