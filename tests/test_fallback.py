from router.classifier import classify_task
from router.fallback import build_fallback_chain
from router.registry import REGISTRY


def test_chain_starts_with_cost_primary():
    task = classify_task("write a readme", task_type="docs")
    chain = build_fallback_chain(task, REGISTRY, "cost", max_len=3)
    assert len(chain) <= 3
    assert chain[0].tier == "mini"  # cheapest capable is the primary


def test_chain_prefers_open_source_backups():
    task = classify_task("simple codegen", task_type="codegen_simple")
    chain = build_fallback_chain(task, REGISTRY, "cost", max_len=3, prefer_open_source=True)
    # At least one backup after the primary should be an open-weight model.
    assert any(m.open_source for m in chain[1:])


def test_chain_models_all_capable():
    task = classify_task("architecture", task_type="architecture")
    chain = build_fallback_chain(task, REGISTRY, "cost")
    for m in chain:
        assert m.supports(task.required_caps)
        assert m.tier == "frontier"
