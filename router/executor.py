"""Runtime orchestration: classify -> analyze -> route with fallbacks -> enforce budget.

Brings the three use cases together on the live path:
  • intelligent selection  (classify + analyze_prompt + select_model)
  • fallback routing       (try the chain, skip failures)
  • cost governance        (hard caps checked before every attempt)

The `complete` callable — (model_id, prompt) -> object with .text/.tokens_in/.tokens_out —
is injected, so tests run with a fake (no credit) and prod wires it to a provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .analyze import analyze_prompt
from .classifier import classify_task
from .fallback import build_fallback_chain
from .governance import BudgetExceeded, BudgetManager
from .models import ModelSpec


@dataclass
class ExecutionResult:
    model_id: str
    text: str
    tokens_in: int
    tokens_out: int
    cost: float          # upstream model cost
    billed: float = 0.0  # client charge (cost + markup)
    attempts: list[str] = field(default_factory=list)


class Executor:
    def __init__(self, complete, budget: BudgetManager, registry: list[ModelSpec],
                 objective: str = "cost") -> None:
        self._complete = complete
        self.budget = budget
        self.registry = registry
        self.objective = objective

    def run(self, prompt: str, agent_id: str = "default",
            task_type: str | None = None) -> ExecutionResult:
        task = analyze_prompt(prompt, classify_task(prompt, task_type))
        chain = build_fallback_chain(task, self.registry, self.objective)

        attempts: list[str] = []
        errors: list[str] = []
        for model in chain:
            est = model.cost(task.est_tokens_in, task.est_tokens_out)
            if not self.budget.can_afford(agent_id, est):
                errors.append(f"{model.id}: over budget")
                continue
            attempts.append(model.id)
            try:
                comp = self._complete(model.id, prompt)
            except Exception as exc:  # provider outage/degradation -> fall back
                errors.append(f"{model.id}: {exc}")
                continue
            usage = self.budget.record(agent_id, model, task.task_type,
                                       comp.tokens_in, comp.tokens_out)
            return ExecutionResult(model.id, comp.text, comp.tokens_in, comp.tokens_out,
                                   usage.cost, billed=usage.billed, attempts=attempts)

        if not attempts:
            raise BudgetExceeded("; ".join(errors) or "no affordable model")
        raise RuntimeError("all candidate models failed: " + "; ".join(errors))
