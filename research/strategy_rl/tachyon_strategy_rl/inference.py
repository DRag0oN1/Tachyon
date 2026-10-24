"""Inference gate for the isolated learned policy and its exact environment."""
import hashlib
from pathlib import Path

import numpy as np
import torch

from .environment import ACTION_NAMES, OBSERVATION_NAMES
from .ppo import load_policy


def validated_policy(path: Path, *, require_trained=True):
    model, checkpoint = load_policy(path)
    for name in ("environment.py", "scenario.json", "ppo.py"):
        current = hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        if checkpoint["sourceFingerprints"].get(name) != current:
            raise ValueError("Environment, scenario or neural implementation changed; this checkpoint requires reevaluation/retraining")
    if require_trained and (checkpoint["gradientUpdates"] < 1 or checkpoint["parameterHash"] == checkpoint["initialParameterHash"]):
        raise ValueError("An untrained network cannot be reported as a learned policy")
    return model, checkpoint


class PolicyInference:
    def __init__(self, path: Path):
        torch.set_num_threads(1)
        self.model, self.checkpoint = validated_policy(path)

    def act(self, observation, action_mask):
        observation = np.asarray(observation, dtype=np.float32)
        mask = np.asarray(action_mask)
        if observation.shape != (len(OBSERVATION_NAMES),) or not np.isfinite(observation).all():
            raise ValueError("Observation must follow the finite versioned game-state contract")
        if np.any(observation < -1e-6) or np.any(observation > 1+1e-6):
            raise ValueError("Observation is outside the normalized model domain")
        if mask.shape != (len(ACTION_NAMES),) or mask.dtype != np.bool_ or not mask.any():
            raise ValueError("Supply the environment's boolean legal-action mask")
        with torch.no_grad():
            distribution, value = self.model.distribution(torch.from_numpy(observation).unsqueeze(0), torch.from_numpy(mask).unsqueeze(0))
            probabilities = distribution.probs[0].tolist()
        action = int(np.argmax(probabilities))
        return {"actionId": action, "action": ACTION_NAMES[action], "probabilities": probabilities,
                "estimatedModeledReturn": float(value[0])/self.checkpoint["config"]["reward_scale"],
                "policyParameterHash": self.checkpoint["parameterHash"],
                "performanceDomain": "abstract_simulation_only"}
