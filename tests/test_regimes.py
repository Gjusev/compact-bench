"""Regime end-to-end tests: all 12 tasks x 3 regimes with the stub policy."""

import unittest

from compact_bench import ALL_TASKS, REGIMES, LossyCompaction, StubPolicy, run_task
from compact_bench.metrics import summarize


THRESHOLD = 150
MAX_STEPS = 16


def run_all(regime=REGIMES, compaction=None):
    return [
        run_task(
            task, regime_i, StubPolicy(task.plan),
            threshold_tokens=THRESHOLD, max_steps=MAX_STEPS,
            compaction=compaction,
        )
        for regime_i in (regime if isinstance(regime, tuple) else (regime,))
        for task in ALL_TASKS
    ]


class TestRegimesEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = run_all(tuple(REGIMES))

    def test_all_regimes_solve_all_tasks(self):
        failures = [r for r in self.runs if not r.success]
        self.assertEqual(
            failures, [],
            "stub runs must all succeed; failures: %s"
            % [(r.regime, r.task, r.check_detail) for r in failures],
        )
        self.assertEqual(len(self.runs), len(ALL_TASKS) * len(REGIMES))

    def test_peak_context_ordering(self):
        """SAC < EOCC <= FHA on mean peak context (the paper's core claim shape)."""
        s = summarize(self.runs)
        self.assertLess(
            s["sac"]["mean_peak_context_tokens"],
            s["eocc"]["mean_peak_context_tokens"],
        )
        self.assertLessEqual(
            s["eocc"]["mean_peak_context_tokens"],
            s["fha"]["mean_peak_context_tokens"],
        )

    def test_eocc_never_exceeds_fha_per_task(self):
        by_key = {(r.regime, r.task): r for r in self.runs}
        for task in ALL_TASKS:
            fha = by_key[("fha", task.name)]
            eocc = by_key[("eocc", task.name)]
            self.assertLessEqual(
                eocc.peak_context_tokens, fha.peak_context_tokens,
                "EOCC peak exceeded FHA peak on %s" % task.name,
            )

    def test_eocc_actually_compacts_on_long_input_task(self):
        """The threshold regime must fire on the long-config task, not silently equal FHA."""
        by_key = {(r.regime, r.task): r for r in self.runs}
        eocc = by_key[("eocc", "refactor-long-config-read")]
        self.assertGreater(eocc.compaction_events, 0)
        self.assertLess(eocc.peak_context_tokens, by_key[("fha", "refactor-long-config-read")].peak_context_tokens)

    def test_sac_compacts_every_action(self):
        by_key = {(r.regime, r.task): r for r in self.runs}
        from compact_bench.tokens import estimate_tokens

        for task in ALL_TASKS:
            sac = by_key[("sac", task.name)]
            self.assertEqual(sac.compaction_events, sac.n_actions)
            # SAC's real property: peak context stays BOUNDED no matter how
            # long the history is (task + capped state block). At stub scale
            # the state overhead can slightly exceed a tiny FHA history, so
            # we assert the bound, not FHA dominance.
            self.assertLessEqual(
                sac.peak_context_tokens,
                estimate_tokens(task.prompt) + 350,
                "SAC peak unbounded on %s" % task.name,
            )

    def test_determinism(self):
        """Same inputs -> byte-identical metrics (repro requirement)."""
        again = run_all(tuple(REGIMES))
        self.assertEqual(
            [r.as_dict() for r in self.runs], [r.as_dict() for r in again]
        )

    def test_lossy_compaction_breaks_sac(self):
        """A compaction that loses the progress counter must fail, loudly.

        This proves the counter is load-bearing and the harness can detect
        bad compaction (mechanism check, not just token accounting).
        """
        lossy = run_all("sac", compaction=LossyCompaction())
        failed = [r for r in lossy if not r.success]
        self.assertGreater(
            len(failed), 0,
            "LossyCompaction should break at least one SAC run",
        )


class TestCostAccounting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = run_all(tuple(REGIMES))

    def test_costs_positive_and_long_input_fha_above_sac(self):
        """At stub scale SAC's fixed state overhead can exceed FHA's tiny
        accumulations, so the paper's cost effect is asserted on the
        long-input task where FHA carries a ~2 KB file in context."""
        from compact_bench.metrics import est_cost_usd

        for r in self.runs:
            self.assertGreater(est_cost_usd(r), 0.0)
        by_key = {(r.regime, r.task): r for r in self.runs}
        self.assertGreater(
            est_cost_usd(by_key[("fha", "refactor-long-config-read")]),
            est_cost_usd(by_key[("sac", "refactor-long-config-read")]),
        )

    def test_summarize_counts(self):
        s = summarize(self.runs)
        for regime, stats in s.items():
            self.assertEqual(stats["tasks"], len(ALL_TASKS))
            self.assertEqual(stats["successes"], len(ALL_TASKS))


if __name__ == "__main__":
    unittest.main()
