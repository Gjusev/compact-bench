"""Task-suite tests: environments deterministic, plans solve, checkers catch errors."""

import unittest

from compact_bench import ALL_TASKS, StubPolicy, run_task
from compact_bench.tasks.nav_tasks import GridEnv
from compact_bench.tasks.sql_tasks import SqlEnv


class TestTaskSuite(unittest.TestCase):
    def test_registry_shape(self):
        self.assertEqual(len(ALL_TASKS), 12)
        by_cat = {}
        for t in ALL_TASKS:
            by_cat.setdefault(t.category, []).append(t)
        self.assertEqual(set(by_cat), {"sql", "refactor", "nav"})
        self.assertEqual(len({t.name for t in ALL_TASKS}), 12)
        for t in ALL_TASKS:
            self.assertNotIn("ACTION: ", t.prompt, "marker would confuse stub policy")

    def test_every_task_solves_under_fha(self):
        for task in ALL_TASKS:
            result = run_task(task, "fha", StubPolicy(task.plan))
            self.assertTrue(result.success, "%s: %s" % (task.name, result.check_detail))

    def test_wrong_answer_fails_checker(self):
        task = next(t for t in ALL_TASKS if t.name == "sql-total-revenue")
        bad_plan = list(task.plan)
        bad_plan[-1] = "finish: 999.99"
        result = run_task(task, "fha", StubPolicy(bad_plan))
        self.assertFalse(result.success)
        self.assertIn("999.99", result.check_detail)

    def test_sql_env_ground_truth(self):
        env = SqlEnv()
        self.assertEqual(round(env.query_scalar("SELECT SUM(amount) FROM orders"), 2), 660.75)
        self.assertEqual(
            env.query_scalar(
                "SELECT c.name FROM orders o JOIN customers c ON c.id=o.customer_id"
                " GROUP BY c.name ORDER BY SUM(o.amount) DESC LIMIT 1"
            ),
            "Lin",
        )
        self.assertEqual(
            env.query_scalar(
                "SELECT COUNT(*) FROM orders o JOIN customers c ON c.id=o.customer_id"
                " WHERE c.region='EU'"
            ),
            5,
        )
        self.assertEqual(
            env.query_scalar("SELECT COUNT(*) FROM orders WHERE discount IS NULL"), 4
        )

    def test_sql_env_deterministic(self):
        a = SqlEnv().execute("sql: SELECT name FROM customers ORDER BY id")
        b = SqlEnv().execute("sql: SELECT name FROM customers ORDER BY id")
        self.assertEqual(a, b)
        self.assertEqual(a.splitlines()[0], "name")
        self.assertEqual(a.splitlines()[1], "Ada")

    def test_grid_bump_and_bounds(self):
        env = GridEnv(walls=((1, 0),), goal=(4, 0), items=())
        self.assertIn("BUMPED WALL", env.execute("move E"))
        self.assertEqual(env.pos, (0, 0))
        self.assertIn("BUMPED WALL", env.execute("move N"))  # off-grid is a wall
        self.assertEqual(env.pos, (0, 0))

    def test_grid_collect_and_goal(self):
        env = GridEnv(walls=(), goal=(2, 0), items=((1, 0),))
        env.execute("move E")
        self.assertEqual(env.collected, {(1, 0)})
        obs = env.execute("move E")
        self.assertIn("GOAL REACHED", obs)
        self.assertEqual(env.pos, (2, 0))

    def test_file_env_move_write_rm(self):
        env = next(
            t for t in ALL_TASKS if t.name == "refactor-rename-module"
        ).build_env()
        self.assertIn("WROTE", env.execute("write new.txt :: hello"))
        self.assertIn("MOVED", env.execute("move new.txt renamed.txt"))
        self.assertIn("DELETED", env.execute("rm renamed.txt"))
        self.assertIn("FILE NOT FOUND", env.execute("read renamed.txt"))


if __name__ == "__main__":
    unittest.main()
