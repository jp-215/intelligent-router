"""API request schemas (DTOs).

Pydantic models that define and validate the JSON bodies accepted by the HTTP routes.
Kept separate from the routes so the public contract lives in one readable place.
Responses are returned as plain JSON dicts assembled in ``routes`` from domain objects.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

_OBJECTIVE = Field(default="cost", pattern="^(cost|quality|balanced)$")


class RouteRequest(BaseModel):
    """Route a single task to a model (no model call is made)."""

    prompt: str
    task_type: str | None = None
    objective: str = _OBJECTIVE


class PlanRequest(BaseModel):
    """Decompose a feature into stories/tasks and route each one."""

    feature: str
    objective: str = _OBJECTIVE
    decompose_model: str = "gemini-3.5-flash"


class CompleteRequest(BaseModel):
    """Full path: classify -> fallback chain -> budget-enforced -> run."""

    prompt: str
    agent_id: str = "default"
    task_type: str | None = None
    objective: str = _OBJECTIVE


class BuildRequest(BaseModel):
    """Map-reduce a task DAG (map on cheap tiers, reduce on pro/frontier)."""

    epic: str
    stories: list[dict]  # [{id,title,tasks:[{id,title,task_type,depends_on}]}]
    # Optional raw original user dialog; falls back to ``epic``. Re-injected into every
    # reduce step as the immutable Source of Truth (anti-semantic-drift).
    source_of_truth: str | None = None
