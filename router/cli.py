"""Command-line entry point.

  router models                      list the catalog (free)
  router route "<task>"             show the chosen model for one task (free, no API call)
  router plan "<feature>"           decompose -> route every task (one cheap LLM call)
"""

from __future__ import annotations

import argparse

from .classifier import classify_task
from .decompose import plan_feature
from .registry import REGISTRY
from .router import select_model


def cmd_models(_args) -> int:
    for m in sorted(REGISTRY, key=lambda s: (s.rank, s.id)):
        caps = ",".join(sorted(m.capabilities)) or "-"
        print(f"{m.tier:9} {m.id:26} in=${m.price_in:<5} out=${m.price_out:<6} [{caps}]")
    return 0


def cmd_route(args) -> int:
    tc = classify_task(args.task, args.type)
    decision = select_model(tc, REGISTRY, args.objective)
    print(f"task type : {tc.task_type}")
    print(f"min tier  : {tc.min_tier}  caps={set(tc.required_caps) or '-'}")
    print(f"chosen    : {decision.model.id} ({decision.model.tier})")
    print(f"est cost  : ${decision.est_cost:.5f}")
    print(f"why       : {decision.rationale}")
    return 0


def _inference_llm(model_id: str):
    from .providers import InferenceProvider

    provider = InferenceProvider()

    def call(prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        return provider.complete(model_id, messages, max_tokens=2048).text

    return call


def cmd_plan(args) -> int:
    llm = _inference_llm(args.decompose_model)
    plan = plan_feature(args.feature, llm, REGISTRY, args.objective)
    print(f"FEATURE: {plan.feature}\n")
    for story in plan.stories:
        print(f"📌 {story.title}")
        for task in story.tasks:
            d = task.decision
            print(f"   - [{task.task_type}] {task.title}")
            print(f"       -> {d.model.id} (${d.est_cost:.5f})")
    print(f"\nTasks: {plan.task_count} | Estimated cost: ${plan.est_cost:.4f} "
          f"| Objective: {args.objective}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="router", description="Intelligent model router")
    parser.add_argument("--objective", default="cost", choices=["cost", "quality", "balanced"])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("models", help="list the model catalog")

    p_route = sub.add_parser("route", help="route a single task")
    p_route.add_argument("task")
    p_route.add_argument("--type", default=None, help="explicit task type (skip inference)")

    p_plan = sub.add_parser("plan", help="decompose a feature and route every task")
    p_plan.add_argument("feature")
    p_plan.add_argument("--decompose-model", default="gemini-3.5-flash",
                        help="cheap model used for the decomposition step")

    args = parser.parse_args(argv)
    if args.command == "models":
        return cmd_models(args)
    if args.command == "route":
        return cmd_route(args)
    if args.command == "plan":
        return cmd_plan(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
