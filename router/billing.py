"""Monetization: turn routed (cheap) upstream cost into a billable price.

An operator running this router charges clients a markup over what the routed model
actually cost. The spread (revenue − upstream cost) is the operator's margin — and because
the router already picks the cheapest capable model, that margin is maximized.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BillingPolicy:
    markup_pct: float = 0.0   # fraction added over upstream cost (0.20 = +20%)
    flat_fee: float = 0.0     # flat fee added per call (USD)
    min_charge: float = 0.0   # minimum charge per call (USD)

    def price(self, upstream_cost: float) -> float:
        """Billable price for a call that cost `upstream_cost` on the model."""
        billed = upstream_cost * (1 + self.markup_pct) + self.flat_fee
        return round(max(billed, self.min_charge), 6)

    @classmethod
    def from_env(cls) -> BillingPolicy:
        return cls(
            markup_pct=float(os.getenv("ROUTER_MARKUP_PCT", "0")),
            flat_fee=float(os.getenv("ROUTER_FLAT_FEE", "0")),
            min_charge=float(os.getenv("ROUTER_MIN_CHARGE", "0")),
        )
