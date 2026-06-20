# 🧭 intelligent-router

A **cost-optimizing intelligent router** for LLM workloads. Goal: **make a fixed credit
(e.g. $50) go as far as possible** by sending each task to the *cheapest model capable of
doing it well* — flash/mini models for READMEs and boilerplate, frontier models (Claude
Opus, GPT-5.4) only for hard reasoning, architecture, and security review.

You give it a **feature**; it decomposes into **user stories → tasks**, classifies each
task, and routes each to a model under your objective (`cost` / `quality` / `balanced`).

## How it works

```
 feature ──► decompose (1 cheap LLM call) ──► stories ──► tasks
                                                            │
                                              classify task (rule-based, free)
                                                            │  min tier + capabilities
                                                            ▼
                                              route: cheapest capable model
                                                            │
                                              ┌─────────────┴─────────────┐
                                          inference endpoint        OpenRouter
                                          (OpenAI-compatible)       (optional)
                                                            │
                                                  budget tracker ($/tokens)
```

## Why it saves money

The classifier maps each task to the **minimum tier** that does it well:

| Task | Tier | Example model picked (cost objective) |
|------|------|---------------------------------------|
| README / docs / comments | mini | gemini-3.5-flash / deepseek-v4-flash |
| classify / extract | nano–mini | deepseek-v4-flash |
| simple codegen / tests | standard | glm-4.7 / qwen3.5-plus |
| complex implementation | pro | claude-sonnet-4-6 / deepseek-v4-pro |
| architecture / security review | frontier | claude-opus-4-8 / gpt-5.4 |

You never pay frontier prices for a task a flash model handles — that's the whole game.

## Models

Catalog (all on the shared inference endpoint by default): `claude-opus-4-8`,
`claude-opus-4-6`, `gpt-5.4`, `gemini-3.1-pro-preview`, `claude-sonnet-4-6`,
`deepseek-v4-pro`, `glm-5.1`, `qwen3.7-plus`, `qwen3.5-plus`, `kimi-k2.6`, `glm-4.7`,
`gemini-3.5-flash`, `deepseek-v4-flash`.

> ⚠️ **Pricing is estimated by tier** — several models are too new for a reliable price
> list. Cost routing is only as accurate as the numbers. Drop real prices into a JSON file
> and point `ROUTER_PRICING_JSON` at it (see `.env.example`).

## Usage

```bash
pip install -r requirements.txt
cp .env.example .env        # add INFERENCE_API_KEY

# Free, no API call — see how a single task routes:
python -m router.cli route "Write a comprehensive README" 
python -m router.cli route "Design the gateway architecture" --objective cost

# List the catalog (free):
python -m router.cli models

# Decompose a feature and route every task (one cheap LLM call for the breakdown):
python -m router.cli plan "Users can sign up and log in with email"
```

## Development

```bash
pip install -r requirements-dev.txt
ruff check .
pytest          # fully mocked — runs offline and burns ZERO credit
```

CI runs ruff + pytest on Python 3.10–3.12.

## Use cases covered

**1. Intelligent model selection** — `classifier.py` + `analyze.py` analyze task type *and*
prompt attributes (estimated size → long-context need, vision hints) to pick the optimal
model; `router.py` selects the cheapest capable one.

**2. Fallback routing** — `fallback.py` builds an ordered chain (primary + resilient
backups, preferring open-weight models); `executor.py` tries each in turn, skipping any
that error — so a provider outage/degradation doesn't fail the request.

**3. Cost governance** — `governance.py` enforces **hard spend caps** (global *and*
per-agent) checked before every call, with granular usage analytics (`report()` breaks
spend down by agent, model, and task type). `executor.py` enforces caps on the live path.

```bash
# the runtime path (intelligent select -> fallback -> budget-enforced):
#   Executor(complete, BudgetManager(global_cap=50, agent_caps={"agent-x": 5}), REGISTRY).run(prompt, agent_id="agent-x")
```

## Roadmap (rest of the epic)
- **UX dashboard** — visualize spend, model mix, and per-task routing decisions.
- **Real pricing + live model verification** (some IDs 403 on the endpoint).
- **OpenRouter provider** — set `OPENROUTER_API_KEY` to route across providers.
- **Adaptive routing** — learn from observed quality/latency to tune the tier mapping.

---

*Built by the JayBot mesh. 🤖*
