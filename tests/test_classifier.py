from router.core.classifier import classify_task
from router.core.models import CAP_VISION


def test_readme_is_cheap_tier():
    tc = classify_task("Write a comprehensive README for the project")
    assert tc.task_type == "docs"
    assert tc.min_tier in ("nano", "mini")


def test_architecture_is_frontier():
    tc = classify_task("Design the system architecture and tradeoffs for the gateway")
    assert tc.task_type == "architecture"
    assert tc.min_tier == "frontier"


def test_security_review_is_frontier():
    tc = classify_task("Do a security review of the auth flow for vulnerabilities")
    assert tc.task_type == "security_review"
    assert tc.min_tier == "frontier"


def test_vision_requires_vision_cap():
    tc = classify_task("Describe this screenshot image", task_type="vision")
    assert CAP_VISION in tc.required_caps


def test_explicit_type_overrides_keywords():
    tc = classify_task("anything at all", task_type="classify")
    assert tc.task_type == "classify"
    assert tc.min_tier == "nano"


def test_unknown_defaults_to_codegen_simple():
    tc = classify_task("do the thing with the stuff")
    assert tc.task_type == "codegen_simple"
