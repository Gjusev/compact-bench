"""compact-bench: deterministic 3-regime context-compaction benchmark harness.

Reproduction scaffold for "You don't need long context" (NVIDIA,
arXiv:2611.05306). Zero-dependency core (Python stdlib only).
"""

__version__ = "0.1.0"

from .agent import REGIMES, RunResult, StubPolicy, run_task
from .compaction import CompactionStrategy, LossyCompaction, current_step
from .tasks import ALL_TASKS, get_tasks

__all__ = [
    "REGIMES",
    "RunResult",
    "StubPolicy",
    "run_task",
    "CompactionStrategy",
    "LossyCompaction",
    "current_step",
    "ALL_TASKS",
    "get_tasks",
    "__version__",
]
