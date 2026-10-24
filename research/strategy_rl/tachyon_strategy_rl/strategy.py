"""Interpret trained-policy rollouts; never invent a second discovered strategy."""
from collections import Counter
import gzip
import json
from pathlib import Path

import numpy as np

from .design import architecture_from_strategy, validate_strategy


def _quantile(values, fraction=.5):
    return float(np.quantile(values, fraction))


def _placements(row):
    return [e for e in row["trace"] if e["success"] and e["action_id"] in (9, 10)]


def _family(row):
    placements = _placements(row)
    if not placements: return "no_scoring_sequence"
    share = sum(e["goal_index"] == 1 for e in placements)/len(placements)
    return "elevated_quadrant_cycles" if share >= .65 else "low_quadrant_cycles" if share <= .35 else "mixed_routes"


def extract_family(name, rows, policy_hashes):
    counts = Counter(e["action"] for row in rows for e in row["trace"])
    transitions = Counter((a["action"], b["action"]) for row in rows
                          for a, b in zip(row["trace"], row["trace"][1:]) if a["success"] and b["success"])
    representative = max(rows, key=lambda row: (row["score"], -row["path_length_m"]))
    threshold = _quantile([row["score"] for row in rows], .75)
    stronger = [row for row in rows if row["score"] >= threshold]
    placements = _placements(representative)
    required_reach = max(float(e["goal_height_m"]) for e in placements)
    cup_needed = any(e["success"] and e["action_id"] == 15 for e in representative["trace"])
    targets = {"driveSpeedMps": _quantile([r["capabilities"]["drive_speed_m_s"] for r in stronger]),
               "reachM": max(required_reach, _quantile([max(float(e["goal_height_m"]) for e in _placements(r)) for r in stronger], .75)),
               "acquisitionSeconds": _quantile([r["capabilities"]["acquisition_seconds"] for r in stronger]),
               "placementSeconds": _quantile([r["capabilities"]["placement_seconds"] for r in stronger]),
               "acquisitionSuccessProbability": _quantile([r["capabilities"]["acquisition_success_probability"] for r in stronger]),
               "placementSuccessProbability": _quantile([r["capabilities"]["placement_success_probability"] for r in stronger])}
    joint = representative["capabilities"]
    # Keep the design target jointly supported by one feasible sampled budget;
    # independently combining favorable marginal percentiles can be infeasible.
    targets.update(driveSpeedMps=joint["drive_speed_m_s"], reachM=required_reach,
                   acquisitionSeconds=joint["acquisition_seconds"], placementSeconds=joint["placement_seconds"],
                   acquisitionSuccessProbability=joint["acquisition_success_probability"],
                   placementSuccessProbability=joint["placement_success_probability"])
    objectives = {key: float(np.mean([r["points_by_objective"][key] for r in rows]))
                  for key in rows[0]["points_by_objective"]}
    visits = Counter(e["action"] for row in rows for e in row["trace"] if e["success"] and e["action_id"] < 7)
    mechanisms = ["single_pin_acquisition", "pin_half_orientation_retention", "single_pin_transfer", "scoring_reach"]
    if cup_needed: mechanisms.extend(("independent_single_cup_retention", "cup_interface_preparation"))
    if counts.get("toggle", 0): mechanisms.append("toggle_actuation")
    spec = {"schemaVersion": 1, "id": "ppo-strategy-"+name,
            "performanceDomain": "abstract_simulation_only", "scenario": rows[0]["scenario"],
            "competition": {"name": "V5 Override", "version": "2.1", "scope": "two abstract quadrant stack interfaces, not the central midfield goal"},
            "evidence": {"origin": "trained_neural_ppo_rollouts", "episodes": len(rows),
                         "capabilityConfigurations": len({r["capability_seed"] for r in rows}),
                         "trainingSeeds": sorted({r["policy_name"] for r in rows}),
                         "checkpointParameterHashes": sorted({policy_hashes[r["policy_name"]] for r in rows}),
                         "meanScore": float(np.mean([r["score"] for r in rows])),
                         "selection": "Observed goal-choice family; target envelopes use its upper score quartile, not a causal minimum search"},
            "preferredScoringObjectives": sorted([{"objective": key, "meanModeledPoints": value} for key, value in objectives.items()], key=lambda item: -item["meanModeledPoints"]),
            "actionPriorities": [{"action": action, "observedCount": count, "frequency": count/sum(counts.values())} for action, count in counts.most_common()],
            "cycleTransitions": [{"from": a, "to": b, "observedCount": count} for (a, b), count in transitions.most_common(15)],
            "movement": {"meanPathLengthM": float(np.mean([r["path_length_m"] for r in rows])),
                         "successfulSiteVisits": dict(visits), "layoutIsAbstract": True},
            "representativeRollout": {"policy": representative["policy_name"], "capabilitySeed": representative["capability_seed"],
                "episodeSeed": representative["episode_seed"], "modeledScore": representative["score"],
                "capabilities": representative["capabilities"], "events": representative["trace"]},
            "capabilityRequirements": {"hardMinimums": {"reachM": required_reach, "pinCapacity": 1, "cupCapacity": int(cup_needed)},
                "minimumScope": "Geometric reach and possession requirements of the representative simulated sequence only",
                "jointReferenceCapabilities": joint,
                "targetBasis": "One observed feasible capability sample; no independent mixing of marginal best features",
                "targets": targets, "empiricalBudgetEnvelope": {key: {"p25": _quantile([r["capabilities"]["allocation"][key] for r in stronger], .25),
                    "median": _quantile([r["capabilities"]["allocation"][key] for r in stronger]),
                    "p75": _quantile([r["capabilities"]["allocation"][key] for r in stronger], .75)} for key in ("drive", "handling", "lift")}},
            "mechanismRequirements": mechanisms,
            "observedTradeoffs": {
                "meanCupPreparationSeconds": float(np.mean([sum(e["end_s"]-e["start_s"] for e in r["trace"] if e["action_id"] in (14,15)) for r in rows])),
                "meanToggleActionSeconds": float(np.mean([sum(e["end_s"]-e["start_s"] for e in r["trace"] if e["action_id"] in (4,5,11)) for r in rows])),
                "meanObservedScoreLost": float(np.mean([sum(max(0., e["score_before"]-e["score_after"]) for e in r["trace"]) for r in rows])),
                "midfieldFinishFraction": float(np.mean([r["terminal_midfield"] for r in rows])),
                "elevatedPlacementFraction": float(np.mean([sum(e["goal_index"] == 1 for e in _placements(r))/len(_placements(r)) for r in rows]))},
            "tradeoffs": ["Drive, handling and reach share the sampled abstract budget; hardware feasibility remains unverified",
                          "Yellow-half scores depend on retaining toggle ownership at the episode end",
                          "Cup preparation costs time without immediate points, but enables another Pin placement",
                          "Midfield positioning trades remaining scoring time against eight modeled terminal points"],
            "limitations": ["Not real robot or match performance", "Assumed positions, reach heights and action dynamics",
                            "One visible scoring half per Pin, with idealized Cup orientation", "No validated CAD geometry or mechanism capability"]}
    return validate_strategy(spec)


