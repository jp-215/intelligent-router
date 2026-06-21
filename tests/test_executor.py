import pytest

from router.handlers.execution import Executor
from router.services.governance import BudgetExceeded, BudgetManager
from router.services.registry import REGISTRY


class Comp:
    def __init__(self, text, tin=1000, tout=500):
        self.text = text
        self.tokens_in = tin
        self.tokens_out = tout


def test_runs_on_primary_and_records_budget():
    calls = []

    def complete(model_id, prompt):
        calls.append(model_id)
        return Comp("ok")

    b = BudgetManager(global_cap=50.0)
    ex = Executor(complete, b, REGISTRY, objective="cost")
    result = ex.run("Write a README", task_type="docs")

    assert result.text == "ok"
    assert len(calls) == 1                 # primary succeeded, no fallback
    assert b.spent > 0
    assert result.model_id == result.attempts[-1]


def test_falls_back_when_primary_errors():
    seen = []

    def complete(model_id, prompt):
        seen.append(model_id)
        if len(seen) == 1:
            raise RuntimeError("simulated outage")
        return Comp("recovered")

    b = BudgetManager(global_cap=50.0)
    ex = Executor(complete, b, REGISTRY, objective="cost")
    result = ex.run("simple codegen", task_type="codegen_simple")

    assert result.text == "recovered"
    assert len(seen) == 2                   # first failed, second succeeded
    assert len(result.attempts) == 2


def test_hard_cap_blocks_all_and_raises():
    def complete(model_id, prompt):
        return Comp("should not happen")

    b = BudgetManager(global_cap=0.0)       # nothing affordable
    ex = Executor(complete, b, REGISTRY, objective="cost")
    with pytest.raises(BudgetExceeded):
        ex.run("architecture", task_type="architecture")
