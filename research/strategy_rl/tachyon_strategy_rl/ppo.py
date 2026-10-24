"""Neural clipped PPO with on-policy samples, GAE and real Adam updates.

The policy receives game observations and sampled abstract capability vectors,
never CAD designs, assembly identities or pre-ranked action sequences.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import time

import numpy as np
import torch
from torch import nn
from torch.distributions import Categorical

from .environment import ACTION_NAMES, OBSERVATION_NAMES, Env, sample_capabilities


@dataclass(frozen=True)
class TrainConfig:
    seed: int = 17
    total_steps: int = 262144
    environments: int = 16
    rollout_steps: int = 128
    hidden_size: int = 64
    learning_rate: float = 0.0003
    epochs: int = 4
    minibatch_size: int = 256
    gamma: float = 1.0
    gae_lambda: float = 0.95
    clip_ratio: float = 0.2
    entropy_coefficient: float = 0.015
    value_coefficient: float = 0.5
    max_gradient_norm: float = 0.5
    reward_scale: float = 0.1

    def validate(self):
        batch = self.environments * self.rollout_steps
        if min(self.total_steps, self.environments, self.rollout_steps, self.epochs, self.minibatch_size) < 1:
            raise ValueError("Training sizes must be positive")
        if self.total_steps % batch or batch % self.minibatch_size:
            raise ValueError("Use complete rollout batches and evenly sized minibatches")
        if not (0 < self.gamma <= 1 and 0 < self.gae_lambda <= 1 and 0 < self.clip_ratio < 1):
            raise ValueError("Invalid PPO discount, GAE or clipping setting")
        if not (0 < self.reward_scale and 0 < self.learning_rate and 0 < self.max_gradient_norm):
            raise ValueError("Training scales must be positive")


class ActorCritic(nn.Module):
    def __init__(self, observation_size=len(OBSERVATION_NAMES), actions=len(ACTION_NAMES), hidden_size=64):
        super().__init__()
        self.observation_size, self.action_count, self.hidden_size = observation_size, actions, hidden_size
        self.body = nn.Sequential(nn.Linear(observation_size, hidden_size), nn.Tanh(),
                                  nn.Linear(hidden_size, hidden_size), nn.Tanh())
        self.actor, self.critic = nn.Linear(hidden_size, actions), nn.Linear(hidden_size, 1)
        for layer in self.modules():
            if isinstance(layer, nn.Linear):
                nn.init.orthogonal_(layer.weight, math.sqrt(2)); nn.init.zeros_(layer.bias)
        nn.init.orthogonal_(self.actor.weight, .01)
        nn.init.orthogonal_(self.critic.weight, 1)

    def forward(self, observation):
        latent = self.body(observation)
        return self.actor(latent), self.critic(latent).squeeze(-1)

    def distribution(self, observation, action_mask):
        if action_mask.shape[-1] != self.action_count or not bool(action_mask.any(dim=-1).all()):
            raise ValueError("Each state needs a valid action mask")
        logits, value = self(observation)
        return Categorical(logits=logits.masked_fill(~action_mask, -1e9)), value


def parameter_hash(model):
    digest = hashlib.sha256()
    for key, value in sorted(model.state_dict().items()):
        digest.update(key.encode()); digest.update(value.detach().cpu().numpy().tobytes())
    return digest.hexdigest()


def generalized_advantages(rewards, values, dones, last_value, gamma, gae_lambda):
    result = torch.zeros_like(rewards)
    carry = torch.zeros_like(last_value)
    for index in reversed(range(len(rewards))):
        next_value = last_value if index == len(rewards)-1 else values[index+1]
        continuation = 1.0 - dones[index]
        delta = rewards[index] + gamma*next_value*continuation - values[index]
        carry = delta + gamma*gae_lambda*continuation*carry
        result[index] = carry
    return result, result + values


def source_fingerprints():
    root = Path(__file__).parent
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.glob("*")) if p.suffix in (".py", ".json")}


def _checkpoint(model, optimizer, config, steps, updates, initial_hash, cap_seeds):
    return {"formatVersion": 1, "algorithm": "clipped-PPO-GAE", "modelState": model.state_dict(),
            "optimizerState": optimizer.state_dict(), "config": asdict(config), "steps": steps,
            "gradientUpdates": updates, "initialParameterHash": initial_hash,
            "parameterHash": parameter_hash(model), "capabilitySeeds": cap_seeds,
            "observationNames": list(OBSERVATION_NAMES), "actionNames": list(ACTION_NAMES),
            "sourceFingerprints": source_fingerprints(), "torchVersion": str(torch.__version__),
            "numpyVersion": np.__version__, "torchRngState": torch.get_rng_state(),
            "device": "cpu", "performanceDomain": "abstract_simulation_only"}


def train(config: TrainConfig, output: Path, progress=print):
    config.validate()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "checkpoint.pt").exists() or (output / "training.jsonl").exists():
        raise ValueError("Training output exists; choose a new run directory")
    torch.set_num_threads(1); torch.use_deterministic_algorithms(True)
    torch.manual_seed(config.seed); np.random.seed(config.seed); random.seed(config.seed)
    generator = np.random.default_rng(config.seed)
    model = ActorCritic(hidden_size=config.hidden_size)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate, eps=1e-5)
    initial = torch.cat([p.detach().flatten().clone() for p in model.parameters()])
    initial_hash = parameter_hash(model)
    cap_seeds = []
    envs = []

    def reset(environment=None):
        cap_seed, episode_seed = (int(v) for v in generator.integers(0, 1_000_000_000, size=2))
        cap_seeds.append(cap_seed)
        capability = sample_capabilities(cap_seed)
        if environment is None:
            environment = Env(seed=episode_seed, capabilities=capability)
        observation = environment.reset(seed=episode_seed, capabilities=capability)
        return environment, observation

    observations = []
    for _ in range(config.environments):
        environment, observation = reset()
        envs.append(environment); observations.append(observation)
    observations = np.asarray(observations, dtype=np.float32)
    torch.save(_checkpoint(model, optimizer, config, 0, 0, initial_hash, cap_seeds), output / "initial.pt")
    shape = (config.rollout_steps, config.environments)
    updates = 0
    completed_scores = []
    started = time.monotonic()
    for iteration in range(config.total_steps // (config.environments*config.rollout_steps)):
        obs = torch.empty((*shape, len(OBSERVATION_NAMES)))
        masks = torch.empty((*shape, len(ACTION_NAMES)), dtype=torch.bool)
        actions = torch.empty(shape, dtype=torch.long)
        old_logprobs, values, rewards, dones = [torch.empty(shape) for _ in range(4)]
        for step in range(config.rollout_steps):
            observation = torch.from_numpy(observations)
            mask = torch.from_numpy(np.stack([env.action_mask() for env in envs]))
            with torch.no_grad():
                distribution, value = model.distribution(observation, mask)
                action = distribution.sample()
            obs[step], masks[step], actions[step] = observation, mask, action
            old_logprobs[step], values[step] = distribution.log_prob(action), value
            next_observations = []
            for index, environment in enumerate(envs):
                next_observation, reward, done, _ = environment.step(int(action[index]))
                rewards[step, index] = reward*config.reward_scale
                dones[step, index] = float(done)
                if done:
                    completed_scores.append(float(environment.score))
                    _, next_observation = reset(environment)
                next_observations.append(next_observation)
            observations = np.asarray(next_observations, dtype=np.float32)
        with torch.no_grad():
            _, last_value = model(torch.from_numpy(observations))
            advantages, returns = generalized_advantages(rewards, values, dones, last_value, config.gamma, config.gae_lambda)
        batch_obs = obs.flatten(0, 1); batch_masks = masks.flatten(0, 1)
        batch_actions, batch_logprobs = actions.flatten(), old_logprobs.flatten()
        batch_advantages, batch_returns = advantages.flatten(), returns.flatten()
        batch_advantages = (batch_advantages - batch_advantages.mean()) / (batch_advantages.std(unbiased=False) + 1e-8)
        measurements = []
        for _ in range(config.epochs):
            for indices in torch.randperm(len(batch_obs)).split(config.minibatch_size):
                distribution, value = model.distribution(batch_obs[indices], batch_masks[indices])
                logprob = distribution.log_prob(batch_actions[indices])
                ratio = (logprob-batch_logprobs[indices]).exp()
                raw, clipped = ratio*batch_advantages[indices], ratio.clamp(1-config.clip_ratio, 1+config.clip_ratio)*batch_advantages[indices]
                actor_loss = -torch.minimum(raw, clipped).mean()
                value_loss = .5*(value-batch_returns[indices]).square().mean()
                entropy = distribution.entropy().mean()
                loss = actor_loss + config.value_coefficient*value_loss - config.entropy_coefficient*entropy
                if not bool(torch.isfinite(loss)):
                    raise RuntimeError("Nonfinite PPO loss; training aborted")
                optimizer.zero_grad(set_to_none=True); loss.backward()
                gradient_norm = nn.utils.clip_grad_norm_(model.parameters(), config.max_gradient_norm)
                if not bool(torch.isfinite(gradient_norm)):
                    raise RuntimeError("Nonfinite neural gradient")
                optimizer.step(); updates += 1
                with torch.no_grad():
                    measurements.append((float(actor_loss.detach()), float(value_loss.detach()), float(entropy.detach()), float(gradient_norm),
                                         float(((ratio-1)-ratio.log()).mean()), float(((ratio-1).abs()>config.clip_ratio).float().mean())))
        steps = (iteration+1)*config.environments*config.rollout_steps
        statistics = np.mean(measurements, axis=0)
        record = {"steps": steps, "gradientUpdates": updates, "episodes": len(completed_scores),
                  "recentMeanScore": float(np.mean(completed_scores[-100:])) if completed_scores else None,
                  **dict(zip(("actorLoss", "valueLoss", "entropy", "gradientNorm", "approximateKl", "clipFraction"), statistics.tolist())),
                  "parameterDeltaL2": float(torch.linalg.vector_norm(torch.cat([p.detach().flatten() for p in model.parameters()])-initial)),
                  "elapsedSeconds": round(time.monotonic()-started, 3)}
        with (output / "training.jsonl").open("a") as stream:
            stream.write(json.dumps(record, allow_nan=False)+"\n")
        if (iteration+1) % 16 == 0 or steps == config.total_steps:
            progress(json.dumps(record), flush=True)
    torch.save(_checkpoint(model, optimizer, config, steps, updates, initial_hash, cap_seeds), output / "checkpoint.pt")
    summary = {**record, "seed": config.seed, "config": asdict(config), "initialParameterHash": initial_hash,
               "finalParameterHash": parameter_hash(model), "performanceDomain": "abstract_simulation_only",
               "trainingCapabilityConfigurations": len(set(cap_seeds)), "sourceFingerprints": source_fingerprints()}
    (output / "training-summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    return model, summary


def load_policy(path: Path):
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if checkpoint.get("formatVersion") != 1 or checkpoint.get("algorithm") != "clipped-PPO-GAE":
        raise ValueError("Unsupported policy checkpoint")
    if checkpoint["observationNames"] != list(OBSERVATION_NAMES) or checkpoint["actionNames"] != list(ACTION_NAMES):
        raise ValueError("Policy/environment observation or action contract changed")
    model = ActorCritic(hidden_size=checkpoint["config"]["hidden_size"])
    model.load_state_dict(checkpoint["modelState"]); model.eval()
    if parameter_hash(model) != checkpoint["parameterHash"]:
        raise ValueError("Policy parameter integrity mismatch")
    return model, checkpoint
