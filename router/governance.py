"""Cost governance: hard spend caps, per-agent budgets, and usage analytics."""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import ModelSpec


class BudgetExceeded(Exception):
    """Raised when a call would breach a hard spend cap."""


@dataclass
class Usage:
    agent_id: str
    model_id: str
    task_type: str
    tokens_in: int
    tokens_out: int
    cost: float


@dataclass
class BudgetManager:
    """Tracks spend globally and per-agent, enforcing hard caps.

    `global_cap` is the total credit (e.g. $50). `agent_caps` sets optional per-agent
    ceilings. Both are enforced before a call is allowed.
    """

    global_cap: float = 50.0
    agent_caps: dict[str, float] = field(default_factory=dict)
    usage: list[Usage] = field(default_factory=list)

    @property
    def spent(self) -> float:
        return sum(u.cost for u in self.usage)

    @property
    def remaining(self) -> float:
        return max(0.0, self.global_cap - self.spent)

    def spent_by_agent(self, agent_id: str) -> float:
        return sum(u.cost for u in self.usage if u.agent_id == agent_id)

    def check(self, agent_id: str, cost: float) -> None:
        """Raise BudgetExceeded if this cost would breach the global or agent cap."""
        if self.spent + cost > self.global_cap:
            raise BudgetExceeded(
                f"global cap ${self.global_cap:.2f} would be exceeded "
                f"(spent ${self.spent:.4f} + ${cost:.4f})"
            )
        cap = self.agent_caps.get(agent_id)
        if cap is not None and self.spent_by_agent(agent_id) + cost > cap:
            raise BudgetExceeded(f"agent '{agent_id}' cap ${cap:.2f} would be exceeded")

    def can_afford(self, agent_id: str, cost: float) -> bool:
        try:
            self.check(agent_id, cost)
            return True
        except BudgetExceeded:
            return False

    def record(self, agent_id: str, model: ModelSpec, task_type: str,
               tokens_in: int, tokens_out: int) -> Usage:
        u = Usage(agent_id, model.id, task_type, tokens_in, tokens_out,
                  model.cost(tokens_in, tokens_out))
        self.usage.append(u)
        return u

    # --- analytics ---
    def _agg(self, key) -> dict[str, float]:
        out: dict[str, float] = {}
        for u in self.usage:
            k = key(u)
            out[k] = out.get(k, 0.0) + u.cost
        return out

    def report(self) -> dict:
        return {
            "spent": round(self.spent, 6),
            "remaining": round(self.remaining, 6),
            "by_agent": {k: round(v, 6) for k, v in self._agg(lambda u: u.agent_id).items()},
            "by_model": {k: round(v, 6) for k, v in self._agg(lambda u: u.model_id).items()},
            "by_task_type": {k: round(v, 6) for k, v in self._agg(lambda u: u.task_type).items()},
            "calls": len(self.usage),
        }
