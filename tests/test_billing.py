from router.services.billing import BillingPolicy
from router.services.governance import BudgetManager
from router.services.registry import by_id


def test_markup_price():
    p = BillingPolicy(markup_pct=0.20)
    assert p.price(1.0) == 1.2


def test_flat_fee_and_min_charge():
    p = BillingPolicy(markup_pct=0.0, flat_fee=0.01, min_charge=0.05)
    assert p.price(0.0) == 0.05      # min charge floor
    assert p.price(1.0) == 1.01      # cost + flat fee


def test_no_markup_is_passthrough():
    assert BillingPolicy().price(0.5) == 0.5


def test_budget_tracks_revenue_and_margin():
    b = BudgetManager(global_cap=50.0, billing=BillingPolicy(markup_pct=0.5))
    model = by_id("gemini-3.5-flash")
    u = b.record("client-a", model, "docs", 1000, 1000)
    assert u.billed > u.cost
    assert b.revenue > b.spent
    assert round(b.margin, 6) == round(b.revenue - b.spent, 6)


def test_report_includes_billing_fields():
    b = BudgetManager(global_cap=50.0, billing=BillingPolicy(markup_pct=0.25))
    b.record("client-a", by_id("gemini-3.5-flash"), "docs", 1000, 1000)
    b.record("client-b", by_id("claude-opus-4-8"), "architecture", 1000, 1000)
    rep = b.report()
    assert rep["markup_pct"] == 0.25
    assert rep["revenue"] >= rep["spent"]
    assert set(rep["revenue_by_agent"]) == {"client-a", "client-b"}
