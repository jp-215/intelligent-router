"""Feature -> user stories -> tasks -> model assignment.

The decomposition itself is an LLM call (use a CHEAP model for it). The LLM is passed
in as a callable `llm(prompt) -> str`, so tests run with a fake and no credit is spent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .classifier import classify_task
from .models import ModelSpec
from .router import RoutingDecision, select_model

TASK_TYPES = (
    "classify, extract, summarize, docs, boilerplate, commit_message, codegen_simple, "
    "test_gen, codegen_complex, review, security_review, architecture, reasoning_hard, vision"
)

DECOMPOSE_PROMPT = (
    "You are a senior engineering planner. Break the FEATURE into user stories, and each "
    "story into concrete technical tasks. For each task pick a \"type\" from this set: "
    f"{TASK_TYPES}.\n"
    "Respond ONLY with JSON of the form:\n"
    '{"stories":[{"title":"...","tasks":[{"title":"...","type":"..."}]}]}\n'
    "FEATURE: __FEATURE__"
)


@dataclass
class TaskPlan:
    title: str
    task_type: str
    decision: RoutingDecision


@dataclass
class StoryPlan:
    title: str
    tasks: list[TaskPlan] = field(default_factory=list)


@dataclass
class FeaturePlan:
    feature: str
    stories: list[StoryPlan] = field(default_factory=list)

    @property
    def est_cost(self) -> float:
        return sum(t.decision.est_cost for s in self.stories for t in s.tasks)

    @property
    def task_count(self) -> int:
        return sum(len(s.tasks) for s in self.stories)


def parse_decomposition(text: str) -> list[dict]:
    """Parse the LLM's JSON (tolerant of code fences) into a list of story dicts."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") : text.rfind("}") + 1]
    data = json.loads(text)
    return data.get("stories", [])


def plan_feature(feature: str, llm, registry: list[ModelSpec],
                 objective: str = "cost") -> FeaturePlan:
    """Decompose a feature and route every task to a model under `objective`."""
    raw = llm(DECOMPOSE_PROMPT.replace("__FEATURE__", feature))
    stories = parse_decomposition(raw)

    plan = FeaturePlan(feature=feature)
    for story in stories:
        sp = StoryPlan(title=story.get("title", "untitled story"))
        for task in story.get("tasks", []):
            title = task.get("title", "untitled task")
            tc = classify_task(title, task.get("type"))
            decision = select_model(tc, registry, objective)
            sp.tasks.append(TaskPlan(title=title, task_type=tc.task_type, decision=decision))
        plan.stories.append(sp)
    return plan
