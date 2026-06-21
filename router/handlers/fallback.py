"""Fallback routing: an ordered chain of models to try on outage/degradation.

The primary is the objective-optimal pick; backups are added for resilience, preferring
open-weight models (deepseek/qwen/glm/kimi) so a frontier-provider outage doesn't take
the whole request down.
"""

from __future__ import annotations

from ..core.classifier import TaskClass
from ..core.models import ModelSpec
from .routing import candidates, select_model


def build_fallback_chain(task: TaskClass, registry: list[ModelSpec],
                         objective: str = "cost", max_len: int = 3,
                         prefer_open_source: bool = True) -> list[ModelSpec]:
    """Ordered list of capable models to try: primary first, then resilient backups."""
    primary = select_model(task, registry, objective).model
    pool = [m for m in candidates(task, registry) if m.id != primary.id]

    def backup_key(m: ModelSpec):
        # Prefer open-source first (resilience), then cheapest.
        os_rank = 0 if (prefer_open_source and m.open_source) else 1
        return (os_rank, m.cost(task.est_tokens_in, task.est_tokens_out))

    chain = [primary, *sorted(pool, key=backup_key)]
    # De-dup by provider+family where possible isn't needed here; cap the length.
    return chain[:max_len]
