import argparse
from dataclasses import replace
from pathlib import Path

from .ppo import TrainConfig, train


def main():
    parser = argparse.ArgumentParser(prog="tachyon-strategy-rl")
    sub = parser.add_subparsers(dest="command", required=True)
    training = sub.add_parser("train", help="Train a real neural PPO policy; no CAD input")
    training.add_argument("--output", type=Path, required=True)
    training.add_argument("--seed", type=int, default=17)
    training.add_argument("--steps", type=int, default=262144)
    evaluation = sub.add_parser("evaluate", help="Compare frozen policies with held-out random/heuristic baselines")
    evaluation.add_argument("--checkpoints", type=Path, nargs="+", required=True)
    evaluation.add_argument("--output", type=Path, required=True)
    evaluation.add_argument("--configurations", type=int, default=64)
    evaluation.add_argument("--episodes-per-configuration", type=int, default=3)
    export = sub.add_parser("export", help="Extract observed strategies and capability-driven architecture proposals")
    export.add_argument("--evaluation", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "train":
        train(replace(TrainConfig(), seed=args.seed, total_steps=args.steps), args.output)
    elif args.command == "evaluate":
        from .evaluate import evaluate
        evaluate(args.checkpoints, args.output, args.configurations, args.episodes_per_configuration)
    else:
        from .strategy import export_strategies
        export_strategies(args.evaluation, args.output)


if __name__ == "__main__":
    main()
