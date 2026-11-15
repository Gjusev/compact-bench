"""Task registry: 12 deterministic tasks across 3 categories."""

from .base import Task
from .nav_tasks import ALL_NAV_TASKS
from .refactor_tasks import ALL_REFACTOR_TASKS
from .sql_tasks import ALL_SQL_TASKS

ALL_TASKS = tuple(ALL_SQL_TASKS + ALL_REFACTOR_TASKS + ALL_NAV_TASKS)

CATEGORIES = ("sql", "refactor", "nav")


def get_tasks(category=None):
    if category is None:
        return list(ALL_TASKS)
    if category not in CATEGORIES:
        raise ValueError("unknown category %r; expected one of %s" % (category, CATEGORIES))
    return [t for t in ALL_TASKS if t.category == category]


__all__ = ["Task", "ALL_TASKS", "CATEGORIES", "get_tasks"]
