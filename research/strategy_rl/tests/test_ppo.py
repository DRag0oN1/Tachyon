from pathlib import Path

import numpy as np
import pytest
import torch

from tachyon_strategy_rl.environment import ACTION_NAMES, OBSERVATION_NAMES, Env
from tachyon_strategy_rl.ppo import ActorCritic, TrainConfig, generalized_advantages, load_policy, parameter_hash, train


def test_gae_matches_undiscounted_returns_and_stops_at_episode_boundaries():
    reward = torch.tensor([[1.], [2.], [10.]])
    values = torch.tensor([[.4], [.8], [3.]])
    done = torch.tensor([[0.], [1.], [0.]])
    advantages, returns = generalized_advantages(reward, values, done, torch.tensor([4.]), 1., 1.)
    torch.testing.assert_close(returns[:, 0], torch.tensor([3., 2., 14.]))
    torch.testing.assert_close(advantages, returns-values)


def test_actor_is_neural_and_never_samples_masked_actions():
    torch.manual_seed(7)
    model = ActorCritic()
    obs = torch.zeros((128, len(OBSERVATION_NAMES)))
    mask = torch.zeros((128, len(ACTION_NAMES)), dtype=torch.bool); mask[:, 12] = True
    distribution, values = model.distribution(obs, mask)
    assert distribution.sample().tolist() == [12]*128
    assert values.shape == (128,)
    assert sum(p.numel() for p in model.parameters()) > 5000
    with pytest.raises(ValueError): model.distribution(obs, torch.zeros_like(mask))


def test_actual_on_policy_updates_change_weights_and_checkpoint_round_trips(tmp_path):
    config = TrainConfig(total_steps=128, environments=4, rollout_steps=16, epochs=2, minibatch_size=32)
    model, report = train(config, tmp_path / "run", progress=lambda *args, **kwargs: None)
    assert report["gradientUpdates"] == 8
    assert report["parameterDeltaL2"] > 0
    assert report["gradientNorm"] > 0
    assert report["initialParameterHash"] != report["finalParameterHash"]
    loaded, checkpoint = load_policy(tmp_path / "run/checkpoint.pt")
    assert parameter_hash(loaded) == parameter_hash(model)
    env = Env(seed=3)
    obs = torch.from_numpy(env.observe()).unsqueeze(0)
    mask = torch.from_numpy(env.action_mask()).unsqueeze(0)
    with torch.no_grad():
        before, _ = model.distribution(obs, mask); after, _ = loaded.distribution(obs, mask)
    torch.testing.assert_close(before.probs, after.probs)
    assert checkpoint["steps"] == 128
    assert checkpoint["optimizerState"]["state"]
    with pytest.raises(ValueError): train(config, tmp_path / "run")


def test_same_seed_reproduces_neural_training_parameters(tmp_path):
    config = TrainConfig(total_steps=64, environments=4, rollout_steps=16, epochs=1, minibatch_size=32)
    first, _ = train(config, tmp_path / "a", progress=lambda *a, **kw: None)
    second, _ = train(config, tmp_path / "b", progress=lambda *a, **kw: None)
    assert parameter_hash(first) == parameter_hash(second)


def test_config_rejects_partial_batches():
    with pytest.raises(ValueError): TrainConfig(total_steps=101).validate()
