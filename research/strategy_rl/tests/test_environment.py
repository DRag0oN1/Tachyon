"""Decision-state, score, possession, stacking, and clock invariants."""

from copy import deepcopy
import json

import numpy as np
import pytest

from tachyon_strategy_rl.environment import (
    ACTION_COUNT, ACTION_NAMES, CAPABILITY_NAMES, OBSERVATION_NAMES, OBS_SIZE,
    Capabilities, Env, sample_capabilities,
)


class FixedRng:
    """Keep success/failure and durations exact for transition assertions."""

    def __init__(self, roll=0.0):
        self.roll = roll

    def random(self):
        return self.roll

    def uniform(self, low, high):
        return (low + high) / 2


@pytest.fixture
def env():
    scenario = Env(0).scenario
    scenario["assumptions"]["noise"]["duration_uniform_fraction"] = 0.0
    for toggle in scenario["assumptions"]["toggles"]:
        toggle["opponent_recapture_rate_per_s"] = 0.0
    result = Env(1, Capabilities(0.2, 0.4, 0.4), scenario)
    result.rng = FixedRng()
    return result


def move(env, site):
    if env.location != site:
        assert env.action_mask()[site]
        _, _, done, info = env.step(site)
        assert info["success"] and not done


def acquire(env, color=0, site=0):
    move(env, site)
    assert env.action_mask()[7 + color]
    return env.step(7 + color)


def place(env, color=0, goal=0):
    move(env, goal + 2)
    assert env.action_mask()[9 + color]
    return env.step(9 + color)


def add_cup(env, goal=0):
    move(env, 0)
    assert env.action_mask()[14]
    env.step(14)
    move(env, goal + 2)
    assert env.action_mask()[15]
    return env.step(15)


def test_exported_contract_and_json_safe_state(env):
    assert ACTION_COUNT == len(ACTION_NAMES) == 16
    assert ACTION_NAMES[7:14] == ("acquire_alliance", "acquire_yellow", "place_alliance", "place_yellow", "toggle", "wait", "park_and_wait")
    assert ACTION_NAMES[14:] == ("acquire_cup", "place_cup")
    assert OBS_SIZE == len(OBSERVATION_NAMES) == len(set(OBSERVATION_NAMES)) == 57
    assert len(CAPABILITY_NAMES) == 13
    for _ in range(3):
        obs, reward, done, info = env.step(12)
        assert obs.shape == (57,) and obs.dtype == np.float32
        assert np.all(np.isfinite(obs)) and np.all((obs >= 0) & (obs <= 1))
        assert env.action_mask().shape == (16,) and env.action_mask().dtype == np.bool_
        assert type(reward) is float and type(done) is bool
        json.dumps(info, allow_nan=False)
    json.dumps(env.trace, allow_nan=False)
    json.dumps(env.summary(), allow_nan=False)
    assert env.location == env.location_index == -1
    assert env.sites.shape == (7, 2) and env.stock.shape == env.goal_counts.shape == (2, 2)


def test_seeded_reproducibility_and_reset():
    a, b = Env(25), Env(25)
    chooser = np.random.default_rng(17)
    first = a.observe().copy()
    while not a.done:
        action = int(chooser.choice(np.flatnonzero(a.action_mask())))
        ao, ar, ad, ai = a.step(action)
        bo, br, bd, bi = b.step(action)
        np.testing.assert_array_equal(ao, bo)
        assert (ar, ad, ai) == (br, bd, bi)
    assert a.trace == b.trace and a.summary() == b.summary()
    assert a.reset(seed=25).dtype == np.float32
    np.testing.assert_array_equal(a.observe(), first)
    assert not a.trace and a.elapsed == 0 and not a.done


def test_opponent_schedule_is_policy_and_capability_independent():
    a = Env(127, Capabilities(0.7, 0.2, 0.1))
    b = Env(127, Capabilities(0.1, 0.2, 0.7))
    assert a._opponent_schedule == b._opponent_schedule
    assert any(a._opponent_schedule)
    for _ in range(10):
        a.step(12)
        b.step(0 if b.location != 0 else 1)
    assert a._opponent_schedule == b._opponent_schedule
    c = Env(128)
    assert a._opponent_schedule != c._opponent_schedule


