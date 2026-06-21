"""Report route: usage + cost analytics from the budget ledger."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..handlers.reporting import dashboard_payload
from ..services.governance import BudgetManager
from .dependencies import get_budget

router = APIRouter()


@router.get("/report")
def report(budget: BudgetManager = Depends(get_budget)) -> dict:
    return dashboard_payload(budget)
