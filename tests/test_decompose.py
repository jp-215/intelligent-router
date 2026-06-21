from router.handlers.planning import parse_decomposition, plan_feature
from router.services.registry import REGISTRY

FAKE_LLM_JSON = """```json
{"stories": [
  {"title": "User can sign up", "tasks": [
    {"title": "Write the signup README section", "type": "docs"},
    {"title": "Implement signup endpoint with validation", "type": "codegen_complex"},
    {"title": "Write unit tests for signup", "type": "test_gen"}
  ]},
  {"title": "Security", "tasks": [
    {"title": "Security review of auth", "type": "security_review"}
  ]}
]}
```"""


def fake_llm(_prompt: str) -> str:
    return FAKE_LLM_JSON


def test_parse_handles_code_fence():
    stories = parse_decomposition(FAKE_LLM_JSON)
    assert len(stories) == 2
    assert stories[0]["title"] == "User can sign up"


def test_plan_routes_every_task():
    plan = plan_feature("User signup", fake_llm, REGISTRY, objective="cost")
    assert plan.task_count == 4
    assert plan.est_cost > 0

    # The cheap docs task should get a cheaper model than the security review.
    docs = plan.stories[0].tasks[0]
    sec = plan.stories[1].tasks[0]
    assert docs.decision.model.rank < sec.decision.model.rank
    assert sec.decision.model.tier == "frontier"


def test_plan_cost_objective_beats_quality():
    cheap = plan_feature("User signup", fake_llm, REGISTRY, "cost").est_cost
    pricey = plan_feature("User signup", fake_llm, REGISTRY, "quality").est_cost
    assert cheap <= pricey
