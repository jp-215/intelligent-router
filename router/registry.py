"""The catalog of routable models.

⚠️  PRICING IS ESTIMATED by tier — several of these models are newer than any
reliable price list we have. Replace `TIER_PRICING` (or override per-model) with real
$/1M-token numbers before trusting cost optimization. Override at runtime by pointing
ROUTER_PRICING_JSON at a file of {"model_id": {"price_in": x, "price_out": y}}.
"""

from __future__ import annotations

import json
import os

from .models import (
    CAP_CODE,
    CAP_LONG_CONTEXT,
    CAP_REASONING,
    CAP_VISION,
    ModelSpec,
)

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

# (id, tier, capabilities). All default to the shared inference endpoint.
_CATALOG = [
    ("claude-opus-4-8", "frontier", _FULL),
    ("claude-opus-4-6", "frontier", _FULL),
    ("gpt-5.4", "frontier", _FULL),
    ("gemini-3.1-pro-preview", "pro", _FULL),
    ("claude-sonnet-4-6", "pro", _FULL),
    ("deepseek-v4-pro", "pro", _REASON_CODE_LONG),
    ("glm-5.1", "pro", _REASON_CODE_LONG),
    ("qwen3.7-plus", "standard", _REASON_CODE_LONG),
    ("qwen3.5-plus", "standard", _REASON_CODE),
    ("kimi-k2.6", "standard", _REASON_CODE_LONG),
    ("glm-4.7", "standard", _REASON_CODE),
    ("gemini-3.5-flash", "mini", _FULL),
    ("deepseek-v4-flash", "mini", _REASON_CODE),
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
            )
        )
    return out


def build_registry() -> list[ModelSpec]:
    specs = []
    for model_id, tier, caps in _CATALOG:
        price_in, price_out = TIER_PRICING[tier]
        specs.append(
            ModelSpec(id=model_id, provider="inference", tier=tier,
                      price_in=price_in, price_out=price_out, capabilities=caps)
        )
    return _apply_overrides(specs)


REGISTRY: list[ModelSpec] = build_registry()


def by_id(model_id: str, registry: list[ModelSpec] | None = None) -> ModelSpec | None:
    for s in registry or REGISTRY:
        if s.id == model_id:
            return s
    return None
