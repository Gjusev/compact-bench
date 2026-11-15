"""Compaction mechanism tests."""

import unittest

from compact_bench import ALL_TASKS, LossyCompaction, StubPolicy, run_task
from compact_bench.compaction import (
    ACTION_MARKER,
    STATE_HEADER,
    CompactionStrategy,
    current_step,
    make_state_block,
    should_compact,
)
from compact_bench.tokens import estimate_context_tokens, estimate_tokens


def _find(name):
    return next(t for t in ALL_TASKS if t.name == name)


class TestStateBlock(unittest.TestCase):
    def test_state_block_carries_progress_counter(self):
        task = _find("nav-corridor")
        context = [task.prompt, ACTION_MARKER + "move E", "OBSERVATION: position=(1,0)"]
        block = make_state_block(context)
        self.assertIn("ACTIONS SO FAR: 1", block)
        self.assertIn(STATE_HEADER, block)
        self.assertIn("position=(1,0)", block)

    def test_current_step_counter_plus_post_compaction_actions(self):
        task = _find("nav-corridor")
        compacted = CompactionStrategy().compact(
            [task.prompt, ACTION_MARKER + "move E", "OBSERVATION: position=(1,0)"],
            task.prompt,
        )
        self.assertEqual(current_step(compacted), 1)
        compacted.append(ACTION_MARKER + "move E")
        compacted.append("OBSERVATION: position=(2,0)")
        self.assertEqual(current_step(compacted), 2)

    def test_current_step_marker_fallback_without_compaction(self):
        task = _find("nav-corridor")
        context = [task.prompt, ACTION_MARKER + "move E", "OBSERVATION: position=(1,0)",
                   ACTION_MARKER + "move E", "OBSERVATION: position=(2,0)"]
        self.assertEqual(current_step(context), 2)

    def test_lossy_compaction_drops_counter(self):
        task = _find("nav-corridor")
        context = [task.prompt, ACTION_MARKER + "move E", "OBSERVATION: position=(1,0)"]
        compacted = LossyCompaction().compact(context, task.prompt)
        self.assertNotIn("ACTIONS SO FAR: 1", "\n".join(compacted))
        # progress lost: with no ACTION markers left in context the step falls to 0
        self.assertEqual(current_step(compacted), 0)


class TestThresholdBehaviour(unittest.TestCase):
    def test_should_compact_threshold_compare(self):
        ctx = ["x" * 400]  # 100 tokens
        self.assertFalse(should_compact(ctx, 100))
        self.assertTrue(should_compact(ctx, 99))

    def test_eocc_with_huge_threshold_never_compacts(self):
        task = _find("nav-corridor")
        result = run_task(task, "eocc", StubPolicy(task.plan), threshold_tokens=10**9)
        self.assertEqual(result.compaction_events, 0)
        fha = run_task(task, "fha", StubPolicy(task.plan))
        self.assertEqual(result.peak_context_tokens, fha.peak_context_tokens)
        self.assertEqual(result.total_input_tokens, fha.total_input_tokens)

    def test_eocc_tiny_threshold_compacts_and_still_solves(self):
        for task in ALL_TASKS:
            result = run_task(task, "eocc", StubPolicy(task.plan), threshold_tokens=55)
            self.assertTrue(result.success, "%s failed: %s" % (task.name, result.check_detail))
            self.assertGreater(result.compaction_events, 0, task.name)

    def test_sac_always_resets_to_task_plus_state(self):
        task = _find("sql-top-customer")
        policy = StubPolicy(task.plan)
        seen = []

        def recording_policy(context):
            seen.append(list(context))
            return policy(context)

        run_task(task, "sac", recording_policy)
        # every context after the first must start with the task and carry state
        for context in seen[1:]:
            self.assertEqual(context[0], task.prompt)
            self.assertIn(STATE_HEADER, context[1])


class TestTokenEstimator(unittest.TestCase):
    def test_estimator_is_monotone_and_stable(self):
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens("abcd"), 1)
        self.assertGreater(estimate_tokens("a" * 401), estimate_tokens("a" * 400))
        ctx = ["a", "b"]
        self.assertEqual(
            estimate_context_tokens(ctx + ["c"]),
            estimate_context_tokens(ctx) + estimate_tokens("c"),
        )

    def test_observation_truncation_bounded(self):
        big = "OBSERVATION: " + "y" * 5000
        block = make_state_block(["t", ACTION_MARKER + "a", big])
        self.assertLess(len(block), 2000)


if __name__ == "__main__":
    unittest.main()
