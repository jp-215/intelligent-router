import pytest

from router.services.governance import BudgetExceeded, BudgetManager
from router.services.registry import by_id


def test_global_cap_enforced():
    b = BudgetManager(global_cap=0.01)
    big = by_id("claude-opus-4-8").cost(1_000_000, 1_000_000)
    with pytest.raises(BudgetExceeded):
        b.check("agent1", big)


def test_per_agent_cap_enforced():
    b = BudgetManager(global_cap=100.0, agent_caps={"a": 0.001})
    cost = by_id("gemini-3.5-flash").cost(1_000_000, 1_000_000)
    assert not b.can_afford("a", cost)       # blocked by agent cap
    assert b.can_afford("b", cost)           # other agent has no cap


def test_record_and_report():
    b = BudgetManager(global_cap=50.0)
    b.record("a", by_id("gemini-3.5-flash"), "docs", 1000, 1000)
    b.record("b", by_id("claude-opus-4-8"), "architecture", 1000, 1000)
    rep = b.report()
    assert rep["calls"] == 2
    assert set(rep["by_agent"]) == {"a", "b"}
    assert set(rep["by_task_type"]) == {"docs", "architecture"}
    assert rep["spent"] > 0
    assert rep["remaining"] == pytest.approx(50.0 - rep["spent"])
