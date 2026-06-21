"""Centralized configuration — the single place env vars are read.

Every tunable is documented here so an operator can see the whole surface at a glance,
and the rest of the codebase depends on a typed ``Settings`` object instead of scattered
``os.getenv`` calls.

Environment variables
---------------------
Routing / budget
  ROUTER_BUDGET_CAP      Hard global spend cap in USD (default 50).
  ROUTER_MAX_TOKENS      max_tokens sent to providers on a completion (default 8000).

Monetization (see ``services.billing.BillingPolicy``)
  ROUTER_MARKUP_PCT      Fraction added over upstream cost, e.g. 0.20 = +20% (default 0).
  ROUTER_FLAT_FEE        Flat fee added per call, USD (default 0).
  ROUTER_MIN_CHARGE      Minimum charge per call, USD (default 0).

Per-client metering
  ROUTER_CLIENT_KEYS     "key:client,key2:client2" — maps X-API-Key headers to client ids.

Providers (read by ``services.providers`` / ``services.registry``)
  INFERENCE_API_KEY      Auth for the shared inference endpoint.
  INFERENCE_BASE_URL     Override the inference base URL.
  OPENROUTER_API_KEY     Enables OpenRouter-backed models when set.
  ROUTER_OPENROUTER_MODELS  Path to the OpenRouter model catalog JSON.
  ROUTER_PRICING_JSON    Path to per-model price overrides.

Serving
  ENABLE_MCP             "1" mounts the FastAPI surface as MCP tools (needs fastapi-mcp).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .services.billing import BillingPolicy


def _parse_client_keys(raw: str) -> dict[str, str]:
    """Parse "key:client,key2:client2" into {key: client_id}."""
    mapping: dict[str, str] = {}
    for pair in raw.split(","):
        if ":" in pair:
            key, client = pair.split(":", 1)
            mapping[key.strip()] = client.strip()
    return mapping


@dataclass(frozen=True)
class Settings:
    """Typed application configuration, assembled from the environment."""

    budget_cap: float = 50.0
    max_tokens: int = 8000
    client_keys: dict[str, str] = field(default_factory=dict)
    enable_mcp: bool = False
    billing: BillingPolicy = field(default_factory=BillingPolicy)

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            budget_cap=float(os.getenv("ROUTER_BUDGET_CAP", "50")),
            max_tokens=int(os.getenv("ROUTER_MAX_TOKENS", "8000")),
            client_keys=_parse_client_keys(os.getenv("ROUTER_CLIENT_KEYS", "")),
            enable_mcp=os.getenv("ENABLE_MCP", "0") == "1",
            billing=BillingPolicy.from_env(),
        )


def get_settings() -> Settings:
    """Build settings from the current environment (call at app startup)."""
    return Settings.from_env()
