"""Routing routes: route one task, plan a feature, complete a task, build a DAG.

Each handler is intentionally thin — it validates input (via the ``schemas`` models),
delegates to the ``handlers`` layer, and shapes a JSON response. Budget breaches surface
as HTTP 402; provider failures as 502; malformed DAGs as 400.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..core.analyze import analyze_prompt
from ..core.classifier import classify_task
from ..handlers.aggregation import Aggregator, build_runner
from ..handlers.execution import Executor
from ..handlers.planning import plan_feature
from ..handlers.routing import select_model
from ..schemas import BuildRequest, CompleteRequest, PlanRequest, RouteRequest
from ..services.governance import BudgetExceeded, BudgetManager
from ..services.registry import REGISTRY
from .dependencies import client_id, get_budget, get_completer

router = APIRouter()


@router.post("/route")
def route(req: RouteRequest) -> dict:
    task = analyze_prompt(req.prompt, classify_task(req.prompt, req.task_type))
    decision = select_model(task, REGISTRY, req.objective)
    return {
        "task_type": task.task_type,
        "min_tier": task.min_tier,
        "required_caps": sorted(task.required_caps),
        "model": decision.model.id,
        "tier": decision.model.tier,
        "est_cost": round(decision.est_cost, 6),
        "rationale": decision.rationale,
    }


@router.post("/plan")
def plan(req: PlanRequest, completer=Depends(get_completer)) -> dict:
    def llm(prompt: str) -> str:
        return completer(req.decompose_model, prompt).text

    fp = plan_feature(req.feature, llm, REGISTRY, req.objective)
    return {
        "feature": fp.feature,
        "task_count": fp.task_count,
        "est_cost": round(fp.est_cost, 6),
        "stories": [
            {
                "title": s.title,
                "tasks": [
                    {"title": t.title, "task_type": t.task_type,
                     "model": t.decision.model.id, "est_cost": round(t.decision.est_cost, 6)}
                    for t in s.tasks
                ],
            }
            for s in fp.stories
        ],
    }


@router.post("/complete")
def complete(req: CompleteRequest, completer=Depends(get_completer),
             budget: BudgetManager = Depends(get_budget),
             client: str | None = Depends(client_id)) -> dict:
    ex = Executor(completer, budget, REGISTRY, objective=req.objective)
    agent = client or req.agent_id  # X-API-Key client wins, for per-client billing
    try:
        result = ex.run(req.prompt, agent_id=agent, task_type=req.task_type)
    except BudgetExceeded as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "model": result.model_id,
        "text": result.text,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "cost": round(result.cost, 6),       # what the model cost (upstream)
        "billed": round(result.billed, 6),   # what the client is charged
        "client": agent,
        "attempts": result.attempts,
    }


@router.post("/build")
def build(req: BuildRequest, completer=Depends(get_completer),
          budget: BudgetManager = Depends(get_budget),
          client: str | None = Depends(client_id)) -> dict:
    """Map-Reduce a task DAG: map tasks on cheap tiers, story-reduce on pro, epic-reduce
    on a frontier model."""
    agent = client or "aggregator"
    aggr = Aggregator(build_runner(completer, budget))
    try:
        result = aggr.run(
            {"epic": req.epic, "stories": req.stories,
             "source_of_truth": req.source_of_truth},
            agent_id=agent,
        )
    except BudgetExceeded as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid DAG: {exc}") from exc
    return {
        "epic": result.epic,
        "final_output": result.final_output,
        "total_cost": result.total_cost,
        "total_billed": result.total_billed,
        "tier_usage": result.tier_usage,
        "used_frontier": result.used_frontier,
        "steps": [vars(s) for s in result.steps],
    }
