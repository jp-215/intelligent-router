from router.core.models import TIERS
from router.services.registry import REGISTRY, build_registry, by_id


def test_all_listed_models_present():
    ids = {m.id for m in REGISTRY}
    for expected in ["claude-opus-4-8", "claude-sonnet-4-6", "gpt-5.4",
                     "gemini-3.5-flash", "deepseek-v4-flash", "glm-5.1"]:
        assert expected in ids


def test_specs_are_valid():
    for m in REGISTRY:
        assert m.tier in TIERS
        assert m.price_in > 0 and m.price_out > 0
        assert m.price_out >= m.price_in  # output is never cheaper than input


def test_cheaper_tier_is_actually_cheaper():
    flash = by_id("gemini-3.5-flash")
    opus = by_id("claude-opus-4-8")
    assert flash.cost(1000, 1000) < opus.cost(1000, 1000)


def test_pricing_override(tmp_path, monkeypatch):
    f = tmp_path / "prices.json"
    f.write_text('{"gemini-3.5-flash": {"price_in": 99.0, "price_out": 99.0}}')
    monkeypatch.setenv("ROUTER_PRICING_JSON", str(f))
    reg = build_registry()
    flash = by_id("gemini-3.5-flash", reg)
    assert flash.price_in == 99.0
