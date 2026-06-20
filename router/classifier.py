"""Classify a task into the minimum capability it needs.

This is the "monetize low models for cheap tasks" brain: a README maps to a cheap
tier; an architecture decision maps to frontier. Rule-based + keyword heuristics so it
is deterministic and free (no LLM call needed to decide routing).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import CAP_CODE, CAP_LONG_CONTEXT, CAP_REASONING, CAP_VISION


@dataclass(frozen=True)
class TaskClass:
    task_type: str
    min_tier: str
    required_caps: frozenset[str] = field(default_factory=frozenset)
    est_tokens_in: int = 1000
    est_tokens_out: int = 600


# task_type -> (min_tier, caps, est_in, est_out). Cheapest tier that does the job well.
TASK_PROFILES = {
    "classify": ("nano", frozenset(), 400, 50),
    "extract": ("nano", frozenset(), 800, 200),
    "summarize": ("mini", frozenset(), 2000, 400),
    "docs": ("mini", frozenset({CAP_CODE}), 1500, 800),
    "boilerplate": ("mini", frozenset({CAP_CODE}), 1200, 1200),
    "commit_message": ("nano", frozenset({CAP_CODE}), 600, 100),
    "codegen_simple": ("standard", frozenset({CAP_CODE}), 2000, 1500),
    "test_gen": ("standard", frozenset({CAP_CODE}), 2500, 1800),
    "codegen_complex": ("pro", frozenset({CAP_CODE, CAP_REASONING}), 4000, 3000),
    "review": ("pro", frozenset({CAP_CODE, CAP_REASONING}), 5000, 1500),
    "security_review": ("frontier", frozenset({CAP_CODE, CAP_REASONING}), 6000, 2000),
    "architecture": ("frontier", frozenset({CAP_REASONING, CAP_LONG_CONTEXT}), 4000, 2500),
    "reasoning_hard": ("frontier", frozenset({CAP_REASONING}), 3000, 2000),
    "vision": ("pro", frozenset({CAP_VISION}), 2000, 600),
}

DEFAULT_PROFILE = ("standard", frozenset({CAP_CODE}), 2000, 1200)

# keyword -> task_type, checked in order.
_KEYWORDS = [
    (("readme", "documentation", "docstring", "comment", "changelog"), "docs"),
    (("commit message",), "commit_message"),
    (("boilerplate", "scaffold", "skeleton", "stub"), "boilerplate"),
    (("classify", "categorize", "label", "sentiment"), "classify"),
    (("extract", "parse", "pull out"), "extract"),
    (("summarize", "tl;dr", "summary"), "summarize"),
    (("unit test", "write tests", "test coverage"), "test_gen"),
    (("security", "vulnerability", "exploit", "auth review"), "security_review"),
    (("architecture", "system design", "design doc", "tradeoff"), "architecture"),
    (("review", "code review", "critique"), "review"),
    (("image", "screenshot", "photo", "diagram of"), "vision"),
    (("prove", "complex reasoning", "algorithm design", "optimize"), "reasoning_hard"),
    (("implement", "build", "write a function", "feature"), "codegen_complex"),
]


def classify_task(text: str, task_type: str | None = None) -> TaskClass:
    """Classify free-text (or an explicit task_type) into a TaskClass."""
    if task_type is None:
        task_type = _infer_type(text)
    profile = TASK_PROFILES.get(task_type, DEFAULT_PROFILE)
    min_tier, caps, est_in, est_out = profile
    return TaskClass(task_type=task_type, min_tier=min_tier, required_caps=caps,
                     est_tokens_in=est_in, est_tokens_out=est_out)


def _infer_type(text: str) -> str:
    low = text.lower()
    for keywords, task_type in _KEYWORDS:
        if any(k in low for k in keywords):
            return task_type
    return "codegen_simple"
