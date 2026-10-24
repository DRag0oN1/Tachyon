import numpy as np

from tachyon_strategy_rl.environment import Env, sample_capabilities
from tachyon_strategy_rl.evaluate import EvaluationCase, clustered_interval, held_out_cases, heuristic_action, rollout


def test_holdouts_have_distinct_capability_seeds_and_paired_noise_cases():
    cases = held_out_cases(8, 3)
    assert len(cases) == 24
    assert len({c.capability_seed for c in cases}) == 8
    assert len({c.episode_seed for c in cases}) == 24
    assert all(c.capability_seed >= 2_000_000_000 and c.episode_seed >= 3_000_000_000 for c in cases)
    assert {c.split for c in cases} == {"held_out_distribution", "held_out_budget_corners"}


def test_heuristic_uses_legal_actions_and_repeated_cup_interfaces():
    r = rollout(EvaluationCase(2_000_000_003, 3_000_000_001, "test", 2), "heuristic", include_trace=True)
    assert r["done"] and r["elapsed"] == 105
    assert all(e["details"]["valid_action"] for e in r["trace"])
    assert all(sum(e["inventory_after"]) <= 1 and e["inventory_cup_after"] <= 1 for e in r["trace"])
    assert r["action_counts"]["place_cup"] > 0
    assert sum(g["alliance"]+g["yellow"] for g in r["goal_counts"]) > 1


def test_random_baseline_repeats_for_the_same_case():
    case = EvaluationCase(2_000_000_001, 3_000_000_002, "test", .65)
    assert rollout(case, "random", include_trace=True) == rollout(case, "random", include_trace=True)


def test_cluster_bootstrap_keeps_repeated_configurations_together():
    rows = [{"capability_seed": seed} for seed in (1,1,2,2)]
    assert clustered_interval(rows, [10,10,10,10]) == [10,10]
    low, high = clustered_interval(rows, [0,0,20,20])
    assert low == 0 and high == 20
