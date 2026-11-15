"""Task interface: deterministic environments with scripted reference plans."""


class Task:
    """A benchmark task.

    Attributes:
        name: unique id, e.g. "sql-total-revenue".
        category: one of "sql", "refactor", "nav".
        prompt: the task statement as the agent first sees it. Must NOT contain
            the "ACTION: " marker (the stub policy uses it to count progress).
        plan: the scripted reference solution (one action per entry). The stub
            policy recovers the current plan index from the context, so the
            plan doubles as ground truth for compaction fidelity.
        build_env: zero-arg factory returning a fresh deterministic environment.
        check: (env, answer) -> (ok: bool, detail: str).
    """

    def __init__(self, name, category, prompt, plan, build_env, check):
        self.name = name
        self.category = category
        self.prompt = prompt
        self.plan = tuple(plan)
        self.build_env = build_env
        self._check = check

    def check(self, env, answer):
        return self._check(env, answer)
