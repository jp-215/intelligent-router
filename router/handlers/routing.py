"""The router: given a classified task, pick the best model under an objective."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.classifier import TaskClass
from ..core.models import ModelSpec, tier_rank

OBJECTIVES = ("cost", "quality", "balanced")


@dataclass(frozen=True)
class RoutingDecision:
    model: ModelSpec
    est_cost: float
    rationale: str


def candidates(task: TaskClass, registry: list[ModelSpec]) -> list[ModelSpec]:
    """Models that meet the minimum tier AND have the required capabilities."""
    min_rank = tier_rank(task.min_tier)
    return [m for m in registry if m.rank >= min_rank and m.supports(task.required_caps)]


def select_model(task: TaskClass, registry: list[ModelSpec],
                 objective: str = "cost") -> RoutingDecision:
    if objective not in OBJECTIVES:
        raise ValueError(f"objective must be one of {OBJECTIVES}")

    pool = candidates(task, registry)
    if not pool:
        raise ValueError(f"no model satisfies tier={task.min_tier} caps={set(task.required_caps)}")

    def est(m: ModelSpec) -> float:
        return m.cost(task.est_tokens_in, task.est_tokens_out)

    if objective == "cost":
        # Cheapest capable model — the core "maximize the credit" behavior.
        chosen = min(pool, key=lambda m: (est(m), m.rank))
        why = f"cheapest model meeting tier '{task.min_tier}'"
    elif objective == "quality":
        chosen = max(pool, key=lambda m: (m.rank, -est(m)))
        why = "highest-tier capable model"
    else:  # balanced: lowest tier that qualifies, cheapest within it
        min_tier_rank = min(m.rank for m in pool)
        floor = [m for m in pool if m.rank == min_tier_rank]
        chosen = min(floor, key=est)
        why = "lowest qualifying tier, cheapest within it"

    return RoutingDecision(
        model=chosen,
        est_cost=est(chosen),
        rationale=f"{task.task_type}: {why} -> {chosen.id} (${est(chosen):.5f})",
    )
