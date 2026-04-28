from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

VdiStatus = Literal["online", "offline", "mock"]
Esp32Status = Literal["connected", "disconnected", "mock_connected"]
AiMode = Literal["local", "external", "serverless", "hybrid", "hybrid_mock"]
SystemMode = Literal[
    "view",
    "live_control",
    "annotation",
    "agent_assist",
    "step_auto",
    "observe",
]


class ObsStatus(BaseModel):
    status: Literal["online", "offline", "mock"] = "mock"
    delay_ms: int = Field(1200, alias="delayMs")

    model_config = {"populate_by_name": True}


class Esp32Info(BaseModel):
    status: Esp32Status = "mock_connected"


class AiInfo(BaseModel):
    mode: AiMode = "hybrid_mock"


class MemoryInfo(BaseModel):
    status: Literal["ok", "warn", "error"] = "ok"


class SystemStatus(BaseModel):
    vdi: VdiStatus = "mock"
    obs: ObsStatus = ObsStatus()
    esp32: Esp32Info = Esp32Info()
    ai: AiInfo = AiInfo()
    memory: MemoryInfo = MemoryInfo()
    current_mode: SystemMode = Field("live_control", alias="currentMode")
    agents_paused: bool = Field(False, alias="agentsPaused")
    emergency_stop: bool = Field(False, alias="emergencyStop")

    model_config = {"populate_by_name": True}


class ModePatch(BaseModel):
    mode: SystemMode


class PauseAgentsBody(BaseModel):
    paused: Optional[bool] = None
