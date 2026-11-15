#!/usr/bin/env python3
"""Offline benchmark runner: 12 tasks x 3 regimes with the deterministic stub.

This validates the HARNESS, not the paper: the stub agent is scripted, so the
numbers below measure how each regime moves context size / cost accounting,
with success rate serving as a regression check (all runs must succeed).

Usage (from repo root):
    python3 eval/run_bench.py [--category sql|refactor|nav] [--regime fha|eocc|sac]
                              [--threshold-tokens 350] [--max-steps 16]
                              [--out results/offline_stub_runs.json]
"""

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from compact_bench import StubPolicy, get_tasks, run_task  # noqa: E402
from compact_bench.metrics import PriceConfig, render_table  # noqa: E402

REGIMES = ("fha", "eocc", "sac")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", choices=("sql", "refactor", "nav"), default=None)
    parser.add_argument("--regime", choices=REGIMES, default=None)
    parser.add_argument("--threshold-tokens", type=int, default=150)
    parser.add_argument("--max-steps", type=int, default=16)
    parser.add_argument("--input-usd-per-mtok", type=float, default=3.0)
    parser.add_argument("--output-usd-per-mtok", type=float, default=15.0)
    parser.add_argument(
        "--out", default="results/offline_stub_runs.json",
        help="where to write the JSON results (labelled harness-validation)",
    )
    args = parser.parse_args(argv)

    tasks = get_tasks(args.category)
    regimes = (args.regime,) if args.regime else REGIMES
    prices = PriceConfig(args.input_usd_per_mtok, args.output_usd_per_mtok)

    runs = []
    for regime in regimes:
        for task in tasks:
            runs.append(
                run_task(
                    task,
                    regime,
                    StubPolicy(task.plan),
                    threshold_tokens=args.threshold_tokens,
                    max_steps=args.max_steps,
                )
            )

    print(render_table(runs, prices))
    print()
    failures = [r for r in runs if not r.success]
    if failures:
        print("FAILURES (stub should never fail — this is a harness bug):")
        for r in failures:
            print("  %s / %s: %s" % (r.regime, r.task, r.check_detail))

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "label": "harness-validation (deterministic stub agent — NOT benchmark results)",
        "threshold_tokens": args.threshold_tokens,
        "max_steps": args.max_steps,
        "prices_usd_per_mtok": {
            "input": prices.input_usd_per_mtok,
            "output": prices.output_usd_per_mtok,
        },
        "runs": [r.as_dict() for r in runs],
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d runs)" % (out_path, len(runs)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
