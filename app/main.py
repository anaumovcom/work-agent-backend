from __future__ import annotations

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    routes_agents,
    routes_approvals,
    routes_diagnostics,
    routes_history,
    routes_memory,
    routes_scenarios,
    routes_settings,
    routes_status,
    routes_vdi,
)
from .core.config import get_settings
from .core.websocket_manager import websocket_endpoint
from .mocks.initial_data import seed
from .services.vdi_service import init_vdi_runtime, shutdown_vdi_runtime

settings = get_settings()

app = FastAPI(title="Work Agent Backend", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    seed()
    await init_vdi_runtime()


@app.on_event("shutdown")
async def _shutdown() -> None:
    await shutdown_vdi_runtime()


app.include_router(routes_status.router)
app.include_router(routes_vdi.router)
app.include_router(routes_agents.router)
app.include_router(routes_approvals.router)
app.include_router(routes_memory.router)
app.include_router(routes_history.router)
app.include_router(routes_scenarios.router)
app.include_router(routes_diagnostics.router)
app.include_router(routes_settings.router)


@app.websocket("/ws/events")
async def ws_events(ws: WebSocket) -> None:
    await websocket_endpoint(ws)


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}
