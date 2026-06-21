from router.aggregator import Aggregator, RunResult, build_runner
from router.governance import BudgetManager

EPIC = {
    "epic": "User signup feature",
    "stories": [
        {"id": "s1", "title": "Backend", "tasks": [
            {"id": "t1", "title": "Write README", "task_type": "docs", "depends_on": []},
            {"id": "t2", "title": "Implement endpoint", "task_type": "codegen_complex",
             "depends_on": ["t1"]},
        ]},
        {"id": "s2", "title": "Frontend", "tasks": [
            {"id": "t3", "title": "Build form", "task_type": "codegen_simple", "depends_on": []},
        ]},
    ],
}


def fake_run_task(prompt, min_tier, caps, agent_id):
    # Echo the requested tier so we can assert routing per phase.
    return RunResult(text=f"[{min_tier}] out", model_id=f"model-{min_tier}",
                     tier=min_tier, cost=0.001, billed=0.0012)


def test_mapreduce_phases_and_frontier():
    res = Aggregator(fake_run_task).run(EPIC)
    phases = [s.phase for s in res.steps]
    # 3 map tasks + 2 story reduces + 1 epic reduce
    assert phases.count("map") == 3
    assert phases.count("story_reduce") == 2
    assert phases.count("epic_reduce") == 1

    # Story reduces run on pro; the epic reduce runs on frontier (monetized).
    story = [s for s in res.steps if s.phase == "story_reduce"]
    epic = [s for s in res.steps if s.phase == "epic_reduce"][0]
    assert all(s.tier == "pro" for s in story)
    assert epic.tier == "frontier"
    assert res.used_frontier
    assert res.tier_usage.get("frontier") == 1


def test_costs_aggregate():
    res = Aggregator(fake_run_task).run(EPIC)
    assert res.total_cost == round(0.001 * 6, 6)
    assert res.total_billed == round(0.0012 * 6, 6)


def test_dependency_context_passed():
    seen = []

    def rec(prompt, min_tier, caps, agent_id):
        seen.append(prompt)
        return RunResult("X", "m", min_tier, 0.0, 0.0)

    Aggregator(rec).run({"epic": "E", "stories": [
        {"id": "s1", "title": "S", "tasks": [
            {"id": "a", "title": "first", "task_type": "docs", "depends_on": []},
            {"id": "b", "title": "second", "task_type": "docs", "depends_on": ["a"]},
        ]},
    ]})
    # The dependent task's prompt should carry context from its dependency.
    b_prompt = [p for p in seen if "second" in p][0]
    assert "from a" in b_prompt


def test_build_runner_routes_and_records_budget():
    class Comp:
        def __init__(self, t):
            self.text = t
            self.tokens_in = 100
            self.tokens_out = 200

    budget = BudgetManager(global_cap=50.0)
    runner = build_runner(lambda model_id, prompt: Comp("ok"), budget)
    res = Aggregator(runner).run(EPIC, agent_id="client-x")
    assert res.used_frontier              # epic reduce hit a frontier model
    assert budget.spent > 0               # budget recorded real usage
    assert "client-x" in budget.report()["by_agent"]
