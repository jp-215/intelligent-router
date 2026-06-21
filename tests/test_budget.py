from router.services.budget import BudgetTracker
from router.services.registry import by_id


def test_records_and_tracks_spend():
    b = BudgetTracker(total_usd=50.0)
    model = by_id("gemini-3.5-flash")
    b.record(model, 1_000_000, 1_000_000)
    assert b.spent == model.cost(1_000_000, 1_000_000)
    assert b.remaining == 50.0 - b.spent
    assert not b.over_budget


def test_over_budget_flag():
    b = BudgetTracker(total_usd=0.01)
    b.record(by_id("claude-opus-4-8"), 1_000_000, 1_000_000)
    assert b.over_budget
    assert b.remaining == 0.0


def test_can_afford():
    b = BudgetTracker(total_usd=1.0)
    cheap = by_id("deepseek-v4-flash")
    assert b.can_afford(cheap, 1000, 1000)


def test_by_model_breakdown():
    b = BudgetTracker()
    m = by_id("qwen3.5-plus")
    b.record(m, 100, 100)
    b.record(m, 100, 100)
    assert set(b.by_model().keys()) == {"qwen3.5-plus"}
