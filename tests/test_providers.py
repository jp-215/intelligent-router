import json

from router.registry import build_registry


def _write_catalog(tmp_path):
    f = tmp_path / "or.json"
    f.write_text(json.dumps([
        {"id": "vendor/cheap-nano", "tier": "nano", "caps": ["code"],
         "price_in": 0.01, "price_out": 0.02, "open_source": True},
        {"id": "vendor/frontier-x", "tier": "frontier", "caps": ["reasoning", "code"],
         "price_in": 5.0, "price_out": 25.0},
    ]))
    return str(f)


def test_openrouter_models_loaded_when_key_set(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("ROUTER_OPENROUTER_MODELS", _write_catalog(tmp_path))
    reg = build_registry()
    providers = {m.provider for m in reg}
    assert "openrouter" in providers
    assert any(m.id == "vendor/cheap-nano" and m.provider == "openrouter" for m in reg)


def test_openrouter_models_absent_without_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("ROUTER_OPENROUTER_MODELS", _write_catalog(tmp_path))
    reg = build_registry()
    assert all(m.provider == "inference" for m in reg)


def test_cheaper_openrouter_model_wins_on_cost(tmp_path, monkeypatch):
    from router.classifier import classify_task
    from router.router import select_model
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("ROUTER_OPENROUTER_MODELS", _write_catalog(tmp_path))
    reg = build_registry()
    tc = classify_task("classify this", task_type="classify")  # nano tier
    decision = select_model(tc, reg, "cost")
    # The injected nano at $0.01/$0.02 undercuts the inference nano estimate.
    assert decision.model.id == "vendor/cheap-nano"
    assert decision.model.provider == "openrouter"
