"""Frozen-policy capability experiments. No optimizer or training calls.

Single-property interventions deliberately leave the learned joint capability
manifold. They diagnose this simulator, not independently realizable hardware.
Budget transfers and fixed simplex profiles provide separate feasible controls.
"""
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType

import numpy as np
import torch

from .environment import ACTION_NAMES, Capabilities, Env, sample_capabilities
from .evaluate import clustered_interval
from .inference import validated_policy


DOMAINS = {
    "drive_speed_m_s": (.65, 2.65), "max_reach_m": (.32, 1.22),
    "acquisition_seconds": (1.2, 3.2), "placement_seconds": (1., 2.5),
    "acquisition_success_probability": (.70, .98),
    "placement_success_probability": (.70, .98), "turn_seconds": (.20, .70),
}
SWEEPS = {
    "drive_speed_m_s": ([.75, 1.3, 2.1], "higher"),
    "max_reach_m": ([.32, .36, .60], "higher"),
    "acquisition_seconds": ([1.4, 2.2, 3.0], "lower"),
    "placement_seconds": ([1.1, 1.75, 2.4], "lower"),
    "acquisition_success_probability": ([.72, .84, .96], "higher"),
    "placement_success_probability": ([.72, .84, .96], "higher"),
    "turn_seconds": ([.25, .45, .65], "lower"),
}
PROFILES = {"balanced": (1/3, 1/3, 1/3), "drive_priority": (.60, .25, .15),
            "handling_priority": (.25, .60, .15), "reach_priority": (.25, .25, .50)}


class DiagnosticCapabilities(Capabilities):
    def __init__(self, base, overrides):
        super().__init__(base.drive, base.handling, base.lift)
        object.__setattr__(self, "overrides", MappingProxyType(dict(overrides)))
        self.validate()

    def __getattribute__(self, name):
        if name in DOMAINS:
            overrides = object.__getattribute__(self, "overrides")
            if name in overrides:
                return overrides[name]
        return object.__getattribute__(self, name)

    def validate(self):
        super().validate()
        for key, value in self.overrides.items():
            if key not in DOMAINS or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Unsupported or nonfinite capability intervention")
            low, high = DOMAINS[key]
            if not low <= value <= high:
                raise ValueError(f"{key} lies outside the modeled marginal range [{low}, {high}]")

    def to_dict(self):
        return {**super().to_dict(), "diagnosticOverrides": dict(self.overrides),
                "jointDomainStatus": "off_training_manifold_diagnostic" if self.overrides else "original_simplex"}


def variants():
    result = [{"id": "reference", "mode": "original_simplex"}]
    for field, (levels, _) in SWEEPS.items():
        result.extend({"id": f"{field}={level}", "mode": "single_feature_diagnostic", "overrides": {field: level}}
                      for level in levels)
    for receiver, donor in (("drive", "lift"), ("handling", "lift"), ("lift", "drive"),
                            ("drive", "handling"), ("handling", "drive"), ("lift", "handling")):
        result.append({"id": f"budget_{receiver}_from_{donor}", "mode": "coupled_simplex_transfer",
                       "receiver": receiver, "donor": donor, "donorFraction": .30})
    result.extend({"id": "profile_"+name, "mode": "fixed_simplex_profile", "allocation": list(values)}
                  for name, values in PROFILES.items())
    return result


def capabilities_for(base, variant):
    if variant["mode"] == "single_feature_diagnostic":
        return DiagnosticCapabilities(base, variant["overrides"])
    if variant["mode"] == "fixed_simplex_profile":
        return Capabilities(*variant["allocation"])
    if variant["mode"] == "coupled_simplex_transfer":
        allocation = {key: getattr(base, key) for key in ("drive", "handling", "lift")}
        transfer = allocation[variant["donor"]]*variant["donorFraction"]
        allocation[variant["donor"]] -= transfer
        allocation[variant["receiver"]] += transfer
        return Capabilities(**allocation)
    return base


def context_key(env):
    return json.dumps({"timeBand": "late" if env.elapsed >= 90 else "middle" if env.elapsed >= 45 else "early",
                       "site": env.location_index, "pinCarried": bool(env.inventory.sum()),
                       "cupCarried": bool(env.inventory_cup),
                       "lowCupReady": bool(env.cup_ready[0]),
                       "lowReachable": env.goal_height_m(0) <= env.capabilities.max_reach_m}, sort_keys=True)


