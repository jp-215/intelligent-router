"""FastAPI application factory for the intelligent router.

The same routing engine, exposed over HTTP so it can run as a service — or be mounted as
an MCP server (set ENABLE_MCP=1 with ``fastapi-mcp`` installed). Endpoints:

  GET  /health                 liveness
  GET  /models                 list the model catalog
  POST /route                  route ONE task (free, no model call)
  POST /plan                   decompose a feature -> route every task (one cheap call)
  POST /complete               full path: select -> fallback -> budget-enforced -> run
  POST /build                  map-reduce a task DAG (cheap map, pro/frontier reduce)
  GET  /report                 usage + cost analytics

Layout: routes (this layer) -> handlers (orchestration) -> services (infra) -> core
(pure domain). Shared dependencies live in ``router.routes.dependencies`` and are
re-exported here for convenience and test overrides.
"""

from __future__ import annotations

from fastapi import FastAPI

from .config import get_settings
from .routes import api_router

# Re-exported so tests can do `from router.api import app, get_budget, get_completer`
# and override the same dependency objects the routes use.
from .routes.dependencies import (  # noqa: F401
    client_id,
    get_budget,
    get_completer,
)


def create_app() -> FastAPI:
    """Build the FastAPI app: mount the routers, optionally expose MCP tools."""
    app = FastAPI(title="Intelligent Router API", version="0.1.0")
    app.include_router(api_router)

    # Optional: expose every endpoint as MCP tools (pip install fastapi-mcp; ENABLE_MCP=1).
    if get_settings().enable_mcp:  # pragma: no cover
        try:
            from fastapi_mcp import FastApiMCP

            FastApiMCP(app).mount()
        except ImportError:
            pass

    return app


app = create_app()
