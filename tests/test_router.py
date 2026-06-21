import pytest

from router.core.classifier import classify_task
from router.core.models import CAP_VISION, ModelSpec
from router.handlers.routing import candidates, select_model
from router.services.registry import REGISTRY


def test_cheap_task_routes_to_cheap_model():
    tc = classify_task("Write a README", task_type="docs")
    decision = select_model(tc, REGISTRY, objective="cost")
    # Should pick a mini/nano-tier model, not a frontier one.
    assert decision.model.rank <= 1
    assert decision.est_cost > 0


def test_hard_task_routes_to_frontier():
    tc = classify_task("architecture", task_type="architecture")
    decision = select_model(tc, REGISTRY, objective="cost")
    assert decision.model.tier == "frontier"


def test_cost_objective_is_cheapest_capable():
    tc = classify_task("simple codegen", task_type="codegen_simple")
    pool = candidates(tc, REGISTRY)
    decision = select_model(tc, REGISTRY, objective="cost")
    cheapest = min(c.cost(tc.est_tokens_in, tc.est_tokens_out) for c in pool)
    assert decision.est_cost == pytest.approx(cheapest)


def test_quality_objective_picks_higher_tier_than_cost():
    tc = classify_task("simple codegen", task_type="codegen_simple")
    cost_pick = select_model(tc, REGISTRY, "cost").model
    quality_pick = select_model(tc, REGISTRY, "quality").model
    assert quality_pick.rank >= cost_pick.rank


def test_vision_requirement_filters_pool():
    tc = classify_task("look at image", task_type="vision")
    for m in candidates(tc, REGISTRY):
        assert CAP_VISION in m.capabilities


def test_no_candidate_raises():
    tiny = [ModelSpec("only-nano", "inference", "nano", 0.1, 0.1, frozenset())]
    tc = classify_task("architecture", task_type="architecture")
    with pytest.raises(ValueError):
        select_model(tc, tiny, "cost")
