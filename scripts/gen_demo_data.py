"""Generate web/report.json from a simulated run (no API credit spent).

Runs a spread of tasks through the Executor with a fake completion fn so the dashboard
has realistic-shaped data to render. Replace with real usage once you log live runs.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from router.dashboard import write_payload  # noqa: E402
from router.executor import Executor  # noqa: E402
from router.governance import BudgetManager  # noqa: E402
from router.registry import REGISTRY  # noqa: E402


class _Comp:
    def __init__(self, tin: int, tout: int) -> None:
        self.text = "ok"
        self.tokens_in = tin
        self.tokens_out = tout


def _fake_complete(model_id: str, prompt: str) -> _Comp:
    # token shape scales loosely with prompt length
    return _Comp(max(200, len(prompt) // 3), 400)


# (agent, prompt, task_type)
SAMPLE = [
    ("docs-bot", "Write a comprehensive README for the gateway", "docs"),
    ("docs-bot", "Write docstrings for the router module", "docs"),
    ("triage-bot", "Classify this support ticket", "classify"),
    ("triage-bot", "Extract entities from the log line", "extract"),
    ("build-bot", "Implement the signup endpoint with validation", "codegen_complex"),
    ("build-bot", "Write unit tests for the signup flow", "test_gen"),
    ("arch-bot", "Design the multi-region routing architecture", "architecture"),
    ("sec-bot", "Security review of the auth token handling", "security_review"),
]


def main() -> int:
    budget = BudgetManager(global_cap=50.0,
                           agent_caps={"docs-bot": 5.0, "triage-bot": 2.0})
    ex = Executor(_fake_complete, budget, REGISTRY, objective="cost")
    for agent, prompt, ttype in SAMPLE:
        ex.run(prompt, agent_id=agent, task_type=ttype)

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "web", "report.json")
    payload = write_payload(budget, out)
    print(f"wrote {out}: spent ${payload['spent']:.4f} over {payload['calls']} calls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
