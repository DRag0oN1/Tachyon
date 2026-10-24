"""Isolated, abstract Override strategy environment; only stdlib and NumPy.

The accompanying scenario separates verified scoring facts from authored model
assumptions. Capabilities are sampled before play, never inferred from CAD.
Rewards are unscaled score differences. This module does not train a policy.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import json
import math
from numbers import Integral
from pathlib import Path
from typing import Any

import numpy as np


SITE_NAMES = ("supply0", "supply1", "goal0", "goal1", "toggle0", "toggle1", "midfield")
ACTION_NAMES = tuple(f"move_to_{name}" for name in SITE_NAMES) + (
    "acquire_alliance", "acquire_yellow", "place_alliance", "place_yellow",
    "toggle", "wait", "park_and_wait", "acquire_cup", "place_cup",
)
ACTION_COUNT = len(ACTION_NAMES)
CAPABILITY_NAMES = (
    "drive_allocation", "handling_allocation", "lift_allocation",
    "drive_speed_m_s", "acquisition_seconds", "placement_seconds",
    "acquisition_success_probability", "placement_success_probability",
    "movement_success_probability", "toggle_success_probability",
    "payload_capacity", "max_reach_m", "turn_seconds",
)
OBSERVATION_NAMES = (
    "time_remaining_fraction", "steps_remaining_fraction", "position_x", "position_y",
    "inventory_alliance", "inventory_yellow",
    "supply0_alliance", "supply0_yellow", "supply1_alliance", "supply1_yellow",
    "goal0_alliance", "goal0_yellow", "goal1_alliance", "goal1_yellow",
    "toggle0_owner", "toggle1_owner",
) + CAPABILITY_NAMES + (
    "goal0_required_reach", "goal1_required_reach", "goal0_reachable", "goal1_reachable",
    "goal0_remaining_capacity", "goal1_remaining_capacity",
) + tuple(f"distance_to_{name}" for name in SITE_NAMES) + tuple(
    f"at_{name}" for name in SITE_NAMES
) + ("toggle0_opponent_hazard", "toggle1_opponent_hazard", "terminal",
     "inventory_cup", "supply0_cups", "supply1_cups", "goal0_cup_ready", "goal1_cup_ready")
OBS_SIZE = len(OBSERVATION_NAMES)
_EPS = 1e-9


@dataclass(frozen=True)
class Capabilities:
    """Feasible abstract budget; derived features cannot be tuned independently."""

    drive: float
    handling: float
    lift: float

    def validate(self) -> None:
        allocation = np.asarray([self.drive, self.handling, self.lift], dtype=float)
        if not np.all(np.isfinite(allocation)) or np.any(allocation < 0):
            raise ValueError("Capability allocations must be finite and nonnegative")
        if np.any(allocation > 1) or not math.isclose(float(allocation.sum()), 1.0, abs_tol=1e-8):
            raise ValueError("Abstract drive/handling/lift budget must sum to one")

    @property
    def drive_speed_m_s(self) -> float:
        return 0.65 + 2.0 * self.drive

    @property
    def acquisition_seconds(self) -> float:
        return 3.2 - 2.0 * self.handling

    @property
    def placement_seconds(self) -> float:
        return 2.5 - 1.5 * self.handling

    @property
    def acquisition_success_probability(self) -> float:
        return 0.70 + 0.28 * self.handling

    @property
    def placement_success_probability(self) -> float:
        return 0.70 + 0.28 * self.handling + 0.02 * self.lift

    @property
    def movement_success_probability(self) -> float:
        return 0.94 + 0.05 * self.drive

    @property
    def toggle_success_probability(self) -> float:
        return 0.85 + 0.10 * self.handling + 0.05 * self.lift

    @property
    def payload_capacity(self) -> int:
        return 1

    @property
    def max_reach_m(self) -> float:
        return 0.32 + 0.90 * self.lift

    @property
    def turn_seconds(self) -> float:
        return 0.20 + 0.50 * (1.0 - self.drive)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allocation": {"drive": float(self.drive), "handling": float(self.handling), "lift": float(self.lift)},
            "drive_allocation": float(self.drive), "handling_allocation": float(self.handling),
            "lift_allocation": float(self.lift),
            **{name: (int(getattr(self, name)) if name == "payload_capacity" else float(getattr(self, name)))
               for name in CAPABILITY_NAMES[3:]},
        }

    def vector(self) -> np.ndarray:
        """13 float32 features, normalized to [0, 1] in CAPABILITY_NAMES order."""
        return np.asarray([
            self.drive, self.handling, self.lift, self.drive_speed_m_s / 2.65,
            self.acquisition_seconds / 3.2, self.placement_seconds / 2.5,
            self.acquisition_success_probability, self.placement_success_probability,
            self.movement_success_probability, self.toggle_success_probability,
            float(self.payload_capacity), self.max_reach_m / 1.22, self.turn_seconds / 0.7,
        ], dtype=np.float32)


def sample_capabilities(seed: int, concentration: float = 2.0) -> Capabilities:
    if not math.isfinite(concentration) or concentration <= 0:
        raise ValueError("Dirichlet concentration must be finite and positive")
    allocation = np.random.default_rng(seed).dirichlet(np.full(3, concentration))
    capabilities = Capabilities(*map(float, allocation))
    capabilities.validate()
    return capabilities


class Env:
    """Semi-Markov actions in an authored seven-site, 105-second scenario.

    ``location_index`` is -1 between sites; owners are -1 opponent, 0 neutral,
    +1 ours. Each pin token counts one visible half (SC3 abstraction), not
    an entire pin's possible halves. Carry at most one pin plus one cup (SG6).
    Repeated pin placement requires an intervening cup (SC2).
    ``info['duration_s']`` includes any horizon-ending wait. A
    masked action safely consumes a wait interval; step after done raises.
    """

    def __init__(self, seed: int, capabilities: Capabilities | None = None, scenario: dict | None = None):
        if scenario is None:
            scenario = json.loads(Path(__file__).with_name("scenario.json").read_text())
        self.scenario = deepcopy(scenario)
        self._cfg = self.scenario["assumptions"]
        self._facts = self.scenario["official_facts"]
        self.episode_seconds = float(self._facts["driver_seconds"])
        self.field_side_m = float(self._facts["field_side_m"])
        self.max_steps = self._cfg["max_steps"]
        self.sites = np.asarray([site["xy_m"] for site in self._cfg["sites"]], dtype=float)
        self._validate_scenario()
        self._initial_stock = np.asarray([
            [supply["alliance"], supply["yellow"]] for supply in self._cfg["supplies"]
        ], dtype=np.int64)
        self._initial_cup_stock = np.asarray([supply["cups"] for supply in self._cfg["supplies"]], dtype=np.int64)
        self._goal_capacities = np.asarray([goal["capacity"] for goal in self._cfg["goals"]], dtype=np.int64)
        self.opponent_hazard_rates = np.asarray([
            toggle["opponent_recapture_rate_per_s"] for toggle in self._cfg["toggles"]
        ], dtype=float)
        self._fixed_capabilities = capabilities
        self.reset(seed=seed, capabilities=capabilities)

    def _validate_scenario(self) -> None:
        if self.episode_seconds != 105.0 or self.field_side_m != 3.6576:
            raise ValueError("This bounded scenario requires 105 seconds and a 3.6576 m field")
        if [self._facts[k] for k in ("alliance_pin_half_points", "owned_yellow_pin_half_points", "terminal_midfield_points")] != [5, 10, 8]:
            raise ValueError("The bounded Override scoring facts must remain 5, 10, 8")
        if not isinstance(self.max_steps, Integral) or not 1 <= self.max_steps <= 256:
            raise ValueError("max_steps must be an integer in [1, 256]")
        if self.sites.shape != (7, 2) or not np.all(np.isfinite(self.sites)) or np.any(self.sites < 0) or np.any(self.sites > self.field_side_m):
            raise ValueError("Exactly seven finite sites must lie inside the field")
        if tuple(site["name"] for site in self._cfg["sites"]) != SITE_NAMES:
            raise ValueError("Site order must match SITE_NAMES")
        if len({tuple(xy) for xy in self.sites}) != 7:
            raise ValueError("Sites must have distinct coordinates")
        start = np.asarray(self._cfg["start_xy_m"], dtype=float)
        if start.shape != (2,) or not np.all(np.isfinite(start)) or np.any(start < 0) or np.any(start > self.field_side_m):
            raise ValueError("The start position must lie inside the field")
        if len(self._cfg["supplies"]) != 2 or len(self._cfg["goals"]) != 2 or len(self._cfg["toggles"]) != 2:
            raise ValueError("Require two supplies, two goals, and two toggles")
        for i, supply in enumerate(self._cfg["supplies"]):
            if supply["site_index"] != i or any(not isinstance(supply[k], Integral) or supply[k] < 0 for k in ("alliance", "yellow", "cups")):
                raise ValueError("Supply counts must be finite nonnegative integers in site order")
        for i, goal in enumerate(self._cfg["goals"]):
            if goal["site_index"] != i + 2 or goal["toggle_index"] != i:
                raise ValueError("Each goal maps to its matching abstract toggle")
            if not isinstance(goal["capacity"], Integral) or goal["capacity"] < 1:
                raise ValueError("Goal capacity must be a positive integer")
            if any(not math.isfinite(goal[k]) or goal[k] < 0 for k in ("base_height_m", "height_per_pin_m")):
                raise ValueError("Goal heights must be finite and nonnegative")
        for i, toggle in enumerate(self._cfg["toggles"]):
            rate = toggle["opponent_recapture_rate_per_s"]
            if toggle["site_index"] != i + 4 or toggle["initial_owner"] not in (-1, 0, 1) or not math.isfinite(rate) or not 0 <= rate <= 10:
                raise ValueError("Invalid toggle owner, site, or opponent hazard (allowed 0..10/s)")
        if self._cfg["wait_seconds"] not in (0.75, 1.0):
            raise ValueError("wait_seconds must be 0.75 or 1.0")
        if self._cfg["park_window_seconds"] != 15.0 or not math.isfinite(self._cfg["toggle_seconds"]) or self._cfg["toggle_seconds"] <= 0:
            raise ValueError("Require a 15-second park window and positive toggle duration")
        noise = self._cfg["noise"]
        if not math.isfinite(noise["duration_uniform_fraction"]) or not 0 <= noise["duration_uniform_fraction"] < 1:
            raise ValueError("Duration noise must be in [0, 1)")
        lo, hi = noise["failed_move_progress_fraction"]
        if not 0 <= lo <= hi < 1:
            raise ValueError("Failed movement progress must be a fraction below one")
        if not noise["failed_acquisition_preserves_stock"] or not noise["failed_placement_preserves_inventory"]:
            raise ValueError("This model preserves pins on failed acquisition/placement")

    def reset(self, seed: int | None = None, capabilities: Capabilities | None = None) -> np.ndarray:
        if seed is not None:
            if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
                raise ValueError("seed must be a nonnegative integer")
            self.seed = int(seed)
        elif not hasattr(self, "seed"):
            raise ValueError("An initial seed is required")
        if capabilities is not None:
            capabilities.validate()
            self._fixed_capabilities = capabilities
        self.capabilities = self._fixed_capabilities or sample_capabilities(self.seed)
        self.capabilities.validate()
        action_seed, opponent_seed = np.random.SeedSequence(self.seed).spawn(2)
        self.rng = np.random.default_rng(action_seed)
        opponent_streams = opponent_seed.spawn(2)
        schedules = []
        for rate, stream in zip(self.opponent_hazard_rates, opponent_streams):
            event_rng = np.random.default_rng(stream)
            arrivals: list[float] = []
            when = 0.0
            if rate > 0:
                while True:
                    when += float(event_rng.exponential(1.0 / rate))
                    if when > self.episode_seconds:
                        break
                    arrivals.append(when)
            schedules.append(tuple(arrivals))
        self._opponent_schedule = tuple(schedules)
        self._opponent_cursors = [0, 0]
        self.elapsed = 0.0
        self.steps = 0
        self.done = False
        self.position = np.asarray(self._cfg["start_xy_m"], dtype=float).copy()
        self.inventory = np.zeros(2, dtype=np.int64)
        self.inventory_cup = 0
        self.stock = self._initial_stock.copy()
        self.cup_stock = self._initial_cup_stock.copy()
        self.goal_counts = np.zeros((2, 2), dtype=np.int64)
        self.cup_ready = np.zeros(2, dtype=np.bool_)
        self.toggle_owners = np.asarray([toggle["initial_owner"] for toggle in self._cfg["toggles"]], dtype=np.int64)
        self.path_length_m = 0.0
        self.terminal_midfield = False
        self.trace: list[dict[str, Any]] = []
        self._action_counts: Counter[str] = Counter()
        return self.observe()

    @property
    def location_index(self) -> int:
        matches = np.flatnonzero(np.linalg.norm(self.sites - self.position, axis=1) <= _EPS)
        return int(matches[0]) if len(matches) else -1

    @property
    def location(self) -> int:
        """Public heuristic alias: -1 between sites, otherwise site index 0..6."""
        return self.location_index

    @property
    def goal_cup_counts(self) -> np.ndarray:
        """Placed cups derived from the enforced alternating stack invariant."""
        return np.maximum(0, self.goal_counts.sum(axis=1) - 1) + self.cup_ready.astype(np.int64)

    @property
    def score(self) -> float:
        return float(sum(self._points_by_objective().values()))

    def _points_by_objective(self) -> dict[str, int]:
        return {
            "alliance_pin_halves": int(self.goal_counts[:, 0].sum()) * self._facts["alliance_pin_half_points"],
            "owned_yellow_pin_halves": sum(int(self.goal_counts[i, 1]) for i in range(2) if self.toggle_owners[i] == 1) * self._facts["owned_yellow_pin_half_points"],
            "terminal_midfield": int(self.terminal_midfield) * self._facts["terminal_midfield_points"],
        }

    def goal_height_m(self, goal_index: int) -> float:
        goal = self._cfg["goals"][goal_index]
        return float(goal["base_height_m"] + goal["height_per_pin_m"] * int(self.goal_counts[goal_index].sum()))

    def action_mask(self) -> np.ndarray:
        mask = np.zeros(ACTION_COUNT, dtype=np.bool_)
        mask[12] = True  # The fallback action remains defined even at terminal.
        if self.done:
            return mask
        location = self.location_index
        mask[:7] = True
        if location >= 0:
            mask[location] = False
        if location in (0, 1) and int(self.inventory.sum()) < self.capabilities.payload_capacity:
            mask[7:9] = self.stock[location] > 0
        if location in (0, 1) and self.inventory_cup < 1:
            mask[14] = self.cup_stock[location] > 0
        if location in (2, 3):
            goal = location - 2
            if self.goal_counts[goal].sum() < self._goal_capacities[goal] and self.goal_height_m(goal) <= self.capabilities.max_reach_m + _EPS:
                count = int(self.goal_counts[goal].sum())
                if count == 0 or self.cup_ready[goal]:
                    mask[9:11] = self.inventory > 0
                mask[15] = count >= 1 and not self.cup_ready[goal] and self.inventory_cup == 1
        if location in (4, 5):
            mask[11] = self.toggle_owners[location - 4] != 1
        mask[13] = location == 6 and self.elapsed >= self.episode_seconds - self._cfg["park_window_seconds"] - _EPS
        return mask

    def observe(self) -> np.ndarray:
        """Complete visible decision state; future opponent arrivals are hidden.

        Owners map -1/0/+1 to 0/.5/1. Distances use the field diagonal, stocks
        their initial counts, goal counts/capacities their capacity, and reach
        1.22 m. Hazards use r/(1+r), which preserves the exact rate. No history
        or heading affects transitions; each move has fresh turn overhead.
        """
        heights = [self.goal_height_m(i) for i in range(2)]
        location = self.location_index
        observation = np.concatenate((
            [max(0.0, 1.0 - self.elapsed / self.episode_seconds), max(0.0, 1.0 - self.steps / self.max_steps)],
            self.position / self.field_side_m,
            self.inventory / self.capabilities.payload_capacity,
            (self.stock / np.maximum(1, self._initial_stock)).ravel(),
            (self.goal_counts / self._goal_capacities[:, None]).ravel(),
            (self.toggle_owners + 1) / 2,
            self.capabilities.vector(),
            np.asarray(heights) / 1.22,
            [float(height <= self.capabilities.max_reach_m + _EPS) for height in heights],
            1.0 - self.goal_counts.sum(axis=1) / self._goal_capacities,
            np.linalg.norm(self.sites - self.position, axis=1) / (self.field_side_m * math.sqrt(2)),
            [float(location == i) for i in range(7)],
            self.opponent_hazard_rates / (1.0 + self.opponent_hazard_rates),
            [float(self.done)],
            [float(self.inventory_cup)],
            self.cup_stock / np.maximum(1, self._initial_cup_stock),
            self.cup_ready.astype(float),
        )).astype(np.float32)
        assert observation.shape == (OBS_SIZE,)
        return observation

    def _advance(self, end_s: float) -> list[dict[str, Any]]:
        events = []
        for toggle, schedule in enumerate(self._opponent_schedule):
            cursor = self._opponent_cursors[toggle]
            while cursor < len(schedule) and schedule[cursor] <= end_s:
                old_owner = int(self.toggle_owners[toggle])
                self.toggle_owners[toggle] = -1
                events.append({"time_s": float(schedule[cursor]), "toggle_index": toggle, "owner_before": old_owner, "owner_after": -1})
                cursor += 1
            self._opponent_cursors[toggle] = cursor
        self.elapsed = float(end_s)
        return sorted(events, key=lambda event: (event["time_s"], event["toggle_index"]))

    def _duration(self, nominal: float) -> float:
        fraction = self._cfg["noise"]["duration_uniform_fraction"]
        return float(nominal * self.rng.uniform(1.0 - fraction, 1.0 + fraction))

    def step(self, action: int) -> tuple[np.ndarray, float, bool, dict[str, Any]]:
        if self.done:
            raise RuntimeError("Episode is done; call reset before stepping again")
        if isinstance(action, bool) or not isinstance(action, Integral) or not 0 <= action < ACTION_COUNT:
            raise ValueError("action must be an integer in [0, 15]")
        action = int(action)
        valid = bool(self.action_mask()[action])
        start = float(self.elapsed)
        before_score = self.score
        before_xy = self.position.copy()
        before_inventory = self.inventory.tolist()
        before_cup = int(self.inventory_cup)
        location_before = self.location_index
        goal_index = location_before - 2 if location_before in (2, 3) and action in (9, 10, 15) else None
        goal_height = self.goal_height_m(goal_index) if goal_index is not None else None
        details: dict[str, Any] = {"valid_action": valid, "location_before": location_before}
        target_xy = self.position.copy()
        move_fraction = 0.0
        probability = 1.0
        turn_duration = 0.0
        if not valid:
            duration = float(self._cfg["wait_seconds"])
            details["failure_reason"] = "masked_action"
        elif action < 7:
            target_xy = self.sites[action].copy()
            distance = float(np.linalg.norm(target_xy - self.position))
            travel = distance / self.capabilities.drive_speed_m_s
            duration = self._duration(self.capabilities.turn_seconds + travel)
            turn_duration = duration * self.capabilities.turn_seconds / (self.capabilities.turn_seconds + travel)
            probability = self.capabilities.movement_success_probability
        elif action in (7, 8, 14):
            duration = self._duration(self.capabilities.acquisition_seconds)
            probability = self.capabilities.acquisition_success_probability
        elif action in (9, 10, 15):
            duration = self._duration(self.capabilities.placement_seconds)
            probability = self.capabilities.placement_success_probability
        elif action == 11:
            duration = self._duration(self._cfg["toggle_seconds"])
            probability = self.capabilities.toggle_success_probability
        elif action == 13:
            duration = self.episode_seconds - self.elapsed
        else:
            duration = float(self._cfg["wait_seconds"])
        completes = duration <= self.episode_seconds - start + _EPS
        actual_duration = min(duration, self.episode_seconds - start)
        # A deadline-interrupted discrete action has no acquisition/placement effect.
        sampled_success = valid and (probability >= 1.0 or float(self.rng.random()) < probability)
        success = bool(sampled_success and completes)
        if valid and action < 7:
            progress_limit = 1.0 if sampled_success else float(self.rng.uniform(*self._cfg["noise"]["failed_move_progress_fraction"]))
            move_fraction = progress_limit * min(1.0, max(0.0, actual_duration - turn_duration) / max(_EPS, duration - turn_duration))
            self.position = before_xy + (target_xy - before_xy) * move_fraction
            if success:
                self.position = target_xy.copy()
            self.path_length_m += float(np.linalg.norm(self.position - before_xy))
            details.update({"target_site_index": action, "movement_fraction": float(move_fraction)})
        recaptures = self._advance(min(self.episode_seconds, start + actual_duration))
        if success:
            if action in (7, 8):
                color = action - 7
                self.stock[location_before, color] -= 1
                self.inventory[color] += 1
            elif action in (9, 10):
                color = action - 9
                self.inventory[color] -= 1
                self.goal_counts[goal_index, color] += 1
                self.cup_ready[goal_index] = False
            elif action == 11:
                self.toggle_owners[location_before - 4] = 1
            elif action == 14:
                self.cup_stock[location_before] -= 1
                self.inventory_cup += 1
            elif action == 15:
                self.inventory_cup -= 1
                self.cup_ready[goal_index] = True
        if not completes:
            details["failure_reason"] = "deadline"
        elif valid and not sampled_success:
            details["failure_reason"] = "stochastic_failure"
        details.update({"planned_duration_s": float(duration), "completed": bool(completes), "success_probability": float(probability)})
        self.steps += 1
        self._action_counts[ACTION_NAMES[action]] += 1
        horizon_reached = self.steps >= self.max_steps
        if horizon_reached and self.elapsed < self.episode_seconds:
            details["horizon_wait_s"] = float(self.episode_seconds - self.elapsed)
            recaptures.extend(self._advance(self.episode_seconds))
        self.done = bool(self.elapsed >= self.episode_seconds - _EPS or horizon_reached or (valid and action == 13))
        if self.done:
            # Snap only the clock; never finish a discrete action on the robot's behalf.
            self.elapsed = self.episode_seconds
            self.terminal_midfield = self.location_index == 6
            details["termination_reason"] = "park_and_wait" if valid and action == 13 else ("step_horizon" if horizon_reached else "time_limit")
        after_score = self.score
        reward = float(after_score - before_score)
        details["opponent_recaptures"] = recaptures
        event = {
            "action": ACTION_NAMES[action], "action_id": action,
            "start_s": start, "end_s": float(self.elapsed),
            "from_xy": before_xy.tolist(), "to_xy": self.position.tolist(),
            "success": success, "score_before": before_score, "score_after": after_score,
            "reward": reward, "location_index": self.location_index,
            "inventory_before": before_inventory, "inventory_after": self.inventory.tolist(),
            "inventory_cup_before": before_cup, "inventory_cup_after": int(self.inventory_cup),
            "goal_index": goal_index, "goal_height_m": goal_height, "details": details,
        }
        self.trace.append(event)
        info = {
            "duration_s": float(self.elapsed - start), "elapsed": float(self.elapsed),
            "score": after_score, "valid_action": valid, "success": success,
            "action_mask": self.action_mask().tolist(), "event": deepcopy(event),
        }
        return self.observe(), reward, self.done, info

    def summary(self) -> dict[str, Any]:
        """JSON-safe current score accounting; event detail lives in ``trace``."""
        return {
            "seed": self.seed, "scenario": self.scenario["name"], "abstract_model": True,
            "score": self.score, "capabilities": self.capabilities.to_dict(),
            "points_by_objective": self._points_by_objective(),
            "action_counts": {name: int(self._action_counts[name]) for name in ACTION_NAMES},
            "goal_counts": [{"alliance": int(counts[0]), "yellow": int(counts[1])} for counts in self.goal_counts],
            "goal_count_unit": "pin tokens with exactly one counted visible half per token",
            "goal_cup_counts": self.goal_cup_counts.tolist(), "cup_ready": self.cup_ready.tolist(),
            "terminal_midfield": bool(self.terminal_midfield),
            "path_length_m": float(self.path_length_m), "elapsed": float(self.elapsed),
            "steps": int(self.steps), "done": bool(self.done),
            "inventory": self.inventory.tolist(), "stock": self.stock.tolist(),
            "inventory_cup": int(self.inventory_cup), "cup_stock": self.cup_stock.tolist(),
            "toggle_owners": self.toggle_owners.tolist(),
        }
