"""Core types: model capabilities, tiers, and the cost model."""

from __future__ import annotations

from dataclasses import dataclass, field

# Capability flags a task may require.
CAP_REASONING = "reasoning"
CAP_VISION = "vision"
CAP_LONG_CONTEXT = "long_context"
CAP_CODE = "code"

# Tiers ordered cheapest/least-capable -> most-capable.
TIERS = ["nano", "mini", "standard", "pro", "frontier"]


def tier_rank(tier: str) -> int:
    if tier not in TIERS:
        raise ValueError(f"unknown tier: {tier}")
    return TIERS.index(tier)


@dataclass(frozen=True)
class ModelSpec:
    """A routable model. Prices are USD per 1M tokens (ESTIMATES — see registry)."""

    id: str
    provider: str  # "inference" | "openrouter"
    tier: str
    price_in: float
    price_out: float
    capabilities: frozenset[str] = field(default_factory=frozenset)
    open_source: bool = False  # open-weight model — preferred as a resilient fallback

    def supports(self, required_caps: frozenset[str]) -> bool:
        return required_caps.issubset(self.capabilities)

    def cost(self, tokens_in: int, tokens_out: int) -> float:
        """Estimated USD cost for a call of this token shape."""
        return tokens_in / 1_000_000 * self.price_in + tokens_out / 1_000_000 * self.price_out

    @property
    def rank(self) -> int:
        return tier_rank(self.tier)
