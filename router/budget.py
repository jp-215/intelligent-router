"""Track spend against the credit budget (default $50)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import ModelSpec


@dataclass
class Entry:
    model_id: str
    tokens_in: int
    tokens_out: int
    cost: float


@dataclass
class BudgetTracker:
    total_usd: float = 50.0
    entries: list[Entry] = field(default_factory=list)

    def record(self, model: ModelSpec, tokens_in: int, tokens_out: int) -> Entry:
        cost = model.cost(tokens_in, tokens_out)
        entry = Entry(model.id, tokens_in, tokens_out, cost)
        self.entries.append(entry)
        return entry

    @property
    def spent(self) -> float:
        return sum(e.cost for e in self.entries)

    @property
    def remaining(self) -> float:
        return max(0.0, self.total_usd - self.spent)

    @property
    def over_budget(self) -> bool:
        return self.spent > self.total_usd

    def can_afford(self, model: ModelSpec, tokens_in: int, tokens_out: int) -> bool:
        return model.cost(tokens_in, tokens_out) <= self.remaining

    def by_model(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for e in self.entries:
            out[e.model_id] = out.get(e.model_id, 0.0) + e.cost
        return out
