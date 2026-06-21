"""Prompt-attribute analysis to sharpen model selection.

Refines a TaskClass using the actual prompt: estimated token size, long-context need,
and vision signals — so routing reflects the real request, not just the task type.
"""

from __future__ import annotations

from dataclasses import replace

from ..utils.tokens import estimate_tokens
from .classifier import TaskClass
from .models import CAP_LONG_CONTEXT, CAP_VISION

# estimate_tokens is re-exported here so historical callers keep working.
__all__ = ["LONG_CONTEXT_TOKENS", "analyze_prompt", "estimate_tokens"]

LONG_CONTEXT_TOKENS = 8000  # above this estimated input, require long-context capability
_VISION_HINTS = ("image", "screenshot", "photo", "picture", "this diagram", "attached")


def analyze_prompt(prompt: str, task: TaskClass) -> TaskClass:
    """Return a TaskClass refined by the prompt's measurable attributes."""
    est_in = max(task.est_tokens_in, estimate_tokens(prompt))
    caps = set(task.required_caps)

    if est_in >= LONG_CONTEXT_TOKENS:
        caps.add(CAP_LONG_CONTEXT)
    low = prompt.lower()
    if any(h in low for h in _VISION_HINTS):
        caps.add(CAP_VISION)

    return replace(task, est_tokens_in=est_in, required_caps=frozenset(caps))
