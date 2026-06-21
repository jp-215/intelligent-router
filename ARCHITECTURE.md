# 🧭 Architecture — DAG Map-Reduce Orchestration

The router decomposes an **Epic → Stories → Tasks** (a DAG with `depends_on` edges),
executes tasks with a tiered model catalog, and merges them hierarchically with
**Map-Reduce** — keeping cost low on the leaves and spending frontier-model budget only at
the final integration.

```
                       [ Epic: high-level feature ]
                                  ▲
                   Reduce 2 ─ epic integration ─ FRONTIER (claude-opus-4-8 / gpt-5.4)
                ┌─────────────────┴─────────────────┐
          [ Story: Backend ]                  [ Story: Frontend ]
                ▲                                    ▲
        Reduce 1 ─ story module ─ PRO        Reduce 1 ─ story module ─ PRO
          ┌─────┴─────┐                            ┌─────┴─────┐
       [Task A]    [Task B]                      [Task C]    [Task D]
       (flash)    (standard)                     (flash)    (standard)
         └ Map phase: cheapest capable model, run in dependency order ┘
```

## Phases
1. **Decompose → DAG** — Epic split into stories and tasks; each task declares
   `depends_on`. `router/core/dag.py` validates acyclicity and computes parallel **levels**.
2. **Map (execute)** — each task routed to the *cheapest capable* model
   (`router.handlers.routing.select_model`), executed in dependency order; tasks in the same level
   are independent and parallelizable.
3. **Reduce 1 (story)** — a story's task outputs are condensed on a **pro** model.
4. **Reduce 2 (epic)** — compressed story modules are integrated on a **frontier** model.
   This is where frontier models are used (and billed with markup).

## Guardrails (enforced in code)
- **State isolation** — task outputs stay within their story; the epic reducer sees only
  compressed story modules, never raw task dumps (`router/handlers/aggregation.py`).
- **Acyclic enforcement** — `dag.validate` rejects unknown deps and cycles before any call.
- **Budget before inference** — `build_runner` checks `BudgetManager.can_afford` *before*
  each call; `/build` returns **402** if a hard cap would be breached.
- **Offline tests** — the whole pipeline is unit-tested with injected fakes; no live credit.

## Modules
- `router/core/dag.py` — DAG validation, topological order, parallel levels.
- `router/handlers/aggregation.py` — `Aggregator` (map-reduce) + `build_runner` (production run_task).
- `router/api.py` — `POST /build` runs the pipeline over a supplied DAG.

## API
`POST /build`
```json
{
  "epic": "User signup",
  "stories": [
    {"id": "s1", "title": "Backend", "tasks": [
      {"id": "t1", "title": "Write README", "task_type": "docs", "depends_on": []},
      {"id": "t2", "title": "Implement endpoint", "task_type": "codegen_complex", "depends_on": ["t1"]}
    ]}
  ]
}
```
Returns the final integrated output, per-step model/tier, `tier_usage`, and total
cost/billed (with the frontier epic-reduce included).

## Providers / scaling
Models carry a `provider` field; `router/services/providers.py` ships an OpenRouter provider that
activates with `OPENROUTER_API_KEY`. Add providers by registering models with the new
`provider` and supplying a client — routing, fallback, budgeting, and map-reduce all apply
unchanged.
