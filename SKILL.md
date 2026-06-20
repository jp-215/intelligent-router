---
name: intelligent-router
description: Route each LLM task to the cheapest capable model (with fallback + hard budget caps) to stretch a fixed credit. Invoke with a task to get the optimal model; run it to get the answer.
---

# Intelligent Router

Send every task to the **cheapest model capable of doing it well** instead of defaulting to
a frontier model. A README does not need Claude Opus — a flash model handles it for a
fraction of the cost. Use this to make a fixed credit (e.g. $50) go as far as possible,
with automatic fallback on outage and hard spend caps.

## The core value: build an ENTIRE application for a fraction of the cost

Don't burn a frontier model on a whole build. Decompose the app and route each piece to the
**cheapest model that can do that piece** — flash/mini for boilerplate, READMEs, configs and
simple components; frontier only for architecture and security. The app gets built; the
token bill collapses.

**Build-an-app workflow:**
1. `mcp__intelligent-router__plan` with `{ "feature": "<the whole app/feature>" }` →
   decomposes into user stories → tasks, each tagged with a type and pre-assigned the
   cheapest capable model, with a total cost estimate.
2. For each task, `mcp__intelligent-router__complete` with
   `{ "prompt": "<the task>", "task_type": "<type>", "agent_id": "<app-name>" }` →
   generates that artifact on the cheapest capable model (with fallback + budget enforcement).
3. Assemble the returned artifacts into files and commit/push to GitHub.
4. `mcp__intelligent-router__report` → show total spend vs. budget per model/task.

The result: README & boilerplate cost ~$0.001 each on a flash model, architecture decisions
use a frontier model only where it matters, and the whole app ships well under budget.

## When to use
- **Building a whole application/feature cheaply** — the primary use case (workflow above).
- A single task needs an LLM and you want the cheapest capable model.
- You are routing many different kinds of tasks (docs, codegen, review, architecture).
- You need fallback when a provider degrades, or hard per-agent / global budget limits.

## How to invoke

This skill is backed by a live MCP server (`intelligent-router`, 6 tools) over a local
FastAPI service. Default to the **`route`** tool; escalate to `complete`/`plan` on request.

| Intent | Tool | Cost |
|--------|------|------|
| "route X" / pick the model for a task | `mcp__intelligent-router__route` | free |
| "run X" / get the answer | `mcp__intelligent-router__complete` | real model call |
| "break down feature X" | `mcp__intelligent-router__plan` | one cheap call |
| "what models?" | `mcp__intelligent-router__models` | free |
| "usage" / "spend" / "budget" | `mcp__intelligent-router__report` | free |

Default request body: `{ "prompt": <user text>, "objective": "cost" }`. Use
`objective: "quality"` or `"balanced"` only when the user asks. For `complete`, pass
`agent_id` so spend is attributed per agent.

If the MCP tool is unavailable, fall back to the repo CLI:
`python -m router.cli route "<task>"`.

## How routing decides (the engine)
1. **Classify** the task to the minimum capability tier it needs:

   | Task | Min tier |
   |------|----------|
   | classify / extract | nano |
   | summarize / README / docs / comments / commit msg | mini |
   | simple codegen / unit tests | standard |
   | complex implementation / code review | pro |
   | architecture / design / security review / hard reasoning | frontier |
   | image/screenshot present | + vision capability |
   | input > ~8k tokens | + long-context capability |

2. **Pick the cheapest model** at or above that tier with the required capabilities.
3. **Fallback chain**: primary + backups, preferring open-weight models
   (deepseek / qwen / glm / kimi); try each in order on error.
4. **Budget**: enforce global + per-agent hard caps *before* each call; record real token
   usage after, for analytics.

## Model catalog (tiers)
- **frontier**: claude-opus-4-8, claude-opus-4-6, gpt-5.4
- **pro**: gemini-3.1-pro-preview, claude-sonnet-4-6, deepseek-v4-pro*, glm-5.1*
- **standard**: qwen3.7-plus*, qwen3.5-plus*, kimi-k2.6*, glm-4.7*
- **mini**: gemini-3.5-flash, deepseek-v4-flash*

(* = open-weight, preferred for fallback.) Pricing is estimated by tier — supply real
per-model prices for accurate cost optimization.

## Monetization (any agent can resell this)

The router meters every call and bills clients a **markup over the routed (cheap) cost** —
the operator keeps the spread. Because routing already picks the cheapest capable model, the
margin is maximized.

- Set the markup: `ROUTER_MARKUP_PCT` (e.g. `0.20` = +20%), optional `ROUTER_FLAT_FEE`,
  `ROUTER_MIN_CHARGE`.
- Identify/bill each client: send `X-API-Key`; map keys→clients via `ROUTER_CLIENT_KEYS`.
- `mcp__intelligent-router__complete` returns both `cost` (upstream) and `billed` (client charge).
- `mcp__intelligent-router__report` returns `revenue`, `margin`, and `revenue_by_agent`.

Example: a client builds a whole app through the router; the parts run on flash/standard
models costing the operator ~$0.05, the client is billed ~$0.06 (+20%), and the router took
care of routing, fallback, and budget — that $0.01 spread per build is the operator's margin.

## Guardrails
- Never exceed the configured spend cap — refuse rather than overspend.
- Default objective is `cost` (maximize the credit).
- API keys come from environment variables (`INFERENCE_API_KEY`, optional
  `OPENROUTER_API_KEY`) — never hardcoded or pasted into chat.

## Reference
Full implementation (classifier, cost router, fallback, budget governance, FastAPI, MCP,
dashboard, tests): https://github.com/jp-215/intelligent-router
