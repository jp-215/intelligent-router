"""Meta routes: service health and the model catalog."""

from __future__ import annotations

from fastapi import APIRouter

from ..services.registry import REGISTRY

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "intelligent-router"}


@router.get("/models")
def models() -> list[dict]:
    return [
        {
            "id": m.id, "tier": m.tier, "provider": m.provider,
            "price_in": m.price_in, "price_out": m.price_out,
            "open_source": m.open_source, "capabilities": sorted(m.capabilities),
        }
        for m in sorted(REGISTRY, key=lambda s: (s.rank, s.id))
    ]
