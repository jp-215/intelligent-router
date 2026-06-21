"""Shared FastAPI dependencies: settings, the budget singleton, client id, completer.

These are the seams the routes wire through ``Depends(...)`` — and the seams tests
override (e.g. ``app.dependency_overrides[get_completer]``) to run with a fake provider
and spend no credit.
"""

from __future__ import annotations

from fastapi import Header

from ..config import get_settings
from ..services.governance import BudgetManager

# Settings and the budget ledger are process-wide singletons, built once at import.
settings = get_settings()

# Monetization: clients are billed cost + markup. The router already routes to the
# cheapest capable model, so the operator's margin is maximized.
_budget = BudgetManager(global_cap=settings.budget_cap, billing=settings.billing)


def get_budget() -> BudgetManager:
    return _budget


def client_id(x_api_key: str | None = Header(default=None)) -> str | None:
    """Identify the calling client/agent for per-client metering & billing.

    Maps an X-API-Key header to a client id via ROUTER_CLIENT_KEYS; falls back to the
    key prefix so unknown-but-present keys are still metered separately.
    """
    if not x_api_key:
        return None
    return settings.client_keys.get(x_api_key, x_api_key[:12])


def get_completer():
    """Provider-aware completer: dispatch each model to its provider (inference vs
    OpenRouter) based on the registry. Overridden in tests."""
    from ..services.providers import InferenceProvider, OpenRouterProvider
    from ..services.registry import by_id

    inference = InferenceProvider()
    openrouter = OpenRouterProvider()

    def complete(model_id: str, prompt: str):
        msgs = [{"role": "user", "content": prompt}]
        spec = by_id(model_id)
        provider = openrouter if (spec and spec.provider == "openrouter") else inference
        return provider.complete(model_id, msgs, max_tokens=settings.max_tokens)

    return complete
