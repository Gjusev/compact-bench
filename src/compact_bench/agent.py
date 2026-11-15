"""Agent loop with configurable context regime (FHA / EOCC / SAC)."""

from dataclasses import dataclass, field
from typing import Callable, List

from .compaction import (
    ACTION_MARKER,
    OBS_MARKER,
    CompactionStrategy,
    should_compact,
)
from .tokens import estimate_context_tokens, estimate_tokens

REGIMES = ("fha", "eocc", "sac")


@dataclass
class RunResult:
    task: str
    category: str
    regime: str
    success: bool
    check_detail: str
    n_actions: int
    compaction_events: int
    peak_context_tokens: int
    total_input_tokens: int
    total_output_tokens: int
    finish_answer: str = ""
    max_steps_reached: bool = False

    def as_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class StubPolicy:
    """Deterministic scripted stand-in for an LLM policy.

    It recovers its progress (which plan step is next) FROM THE CONTEXT,
    exactly like a real model would. This makes compaction quality
    load-bearing: a compaction that loses the progress counter breaks the
    agent, and the tests detect it.
    """

    plan: List[str]

    def __call__(self, context) -> str:
        from .compaction import current_step

        step = current_step(context)
        if step >= len(self.plan):
            return "finish: plan exhausted"
        return self.plan[step]


def run_task(
    task,
    regime: str,
    policy: Callable[[List[str]], str],
    threshold_tokens: int = 350,
    max_steps: int = 16,
    compaction: CompactionStrategy = None,
) -> RunResult:
    """Run one task under one regime; return metrics for the comparison table.

    token accounting:
      - peak_context_tokens: max context size shown to the policy at any step
      - total_input_tokens: sum over steps of the context size shown
      - total_output_tokens: model-generated text (actions + compaction
        handoff blocks; environment observations are NOT model output)
    """
    if regime not in REGIMES:
        raise ValueError("unknown regime %r; expected one of %s" % (regime, REGIMES))
    compaction = compaction or CompactionStrategy()

    env = task.build_env()
    context: List[str] = [task.prompt]
    peak = total_in = total_out = events = n_actions = 0
    answer = ""
    max_steps_reached = True

    for _ in range(max_steps):
        ctx_tokens = estimate_context_tokens(context)
        peak = max(peak, ctx_tokens)
        total_in += ctx_tokens

        # strip only leading whitespace: trailing whitespace can be part of
        # the payload (e.g. a "write" action whose content ends with a newline)
        action = policy(context).lstrip()
        total_out += estimate_tokens(action)

        if action == "finish" or action.startswith("finish:") or action.startswith("finish "):
            answer = action.split(":", 1)[1].strip() if ":" in action else ""
            max_steps_reached = False
            break

        n_actions += 1
        obs = env.execute(action)
        exchange = [ACTION_MARKER + action, OBS_MARKER + obs]

        if regime == "fha":
            context = context + exchange
        elif regime == "eocc":
            context = context + exchange
            if should_compact(context, threshold_tokens):
                context = compaction.compact(context, task.prompt)
                events += 1
        else:  # sac: one action per context — append the exchange, then reset
            context = context + exchange
            context = compaction.compact(context, task.prompt)
            events += 1

    ok, detail = task.check(env, answer)
    if max_steps_reached:
        ok, detail = False, detail + " (max_steps reached without finish)"
    close = getattr(env, "close", None)
    if callable(close):
        close()
    return RunResult(
        task=task.name,
        category=task.category,
        regime=regime,
        success=ok,
        check_detail=detail,
        n_actions=n_actions,
        compaction_events=events,
        peak_context_tokens=peak,
        total_input_tokens=total_in,
        total_output_tokens=total_out,
        finish_answer=answer,
        max_steps_reached=max_steps_reached,
    )
