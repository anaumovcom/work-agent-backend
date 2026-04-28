from __future__ import annotations

from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    cors_origins: list[str] = Field(alias="corsOrigins")
    frame_provider: str = Field(alias="frameProvider")
    hid_bridge: str = Field(alias="hidBridge")
    obs_ws_url: str = Field(alias="obsWsUrl")
    obs_ws_password: str = Field(alias="obsWsPassword")
    obs_source_name: str = Field(alias="obsSourceName")
    esp32_base_url: str = Field(alias="esp32BaseUrl")
    esp32_ws_url: str = Field(alias="esp32WsUrl")
    esp32_api_token: str = Field(alias="esp32ApiToken")
    vdi_width: int = Field(alias="vdiWidth")
    vdi_height: int = Field(alias="vdiHeight")
    frame_refresh_interval_ms: int = Field(alias="frameRefreshIntervalMs")
    after_action_refresh_delay_ms: int = Field(alias="afterActionRefreshDelayMs")
    stale_frame_warning_ms: int = Field(alias="staleFrameWarningMs")
    stale_frame_block_ms: int = Field(alias="staleFrameBlockMs")
    hid_command_timeout_ms: int = Field(alias="hidCommandTimeoutMs")
    frame_storage_dir: str = Field(alias="frameStorageDir")

    model_config = {"populate_by_name": True}


class AppSettingsUpdate(BaseModel):
    cors_origins: list[str] | None = Field(default=None, alias="corsOrigins")
    frame_provider: str | None = Field(default=None, alias="frameProvider")
    hid_bridge: str | None = Field(default=None, alias="hidBridge")
    obs_ws_url: str | None = Field(default=None, alias="obsWsUrl")
    obs_ws_password: str | None = Field(default=None, alias="obsWsPassword")
    obs_source_name: str | None = Field(default=None, alias="obsSourceName")
    esp32_base_url: str | None = Field(default=None, alias="esp32BaseUrl")
    esp32_ws_url: str | None = Field(default=None, alias="esp32WsUrl")
    esp32_api_token: str | None = Field(default=None, alias="esp32ApiToken")
    vdi_width: int | None = Field(default=None, alias="vdiWidth")
    vdi_height: int | None = Field(default=None, alias="vdiHeight")
    frame_refresh_interval_ms: int | None = Field(default=None, alias="frameRefreshIntervalMs")
    after_action_refresh_delay_ms: int | None = Field(default=None, alias="afterActionRefreshDelayMs")
    stale_frame_warning_ms: int | None = Field(default=None, alias="staleFrameWarningMs")
    stale_frame_block_ms: int | None = Field(default=None, alias="staleFrameBlockMs")
    hid_command_timeout_ms: int | None = Field(default=None, alias="hidCommandTimeoutMs")
    frame_storage_dir: str | None = Field(default=None, alias="frameStorageDir")

    model_config = {"populate_by_name": True}