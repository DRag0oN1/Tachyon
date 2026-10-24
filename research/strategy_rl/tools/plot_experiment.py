"""Plot recorded data only; matplotlib is an optional reporting dependency."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot(root):
    report = json.loads((root / "evaluation/evaluation.json").read_text())
    plt.rcParams.update({"font.family": "sans-serif", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    colors = ["#167b91", "#c66b20", "#6f59a0"]
    fig, (train, test) = plt.subplots(1, 2, figsize=(12.5, 4.8), layout="constrained")
    for seed, color in zip((17, 29, 43), colors):
        rows = [json.loads(line) for line in (root / f"runs/seed-{seed}/training.jsonl").read_text().splitlines()]
        train.plot([r["steps"]/1000 for r in rows], [r["recentMeanScore"] for r in rows], color=color, label=f"PPO seed {seed}")
    train.set(xlabel="Training decisions (thousands)", ylabel="Modeled points / episode",
              title="Real PPO learning: recent 100 training episodes", ylim=(0, 50))
    train.legend(frameon=False, loc="lower right")
    names = ["random", "heuristic", "untrained_seed_17", "untrained_seed_29", "untrained_seed_43",
             "ppo_seed_17", "ppo_seed_29", "ppo_seed_43"]
    labels = ["Random", "Heuristic", "Untrained 17", "Untrained 29", "Untrained 43", "PPO 17", "PPO 29", "PPO 43"]
    means = [report["policies"][n]["meanScore"] for n in names]
    interval = np.array([report["policies"][n]["meanScore95CI"] for n in names])
    test.barh(labels[::-1], means[::-1], color=(['#a3a6ab']*5+colors)[::-1], height=.7)
    test.errorbar(means[::-1], labels[::-1], xerr=np.stack((np.array(means)-interval[:,0], interval[:,1]-means))[:,::-1],
                  fmt="none", ecolor="#273344", capsize=3, linewidth=1)
    test.set(xlabel="Modeled points / episode", title="Held-out: 64 capabilities × 3 episode seeds", xlim=(0, 46))
    for axis in (train, test): axis.grid(axis="x", alpha=.15); axis.set_axisbelow(True)
    fig.suptitle("Tachyon · abstract simulated strategy performance only", fontsize=14, weight="bold")
    fig.savefig(root / "learning-and-evaluation.png", dpi=170)
    plt.close(fig)

    strategy = json.loads(next((root / "strategies").glob("*-strategy.json")).read_text())
    scenario = json.loads((Path(__file__).parents[1] / "tachyon_strategy_rl/scenario.json").read_text())
    fig, (route, cycle) = plt.subplots(1, 2, figsize=(11, 5.2), layout="constrained", gridspec_kw={"width_ratios": [1.2, 1]})
    events = strategy["representativeRollout"]["events"]
    sites = scenario["assumptions"]["sites"]
    for site in sites:
        x, y = site["xy_m"]; route.scatter(x, y, s=75, color="#566575")
        route.annotate(site["name"], (x,y), xytext=(5, 7), textcoords="offset points", fontsize=9)
    traversed = set()
    for event in events:
        start, end = tuple(event["from_xy"]), tuple(event["to_xy"])
        if start == end or (start,end) in traversed: continue
        traversed.add((start,end))
        route.annotate("", end, start, arrowprops={"arrowstyle": "->", "color": colors[0], "alpha": .7,
                                                  "connectionstyle": "arc3,rad=.1", "linewidth": 1.7})
    route.set(xlim=(0,3.65), ylim=(0,3.65), xlabel="Assumed x (m)", ylabel="Assumed y (m)", aspect="equal",
              title="One high-scoring observed rollout: 43 modeled points")
    route.grid(alpha=.15)
    cycle.axis("off")
    counts = strategy["actionPriorities"][:7]
    cycle.text(0, .98, "Observed policy behavior", va="top", fontsize=13, weight="bold")
    cycle.text(0, .88, "Acquire a Pin → low quadrant → place\nFetch / place Cup interface → repeat\nFinish at Midfield when time allows", va="top", linespacing=1.8)
    cycle.text(0, .56, "Most frequent actions (576 evaluation episodes)", va="top", fontsize=10, weight="bold")
    for index, item in enumerate(counts):
        cycle.text(0, .49-.055*index, f"{item['action']:<24}  {item['frequency']:.1%}", family="monospace", fontsize=9)
    cycle.text(0, .05, "One supported family. No second design claimed.\nAssumed layout; not field geometry or real performance.", va="top", fontsize=9, color="#5c6170")
    fig.suptitle("Tachyon · learned low-quadrant strategy playbook", fontsize=14, weight="bold")
    fig.savefig(root / "strategy-playbook.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    plot(parser.parse_args().root)
