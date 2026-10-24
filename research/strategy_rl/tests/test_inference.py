from pathlib import Path

import numpy as np
import pytest
import torch

from tachyon_strategy_rl.environment import Env
from tachyon_strategy_rl.inference import PolicyInference, validated_policy
from tachyon_strategy_rl.ppo import TrainConfig, train


@pytest.fixture(scope="module")
def policy_path(tmp_path_factory):
    root = tmp_path_factory.mktemp("real-neural-inference")
    train(TrainConfig(total_steps=64, environments=4, rollout_steps=16, epochs=1, minibatch_size=32), root,
          progress=lambda *a, **kw: None)
    return root / "checkpoint.pt"


def test_inference_loads_real_updated_weights_and_returns_legal_probabilities(policy_path):
    engine = PolicyInference(policy_path)
    env = Env(seed=18)
    observation, mask = env.observe(), env.action_mask()
    result = engine.act(observation, mask)
    assert mask[result["actionId"]]
    assert sum(result["probabilities"]) == pytest.approx(1.)
    assert all(p == 0 for p, legal in zip(result["probabilities"], mask) if not legal)
    assert result["performanceDomain"] == "abstract_simulation_only"
    assert result == engine.act(observation, mask)


def test_untrained_and_incompatible_inputs_are_refused(policy_path):
    with pytest.raises(ValueError, match="untrained"):
        validated_policy(policy_path.with_name("initial.pt"))
    engine = PolicyInference(policy_path)
    env = Env(seed=2)
    with pytest.raises(ValueError): engine.act([0.], env.action_mask())
    with pytest.raises(ValueError): engine.act(env.observe(), np.zeros_like(env.action_mask()))
    broken = env.observe(); broken[0] = float("nan")
    with pytest.raises(ValueError): engine.act(broken, env.action_mask())


@pytest.mark.parametrize("source", ["environment.py", "scenario.json", "ppo.py"])
def test_changed_model_or_environment_fingerprints_block_inference(policy_path, tmp_path, source):
    checkpoint = torch.load(policy_path, map_location="cpu", weights_only=True)
    checkpoint["sourceFingerprints"][source] = "0"*64
    modified = tmp_path / "incompatible.pt"
    torch.save(checkpoint, modified)
    with pytest.raises(ValueError, match="reevaluation/retraining"):
        validated_policy(modified)