def test_observation_has_hazards_and_cup_state_but_not_future_schedule(env):
    baseline = env.observe().copy()
    env._opponent_schedule = ((1.2345, 2.3456), (3.4567,))
    np.testing.assert_array_equal(env.observe(), baseline)
    env.opponent_hazard_rates[0] = 0.25
    env.inventory_cup = 1
    env.cup_stock[1] -= 1
    env.goal_counts[0, 0] = 1
    env.cup_ready[0] = True
    observed = dict(zip(OBSERVATION_NAMES, env.observe()))
    assert observed["toggle0_opponent_hazard"] == pytest.approx(0.2)
    assert observed["inventory_cup"] == 1
    assert observed["supply1_cups"] == pytest.approx(5 / 6)
    assert observed["goal0_cup_ready"] == 1


def test_capability_sampler_budget_and_minimum_goal_reach():
    for seed in range(200):
        caps = sample_capabilities(seed)
        caps.validate()
        assert sum((caps.drive, caps.handling, caps.lift)) == pytest.approx(1)
        assert min(caps.drive, caps.handling, caps.lift) >= 0
        assert caps.payload_capacity == 1
        assert caps.max_reach_m >= 0.32 > 0.28
        assert caps.drive_speed_m_s == pytest.approx(0.65 + 2 * caps.drive)
        assert caps.acquisition_seconds == pytest.approx(3.2 - 2 * caps.handling)
        assert caps.placement_seconds == pytest.approx(2.5 - 1.5 * caps.handling)
        assert caps.max_reach_m == pytest.approx(0.32 + 0.9 * caps.lift)
        vector = caps.vector()
        assert vector.shape == (13,) and vector.dtype == np.float32
        assert np.all((vector >= 0) & (vector <= 1))
        json.dumps(caps.to_dict(), allow_nan=False)
        assert caps == sample_capabilities(seed)
    assert sample_capabilities(1, 0.5) != sample_capabilities(1, 2.0)
    assert Capabilities(0, 1, 0).payload_capacity == 1


@pytest.mark.parametrize("allocation", [(1, 1, 1), (-0.1, 0.5, 0.6), (np.nan, 0, 1), (np.inf, 0, 0)])
def test_invalid_budget_rejected(allocation):
    with pytest.raises(ValueError):
        Capabilities(*allocation).validate()
    with pytest.raises(ValueError):
        Env(1, Capabilities(*allocation))


@pytest.mark.parametrize("concentration", [0, -1, np.nan, np.inf])
def test_invalid_dirichlet_concentration(concentration):
    with pytest.raises(ValueError):
        sample_capabilities(1, concentration)


def test_sg6_one_pin_and_one_cup_independently(env):
    acquire(env, 0)
    assert env.inventory.tolist() == [1, 0]
    assert not env.action_mask()[7] and not env.action_mask()[8]
    assert env.action_mask()[14]
    env.step(14)
    assert env.inventory_cup == 1 and env.inventory.sum() == 1
    assert not env.action_mask()[14]
    old_stock = env.stock.copy()
    start = env.elapsed
    _, reward, _, info = env.step(8)
    assert not info["valid_action"] and not info["success"] and reward == 0
    assert env.elapsed > start and env.inventory.sum() == 1 and env.inventory_cup == 1
    np.testing.assert_array_equal(env.stock, old_stock)


def test_sc2_successive_pin_requires_a_cup(env):
    acquire(env)
    _, reward, _, _ = place(env)
    assert reward == 5 and env.goal_counts[0, 0] == 1 and not env.cup_ready[0]
    acquire(env)
    move(env, 2)
    assert not env.action_mask()[9]
    start = env.elapsed
    env.step(9)
    assert env.elapsed > start and env.goal_counts[0, 0] == 1 and env.inventory[0] == 1
    _, cup_reward, _, info = add_cup(env)
    assert cup_reward == 0 and info["success"] and env.cup_ready[0]
    assert env.inventory_cup == 0 and env.goal_cup_counts.tolist() == [1, 0]
    assert not env.action_mask()[15] and env.action_mask()[9]
    _, reward, _, info = env.step(9)
    assert reward == 5 and env.score == 10 and not env.cup_ready[0]
    assert env.goal_counts[0, 0] == 2 and env.goal_cup_counts[0] == 1
    assert info["event"]["goal_height_m"] == pytest.approx(0.28 + 0.012)


