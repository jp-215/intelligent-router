from router.analyze import analyze_prompt, estimate_tokens
from router.classifier import classify_task
from router.models import CAP_LONG_CONTEXT, CAP_VISION


def test_estimate_tokens():
    assert estimate_tokens("") == 1
    assert estimate_tokens("a" * 400) == 100


def test_large_prompt_requires_long_context():
    task = classify_task("summarize this", task_type="summarize")
    big = analyze_prompt("x" * 40000, task)
    assert CAP_LONG_CONTEXT in big.required_caps
    assert big.est_tokens_in >= 10000


def test_vision_hint_adds_vision_cap():
    task = classify_task("what is in this", task_type="summarize")
    refined = analyze_prompt("Describe this screenshot please", task)
    assert CAP_VISION in refined.required_caps


def test_small_text_prompt_unchanged_caps():
    task = classify_task("classify this", task_type="classify")
    refined = analyze_prompt("short prompt", task)
    assert CAP_LONG_CONTEXT not in refined.required_caps
    assert CAP_VISION not in refined.required_caps
