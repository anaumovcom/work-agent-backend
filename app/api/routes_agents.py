from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models.agents import (
    AgentMessage,
    AgentTask,
    CreateTaskRequest,
    NewStep,
    Plan,
    ReorderRequest,
    SendMessageRequest,
    StepPatch,
)
from ..services import agent_service

router = APIRouter(prefix="/api", tags=["agents"])


# --- messages ---

@router.get("/agents/messages", response_model=list[AgentMessage])
async def list_messages() -> list[AgentMessage]:
    return agent_service.list_messages()


@router.post("/agents/messages", response_model=AgentMessage)
async def send_message(body: SendMessageRequest) -> AgentMessage:
    return await agent_service.send_message(body)


# --- tasks ---

@router.get("/agents/tasks", response_model=list[AgentTask], response_model_by_alias=True)
async def list_tasks() -> list[AgentTask]:
    return agent_service.list_tasks()


@router.get("/agents/tasks/{task_id}", response_model=AgentTask, response_model_by_alias=True)
async def get_task(task_id: str) -> AgentTask:
    t = agent_service.get_task(task_id)
    if not t:
        raise HTTPException(404, "task not found")
    return t


@router.post("/agents/tasks", response_model=AgentTask, response_model_by_alias=True)
async def create_task(req: CreateTaskRequest) -> AgentTask:
    return await agent_service.create_task(req)


@router.post("/agents/tasks/{task_id}/cancel", response_model=AgentTask,
             response_model_by_alias=True)
async def cancel_task(task_id: str) -> AgentTask:
    t = await agent_service.cancel_task(task_id)
    if not t:
        raise HTTPException(404, "task not found")
    return t


# --- plans ---

@router.get("/plans/current", response_model=Plan, response_model_by_alias=True)
async def get_current_plan() -> Plan:
    p = agent_service.current_plan()
    if not p:
        raise HTTPException(404, "no current plan")
    return p


@router.get("/plans/{plan_id}", response_model=Plan, response_model_by_alias=True)
async def get_plan(plan_id: str) -> Plan:
    p = agent_service.get_plan(plan_id)
    if not p:
        raise HTTPException(404, "plan not found")
    return p


@router.patch("/plans/{plan_id}/steps/{step_id}", response_model=Plan,
              response_model_by_alias=True)
async def patch_step(plan_id: str, step_id: str, body: StepPatch) -> Plan:
    p = await agent_service.patch_step(plan_id, step_id, body)
    if not p:
        raise HTTPException(404, "plan/step not found")
    return p


@router.post("/plans/{plan_id}/steps", response_model=Plan, response_model_by_alias=True)
async def add_step(plan_id: str, body: NewStep) -> Plan:
    p = await agent_service.add_step(plan_id, body)
    if not p:
        raise HTTPException(404, "plan not found")
    return p


@router.delete("/plans/{plan_id}/steps/{step_id}", response_model=Plan,
               response_model_by_alias=True)
async def delete_step(plan_id: str, step_id: str) -> Plan:
    p = await agent_service.delete_step(plan_id, step_id)
    if not p:
        raise HTTPException(404, "plan/step not found")
    return p


@router.post("/plans/{plan_id}/steps/reorder", response_model=Plan,
             response_model_by_alias=True)
async def reorder_steps(plan_id: str, body: ReorderRequest) -> Plan:
    p = await agent_service.reorder(plan_id, body)
    if not p:
        raise HTTPException(404, "plan not found")
    return p
