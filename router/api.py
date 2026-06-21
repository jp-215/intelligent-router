"""FastAPI surface for the intelligent router.

Same engine, exposed over HTTP so it can be called as a service — or mounted as an MCP
server (set ENABLE_MCP=1 with `fastapi-mcp` installed). Endpoints:

  GET  /health
  GET  /models                 list the catalog
  POST /route                  route ONE task (free, no model call)
  POST /plan                   decompose a feature -> route every task (one cheap call)
  POST /complete               full path: select -> fallback -> budget-enforced -> run
  GET  /report                 usage + cost analytics
"""

from __future__ import annotations

import os

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .aggregator import Aggregator, build_runner
from .analyze import analyze_prompt
from .billing import BillingPolicy
from .classifier import classify_task
from .dashboard import dashboard_payload
from .decompose import plan_feature
from .executor import Executor
from .governance import BudgetExceeded, BudgetManager
from .registry import REGISTRY
from .router import select_model

app = FastAPI(title="Intelligent Router API", version="0.1.0")

# Monetization: operator sets a markup; clients are billed cost + markup. The router
# already routes to the cheapest capable model, so the margin is maximized.
_budget = BudgetManager(
    global_cap=float(os.getenv("ROUTER_BUDGET_CAP", "50")),
    billing=BillingPolicy.from_env(),
)


def client_id(x_api_key: str | None = Header(default=None)) -> str | None:
    """Identify the calling client/agent for per-client metering & billing.

    Maps an X-API-Key header to a client id via ROUTER_CLIENT_KEYS ("key:client,..."),
    enabling any agent operator to meter and bill each consumer separately.
    """
    if not x_api_key:
        return None
    mapping = {}
    for pair in os.getenv("ROUTER_CLIENT_KEYS", "").split(","):
        if ":" in pair:
            k, cid = pair.split(":", 1)
            mapping[k.strip()] = cid.strip()
    return mapping.get(x_api_key, x_api_key[:12])  # fall back to key prefix as the id


def get_budget() -> BudgetManager:
    return _budget


def get_completer():
    """Default completer hits the real inference provider. Overridden in tests."""
    from .providers import InferenceProvider

    provider = InferenceProvider()

    def complete(model_id: str, prompt: str):
        mt = int(os.getenv("ROUTER_MAX_TOKENS", "8000"))
        msgs = [{"role": "user", "content": prompt}]
        return provider.complete(model_id, msgs, max_tokens=mt)

    return complete


# --- request models ---
class RouteRequest(BaseModel):
    prompt: str
    task_type: str | None = None
    objective: str = Field(default="cost", pattern="^(cost|quality|balanced)$")


class PlanRequest(BaseModel):
    feature: str
    objective: str = Field(default="cost", pattern="^(cost|quality|balanced)$")
    decompose_model: str = "gemini-3.5-flash"


class CompleteRequest(BaseModel):
    prompt: str
    agent_id: str = "default"
    task_type: str | None = None
    objective: str = Field(default="cost", pattern="^(cost|quality|balanced)$")


# --- endpoints ---
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "intelligent-router"}


@app.get("/models")
def models() -> list[dict]:
    return [
        {
            "id": m.id, "tier": m.tier, "provider": m.provider,
            "price_in": m.price_in, "price_out": m.price_out,
            "open_source": m.open_source, "capabilities": sorted(m.capabilities),
        }
        for m in sorted(REGISTRY, key=lambda s: (s.rank, s.id))
    ]


@app.post("/route")
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


@app.post("/plan")
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


@app.post("/complete")
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


class BuildRequest(BaseModel):
    epic: str
    stories: list[dict]  # [{id,title,tasks:[{id,title,task_type,depends_on}]}]


@app.post("/build")
def build(req: BuildRequest, completer=Depends(get_completer),
          budget: BudgetManager = Depends(get_budget),
          client: str | None = Depends(client_id)) -> dict:
    """Map-Reduce a task DAG: map tasks on cheap tiers, story-reduce on pro, epic-reduce
    on a frontier model."""
    agent = client or "aggregator"
    aggr = Aggregator(build_runner(completer, budget))
    try:
        result = aggr.run({"epic": req.epic, "stories": req.stories}, agent_id=agent)
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


@app.get("/report")
def report(budget: BudgetManager = Depends(get_budget)) -> dict:
    return dashboard_payload(budget)


# Optional: expose every endpoint as MCP tools (pip install fastapi-mcp; ENABLE_MCP=1).
if os.getenv("ENABLE_MCP", "0") == "1":  # pragma: no cover
    try:
        from fastapi_mcp import FastApiMCP

        FastApiMCP(app).mount()
    except ImportError:
        pass
