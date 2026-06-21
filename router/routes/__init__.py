"""HTTP layer: thin FastAPI routers + shared dependencies.

``api_router`` aggregates every sub-router; the app factory in ``router.api`` includes it.
"""

from __future__ import annotations

from fastapi import APIRouter

from . import meta, report, routing

api_router = APIRouter()
api_router.include_router(meta.router)
api_router.include_router(routing.router)
api_router.include_router(report.router)

__all__ = ["api_router"]