def test_cup_cannot_be_placed_on_empty_goal_or_without_inventory(env):
    move(env, 2)
    assert not env.action_mask()[15]
    env.inventory_cup = 1
    assert not env.action_mask()[15]
    env.goal_counts[0, 0] = 1
    assert env.action_mask()[15]
    env.inventory_cup = 0
    assert not env.action_mask()[15]


def test_yellow_scoring_neutral_capture_loss_and_recapture(env):
    acquire(env, 1)
    _, reward, _, _ = place(env, 1)
    assert reward == 0 and env.score == 0  # Neutral toggle owns no yellow halves.
    move(env, 4)
    _, reward, _, _ = env.step(11)
    assert reward == 10 and env.score == 10
    assert not env.action_mask()[11]
    env._opponent_schedule = ((env.elapsed + 0.25,), ())
    _, reward, _, info = env.step(12)
    assert reward == -10 and env.score == 0 and env.toggle_owners[0] == -1
    assert len(info["event"]["details"]["opponent_recaptures"]) == 1
    _, reward, _, _ = env.step(11)
    assert reward == 10 and env.score == 10
    assert env.summary()["points_by_objective"]["owned_yellow_pin_halves"] == 10


def test_same_points_at_low_and_elevated_goals(env):
    for goal in (0, 1):
        acquire(env)
        _, reward, _, _ = place(env, goal=goal)
        assert reward == 5
    assert env.score == 10
    assert env.goal_height_m(0) == pytest.approx(0.292)
    assert env.goal_height_m(1) == pytest.approx(0.595)


def test_goal_reach_inventory_capacity_and_toggle_masks(env):
    assert env.action_mask()[12] and not env.action_mask()[7:12].any()
    move(env, 0)
    assert env.action_mask()[7:9].all() and not env.action_mask()[0]
    env.stock[0, 0] = 0
    assert not env.action_mask()[7] and env.action_mask()[8]
    env.inventory[1] = 1
    env.capabilities = Capabilities(0.5, 0.5, 0)
    move(env, 3)
    assert not env.action_mask()[10]  # Elevated goal is unreachable.
    move(env, 2)
    assert not env.action_mask()[9] and env.action_mask()[10]
    env.goal_counts[0] = [8, 0]
    env.cup_ready[0] = True
    env.inventory_cup = 1
    assert not env.action_mask()[9:11].any() and not env.action_mask()[15]
    move(env, 4)
    assert env.action_mask()[11]
    env.toggle_owners[0] = 1
    assert not env.action_mask()[11]


def test_height_increment_can_exhaust_reach(env):
    env.capabilities = Capabilities(0.5, 0.5, 0)
    move(env, 2)
    env.goal_counts[0, 0] = 4
    env.inventory[0] = 1
    env.inventory_cup = 1
    env.cup_ready[0] = True
    assert env.goal_height_m(0) == pytest.approx(0.328)
    assert env.capabilities.max_reach_m == 0.32
    assert not env.action_mask()[9] and not env.action_mask()[15]


def test_finite_cup_and_pin_supply_is_preserved(env):
    initial_pins = env.stock.sum(axis=0).copy()
    initial_cups = int(env.cup_stock.sum())
    for _ in range(3):
        acquire(env)
        move(env, 2)
        if env.goal_counts[0].sum():
            add_cup(env)
        env.step(9)
    np.testing.assert_array_equal(env.stock.sum(axis=0) + env.inventory + env.goal_counts.sum(axis=0), initial_pins)
    assert env.cup_stock.sum() + env.inventory_cup + env.goal_cup_counts.sum() == initial_cups
    move(env, 0)
    env.cup_stock[0] = 0
    assert not env.action_mask()[14]


