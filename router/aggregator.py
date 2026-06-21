"""Hierarchical Map-Reduce over a task DAG.

Map phase: execute each task in dependency order, routed to the cheapest capable model.
Reduce phase 1 (per story): condense a story's task outputs on a PRO-tier model.
Reduce phase 2 (epic): integrate the compressed story modules on a FRONTIER model — this
is where frontier models earn their keep (and their markup).

State isolation: each story's task outputs stay within that story; the epic reducer only
sees the compressed story modules, never the raw task dumps.

The `run_task` callable is injected so the whole pipeline is unit-tested offline with no
live API calls or credit spend.
"""

from __future__ import annotations

from dataclasses import dataclass

from .classifier import TaskClass, classify_task
from .dag import Node, levels
from .governance import BudgetExceeded, BudgetManager
from .models import CAP_CODE, CAP_REASONING, ModelSpec
from .registry import REGISTRY
from .router import select_model

STORY_REDUCE_TIER = "pro"
EPIC_REDUCE_TIER = "frontier"
REDUCE_CAPS = frozenset({CAP_REASONING, CAP_CODE})


def _sot_block(sot: str) -> str:
    """Render the immutable Source-of-Truth anchor injected into every reduce prompt.

    Anti-semantic-drift guardrail: the original user request is re-stated to the reducing
    model so multi-level reduction can't quietly diverge from what was actually asked for.
    """
    if not sot:
        return ""
    return (
        "SOURCE OF TRUTH (the original user request — the final result MUST stay faithful "
        f'to this; do not drift):\n"""\n{sot}\n"""\n\n'
    )


@dataclass
class RunResult:
    text: str
    model_id: str
    tier: str
    cost: float
    billed: float


@dataclass
class StepResult:
    label: str
    phase: str  # "map" | "story_reduce" | "epic_reduce"
    model: str
    tier: str
    cost: float
    billed: float


@dataclass
class MapReduceResult:
    epic: str
    final_output: str
    steps: list[StepResult]

    @property
    def total_cost(self) -> float:
        return round(sum(s.cost for s in self.steps), 6)

    @property
    def total_billed(self) -> float:
        return round(sum(s.billed for s in self.steps), 6)

    @property
    def tier_usage(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for s in self.steps:
            out[s.tier] = out.get(s.tier, 0) + 1
        return out

    @property
    def used_frontier(self) -> bool:
        return any(s.tier == "frontier" for s in self.steps)


class Aggregator:
    def __init__(self, run_task) -> None:
        # run_task(prompt, min_tier, caps, agent_id) -> RunResult
        self.run_task = run_task

    def run(self, epic_spec: dict, agent_id: str = "aggregator") -> MapReduceResult:
        epic = epic_spec.get("epic", "")
        # Immutable Source of Truth: the original user dialog/epic text. Falls back to the
        # epic title if no richer original prompt was supplied. Re-injected into every
        # reduction so the output can't drift from what the user actually asked for.
        sot = epic_spec.get("source_of_truth") or epic
        sot_block = _sot_block(sot)
        steps: list[StepResult] = []
        story_modules: list[tuple[str, str]] = []

        for story in epic_spec.get("stories", []):
            tasks = story.get("tasks", [])
            tmap = {t["id"]: t for t in tasks}
            nodes = [Node(t["id"], tuple(t.get("depends_on", []))) for t in tasks]

            outputs: dict[str, str] = {}  # isolated per story
            for batch in levels(nodes):
                for tid in batch:
                    t = tmap[tid]
                    ctx = "".join(
                        f"\n[from {d}]:\n{outputs.get(d, '')}" for d in t.get("depends_on", [])
                    )
                    prompt = f"Task: {t['title']}" + (f"\nDependency context:{ctx}" if ctx else "")
                    tc: TaskClass = classify_task(t["title"], t.get("task_type"))
                    r = self.run_task(prompt, tc.min_tier, tc.required_caps, agent_id)
                    outputs[tid] = r.text
                    steps.append(StepResult(f"map:{story['id']}:{tid}", "map",
                                            r.model_id, r.tier, r.cost, r.billed))

            joined = "\n\n".join(f"### {tmap[i]['title']}\n{outputs[i]}" for i in outputs)
            sr = self.run_task(
                f"{sot_block}"
                f"Integrate these task outputs into one coherent module for story "
                f"'{story.get('title', '')}', staying faithful to the SOURCE OF TRUTH "
                f"above:\n\n{joined}",
                STORY_REDUCE_TIER, REDUCE_CAPS, agent_id,
            )
            steps.append(StepResult(f"story_reduce:{story['id']}", "story_reduce",
                                    sr.model_id, sr.tier, sr.cost, sr.billed))
            story_modules.append((story.get("title", ""), sr.text))

        joined = "\n\n".join(f"## {title}\n{text}" for title, text in story_modules)
        er = self.run_task(
            f"{sot_block}"
            f"Integrate these story modules into the final deliverable for the epic '{epic}'. "
            f"Validate architectural consistency across modules AND that the result fully "
            f"satisfies the SOURCE OF TRUTH above.\n\n{joined}",
            EPIC_REDUCE_TIER, REDUCE_CAPS, agent_id,
        )
        steps.append(StepResult("epic_reduce", "epic_reduce", er.model_id, er.tier,
                                er.cost, er.billed))
        return MapReduceResult(epic=epic, final_output=er.text, steps=steps)


def build_runner(completer, budget: BudgetManager, registry: list[ModelSpec] | None = None):
    """Production run_task: route to cheapest model at/above min_tier, enforce budget, record."""
    reg = registry or REGISTRY

    def run_task(prompt: str, min_tier: str, caps, agent_id: str) -> RunResult:
        tc = TaskClass(task_type="aggregate", min_tier=min_tier, required_caps=frozenset(caps),
                       est_tokens_in=max(1, len(prompt) // 4), est_tokens_out=1500)
        decision = select_model(tc, reg, "cost")
        if not budget.can_afford(agent_id, decision.est_cost):
            raise BudgetExceeded(f"cap would be exceeded by {decision.model.id}")
        comp = completer(decision.model.id, prompt)
        usage = budget.record(agent_id, decision.model, "aggregate",
                              comp.tokens_in, comp.tokens_out)
        return RunResult(comp.text, decision.model.id, decision.model.tier,
                         usage.cost, usage.billed)

    return run_task
