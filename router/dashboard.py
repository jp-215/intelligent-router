"""Build the data payload the web dashboard renders (from a BudgetManager)."""

from __future__ import annotations

import json

from .governance import BudgetManager


def dashboard_payload(budget: BudgetManager) -> dict:
    """Web-friendly snapshot of spend + analytics."""
    rep = budget.report()
    cap = budget.global_cap
    rep["global_cap"] = round(cap, 6)
    rep["pct_used"] = round(100 * budget.spent / cap, 2) if cap else 0.0
    return rep


def write_payload(budget: BudgetManager, path: str) -> dict:
    payload = dashboard_payload(budget)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return payload