@pytest.mark.parametrize("action", [7, 8, 9, 10, 11, 14, 15])
def test_failed_discrete_actions_cost_time_and_preserve_objects(env, action):
    if action in (7, 8, 14):
        move(env, 0)
    elif action in (9, 10, 15):
        move(env, 2)
        if action == 15:
            env.goal_counts[0, 0] = 1
            env.inventory_cup = 1
        else:
            env.inventory[action - 9] = 1
    else:
        move(env, 4)
    assert env.action_mask()[action]
    before = (env.inventory.copy(), env.stock.copy(), env.goal_counts.copy(), env.cup_stock.copy(), env.cup_ready.copy(), env.inventory_cup)
    env.rng = FixedRng(1.0)
    start = env.elapsed
    _, reward, _, info = env.step(action)
    assert env.elapsed > start and reward == 0 and not info["success"]
    assert info["event"]["details"]["failure_reason"] == "stochastic_failure"
    for old, new in zip(before, (env.inventory, env.stock, env.goal_counts, env.cup_stock, env.cup_ready, env.inventory_cup)):
        np.testing.assert_array_equal(old, new)


def test_failed_movement_costs_time_and_keeps_partial_progress(env):
    env.rng = FixedRng(1.0)
    start = env.position.copy()
    _, reward, _, info = env.step(0)
    traveled = np.linalg.norm(env.position - start)
    assert 0 < traveled < np.linalg.norm(env.sites[0] - start)
    assert env.elapsed > 0 and not info["success"] and reward == 0
    assert env.location == -1 and env.path_length_m == pytest.approx(traveled)


@pytest.mark.parametrize("action", [7, 8, 9, 10, 11, 14, 15])
def test_unfinished_discrete_actions_do_not_complete(env, action):
    if action in (7, 8, 14):
        move(env, 0)
    elif action in (9, 10, 15):
        move(env, 2)
        if action == 15:
            env.goal_counts[0, 0] = 1
            env.inventory_cup = 1
        else:
            env.inventory[action - 9] = 1
    else:
        move(env, 4)
    before_score = env.score
    before = (env.inventory.copy(), env.stock.copy(), env.goal_counts.copy(), env.cup_stock.copy(), env.cup_ready.copy(), env.inventory_cup)
    env.elapsed = 104.99
    _, reward, done, info = env.step(action)
    assert done and env.elapsed == 105 and not info["success"] and reward == 0
    assert env.score == before_score and info["duration_s"] == pytest.approx(0.01)
    assert info["event"]["details"]["failure_reason"] == "deadline"
    for old, new in zip(before, (env.inventory, env.stock, env.goal_counts, env.cup_stock, env.cup_ready, env.inventory_cup)):
        np.testing.assert_array_equal(old, new)


def test_deadline_movement_is_partial_and_cannot_gain_midfield(env):
    start = env.position.copy()
    duration = env.capabilities.turn_seconds + np.linalg.norm(env.sites[6] - start) / env.capabilities.drive_speed_m_s
    env.elapsed = 105 - duration / 2
    _, reward, done, info = env.step(6)
    assert done and not info["success"] and reward == 0 and not env.terminal_midfield
    assert 0 < np.linalg.norm(env.position - start) < np.linalg.norm(env.sites[6] - start)
    assert env.location == -1 and env.elapsed == 105


def test_deadline_during_turn_makes_no_movement(env):
    start = env.position.copy()
    env.elapsed = 104.99
    env.step(6)
    np.testing.assert_array_equal(start, env.position)
    assert env.path_length_m == 0


def test_arrival_exactly_at_deadline_earns_terminal_midfield(env):
    duration = env.capabilities.turn_seconds + np.linalg.norm(env.sites[6] - env.position) / env.capabilities.drive_speed_m_s
    env.elapsed = 105 - duration
    _, reward, done, info = env.step(6)
    assert done and info["success"] and reward == 8
    assert env.terminal_midfield and env.score == 8 and env.elapsed == 105


def test_park_window_terminal_scoring_and_late_recapture(env):
    move(env, 6)
    assert not env.action_mask()[13]
    env.goal_counts[0, 1] = 1
    env.toggle_owners[0] = 1
    env._opponent_schedule = ((100.0,), ())
    env.elapsed = 90.0
    assert env.action_mask()[13]
    _, reward, done, info = env.step(13)
    assert done and env.elapsed == 105 and env.terminal_midfield
    assert reward == -2 and env.score == 8  # Lose ten yellow points, gain eight midfield.
    assert info["duration_s"] == 15
    assert env.action_mask()[12] and env.action_mask().sum() == 1
    with pytest.raises(RuntimeError):
        env.step(12)