def episode(model, capabilities, seed, contexts=None, trace=False):
    env = Env(seed=seed, capabilities=capabilities)
    observation = env.observe()
    decisions = []
    while not env.done:
        mask = env.action_mask()
        with torch.no_grad():
            distribution, _ = model.distribution(torch.from_numpy(observation).unsqueeze(0), torch.from_numpy(mask).unsqueeze(0))
        probabilities = distribution.probs[0].numpy()
        action = int(probabilities.argmax())
        if trace:
            decisions.append({"context": context_key(env), "actionId": action})
        if contexts is not None:
            group = contexts[context_key(env)]
            group["n"] += 1
            group["probabilities"] += probabilities
            group["selected"][ACTION_NAMES[action]] += 1
        observation, _, _, _ = env.step(action)
    placements = [e for e in env.trace if e["success"] and e["action_id"] in (9, 10)]
    row = {**env.summary(), "scoringPlacementCount": len(placements),
           "maxScoringReachM": max((e["goal_height_m"] for e in placements), default=0.),
           "maxTaskReachM": max((e["goal_height_m"] for e in env.trace if e["success"] and e["action_id"] in (9,10,15)), default=0.),
           "failedActions": sum(not e["success"] for e in env.trace),
           "scoringCycleSeconds": [b["end_s"]-a["end_s"] for a,b in zip(placements, placements[1:])],
           "performanceDomain": "abstract_simulation_only"}
    if trace:
        row["trace"] = env.trace
        row["decisionContexts"] = decisions
    return row


def summarize(rows):
    counts = Counter()
    for row in rows: counts.update(row["action_counts"])
    cycles = [v for row in rows for v in row["scoringCycleSeconds"]]
    unique_vectors = len({json.dumps(r["capabilities"], sort_keys=True) for r in rows})
    return {"episodes": len(rows), "capabilityConfigurations": unique_vectors,
            "capabilitySeedBlocks": len({r["capability_seed"] for r in rows}),
            "intervalSamplingUnit": "episode_seed_blocks_at_one_fixed_capability" if unique_vectors == 1 else "sampled_capability_seed_blocks",
            "meanScore": float(np.mean([r["score"] for r in rows])),
            "score95CI": clustered_interval(rows, [r["score"] for r in rows]),
            "meanScoreByPolicy": {key: float(np.mean([r["score"] for r in rows if r["policyName"] == key])) for key in sorted({r["policyName"] for r in rows})},
            "scoringPlacementMean": float(np.mean([r["scoringPlacementCount"] for r in rows])),
            "observedMaxScoringReachM": max(r["maxScoringReachM"] for r in rows),
            "midfieldFinishFraction": float(np.mean([r["terminal_midfield"] for r in rows])),
            "meanFailedActions": float(np.mean([r["failedActions"] for r in rows])),
            "meanPointsByObjective": {key: float(np.mean([r["points_by_objective"][key] for r in rows])) for key in rows[0]["points_by_objective"]},
            "medianScoringCycleSeconds": float(np.median(cycles)) if cycles else None,
            "actionFrequencies": {key: value/sum(counts.values()) for key,value in counts.items()},
            "meanPathLengthM": float(np.mean([r["path_length_m"] for r in rows]))}


def paired_effect(left, right):
    keys = lambda rows: [(r["policyName"], r["capability_seed"], r["episode_seed"]) for r in rows]
    if keys(left) != keys(right): raise ValueError("Paired interventions must share policy and seed cases")
    differences = [a["score"]-b["score"] for a,b in zip(left, right)]
    mean = float(np.mean(differences)); interval = clustered_interval(left, differences)
    return {"meanScoreDifference": mean, "difference95CI": interval,
            "material": abs(mean) >= 2. and (interval[0] > 0 or interval[1] < 0)}


