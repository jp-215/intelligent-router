from router.dashboard import dashboard_payload, write_payload
from router.governance import BudgetManager
from router.registry import by_id


def _budget():
    b = BudgetManager(global_cap=10.0)
    b.record("a", by_id("gemini-3.5-flash"), "docs", 1000, 1000)
    b.record("b", by_id("claude-opus-4-8"), "architecture", 1000, 1000)
    return b


def test_payload_has_expected_keys():
    p = dashboard_payload(_budget())
    for key in ["spent", "remaining", "global_cap", "pct_used",
                "by_model", "by_agent", "by_task_type", "calls"]:
        assert key in p
    assert p["calls"] == 2
    assert p["global_cap"] == 10.0


def test_pct_used_is_consistent():
    b = _budget()
    p = dashboard_payload(b)
    assert p["pct_used"] == round(100 * b.spent / b.global_cap, 2)


def test_zero_cap_pct_is_zero():
    p = dashboard_payload(BudgetManager(global_cap=0.0))
    assert p["pct_used"] == 0.0


def test_write_payload(tmp_path):
    out = tmp_path / "report.json"
    write_payload(_budget(), str(out))
    import json
    data = json.loads(out.read_text())
    assert data["calls"] == 2
