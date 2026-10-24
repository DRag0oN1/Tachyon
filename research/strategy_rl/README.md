# Strategy-first robot co-design experiment

This independent package implements the learner's 2026-10-24 RL architecture:

**Competition rules → abstract game → trained PPO policy → Strategy
Specification → capability-driven architecture proposal → evaluation.**

No CAD design is a training input. The policy sees game state and a sampled,
jointly constrained abstract capability budget. The existing Tachyon server,
frontend, viewer, themes and their dependencies import none of this package.
No diffusion model or general robotics framework is included.

All scores are **abstract simulated strategy performance**. They are not real
robot/match predictions, certified capabilities, complete-game simulation,
competition legality, or generated authentic CAD.

## What actually runs

- PyTorch actor–critic: two 64-unit tanh layers, categorical actor and value head.
- On-policy rollouts, generalized advantage estimation, clipped PPO surrogate,
  entropy bonus, value regression, Adam, and gradient clipping. Actual
  `.backward()` and optimizer updates change the neural weights.
- Seeded movement, action durations, failures, finite object stocks, Cup stack
  interfaces, goal access/reach and opponent Toggle recaptures.
- A budget simplex sampled across drive/handling/lift allocations. Derived
  capabilities trade off speed, handling reliability and reach. This is an
  abstract feasibility model, not an engineering certification.
- Held-out capability and episode seeds, random and explicit greedy baselines,
  untrained network controls, and confidence intervals clustered by capability.
- Learned rollout extraction, strategy JSON, mechanical recipe choices and
  numerical layout intent. Unresolved CAD and physical checks remain explicit.

## Bounded Override scenario

