from __future__ import annotations

from fastapi import APIRouter

from ..models.status import ModePatch, PauseAgentsBody, SystemStatus
from ..services import status_service

router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("", response_model=SystemStatus, response_model_by_alias=True)
async def get_status() -> SystemStatus:
    return await status_service.get_status()


@router.patch("/mode", response_model=SystemStatus, response_model_by_alias=True)
async def patch_mode(body: ModePatch) -> SystemStatus:
    return await status_service.set_mode(body)


@router.post("/pause-agents", response_model=SystemStatus, response_model_by_alias=True)
async def pause_agents(body: PauseAgentsBody | None = None) -> SystemStatus:
    paused = True if body is None or body.paused is None else body.paused
    return await status_service.set_paused(paused)


@router.post("/emergency-stop", response_model=SystemStatus, response_model_by_alias=True)
async def emergency_stop() -> SystemStatus:
    return await status_service.emergency_stop()


@router.post("/reset-emergency-stop", response_model=SystemStatus, response_model_by_alias=True)
async def reset_emergency_stop() -> SystemStatus:
    return await status_service.reset_emergency_stop()
