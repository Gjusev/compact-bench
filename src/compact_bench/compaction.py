"""Context compaction strategies for the three paper regimes.

Regimes (arXiv:2611.05306):
- FHA  (Full-History Accumulation): never compact; baseline.
- EOCC (End-of-Conversation Compaction): when the context crosses a token
  threshold, replace everything with the original task + a bounded handoff
  state block.
- SAC  (Single-Action Compaction): after EVERY action, reset to task + state.

The state block is deliberately structured (progress counter + last
observations) rather than a generic summary — the paper's Appendix A finds
generic summarisation performs worse than a forward-looking handoff brief.
"""

import re

from .tokens import estimate_context_tokens

STATE_HEADER = "--- COMPACTED STATE ---"
STATE_FOOTER = "--- END STATE ---"
OBS_TITLE = "LAST OBSERVATIONS (extractive, truncated):"
ACTION_MARKER = "ACTION: "
OBS_MARKER = "OBSERVATION: "

_COUNTER_RE = re.compile(r"ACTIONS SO FAR:\s*(\d+)")
_OBS_LINE_RE = re.compile(r"^OBSERVATION:\s*(.*)$", re.MULTILINE)


def count_action_markers(text: str) -> int:
    return text.count(ACTION_MARKER)


def current_step(context) -> int:
    """How many actions the agent has taken, recovered from the context.

    Load-bearing for compaction regimes: the agent (stub or LLM) needs its
    progress to survive compaction. A compaction that loses this line makes
    the agent replay its plan from the start.
    """
    joined = "\n".join(context)
    m = _COUNTER_RE.search(joined)
    if m:
        base = int(m.group(1))
        # actions appended after the last compaction are not counted in it
        tail = joined.split(STATE_HEADER, 1)[-1]
        return base + count_action_markers(tail)
    return count_action_markers(joined)


def make_state_block(context, keep_last_observations: int = 4, obs_char_cap: int = 200) -> str:
    """Deterministic extractive handoff state for the current context."""
    joined = "\n".join(context)
    done = current_step(context)
    obs_lines = [ln.strip() for ln in _OBS_LINE_RE.findall(joined)]
    kept = []
    for line in obs_lines[-keep_last_observations:]:
        if len(line) > obs_char_cap:
            line = line[:obs_char_cap] + " ...[truncated]"
        kept.append("- " + line if line else "- (empty)")
    lines = [
        STATE_HEADER,
        "ACTIONS SO FAR: %d" % done,
        OBS_TITLE,
    ]
    lines.extend(kept)
    lines.append(STATE_FOOTER)
    return "\n".join(lines)


class CompactionStrategy:
    """Default strategy: bounded, structured handoff state."""

    def __init__(self, keep_last_observations: int = 4, obs_char_cap: int = 200):
        self.keep_last_observations = keep_last_observations
        self.obs_char_cap = obs_char_cap

    def compact(self, context, task_prompt):
        return [task_prompt, make_state_block(
            context,
            keep_last_observations=self.keep_last_observations,
            obs_char_cap=self.obs_char_cap,
        )]


class LossyCompaction(CompactionStrategy):
    """Deliberately broken strategy used in tests: drops the progress counter.

    Models a compaction that loses the agent's progress state. Under SAC this
    makes the agent replay its plan from step 0 forever — the test proves the
    counter is load-bearing and that the harness can detect bad compaction.
    """

    def compact(self, context, task_prompt):
        block = make_state_block(
            context,
            keep_last_observations=self.keep_last_observations,
            obs_char_cap=self.obs_char_cap,
        )
        # strip every counter line -> progress is lost
        block = _COUNTER_RE.sub("ACTIONS SO FAR: (lost)", block)
        return [task_prompt, block]


def should_compact(context, threshold_tokens: int) -> bool:
    return estimate_context_tokens(context) > threshold_tokens