def export_strategies(evaluation: Path, output: Path):
    evaluation, output = Path(evaluation), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "strategy-manifest.json").exists():
        raise ValueError("Strategy export exists; choose a new output directory")
    report = json.loads((evaluation / "evaluation.json").read_text())
    policy_hashes = {c["name"]: c["parameterHash"] for c in report["checkpoints"]}
    groups = {}
    for name in policy_hashes:
        raw = evaluation / (name+".jsonl")
        text = raw.read_text() if raw.exists() else gzip.decompress(raw.with_suffix(".jsonl.gz").read_bytes()).decode()
        for line in text.splitlines():
            row = json.loads(line); row["policy_name"] = name
            groups.setdefault(_family(row), []).append(row)
    discovered, rejected = [], []
    for name in ("low_quadrant_cycles", "elevated_quadrant_cycles"):
        rows = groups.get(name, [])
        support = {"episodes": len(rows), "capabilityConfigurations": len({r["capability_seed"] for r in rows}),
                   "trainingSeeds": len({r["policy_name"] for r in rows})}
        # Evidence gates are fixed before looking at evaluation results.
        if support["episodes"] < 24 or support["capabilityConfigurations"] < 8 or support["trainingSeeds"] < 2:
            rejected.append({"family": name, "support": support, "reason": "Insufficient replicated rollout support; no discovered architecture emitted"})
            continue
        spec = extract_family(name, rows, policy_hashes)
        architecture = architecture_from_strategy(spec)
        (output / (name+"-strategy.json")).write_text(json.dumps(spec, indent=2, allow_nan=False)+"\n")
        (output / (name+"-architecture.json")).write_text(json.dumps(architecture, indent=2, allow_nan=False)+"\n")
        discovered.append({"family": name, "strategyId": spec["id"], "architectureId": architecture["id"], "support": support})
    result = {"performanceDomain": "abstract_simulation_only", "supportedFamilies": discovered,
              "unsubstantiatedFamilies": rejected, "otherObservedFamilies": {k: len(v) for k,v in groups.items() if k not in ("low_quadrant_cycles", "elevated_quadrant_cycles")},
              "twoDistinctArchitecturesSupported": len(discovered) == 2,
              "cadGenerated": False, "frontendIntegrated": False,
              "feedbackInterface": {"schemaVersion": 1, "robotDesignId": "generated-design-id", "source": "estimated",
                  "capabilities": {"driveSpeedMps": 1., "acquisitionSeconds": 2., "placementSeconds": 2., "reachM": .5},
                  "abstractBudgetCalibrationRequired": True, "automaticTrainingLoopImplemented": False}}
    (output / "strategy-manifest.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result), flush=True)
    return result
