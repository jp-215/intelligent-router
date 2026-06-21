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

### Multi-provider (OpenRouter)

Set `OPENROUTER_API_KEY` and the router also loads an **OpenRouter** model catalog
(`openrouter-models.json`, real slugs + live prices across every tier) as additional,
routable models with `provider: "openrouter"`. Effects:
- **Cross-provider cost optimization** — the cheapest capable model wins regardless of
  provider (e.g. an OpenRouter nano at $0.02/$0.03 can beat the inference-endpoint nano).
- **Cross-provider failover** — fallback chains span providers, so an inference-endpoint
  outage falls through to an equivalent OpenRouter model.
Without the key, no OpenRouter models are loaded (the router never routes to a provider it
can't reach). Customize the catalog via `ROUTER_OPENROUTER_MODELS`.

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

## Project structure

The package is organized in layers, each depending only on the ones below it
(`utils ← core ← services ← handlers ← routes`) — so the dependency graph is acyclic and
every file has an obvious home:

```
router/
├── config.py              # ⚙️  all env vars read here → typed Settings
├── schemas.py             # 📦  API request DTOs (Pydantic)
├── api.py                 # 🚪  create_app(): mounts routers + optional MCP  (uvicorn router.api:app)
├── routes/                # 🌐  thin HTTP layer (one APIRouter per concern)
│   ├── dependencies.py    #     shared Depends(): settings, budget, client id, completer
│   ├── meta.py            #     GET /health, GET /models
│   ├── routing.py         #     POST /route, /plan, /complete, /build
│   └── report.py          #     GET /report
├── handlers/              # 🧠  orchestration the routes call (the business layer)
│   ├── routing.py         #     select_model / candidates  (model selection)
│   ├── fallback.py        #     resilient fallback chains
│   ├── planning.py        #     feature → stories → tasks (decompose + route)
│   ├── execution.py       #     Executor: classify → fallback → budget-enforced run
│   ├── aggregation.py     #     Aggregator: hierarchical map-reduce over a DAG
│   └── reporting.py       #     dashboard payload from the budget ledger
├── services/              # 🔌  stateful / external infrastructure
│   ├── registry.py        #     the model catalog (+ pricing / OpenRouter overrides)
│   ├── providers.py       #     Inference + OpenRouter HTTP clients
│   ├── governance.py      #     BudgetManager: hard caps + usage analytics
│   ├── billing.py         #     BillingPolicy: markup → billable price
│   └── budget.py          #     BudgetTracker
├── core/                  # 🧱  pure domain types & logic (no IO)
│   ├── models.py          #     ModelSpec, tiers, capability flags, cost model
│   ├── classifier.py      #     task → minimum tier + capabilities (rule-based)
│   ├── analyze.py         #     prompt-attribute refinement (size, vision hints)
│   └── dag.py             #     DAG validation, topological order, parallel levels
├── utils/                 # 🔧  shared dependency-free helpers
│   └── tokens.py          #     estimate_tokens
└── cli.py                 # 💻  `python -m router.cli` (models / route / plan)
```

`tests/` covers each module; everything is fully mocked (providers and LLM calls are
injected fakes), so the suite runs offline and burns zero credit.

## Use cases covered

**1. Intelligent model selection** — `core/classifier.py` + `core/analyze.py` analyze task
type *and* prompt attributes (estimated size → long-context need, vision hints) to pick the
optimal model; `handlers/routing.py` selects the cheapest capable one.

**2. Fallback routing** — `handlers/fallback.py` builds an ordered chain (primary + resilient
backups, preferring open-weight models); `handlers/execution.py` tries each in turn, skipping
any that error — so a provider outage/degradation doesn't fail the request.

**3. Cost governance** — `services/governance.py` enforces **hard spend caps** (global *and*
per-agent) checked before every call, with granular usage analytics (`report()` breaks
spend down by agent, model, and task type). `handlers/execution.py` enforces caps on the
live path.

```bash
# the runtime path (intelligent select -> fallback -> budget-enforced):
#   Executor(complete, BudgetManager(global_cap=50, agent_caps={"agent-x": 5}), REGISTRY).run(prompt, agent_id="agent-x")
```

## Map-Reduce orchestration (build a whole app)

For a full **epic** (not a single task), the router runs a **hierarchical Map-Reduce over a
task DAG** instead of one flat model call — this is how you build an entire application while
spending frontier dollars only where they matter.

```
                    [ Epic: high-level feature ]
                               ▲
                 Reduce 2 (epic) ── FRONTIER model: claude-opus-4-8 / gpt-5.4
              ┌────────────────┴────────────────┐
        [ Story: data/domain ]          [ Story: interface/api ]
                 ▲                                 ▲
       Reduce 1 (story) ── PRO model      Reduce 1 (story) ── PRO model
          ┌──────┴──────┐                    ┌──────┴──────┐
       [Task A]      [Task B]             [Task C]      [Task D]
       (flash)       (nano)              (standard)     (flash)
       └── map phase: each task → cheapest capable tier, run in parallel by DAG level ──┘
```

- **DAG decomposition** (`core/dag.py`) — tasks declare `depends_on`; the graph is validated
  acyclic (Kahn's algorithm) and split into **parallel levels** so independent tasks in the
  same level run concurrently in the map phase.
- **Asymmetric map phase** — every leaf task is classified and routed to the *cheapest
  capable* tier (flash/nano/standard). Most of the work happens here, cheaply.
- **Hierarchical reduce** (`handlers/aggregation.py`) — story-level reductions condense each story's
  task outputs on a **pro** model; the epic-level reduce integrates the compressed story
  modules on a **frontier** model for final architectural validation.
- **State isolation** — each story's raw task outputs stay inside that story; the epic
  reducer only ever sees the compressed story modules, never raw task dumps. This keeps the
  context window small (cheaper) and the budget bounded — caps are checked *before* every
  inference call, so a breach aborts with **402** rather than spending.
- **Immutable Source of Truth (anti-semantic-drift)** — the original user request is the
  single Source of Truth for the whole run. `handlers/planning.py` embeds the raw prompt in a
  top-level immutable field and every Story/Task carries a reference back to it;
  `handlers/aggregation.py` re-injects that SoT into **every reduce prompt** (story *and* epic) so multi-level
  reduction can't quietly drift from what was actually asked for. It's deliberately *not*
  injected into the cheap map calls — those stay lean to keep token cost down. Pass it via
  `source_of_truth` on `/build` (falls back to `epic` if omitted).

Exposed as `POST /build` (and the `build` MCP tool).

## API / MCP service

The same engine is exposed over HTTP via FastAPI (`router/api.py`):

| Method | Path | Does | Cost |
|--------|------|------|------|
| GET | `/health` | liveness | free |
| GET | `/models` | list the catalog | free |
| POST | `/route` | route ONE task → chosen model | free (no model call) |
| POST | `/plan` | decompose a feature → route every task | 1 cheap call |
| POST | `/complete` | select → fallback → budget-enforced → run | model call |
| POST | `/build` | epic → DAG → map-reduce (frontier only on epic reduce) | many calls |
| GET | `/report` | usage + cost analytics | free |

```bash
pip install -r requirements.txt
export INFERENCE_API_KEY=...   ROUTER_BUDGET_CAP=50
uvicorn router.api:app --reload --port 8080      # or: docker build -t router . && docker run -p 8080:8080 router

curl localhost:8080/route -H 'content-type: application/json' \
  -d '{"prompt":"Write a README","objective":"cost"}'
curl localhost:8080/complete -H 'content-type: application/json' \
  -d '{"prompt":"Summarize this","agent_id":"agent-x"}'
```

`/complete` enforces budget: returns **402** when a hard cap would be breached, **502** if
all fallback models fail.

### Call it as an MCP
`pip install fastapi-mcp` and start with `ENABLE_MCP=1` — every endpoint is auto-exposed as
an MCP tool, so it can be wired into an MCP client (e.g. OpenClaw) and called like any tool.

## UX dashboard

A static dashboard (`web/index.html`) visualizes the governance analytics: budget gauge
(spent / remaining / % of cap), and spend broken down by **model**, **task type**, and
**agent**. It reads `web/report.json`, produced from a `BudgetManager`:

```bash
python scripts/gen_demo_data.py          # simulate runs -> web/report.json (no credit)
cd web && python -m http.server 8000     # open http://localhost:8000
```

In production, persist real usage and call `router.handlers.reporting.write_payload(budget, "web/report.json")`.

## Roadmap (rest of the epic)
- **Real pricing + live model verification** (some IDs 403 on the endpoint).
- ✅ **OpenRouter provider** — set `OPENROUTER_API_KEY` to route across providers.
- ✅ **Map-Reduce DAG orchestration** — `POST /build` runs epic → stories → tasks.
- **Adaptive routing** — learn from observed quality/latency to tune the tier mapping.
- **Host the dashboard** (GitHub Pages — needs the repo public).

---

*Built by the JayBot mesh. 🤖*