def test_wait_is_always_valid_and_ends_episode(env):
    while not env.done:
        assert env.action_mask()[12]
        env.step(12)
    assert env.steps == 140 and env.elapsed == 105 and env.score == 0
    assert env.action_mask()[12]


def test_invalid_actions_cannot_stall_episode(env):
    while not env.done:
        env.step(9)
    assert env.steps <= 256 and env.elapsed == 105
    assert not any(event["success"] for event in env.trace)


def test_horizon_advances_to_actual_final_ownership_and_midfield(env):
    move(env, 6)
    env.goal_counts[0, 1] = 1
    env.toggle_owners[0] = 1
    env._opponent_schedule = ((104.0,), ())
    env.steps = 255
    start = env.elapsed
    _, reward, done, info = env.step(12)
    assert done and env.steps == 256 and env.elapsed == 105
    assert env.score == 8 and reward == -2 and env.terminal_midfield
    assert info["duration_s"] == pytest.approx(105 - start)
    assert info["event"]["details"]["termination_reason"] == "step_horizon"


@pytest.mark.parametrize("action", [-1, 16, 1.5, True, "wait"])
def test_invalid_action_types_rejected_without_mutation(env, action):
    with pytest.raises(ValueError):
        env.step(action)
    assert env.elapsed == 0 and env.steps == 0


def test_real_rng_produces_failures_and_conserves_score():
    saw_success = saw_failure = False
    for seed in range(10):
        current = Env(seed)
        chooser = np.random.default_rng(seed + 900)
        reward_sum = 0.0
        initial_pins = current.stock.sum(axis=0).copy()
        initial_cups = current.cup_stock.sum()
        while not current.done:
            action = int(chooser.choice(np.flatnonzero(current.action_mask())))
            _, reward, _, info = current.step(action)
            reward_sum += reward
            saw_success |= info["success"]
            saw_failure |= info["event"]["details"].get("failure_reason") == "stochastic_failure"
            assert current.inventory.sum() <= 1 and current.inventory_cup <= 1
            assert np.all(current.stock >= 0) and np.all(current.cup_stock >= 0)
            assert reward_sum == pytest.approx(current.score)
            np.testing.assert_array_equal(current.stock.sum(axis=0) + current.inventory + current.goal_counts.sum(axis=0), initial_pins)
            assert current.cup_stock.sum() + current.inventory_cup + current.goal_cup_counts.sum() == initial_cups
        assert current.steps <= 256 and current.elapsed == 105
        assert sum(current.summary()["points_by_objective"].values()) == current.score
        assert sum(current.summary()["action_counts"].values()) == current.steps
        json.dumps(current.summary(), allow_nan=False)
        json.dumps(current.trace, allow_nan=False)
    assert saw_success and saw_failure


def test_scenario_copy_sources_and_rules(env):
    scenario = deepcopy(env.scenario)
    clone = Env(2, scenario=scenario)
    scenario["assumptions"]["supplies"][0]["alliance"] = 999
    assert clone.stock[0, 0] == 8
    facts = clone.scenario["official_facts"]
    assert facts["alliance_pin_half_points"] == 5 and facts["owned_yellow_pin_half_points"] == 10
    assert {"SG6", "SC2", "SC3", "SC4", "SC5"} <= facts["rule_sources"].keys()
    assert "cups" not in clone.scenario["excluded"]


def test_reset_explicit_capabilities_and_seed(env):
    caps = Capabilities(0.1, 0.8, 0.1)
    env.step(12)
    env.reset(seed=55, capabilities=caps)
    assert env.seed == 55 and env.capabilities == caps
    env.reset(seed=56)
    assert env.capabilities == caps and env.elapsed == 0


@pytest.mark.parametrize("seed", [-1, 1.5, True])
def test_invalid_seed(seed):
    with pytest.raises(ValueError):
        Env(seed)