The source is [Override v2.1, Section 2](https://manuals.vex.com/v5/override/v2.1/game/?view=core).
Source facts and authored assumptions are separated in
[scenario.json](tachyon_strategy_rl/scenario.json). The model uses a 105-second
driver period, five points per counted alliance Pin Half, ten per owned yellow
Pin Half, and eight terminal Midfield points. SG6 limits possession to **one Pin
and one Cup**, independently. Another Pin on an occupied stack needs a Cup.

The model counts one correctly oriented, visible half per Pin and assumes correct
Cup orientation preserves earlier counted halves. It does not simulate full
visibility, contact, stability or object geometry. Two nominal quadrant stack
targets have assumed heights; the elevated target is **not the official central
Midfield Goal**. Site coordinates, stocks, stack increments, success probabilities,
motion timings, 15-second park macro window and opponent process are assumptions.
The park macro window is not asserted to be the official Endgame duration.

Automatic conversion of arbitrary uploaded manuals into simulation code is not
implemented. This first environment is explicitly authored and source checked.

## Reproduce

Verified on macOS arm64, Python 3.12, PyTorch 2.10.0, deterministic CPU execution.
The separate environment does not change the application's `.venv`.

```sh
python3.12 -m venv .local/rl-venv
.local/rl-venv/bin/python -m pip install -r research/strategy_rl/requirements.lock
.local/rl-venv/bin/python -m pip install --no-deps --no-build-isolation -e research/strategy_rl
.local/rl-venv/bin/python -m pytest research/strategy_rl/tests -q

PYTHONPATH=research/strategy_rl .local/rl-venv/bin/python -m tachyon_strategy_rl.cli train \
  --seed 17 --steps 262144 --output .local/strategy-rl/new-seed-17
# Repeat for independently initialized seeds 29 and 43, with new output paths.

PYTHONPATH=research/strategy_rl .local/rl-venv/bin/python -m tachyon_strategy_rl.cli evaluate \
  --checkpoints .local/strategy-rl/new-seed-17/checkpoint.pt \
                .local/strategy-rl/new-seed-29/checkpoint.pt \
                .local/strategy-rl/new-seed-43/checkpoint.pt \
  --configurations 64 --episodes-per-configuration 3 \
  --output .local/strategy-rl/new-evaluation

PYTHONPATH=research/strategy_rl .local/rl-venv/bin/python -m tachyon_strategy_rl.cli export \
  --evaluation .local/strategy-rl/new-evaluation \
  --output .local/strategy-rl/new-export
```

Commands refuse to overwrite completed runs. Checkpoints contain model and Adam
states, RNG state, configuration, sampled capability seeds, action/observation
names, code fingerprints and runtime versions. They are not an exact mid-episode
resume feature. Reproduction means restarting the recorded run from its seed.
Only locally generated, trusted checkpoints should be loaded; loading uses
PyTorch's `weights_only=True` mode. Inference additionally rejects an untrained
model or changed environment/scenario/neural implementation.

## Results and interpretation

The preserved [experiment report](results/override-ppo-v1/REPORT.md) contains
three training runs, held-out evaluations, initial/final checkpoints, learning
curves, the structured Strategy Specification and architecture proposal.

Each trained model received 262,144 simulated decisions and 4,096 gradient
updates. Seed 17 was independently rerun for all 262,144 decisions and reproduced
the complete parameter hash exactly. Held-out evaluation has 64 capability
configurations × 3 episode seeds, including budget-corner stress cases.

The learned policies supported **one low-quadrant scoring family**. The exporter
does not manufacture a second discovered strategy or elevator architecture.
Its fixed support gate requires at least 24 episodes, 8 capability configurations
and 2 training seeds for each distinct family. Absence of a discovered elevated
strategy does not prove elevated strategies are inferior or impossible.

## Designer boundary and future feedback

[strategy.schema.json](tachyon_strategy_rl/strategy.schema.json) is the versioned
handoff. It includes policy evidence, scoring objectives, sequences, action
frequencies, movement, observed trade-offs, minimum requirements for a
representative simulated rollout, a jointly feasible target capability sample,
and mechanism requirements. Empirical target envelopes are not causal minimums.

`architecture_from_strategy` makes drivetrain, intake, single-Pin transfer,
independent Cup-path and scorer decisions, plus layout dimensions and wheel
centers. This deterministic designer consumes learned requirements; it is not
the reinforcement learner. Layout envelopes are labeled conceptual and cannot
be presented as authentic CAD. Component resolution, attachments, actuation,
physical checks and competition legality remain required.

`validate_capability_feedback` defines the future generated-design → measured or
estimated capabilities boundary. Calibration into the abstract budget model is
still needed. An automatic iterative retraining/design loop is not implemented.

Inference and isolated strategy-to-designer contract tests are executed here.
Production app integration remains gated and has not been enabled.

## Inspect the preserved experiment

The bundle includes losslessly compressed complete trained-policy traces,
baseline/control summaries for every episode, checkpoints and training logs.
No proprietary CAD or user uploads are present.

```sh
PYTHONPATH=research/strategy_rl .local/rl-venv/bin/python research/strategy_rl/tools/verify_experiment.py \
  research/strategy_rl/results/override-ppo-v1 --replay-all

PYTHONPATH=research/strategy_rl .local/rl-venv/bin/python -m tachyon_strategy_rl.cli export \
  --evaluation research/strategy_rl/results/override-ppo-v1/evaluation \
  --output .local/strategy-rl/another-bundled-export
```

The verifier recomputes summaries and paired intervals, rejects untrained
checkpoints, exercises the public inference boundary, re-exports the strategy
and architecture, and optionally replays all 1,536 held-out episodes exactly.
`tools/plot_experiment.py` regenerates plots with optional Matplotlib 3.11.2;
plotting is independent of training dependencies. The manifest hashes the
preserved files. These are local build artifacts, not a published submission.

## References and licenses

- [PPO paper](https://arxiv.org/abs/1707.06347): the clipped on-policy algorithm.
- [PyTorch distributions](https://docs.pytorch.org/docs/2.10/distributions.html): categorical neural policy.
- [Override v2.1](https://manuals.vex.com/v5/override/v2.1/game/?view=core): selected scoring/possession rules.
- [Third-party notices](THIRD_PARTY_NOTICES.md). No VEX geometry or manual PDF is bundled.
