"""Deterministic token estimation. Stdlib only, model independent.

The paper counts real tokenizer tokens; offline harness validation only needs
a stable, monotone estimate, so we use the standard chars/4 heuristic. Real
model runs should swap this for a server-reported usage count (the Z.ai
client returns usage when available).
"""

import math


def estimate_tokens(text: str) -> int:
    """Estimate token count of a string (ceil(len/4), min 1 for non-empty)."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def estimate_context_tokens(context) -> int:
    """Estimate token count of a context (a list of message/block strings)."""
    return sum(estimate_tokens(block) for block in context)