def analyze(experiment, output, configurations=16, episodes_per_configuration=2):
    experiment, output = Path(experiment), Path(output)
    if configurations < 4 or episodes_per_configuration < 1: raise ValueError("Require at least four capability clusters")
    output.mkdir(parents=True, exist_ok=False)
    source_report = json.loads((experiment / "evaluation/evaluation.json").read_text())
    torch.set_num_threads(1)
    policies = []
    for checkpoint in source_report["checkpoints"]:
        path = experiment / checkpoint["path"]
        model, data = validated_policy(path)
        policies.append((checkpoint["name"], model, {**checkpoint, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}))
    contexts = defaultdict(lambda: {"n": 0, "probabilities": np.zeros(len(ACTION_NAMES)), "selected": Counter()})
    all_rows, summaries, groups = [], {}, {}
    for stage, capability_start, episode_start in (("calibration", 4_000_000_000, 5_000_000_000),
                                                    ("confirmation", 6_000_000_000, 7_000_000_000)):
        summaries[stage] = {}; groups[stage] = {}
        for variant in variants():
            rows = []
            for name, model, _ in policies:
                for index in range(configurations):
                    cap_seed = capability_start + index
                    base = sample_capabilities(cap_seed)
                    capability = capabilities_for(base, variant)
                    for repetition in range(episodes_per_configuration):
                        seed = episode_start+100*index+repetition
                        row = episode(model, capability, seed,
                                      contexts if stage == "calibration" and variant["id"] == "reference" else None,
                                      trace=variant["id"] == "reference")
                        row.update(policyName=name, capability_seed=cap_seed, episode_seed=seed,
                                   stage=stage, variantId=variant["id"])
                        rows.append(row)
            groups[stage][variant["id"]] = rows
            summaries[stage][variant["id"]] = summarize(rows)
            all_rows.extend(rows)
            print(json.dumps({"stage": stage, "variant": variant["id"], "meanScore": summaries[stage][variant["id"]]["meanScore"]}), flush=True)
    effects = {}
    for field, (levels, direction) in SWEEPS.items():
        preferred, adverse = (levels[-1], levels[0]) if direction == "higher" else (levels[0], levels[-1])
        effects[field] = {stage: paired_effect(groups[stage][f"{field}={preferred}"], groups[stage][f"{field}={adverse}"])
                          for stage in groups}
        effects[field]["replicatedMaterialEffect"] = all(effects[field][stage]["material"] for stage in groups) and (
            effects[field]["calibration"]["meanScoreDifference"]*effects[field]["confirmation"]["meanScoreDifference"] > 0)
    profiles = ["profile_"+key for key in PROFILES]
    selected = max(profiles, key=lambda key: summaries["calibration"][key]["meanScore"])
    profile_comparison = {"selectionRule": "Highest calibration frozen-policy score among four declared abstract simplex profiles",
                          "strategyAwareProfile": selected, "strategyBlindProfile": "profile_balanced",
                          "selectionUsesConfirmation": False,
                          "confirmationDifference": paired_effect(groups["confirmation"][selected], groups["confirmation"]["profile_balanced"]),
                          "meaning": "Abstract capability-profile selection only; no measured or predicted mechanical-topology performance"}
    profiles_out = [{"when": json.loads(key), "observedDecisions": group["n"],
                     "meanNeuralActionProbabilities": dict(zip(ACTION_NAMES, (group["probabilities"]/group["n"]).tolist())),
                     "selectedActionCounts": dict(group["selected"])} for key,group in sorted(contexts.items())]
    distilled = {key: int(group["probabilities"].argmax()) for key,group in contexts.items()}
    covered = matched = total = 0
    for row in groups["confirmation"]["reference"]:
        for decision in row["decisionContexts"]:
            total += 1
            if decision["context"] in distilled:
                covered += 1
                matched += distilled[decision["context"]] == decision["actionId"]
    raw = "".join(json.dumps(row, allow_nan=False)+"\n" for row in all_rows).encode()
    archive = gzip.compress(raw, mtime=0)
    result = {"schemaVersion": 1, "experimentId": "override-frozen-policy-handoff-v1",
              "sourceExperimentId": "override-ppo-v1", "sourceCommit": "ac1aa01",
              "performanceDomain": "abstract_simulation_only", "trainingPerformed": False,
              "runnerSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "episodesSha256": hashlib.sha256(archive).hexdigest(),
              "sourceStrategySha256": hashlib.sha256((experiment/"strategies/low_quadrant_cycles-strategy.json").read_bytes()).hexdigest(),
              "sourceEvaluationSha256": hashlib.sha256((experiment/"evaluation/evaluation.json").read_bytes()).hexdigest(),
              "checkpoints": [metadata for _,_,metadata in policies],
              "design": {"configurationsPerStage": configurations, "episodesPerConfigurationPerPolicy": episodes_per_configuration,
                         "trainingSeeds": [17,29,43], "stagesHaveDisjointSeeds": True,
                         "materialThresholdModeledPoints": 2., "uncertainty": "95% capability-cluster bootstrap, 2000 samples; exploratory intervals, no multiplicity adjustment",
                         "singleFeatureMeaning": "Controlled simulator intervention outside the joint training manifold; not independently feasible hardware",
                         "simplexMeaning": "Feasible abstract coupled changes, not single-feature causal isolation",
                         "acceleration": "not_represented; turn overhead is not acceleration"},
              "variants": variants(), "summaries": summaries, "effects": effects,
              "conditionalPreferences": profiles_out, "strategyAwareVsBlind": profile_comparison,
              "contextApproximationValidation": {"heldOutDecisions": total, "coveredDecisions": covered,
                  "matchedDecisions": matched, "coverage": covered/total, "agreementOnCovered": matched/covered if covered else None,
                  "use": "Descriptive approximation only; actual inference always executes the frozen neural policy"},
              "limitations": ["Authored abstract competition, no physical validation", "Finite seed and capability coverage",
                              "Pooled intervals condition on three fixed trained policies", "Marginal interventions are off the training manifold",
                              "No independent hardware feasibility claim or acceleration model"]}
    (output / "analysis.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    (output / "episodes.jsonl.gz").write_bytes(archive)
    return result
