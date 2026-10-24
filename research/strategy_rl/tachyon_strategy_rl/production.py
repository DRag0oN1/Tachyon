"""One bounded production rollout of the saved frozen policy. Never trains.

Run from research/strategy_rl with the isolated .local/rl-venv interpreter.
Only the fixed original experiment and StrategySpec v2 paths are accepted.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
# Share only the standard-library artifact guard; no FastAPI or Torch enters
# the server process through this module. The child never imports the app.
sys.path.insert(0, str(ROOT / "server"))
from tachyon.strategy_runtime import (  # noqa: E402
    COMPETITION_ID, DOMAIN, ENVIRONMENT_ID, EXPERIMENT, FAMILY, MAX_OUTPUT_BYTES,
    SPEC, StrategyRuntimeError, load_artifacts,
)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise StrategyRuntimeError("RL_RUNTIME_OUTPUT_INVALID")


def rollout(saved):
    # Heavy dependencies are loaded only after the saved files pass checksums.
    import torch
    from .environment import ACTION_NAMES, OBSERVATION_NAMES, Capabilities, Env
    from .handoff import FrozenStrategyController

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    spec = saved.spec
    reference = spec["capabilityRequirements"]["referenceCapabilities"]
    capabilities = Capabilities(**reference["allocation"])
    capabilities.validate()
    if capabilities.to_dict() != reference:
        raise StrategyRuntimeError("RL_ENVIRONMENT_MISMATCH")
    controller = FrozenStrategyController(spec, ROOT / EXPERIMENT)
    # Reuse the saved seed identity, with the supported reference allocation.
    # This is a fresh episode, not the representative sequence in the spec.
    seed = next(sequence["episodeSeed"] for sequence in spec["representativeSequences"]
                if sequence["policy"] == "ppo_seed_17")
    env = Env(seed=seed, capabilities=capabilities)
    decisions = []
    before = controller.engine.checkpoint["parameterHash"]
    with torch.inference_mode():
        for _ in range(env.max_steps):
            observation, mask = env.observe(), env.action_mask()
            decision = controller.act(observation, mask)
            decisions.append({"step": env.steps, "observation": observation.tolist(),
                              "actionMask": mask.tolist(), **decision})
            env.step(decision["actionId"])
            if env.done:
                break
    from .ppo import parameter_hash
    after = parameter_hash(controller.engine.model)
    if not env.done or before != after:
        raise StrategyRuntimeError("RL_ENVIRONMENT_MISMATCH")
    summary = env.summary()
    counts = Counter(event["action"] for event in env.trace)
    primary = spec["policy"]["checkpoint"]
    return {
        "id": spec["id"],
        "competition": {**spec["competition"], "name": "V5 Override", "version": "2.1"},
        "strategyFamily": FAMILY, "source": "trained_ppo", "performanceDomain": DOMAIN,
        "spec": spec, "architectures": saved.architectures,
        "rollout": {
            "events": env.trace, "score": summary["score"],
            "pointsByObjective": summary["points_by_objective"],
            "capabilities": summary["capabilities"],
            "actionFrequencies": {name: counts[name] / len(env.trace) for name in ACTION_NAMES},
            "policyParameterHash": before, "simulationOnly": True,
            "decisions": decisions, "summary": summary,
            "evidence": {"runtime": "FrozenStrategyController", "freshNeuralInference": True,
                         "strategySpecId": spec["id"], "competitionId": COMPETITION_ID,
                         "environmentId": ENVIRONMENT_ID, "episodeSeed": seed,
                         "observationNames": list(OBSERVATION_NAMES), "actionNames": list(ACTION_NAMES),
                         "checkpoint": primary,
                         "verifiedCheckpoints": [{key: entry[key] for key in ("name", "path", "sha256", "parameterHash")}
                                                 for entry in saved.checkpoints],
                         "capabilityBasis": "StrategySpec v2 referenceCapabilities; abstract allocation, not CAD",
                         "parameterHashAfter": after, "trainingPerformed": False},
        },
        "limitations": spec["limitations"] + [
            "Live evidence is one seeded abstract episode, not an estimate of real match performance.",
            "The saved proposals are two engineering alternatives for one learned strategy family; neither is generated CAD.",
            "Only the frozen Override v2.1 scenario is supported; uploaded PDFs do not extend this policy.",
        ],
    }


def main(argv=None):
    try:
        parser = _Parser(add_help=False)
        parser.add_argument("--experiment", required=True)
        parser.add_argument("--spec", required=True)
        args = parser.parse_args(argv)
        if (Path(args.experiment) != ROOT / EXPERIMENT or Path(args.spec) != ROOT / SPEC):
            raise StrategyRuntimeError("RL_ARTIFACT_MISMATCH")
        saved = load_artifacts(ROOT)
        result = rollout(saved)
        raw = json.dumps(result, allow_nan=False, separators=(",", ":"))
        if len(raw.encode()) > MAX_OUTPUT_BYTES:
            raise StrategyRuntimeError("RL_RUNTIME_OUTPUT_LIMIT")
    except StrategyRuntimeError as error:
        print(json.dumps({"error": error.public()}))
        return 1
    except (ImportError, OSError):
        print(json.dumps({"error": StrategyRuntimeError("RL_RUNTIME_UNAVAILABLE").public()}))
        return 1
    except Exception:
        # FrozenStrategyController also rejects content, weights and environment
        # mismatches. No exception text or traceback crosses this boundary.
        print(json.dumps({"error": StrategyRuntimeError("RL_ENVIRONMENT_MISMATCH").public()}))
        return 1
    print(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
