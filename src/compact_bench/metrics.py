"""Metrics: cost estimation and the paper-style 3-regime comparison table."""

from dataclasses import dataclass

DEFAULT_PRICES = {
    # Assumption for offline harness validation ONLY. The paper's Appendix B
    # estimates cost via window-size-dependent pricing; with the Z.ai Coding
    # Plan the real cost is a flat subscription, so these numbers are for
    # relative comparison between regimes, not invoices.
    "input_usd_per_mtok": 3.0,
    "output_usd_per_mtok": 15.0,
}

REGIME_LABELS = {
    "fha": "FHA  (full history)",
    "eocc": "EOCC (threshold)",
    "sac": "SAC  (one action/ctx)",
}


@dataclass
class PriceConfig:
    input_usd_per_mtok: float = DEFAULT_PRICES["input_usd_per_mtok"]
    output_usd_per_mtok: float = DEFAULT_PRICES["output_usd_per_mtok"]


def est_cost_usd(run, prices: PriceConfig = None) -> float:
    p = prices or PriceConfig()
    return (
        run.total_input_tokens / 1e6 * p.input_usd_per_mtok
        + run.total_output_tokens / 1e6 * p.output_usd_per_mtok
    )


def summarize(runs, prices: PriceConfig = None):
    """Aggregate runs (same task set) per regime -> dict keyed by regime."""
    out = {}
    for regime in ("fha", "eocc", "sac"):
        rs = [r for r in runs if r.regime == regime]
        if not rs:
            continue
        n = len(rs)
        out[regime] = {
            "tasks": n,
            "successes": sum(1 for r in rs if r.success),
            "success_rate": sum(1 for r in rs if r.success) / n,
            "mean_peak_context_tokens": sum(r.peak_context_tokens for r in rs) / n,
            "max_peak_context_tokens": max(r.peak_context_tokens for r in rs),
            "mean_actions": sum(r.n_actions for r in rs) / n,
            "compaction_events": sum(r.compaction_events for r in rs),
            "mean_est_cost_usd": sum(est_cost_usd(r, prices) for r in rs) / n,
        }
    return out


def render_table(runs, prices: PriceConfig = None) -> str:
    s = summarize(runs, prices)
    lines = [
        "OFFLINE HARNESS VALIDATION — deterministic stub agent, NOT benchmark results",
        "=" * 88,
        "%-22s %5s %9s %14s %14s %10s %12s" % (
            "Regime", "Tasks", "Success", "Peak ctx mean", "Peak ctx max",
            "$/task est", "Compactions",
        ),
        "-" * 88,
    ]
    for regime in ("fha", "eocc", "sac"):
        if regime not in s:
            continue
        r = s[regime]
        lines.append(
            "%-22s %5d %6.0f%% %12d %14d %10.6f %12d" % (
                REGIME_LABELS[regime],
                r["tasks"],
                100 * r["success_rate"],
                round(r["mean_peak_context_tokens"]),
                r["max_peak_context_tokens"],
                r["mean_est_cost_usd"],
                r["compaction_events"],
            )
        )
    lines.append("=" * 88)
    lines.append(
        "Peak ctx / $ are token-estimated (chars/4 heuristic) on scripted stub runs; "
        "cost uses list-price assumption in compact_bench.metrics, not real billing."
    )
    return "\n".join(lines)
