from __future__ import annotations

from fastapi import APIRouter

from ..models.settings import AppSettings, AppSettingsUpdate
from ..services import settings_service
from ..services.hid_command_queue import hid_queue
from ..services.screen_capture_service import screen_capture

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=AppSettings, response_model_by_alias=True)
async def get_settings_endpoint() -> AppSettings:
    return settings_service.current_settings()


@router.patch("", response_model=AppSettings, response_model_by_alias=True)
async def update_settings_endpoint(update: AppSettingsUpdate) -> AppSettings:
    settings = settings_service.save_settings(update)
    await screen_capture.reconfigure()
    await hid_queue.reconfigure()
    return settings