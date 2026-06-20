---
name: intelligent-router
description: Route each LLM task to the cheapest capable model (with fallback + hard budget caps) to stretch a fixed credit. Invoke with a task to get the optimal model; run it to get the answer.
---

# Intelligent Router

Send every task to the **cheapest model capable of doing it well** instead of defaulting to
a frontier model. A README does not need Claude Opus — a flash model handles it for a
fraction of the cost. Use this to make a fixed credit (e.g. $50) go as far as possible,
with automatic fallback on outage and hard spend caps.

## When to use
- A task or feature needs an LLM and you want to minimize cost without sacrificing quality.
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

## Guardrails
- Never exceed the configured spend cap — refuse rather than overspend.
- Default objective is `cost` (maximize the credit).
- API keys come from environment variables (`INFERENCE_API_KEY`, optional
  `OPENROUTER_API_KEY`) — never hardcoded or pasted into chat.

## Reference
Full implementation (classifier, cost router, fallback, budget governance, FastAPI, MCP,
dashboard, tests): https://github.com/jp-215/intelligent-router
