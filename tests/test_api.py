import pytest
from fastapi.testclient import TestClient

from router.api import app, get_budget, get_completer
from router.governance import BudgetManager


class Comp:
    def __init__(self, text, tin=800, tout=300):
        self.text = text
        self.tokens_in = tin
        self.tokens_out = tout


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_models_lists_catalog(client):
    data = client.get("/models").json()
    assert any(m["id"] == "claude-opus-4-8" for m in data)
    assert all({"id", "tier", "capabilities"} <= set(m) for m in data)


def test_route_is_free_and_picks_cheap(client):
    resp = client.post("/route", json={"prompt": "Write a README", "task_type": "docs"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["task_type"] == "docs"
    assert body["tier"] in ("nano", "mini")


def test_complete_with_mocked_provider(client):
    app.dependency_overrides[get_completer] = lambda: (lambda model_id, prompt: Comp("done"))
    resp = client.post("/complete", json={"prompt": "Write a README", "task_type": "docs",
                                          "agent_id": "tester"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["text"] == "done"
    assert body["cost"] > 0


def test_complete_budget_exceeded_returns_402(client):
    app.dependency_overrides[get_completer] = lambda: (lambda model_id, prompt: Comp("x"))
    app.dependency_overrides[get_budget] = lambda: BudgetManager(global_cap=0.0)
    resp = client.post("/complete", json={"prompt": "architecture", "task_type": "architecture"})
    assert resp.status_code == 402


def test_plan_with_mocked_llm(client):
    fake_json = '{"stories":[{"title":"S","tasks":[{"title":"Write README","type":"docs"}]}]}'
    app.dependency_overrides[get_completer] = lambda: (lambda model_id, prompt: Comp(fake_json))
    resp = client.post("/plan", json={"feature": "signup"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["task_count"] == 1
    assert body["stories"][0]["tasks"][0]["model"]


def test_report(client):
    assert "spent" in client.get("/report").json()
