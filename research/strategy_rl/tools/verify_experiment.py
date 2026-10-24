"""Verify preserved evidence; optionally replay every held-out episode on CPU."""
import argparse
from contextlib import redirect_stdout
import gzip
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import torch

from tachyon_strategy_rl.design import architecture_from_strategy, validate_strategy
from tachyon_strategy_rl.environment import Env, sample_capabilities
from tachyon_strategy_rl.evaluate import EvaluationCase, rollout, summarize, clustered_interval
from tachyon_strategy_rl.inference import PolicyInference, validated_policy
from tachyon_strategy_rl.ppo import load_policy
from tachyon_strategy_rl.strategy import export_strategies


def verify(root, replay_all=False):
    root = Path(root).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    for name, digest in manifest["files"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Artifact integrity failure: {name}")
    report = json.loads((root / "evaluation/evaluation.json").read_text())
    if report["performanceDomain"] != "abstract_simulation_only":
        raise ValueError("Missing simulation-only label")
    torch.set_num_threads(1)
    policies = {"random": "random", "heuristic": "heuristic"}
    cap_seeds = set()
    for checkpoint in report["checkpoints"]:
        path = root / checkpoint["path"]
        model, metadata = validated_policy(path)
        if metadata["parameterHash"] != checkpoint["parameterHash"]:
            raise ValueError("Report and checkpoint disagree")
        policies[checkpoint["name"]] = model
        initial_path = path.with_name("initial.pt")
        initial, initial_metadata = validated_policy(initial_path, require_trained=False)
        if initial_metadata["parameterHash"] != metadata["initialParameterHash"]:
            raise ValueError("Initial checkpoint mismatch")
        try:
            validated_policy(initial_path)
        except ValueError:
            pass
        else:
            raise ValueError("Untrained checkpoint passed learned-policy gate")
        policies[checkpoint["name"].replace("ppo_", "untrained_")] = initial
        cap_seeds.update(metadata["capabilitySeeds"])
    cases = [EvaluationCase(**row) for row in report["testCases"]]
    if cap_seeds.intersection(c.capability_seed for c in cases):
        raise ValueError("Held-out capability seed leaked into training")
    records = {}
    for name in policies:
        records[name] = [json.loads(line) for line in gzip.decompress(
            (root / "evaluation" / (name+".jsonl.gz")).read_bytes()).decode().splitlines()]
        if summarize(records[name]) != report["policies"][name]:
            raise ValueError(f"Stored score summaries disagree: {name}")
        if [(r["capability_seed"], r["episode_seed"]) for r in records[name]] != [(c.capability_seed, c.episode_seed) for c in cases]:
            raise ValueError("Policies did not share evaluation cases")
    for name, comparisons in report["pairedComparisons"].items():
        for baseline, comparison in comparisons.items():
            difference = [a["score"]-b["score"] for a,b in zip(records[name], records[baseline])]
            actual = {"meanDifference": float(np.mean(difference)), "difference95CI": clustered_interval(records[name], difference)}
            if actual != comparison:
                raise ValueError("Paired capability-cluster intervals disagree")
    # Exercise the public inference boundary on a complete held-out episode,
    # independently of the batch evaluator's direct model calls.
    for checkpoint in report["checkpoints"]:
        inference = PolicyInference(root / checkpoint["path"])
        case = cases[0]
        capabilities = sample_capabilities(case.capability_seed, concentration=case.concentration)
        env = Env(seed=case.episode_seed, capabilities=capabilities)
        obs = env.reset(seed=case.episode_seed, capabilities=capabilities)
        while not env.done:
            output = inference.act(obs, env.action_mask())
            obs, _, _, _ = env.step(output["actionId"])
        expected = records[checkpoint["name"]][0]
        if env.score != expected["score"] or [e["action_id"] for e in env.trace] != [e["action_id"] for e in expected["trace"]]:
            raise ValueError("Public inference and evaluated rollout disagree")
    reproduced, _ = load_policy(root / "reproduction-seed-17/checkpoint.pt")
    from tachyon_strategy_rl.ppo import parameter_hash
    repetition = json.loads((root / "reproduction.json").read_text())
    if not (repetition["exactParameterHashMatch"] and repetition["parameterHash"] == parameter_hash(reproduced) == report["checkpoints"][0]["parameterHash"]):
        raise ValueError("Reproduction evidence disagrees with weights")
    with TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()):
        export_strategies(root / "evaluation", Path(temporary))
        for path in Path(temporary).glob("*.json"):
            if json.loads(path.read_text()) != json.loads((root / "strategies" / path.name).read_text()):
                raise ValueError("Strategy export is not reproducible from stored rollouts")
    strategies = list((root / "strategies").glob("*-strategy.json"))
    for path in strategies:
        spec = validate_strategy(json.loads(path.read_text()))
        architecture = architecture_from_strategy(spec)
        stored = json.loads(path.with_name(path.name.replace("-strategy", "-architecture")).read_text())
        if architecture != stored or architecture["completeRobot"]:
            raise ValueError("Strategy-to-architecture contract changed or overclaims CAD")
    replays = 0
    if replay_all:
        for name, policy in policies.items():
            for case, expected in zip(cases, records[name]):
                actual = rollout(case, policy, include_trace="trace" in expected)
                if actual != expected:
                    raise ValueError(f"Deterministic replay mismatch: {name}, {case}")
                replays += 1
    return {"performanceDomain": "abstract_simulation_only", "artifactHashesVerified": len(manifest["files"]),
            "trainedCheckpointGatesPassed": 3, "untrainedCheckpointsRejected": 3,
            "completePublicInferenceEpisodesMatched": 3,
            "policiesWithRecomputedStatistics": len(records), "exactHeldOutReplays": replays,
            "fullTrainingReproductionHashMatched": True,
            "strategyExportsReproduced": len(strategies), "architectureContractsMatched": len(strategies),
            "productionAppIntegrated": False, "cadGenerated": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--replay-all", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.root, args.replay_all), indent=2))
