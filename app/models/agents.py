from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

PlanStepStatus = Literal[
    "pending",
    "running",
    "done",
    "waiting_approval",
    "skipped",
    "failed",
    "cancelled",
    # совместимо с фронтом
    "waiting",
    "active",
    "approval",
    "error",
]

TaskStatus = Literal["pending", "running", "done", "cancelled", "failed", "waiting"]


class PlanStep(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: PlanStepStatus = "waiting"
    agent: Optional[str] = None
    confidence: Optional[float] = None
    expected: Optional[str] = None
    actual: Optional[str] = None


class Plan(BaseModel):
    id: str
    task_id: str = Field(alias="taskId")
    steps: list[PlanStep] = []

    model_config = {"populate_by_name": True}


class Risk(BaseModel):
    tone: Literal["warn", "success", "danger", "info"] = "info"
    text: str


class AgentTask(BaseModel):
    id: str
    title: str
    agent: str = "Supervisor"
    status: TaskStatus = "running"
    plan_id: Optional[str] = Field(default=None, alias="planId")
    context: list[str] = []
    sources: list[str] = []
    risks: list[Risk] = []
    created_at: str = Field(alias="createdAt")

    model_config = {"populate_by_name": True}


class CreateTaskRequest(BaseModel):
    message: str
    context: dict[str, Any] = {}


class AgentMessage(BaseModel):
    id: str
    author: Literal["user", "agent"]
    time: str
    text: Optional[str] = None
    card: Optional[dict[str, Any]] = None


class SendMessageRequest(BaseModel):
    text: str


class StepPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[PlanStepStatus] = None
    agent: Optional[str] = None
    confidence: Optional[float] = None
    expected: Optional[str] = None
    actual: Optional[str] = None


class NewStep(BaseModel):
    title: str
    description: Optional[str] = None
    status: PlanStepStatus = "waiting"
    agent: Optional[str] = None


class ReorderRequest(BaseModel):
    step_ids: list[str] = Field(alias="stepIds")

    model_config = {"populate_by_name": True}
