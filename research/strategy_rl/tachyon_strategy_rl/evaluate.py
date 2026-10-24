"""Paired held-out simulation evaluation. Baselines never train the PPO policy."""
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import torch

from .environment import Env, sample_capabilities
from .inference import validated_policy


@dataclass(frozen=True)
class EvaluationCase:
    capability_seed: int
    episode_seed: int
    split: str
    concentration: float


def held_out_cases(configurations=64, episodes_per_configuration=3):
    if configurations < 4 or episodes_per_configuration < 1:
        raise ValueError("Use at least four held-out configurations")
    return [EvaluationCase(2_000_000_000+i, 3_000_000_000+i*100+j,
                           "held_out_distribution" if i < configurations//2 else "held_out_budget_corners",
                           2.0 if i < configurations//2 else .65)
            for i in range(configurations) for j in range(episodes_per_configuration)]


def heuristic_action(env):
    """Explicit nearest-route greedy baseline; never called during PPO training.

    It knows the same visible game/capability state, not future opponent events.
    It carries at most one Pin and one Cup and plans legal stack interfaces.
    """
    mask = env.action_mask()
    remaining = env.episode_seconds - env.elapsed
    travel = np.linalg.norm(env.sites-env.position, axis=1)/env.capabilities.drive_speed_m_s + env.capabilities.turn_seconds
    if remaining <= travel[6] + 6:
        return 13 if mask[13] else 6 if mask[6] else 12
    reachable = [i for i in range(2) if env.goal_counts[i].sum() < env._goal_capacities[i]
                 and env.goal_height_m(i) <= env.capabilities.max_reach_m + 1e-9]
    if not reachable:
        return 13 if mask[13] else 6 if mask[6] else 12
    inventory = int(env.inventory.sum())
    cup_inventory = int(getattr(env, "inventory_cup", 0))
    cup_ready = getattr(env, "cup_ready", np.ones(2, dtype=bool))
    location = env.location_index
    # Finish placing a carried Pin, preparing its Cup interface when needed.
    if inventory:
        eligible = [i for i in reachable if env.goal_counts[i].sum() == 0 or cup_ready[i] or cup_inventory]
        if eligible:
            goal = min(eligible, key=lambda i: travel[2+i] + (0 if env.inventory[1] == 0 or env.toggle_owners[i] == 1 else travel[4+i]))
            if env.inventory[1] and env.toggle_owners[goal] != 1:
                if location == 4+goal and mask[11]: return 11
                if mask[4+goal]: return 4+goal
            if location == 2+goal:
                if len(mask) > 15 and mask[15]: return 15
                if mask[10]: return 10
                if mask[9]: return 9
            if mask[2+goal]: return 2+goal
    # Obtain the next Pin and, once stacks exist, a Cup for the next interface.
    supplies = [i for i in range(2) if env.stock[i].sum() > 0 or (inventory and getattr(env, "cup_stock", [0, 0])[i] > 0)]
    if not supplies:
        return 13 if mask[13] else 6 if mask[6] else 12
    target = min(supplies, key=lambda i: travel[i])
    if location in supplies:
        needs_cup = any(env.goal_counts[i].sum() > 0 and not cup_ready[i] for i in reachable)
        if needs_cup and len(mask) > 14 and mask[14]: return 14
        if mask[8]: return 8
        if mask[7]: return 7
    return target if mask[target] else 12


def rollout(case: EvaluationCase, policy, *, include_trace=False):
    capability = sample_capabilities(case.capability_seed, concentration=case.concentration)
    env = Env(seed=case.episode_seed, capabilities=capability)
    observation = env.reset(seed=case.episode_seed, capabilities=capability)
    random = np.random.default_rng(case.episode_seed ^ 0xABCDEF)
    while not env.done:
        mask = env.action_mask()
        if policy == "random":
            action = int(random.choice(np.flatnonzero(mask)))
        elif policy == "heuristic":
            action = heuristic_action(env)
        else:
            with torch.no_grad():
                distribution, _ = policy.distribution(torch.from_numpy(observation).unsqueeze(0), torch.from_numpy(mask).unsqueeze(0))
                action = int(distribution.probs.argmax(dim=-1)[0])
        if not mask[action]:
            raise RuntimeError("Evaluation policy selected an illegal action")
        observation, _, _, _ = env.step(action)
    result = {**env.summary(), "capability_seed": case.capability_seed, "episode_seed": case.episode_seed,
              "split": case.split, "performanceDomain": "abstract_simulation_only"}
    if include_trace:
        result["trace"] = env.trace
    return result


def clustered_interval(records, values, seed=20261024):
    """Resample capability configurations, keeping repeated episode seeds together."""
    groups = sorted({r["capability_seed"] for r in records})
    means = np.asarray([np.mean([values[i] for i, r in enumerate(records) if r["capability_seed"] == group]) for group in groups])
    random = np.random.default_rng(seed)
    samples = means[random.integers(0, len(means), size=(2000, len(means)))].mean(axis=1)
    return [float(v) for v in np.quantile(samples, [.025, .975])]


def summarize(records):
    scores = [r["score"] for r in records]
    return {"episodes": len(records), "capabilityConfigurations": len({r["capability_seed"] for r in records}),
            "meanScore": float(np.mean(scores)), "scoreStd": float(np.std(scores)),
            "meanScore95CI": clustered_interval(records, scores),
            "midfieldFraction": float(np.mean([r["terminal_midfield"] for r in records])),
            "meanPathLengthM": float(np.mean([r["path_length_m"] for r in records])),
            "meanScoreBySplit": {split: float(np.mean([r["score"] for r in records if r["split"] == split]))
                                 for split in sorted({r["split"] for r in records})}}


def evaluate(checkpoint_paths, output: Path, configurations=64, episodes_per_configuration=3):
    torch.set_num_threads(1)
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    if (output / "evaluation.json").exists():
        raise ValueError("Evaluation already exists; preserve it and use a new output")
    cases = held_out_cases(configurations, episodes_per_configuration)
    policies = {"random": "random", "heuristic": "heuristic"}
    trained_names = []
    checkpoint_metadata = []
    for path in checkpoint_paths:
        model, checkpoint = validated_policy(Path(path))
        if set(checkpoint["capabilitySeeds"]) & {case.capability_seed for case in cases}:
            raise ValueError("Training/evaluation capability split overlap")
        name = "ppo_seed_"+str(checkpoint["config"]["seed"])
        if name in policies: raise ValueError("Duplicate training seed")
        policies[name] = model; trained_names.append(name)
        initial, _ = validated_policy(Path(path).with_name("initial.pt"), require_trained=False)
        policies["untrained_seed_"+str(checkpoint["config"]["seed"])] = initial
        checkpoint_metadata.append({"name": name, "path": str(path), "steps": checkpoint["steps"],
            "gradientUpdates": checkpoint["gradientUpdates"], "parameterHash": checkpoint["parameterHash"],
            "initialParameterHash": checkpoint["initialParameterHash"], "config": checkpoint["config"]})
    rows = {}
    for name, policy in policies.items():
        rows[name] = [rollout(case, policy, include_trace=name in trained_names) for case in cases]
        with (output / (name+".jsonl")).open("w") as stream:
            for row in rows[name]: stream.write(json.dumps(row, allow_nan=False)+"\n")
        print(json.dumps({"policy": name, **summarize(rows[name])}), flush=True)
    report = {"performanceDomain": "abstract_simulation_only", "policyEvaluation": "deterministic_argmax_of_trained_masked_policy",
              "testCases": [case.__dict__ for case in cases], "checkpoints": checkpoint_metadata,
              "confidenceInterval": "95% percentile bootstrap over held-out capability configurations; repeated episode seeds clustered",
              "policies": {name: summarize(records) for name, records in rows.items()},
              "pairedComparisons": {name: {baseline: {"meanDifference": float(np.mean([a["score"]-b["score"] for a,b in zip(rows[name], rows[baseline])])),
                    "difference95CI": clustered_interval(rows[name], [a["score"]-b["score"] for a,b in zip(rows[name], rows[baseline])])}
                    for baseline in ("random", "heuristic", name.replace("ppo_", "untrained_"))} for name in trained_names},
              "limitations": ["A bounded rule-derived abstraction, not the full game or physics",
                              "Capability budgets are abstract, not mechanically certified",
                              "No real robot or match performance validation"]}
    (output / "evaluation.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    return report
