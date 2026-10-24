"""Versioned frozen-neural-strategy handoff and one-shot capability feedback."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import torch

from .capability_analysis import DiagnosticCapabilities, analyze, episode
from .environment import ACTION_NAMES, OBSERVATION_NAMES, Capabilities
from .inference import PolicyInference, validated_policy


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_episodes(analysis):
    return [json.loads(line) for line in gzip.decompress((Path(analysis)/"episodes.jsonl.gz").read_bytes()).decode().splitlines()]


def strategy_identity(spec):
    payload={key:value for key,value in spec.items() if key!='id'}
    return "strategy-spec-"+hashlib.sha256(json.dumps(payload,sort_keys=True,allow_nan=False).encode()).hexdigest()[:24]


def make_spec(experiment, analysis):
    experiment, analysis = Path(experiment), Path(analysis)
    findings = json.loads((analysis/"analysis.json").read_text())
    for field,path in (("episodesSha256",analysis/"episodes.jsonl.gz"),
                       ("sourceStrategySha256",experiment/"strategies/low_quadrant_cycles-strategy.json"),
                       ("sourceEvaluationSha256",experiment/"evaluation/evaluation.json")):
        if findings.get(field)!=digest(path): raise ValueError("Analysis/source provenance mismatch: "+field)
    old = json.loads((experiment/"strategies/low_quadrant_cycles-strategy.json").read_text())
    primary = next(c for c in findings["checkpoints"] if c["name"] == "ppo_seed_17")
    if digest(experiment/primary["path"]) != primary["sha256"]:
        raise ValueError("Checkpoint changed after capability evaluation")
    selected = findings["strategyAwareVsBlind"]["strategyAwareProfile"].removeprefix("profile_")
    variant=next(v for v in findings['variants'] if v['id']=='profile_'+selected and v['mode']=='fixed_simplex_profile')
    reference = Capabilities(*variant['allocation'])
    reference.validate()
    rows = read_episodes(analysis)
    selected_rows=[r for r in rows if r['variantId']==variant['id']]
    if not selected_rows or any(r['capabilities']!=reference.to_dict() for r in selected_rows):
        raise ValueError("Saved profile allocation and evaluated effective capabilities disagree")
    baseline = [r for r in rows if r["stage"] == "calibration" and r["variantId"] == "reference"]
    required = max(e["goal_height_m"] for e in old["representativeRollout"]["events"] if e["success"] and e["action_id"] in (9,10,15))
    preferred_reach = max(r["maxTaskReachM"] for r in baseline)
    sequences = []
    for name in ("ppo_seed_17", "ppo_seed_29", "ppo_seed_43"):
        subset = [r for r in baseline if r["policyName"] == name]
        center = float(np.mean([r["score"] for r in subset]))
        row = min(subset, key=lambda r: (abs(r["score"]-center), r["path_length_m"]))
        sequences.append({"policy": name, "capabilitySeed": row["capability_seed"], "episodeSeed": row["episode_seed"],
                          "modeledScore": row["score"], "selection": "Near calibration mean, not an action script",
                          "events": row["trace"]})
    profile_summary = findings["summaries"]["calibration"]["profile_"+selected]
    targets = {"driveSpeedMps": reference.drive_speed_m_s, "turnSeconds": reference.turn_seconds,
               "reachM": preferred_reach, "acquisitionSeconds": reference.acquisition_seconds,
               "placementSeconds": reference.placement_seconds,
               "acquisitionSuccessProbability": reference.acquisition_success_probability,
               "placementSuccessProbability": reference.placement_success_probability,
               "cycleSeconds": profile_summary["medianScoringCycleSeconds"]}
    subsystem_requirements = [
        {"id": "drive", "supports": ["move_to_supply0", "move_to_goal0", "move_to_midfield"], "requirements": ["speed_target", "turn_time_target"], "accelerationStatus": "not_identified"},
        {"id": "intake", "supports": ["acquire_alliance", "acquire_cup"], "requirements": ["one_pin", "independent_cup", "orientation_retention", "acquisition_latency", "acquisition_reliability"]},
        {"id": "transfer", "supports": ["acquire_alliance", "place_alliance", "place_cup"], "requirements": ["single_pin_handoff", "independent_cup_path", "avoid_double_possession"]},
        {"id": "scorer", "supports": ["place_alliance", "place_cup"], "requirements": ["reach_floor", "pin_grip", "cup_interface_preparation", "placement_latency", "placement_reliability"]}]
    spec = {"schemaVersion": 2, "kind": "tachyon.strategy_spec", "performanceDomain": "abstract_simulation_only",
            "competition": {"id": "v5-override-v2.1", "environmentId": old["scenario"]},
            "policy": {"experimentId": "override-ppo-v1", "sourceCommit": "ac1aa01",
                       "checkpoint": {"path": primary["path"], "sha256": primary["sha256"], "parameterHash": primary["parameterHash"]},
                       "selection": "Seed 17 chosen by fixed seed identity, not held-out score ranking",
                       "corroboratingCheckpoints": findings["checkpoints"]},
            "strategyFamily": "low_quadrant_cycles", "learnedStrategyCount": 1,
            "objectives": old["preferredScoringObjectives"], "scoringPriorities": old["preferredScoringObjectives"],
            "behavior": {"representation": "frozen_neural_policy_plus_observed_contexts",
                         "conditionalPreferences": findings["conditionalPreferences"],
                         "contextApproximationValidation": findings["contextApproximationValidation"],
                         "inference": {"observationNames": list(OBSERVATION_NAMES), "actionNames": list(ACTION_NAMES),
                                       "actionMaskRequired": True, "runtime": "FrozenStrategyController",
                                       "unknownContextBehavior": "Execute frozen neural policy on valid in-domain observation; never replay a fixed script",
                                       "probabilitySemantics": "Descriptive context averages are not the executable policy or independent legality rules"}},
            "representativeSequences": sequences, "observedActionFrequencies": old["actionPriorities"],
            "cycleTransitions": old["cycleTransitions"], "movement": old["movement"],
            "capabilityRequirements": {"hardMinimums": {"reachM": required, "pinCapacity": 1, "cupCapacity": 1},
                                       "minimumScope": "Pin AND Cup placements of original representative simulated rollout only",
                                       "targets": targets, "referenceCapabilities": reference.to_dict(),
                                       "basis": "Joint abstract profile selected on calibration; reach floor covers observed calibration tasks, not full profile lift range; all are design targets, not hardware measurements",
                                       "evidenceRefs": ["analysis.json#/effects", "analysis.json#/strategyAwareVsBlind", "episodes.jsonl.gz"],
                                       "acceleration": {"status": "not_identified", "reason": "Original environment has no acceleration state/dynamics; turn time is separate"}},
            "mechanicalRequirements": subsystem_requirements,
            "evidence": {"sourceStrategyParameterHashes": old["evidence"]["checkpointParameterHashes"],
                         "sourceRolloutEpisodes": old["evidence"]["episodes"],
                         "analysisExperimentId": findings["experimentId"], "analysisSha256": digest(analysis/"analysis.json"),
                         "episodesSha256": findings['episodesSha256'], "sourceStrategySha256": findings['sourceStrategySha256'],
                         "effects": findings["effects"], "strategyAwareVsBlind": findings["strategyAwareVsBlind"],
                         "uncertainty": findings["design"]["uncertainty"],
                         "targetClaims": "Experimental simulator sensitivity plus engineering realization hypotheses; no causal hardware minimum identified"},
            "limitations": findings["limitations"] + ["One learned family, two engineering alternatives may implement it",
                "No generated CAD, measured robot capability, acceleration requirement or full co-optimization loop",
                "Marginal interventions alter both observed capabilities and transitions; action noise consumption can differ across policies"]}
    spec["id"] = strategy_identity(spec)
    return spec


class FrozenStrategyController:
    """The handoff preserves the complete neural conditional behavior by reference."""
    def __init__(self, spec, experiment):
        if spec.get("schemaVersion") != 2 or spec.get("kind") != "tachyon.strategy_spec" or spec.get("performanceDomain") != "abstract_simulation_only":
            raise ValueError("Expected StrategySpec v2")
        if spec.get('id')!=strategy_identity(spec): raise ValueError("Strategy content identity mismatch")
        scenario=json.loads(Path(__file__).with_name('scenario.json').read_text())
        if spec['competition']['environmentId']!=scenario['name'] or spec['competition']['id']!='v5-override-v'+scenario['official_facts']['manual_version']:
            raise ValueError("Strategy environment is not the frozen policy's bounded scenario")
        root = Path(experiment).resolve()
        reference = spec["policy"]["checkpoint"]
        path = (root/reference["path"]).resolve()
        if not path.is_relative_to(root) or digest(path) != reference["sha256"]:
            raise ValueError("Strategy checkpoint integrity or path mismatch")
        self.engine = PolicyInference(path)
        if self.engine.checkpoint["parameterHash"] != reference["parameterHash"]:
            raise ValueError("Strategy names a different trained policy")
        inference = spec["behavior"]["inference"]
        if inference["observationNames"] != list(OBSERVATION_NAMES) or inference["actionNames"] != list(ACTION_NAMES):
            raise ValueError("Strategy inference contract is incompatible")
        self.id = spec["id"]

    def act(self, observation, action_mask):
        return {**self.engine.act(observation, action_mask), "strategySpecId": self.id}


FEEDBACK_FIELDS = {"driveSpeedMps": "drive_speed_m_s", "reachM": "max_reach_m",
                   "acquisitionSeconds": "acquisition_seconds", "placementSeconds": "placement_seconds",
                   "acquisitionSuccessProbability": "acquisition_success_probability",
                   "placementSuccessProbability": "placement_success_probability", "turnSeconds": "turn_seconds"}


def evaluate_feedback(spec, feedback, experiment, seeds=None):
    if feedback.get("schemaVersion") != 2 or feedback.get("strategySpecId") != spec["id"]:
        raise ValueError("Feedback must name StrategySpec v2 exactly")
    for key in ("robotDesignId", "designRevisionId", "environmentId", "method", "evidenceReference", "testConditions"):
        if not isinstance(feedback.get(key), str) or not feedback[key].strip(): raise ValueError("Missing feedback provenance: "+key)
    if feedback["environmentId"] != spec["competition"]["environmentId"]:
        raise ValueError("Feedback environment mismatch")
    if feedback.get("source") not in ("predicted", "measured", "abstract_simulation"):
        raise ValueError("Distinguish predicted, measured and abstract capabilities")
    if feedback.get("units") != "SI_seconds_metres_probabilities":
        raise ValueError("Explicit units are required")
    values = feedback.get("capabilities", {})
    uncertainty = feedback.get("uncertainty", {})
    overrides = {}
    for key, property_name in FEEDBACK_FIELDS.items():
        value, spread = values.get(key), uncertainty.get(key)
        if isinstance(value, bool) or not isinstance(value, (float,int)) or not math.isfinite(value):
            raise ValueError("Missing finite feedback capability: "+key)
        if isinstance(spread, bool) or not isinstance(spread, (float,int)) or not math.isfinite(spread) or spread < 0:
            raise ValueError("Each capability needs a nonnegative uncertainty bound")
        overrides[property_name] = value
    if set(values)-set(FEEDBACK_FIELDS)-{"accelerationMps2"}:
        raise ValueError("Unsupported capability fields")
    if "accelerationMps2" in values and (isinstance(values["accelerationMps2"],bool) or not isinstance(values["accelerationMps2"],(int,float)) or not math.isfinite(values["accelerationMps2"]) or values["accelerationMps2"] <= 0):
        raise ValueError("Acceleration metadata must be finite and positive")
    reference = spec["capabilityRequirements"]["referenceCapabilities"]["allocation"]
    capability = DiagnosticCapabilities(Capabilities(**reference), overrides)
    controller = FrozenStrategyController(spec, experiment)
    torch.set_num_threads(1)
    seeds = [8_000_000_000+i for i in range(32)] if seeds is None else list(seeds)
    if len(seeds) < 4 or len(set(seeds)) != len(seeds) or any(isinstance(seed,bool) or not isinstance(seed,int) or seed < 0 for seed in seeds):
        raise ValueError("Use at least four unique nonnegative episode seeds")
    rows = [episode(controller.engine.model, capability, seed) for seed in seeds]
    scores = [r["score"] for r in rows]
    bootstrap = np.random.default_rng(20261024).choice(scores, size=(2000,len(scores)),replace=True).mean(axis=1)
    requirements = spec["capabilityRequirements"]
    deficits = [{"capability": "reachM", "supplied": values["reachM"], "target": requirements["targets"]["reachM"],
                 "reason": "Observed stack-interface reach target is not met"}] if values["reachM"] < requirements["targets"]["reachM"] else []
    for field in ("acquisitionSeconds", "placementSeconds", "turnSeconds"):
        if values[field] > requirements["targets"][field]: deficits.append({"capability":field,"supplied":values[field],"target":requirements["targets"][field],"reason":"Latency target exceeded"})
    for field in ("driveSpeedMps", "acquisitionSuccessProbability", "placementSuccessProbability"):
        if values[field] < requirements["targets"][field]: deficits.append({"capability":field,"supplied":values[field],"target":requirements["targets"][field],"reason":"Capability target not met"})
    return {"schemaVersion":2,"strategySpecId":spec["id"],"robotDesignId":feedback["robotDesignId"],
            "designRevisionId":feedback["designRevisionId"],"performanceDomain":"abstract_simulation_only",
            "capabilitySource":feedback["source"],"inputRecord":feedback,"effectiveCapabilities":capability.to_dict(),
            "evaluatorSha256":digest(Path(__file__)),
            "inheritedModelAssumptions":{"movementSuccessProbability":capability.movement_success_probability,
                "toggleSuccessProbability":capability.toggle_success_probability,
                "basis":"Derived from abstract reference allocation; not supplied predictions or measurements",
                "scenarioDynamics":"Unchanged duration noise, stock, layout, opponent process and scoring assumptions"},
            "meanModeledScore":float(np.mean(scores)),"score95CI":np.quantile(bootstrap,[.025,.975]).tolist(),
            "episodeSeeds":seeds,"scores":scores,"actionFrequencies":action_frequencies(rows),
            "scoringPlacementsMean":float(np.mean([r["scoringPlacementCount"] for r in rows])),
            "recommendations":deficits or [{"reason":"Supplied nominal capabilities meet current abstract targets; verify actual mechanisms and uncertainty"}],
            "uncertaintyScope":"Interval covers simulated episode randomness at nominal supplied capabilities, NOT uncertainty in predicted/measured inputs",
            "accelerationUsed":False,"ignoredMetadata":["accelerationMps2"] if "accelerationMps2" in values else [],
            "jointDomainStatus":"off_training_manifold_diagnostic; no silent simplex projection",
            "physicalPerformanceValidated":False,"cadGenerated":False,"optimizerUpdates":0,
            "automaticCoOptimizationImplemented":False}


def action_frequencies(rows):
    from collections import Counter
    counts = Counter()
    for row in rows: counts.update(row["action_counts"])
    return {key:value/sum(counts.values()) for key,value in counts.items()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    investigation=commands.add_parser("analyze"); investigation.add_argument("--experiment",type=Path,required=True)
    investigation.add_argument("--output",type=Path,required=True); investigation.add_argument("--configurations",type=int,default=16)
    investigation.add_argument("--episodes",type=int,default=2)
    export=commands.add_parser("export"); export.add_argument("--experiment",type=Path,required=True)
    export.add_argument("--analysis",type=Path,required=True); export.add_argument("--output",type=Path,required=True)
    feedback=commands.add_parser("feedback"); feedback.add_argument("--experiment",type=Path,required=True)
    feedback.add_argument("--strategy",type=Path,required=True); feedback.add_argument("--input",type=Path,required=True)
    feedback.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.command=="analyze": analyze(args.experiment,args.output,args.configurations,args.episodes)
    elif args.command=="export":
        if args.output.exists(): raise FileExistsError("Choose a new output file")
        payload=make_spec(args.experiment,args.analysis)
        with args.output.open("x") as handle: json.dump(payload,handle,indent=2,allow_nan=False); handle.write("\n")
    else:
        if args.output.exists(): raise FileExistsError("Choose a new output file")
        spec=json.loads(args.strategy.read_text()); record=json.loads(args.input.read_text())
        payload=evaluate_feedback(spec,record,args.experiment)
        with args.output.open("x") as handle: json.dump(payload,handle,indent=2,allow_nan=False); handle.write("\n")


if __name__=="__main__": main()
