"""The catalog of routable models.

⚠️  PRICING IS ESTIMATED by tier — several of these models are newer than any
reliable price list we have. Replace `TIER_PRICING` (or override per-model) with real
$/1M-token numbers before trusting cost optimization. Override at runtime by pointing
ROUTER_PRICING_JSON at a file of {"model_id": {"price_in": x, "price_out": y}}.
"""

from __future__ import annotations

import json
import os

from ..core.models import (
    CAP_CODE,
    CAP_LONG_CONTEXT,
    CAP_REASONING,
    CAP_VISION,
    ModelSpec,
)

_CAP_BY_NAME = {
    "reasoning": CAP_REASONING,
    "code": CAP_CODE,
    "long_context": CAP_LONG_CONTEXT,
    "vision": CAP_VISION,
}

# USD per 1M tokens, (input, output). ESTIMATES — replace with real numbers.
TIER_PRICING = {
    "nano": (0.05, 0.20),
    "mini": (0.15, 0.60),
    "standard": (0.50, 1.50),
    "pro": (1.50, 6.00),
    "frontier": (5.00, 15.00),
}

_REASON_CODE = frozenset({CAP_REASONING, CAP_CODE})
_REASON_CODE_LONG = frozenset({CAP_REASONING, CAP_CODE, CAP_LONG_CONTEXT})
_FULL = frozenset({CAP_REASONING, CAP_CODE, CAP_LONG_CONTEXT, CAP_VISION})

# (id, tier, capabilities, open_source). All default to the shared inference endpoint.
_CATALOG = [
    ("claude-opus-4-8", "frontier", _FULL, False),
    ("claude-opus-4-6", "frontier", _FULL, False),
    ("gpt-5.4", "frontier", _FULL, False),
    ("gemini-3.1-pro-preview", "pro", _FULL, False),
    ("claude-sonnet-4-6", "pro", _FULL, False),
    ("deepseek-v4-pro", "pro", _REASON_CODE_LONG, True),
    ("glm-5.1", "pro", _REASON_CODE_LONG, True),
    ("qwen3.7-plus", "standard", _REASON_CODE_LONG, True),
    ("qwen3.5-plus", "standard", _REASON_CODE, True),
    ("kimi-k2.6", "standard", _REASON_CODE_LONG, True),
    ("glm-4.7", "standard", _REASON_CODE, True),
    ("gemini-3.5-flash", "mini", _FULL, False),
    ("deepseek-v4-flash", "mini", _REASON_CODE, True),
]


def _apply_overrides(specs: list[ModelSpec]) -> list[ModelSpec]:
    path = os.getenv("ROUTER_PRICING_JSON")
    if not path or not os.path.exists(path):
        return specs
    with open(path, encoding="utf-8") as fh:
        overrides = json.load(fh)
    out = []
    for s in specs:
        o = overrides.get(s.id, {})
        out.append(
            ModelSpec(
                id=s.id, provider=s.provider, tier=s.tier,
                price_in=float(o.get("price_in", s.price_in)),
                price_out=float(o.get("price_out", s.price_out)),
                capabilities=s.capabilities,
                open_source=s.open_source,
            )
        )
    return out


def _load_openrouter() -> list[ModelSpec]:
    """Load OpenRouter-backed models from JSON — only when OPENROUTER_API_KEY is set, so
    the router never routes to a provider it can't reach. Path: ROUTER_OPENROUTER_MODELS
    or ./openrouter-models.json at the repo root."""
    if not os.getenv("OPENROUTER_API_KEY"):
        return []
    # repo root = router/services/registry.py -> up three levels
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    default = os.path.join(repo_root, "openrouter-models.json")
    path = os.getenv("ROUTER_OPENROUTER_MODELS", default)
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        entries = json.load(fh)
    specs = []
    for e in entries:
        caps = frozenset(_CAP_BY_NAME[c] for c in e.get("caps", []) if c in _CAP_BY_NAME)
        specs.append(
            ModelSpec(id=e["id"], provider="openrouter", tier=e["tier"],
                      price_in=float(e["price_in"]), price_out=float(e["price_out"]),
                      capabilities=caps, open_source=bool(e.get("open_source", False)))
        )
    return specs


def build_registry() -> list[ModelSpec]:
    specs = []
    for model_id, tier, caps, open_source in _CATALOG:
        price_in, price_out = TIER_PRICING[tier]
        specs.append(
            ModelSpec(id=model_id, provider="inference", tier=tier,
                      price_in=price_in, price_out=price_out, capabilities=caps,
                      open_source=open_source)
        )
    specs.extend(_load_openrouter())
    return _apply_overrides(specs)


REGISTRY: list[ModelSpec] = build_registry()


def by_id(model_id: str, registry: list[ModelSpec] | None = None) -> ModelSpec | None:
    for s in registry or REGISTRY:
        if s.id == model_id:
            return s
    return None
