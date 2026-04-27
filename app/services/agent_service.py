from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..core.event_bus import bus
from ..models.agents import (
    AgentMessage,
    AgentTask,
    CreateTaskRequest,
    NewStep,
    Plan,
    PlanStep,
    ReorderRequest,
    SendMessageRequest,
    StepPatch,
)
from ..storage.repositories import storage
from . import history_service


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_time() -> str:
    return datetime.now().strftime("%H:%M")


# --------- messages ---------

def list_messages() -> list[AgentMessage]:
    return list(storage.messages)


async def push_message(*, author: str, text: Optional[str] = None,
                       card: Optional[dict] = None) -> AgentMessage:
    n = storage.message_counter.next()
    m = AgentMessage(id=f"msg_{n:04d}", author=author, time=_short_time(),  # type: ignore[arg-type]
                     text=text, card=card)
    storage.messages.append(m)
    await bus.publish("agent.message.created", m.model_dump(mode="json"))
    return m


async def send_message(req: SendMessageRequest) -> AgentMessage:
    user_msg = await push_message(author="user", text=req.text)
    await history_service.quick("user", "chat.user_message",
                                f"Пользователь: {req.text}")
    # mock-ответ агента — старт задачи
    from .mock_runtime import handle_user_message
    await handle_user_message(req.text)
    return user_msg


# --------- tasks ---------

def list_tasks() -> list[AgentTask]:
    return storage.tasks.all()


def get_task(task_id: str) -> AgentTask | None:
    return storage.tasks.get(task_id)


async def create_task(req: CreateTaskRequest) -> AgentTask:
    return await create_task_from_text(req.message)


async def create_task_from_text(
    text: str,
    *,
    title: Optional[str] = None,
    agent: str = "Supervisor",
    context: Optional[list[str]] = None,
    sources: Optional[list[str]] = None,
    risks: Optional[list] = None,
) -> AgentTask:
    n = storage.task_counter.next()
    plan_n = storage.plan_counter.next()
    task_id = f"task_{n:03d}"
    plan_id = f"plan_{plan_n:03d}"
    plan = Plan(id=plan_id, taskId=task_id, steps=[])
    storage.plans.put(plan_id, plan)

    task = AgentTask(
        id=task_id,
        title=title or text[:80],
        agent=agent,
        status="running",
        planId=plan_id,
        context=context or [],
        sources=sources or [],
        risks=risks or [],
        createdAt=_now_iso(),
    )
    storage.tasks.put(task_id, task)
    await bus.publish("agent.task.created", task.model_dump(mode="json", by_alias=True))
    await history_service.quick("agent", "task.created", f"Создана задача: {task.title}")
    return task


async def cancel_task(task_id: str) -> AgentTask | None:
    t = storage.tasks.get(task_id)
    if not t:
        return None
    t = t.model_copy(update={"status": "cancelled"})
    storage.tasks.put(task_id, t)
    await bus.publish("agent.task.updated", t.model_dump(mode="json", by_alias=True))
    await history_service.quick("user", "task.cancelled", f"Задача отменена: {task_id}")
    return t


# --------- plans / steps ---------

def get_plan(plan_id: str) -> Plan | None:
    return storage.plans.get(plan_id)


def current_plan() -> Plan | None:
    plans = storage.plans.all()
    if not plans:
        return None
    # выбираем план активной/первой задачи
    for t in storage.tasks.all():
        if t.status == "running" and t.plan_id:
            p = storage.plans.get(t.plan_id)
            if p:
                return p
    return plans[0]


async def patch_step(plan_id: str, step_id: str, patch: StepPatch) -> Plan | None:
    plan = storage.plans.get(plan_id)
    if not plan:
        return None
    update_data = {k: v for k, v in patch.model_dump(exclude_unset=True).items() if v is not None}
    new_steps = []
    found = False
    for s in plan.steps:
        if s.id == step_id:
            found = True
            new_steps.append(s.model_copy(update=update_data))
        else:
            new_steps.append(s)
    if not found:
        return None
    plan = plan.model_copy(update={"steps": new_steps})
    storage.plans.put(plan.id, plan)
    await bus.publish("plan.step.updated", {
        "planId": plan.id, "stepId": step_id, "patch": update_data,
    })
    return plan


async def add_step(plan_id: str, body: NewStep) -> Plan | None:
    plan = storage.plans.get(plan_id)
    if not plan:
        return None
    n = storage.step_counter.next()
    step = PlanStep(
        id=f"step_{n:04d}",
        title=body.title,
        description=body.description,
        status=body.status,
        agent=body.agent,
    )
    plan = plan.model_copy(update={"steps": [*plan.steps, step]})
    storage.plans.put(plan.id, plan)
    await bus.publish("plan.step.created", {
        "planId": plan.id, "step": step.model_dump(mode="json"),
    })
    return plan


async def delete_step(plan_id: str, step_id: str) -> Plan | None:
    plan = storage.plans.get(plan_id)
    if not plan:
        return None
    new_steps = [s for s in plan.steps if s.id != step_id]
    if len(new_steps) == len(plan.steps):
        return None
    plan = plan.model_copy(update={"steps": new_steps})
    storage.plans.put(plan.id, plan)
    await bus.publish("plan.step.deleted", {"planId": plan.id, "stepId": step_id})
    return plan


async def reorder(plan_id: str, body: ReorderRequest) -> Plan | None:
    plan = storage.plans.get(plan_id)
    if not plan:
        return None
    by_id = {s.id: s for s in plan.steps}
    new_steps = [by_id[i] for i in body.step_ids if i in by_id]
    # дописываем оставшиеся
    for s in plan.steps:
        if s.id not in body.step_ids:
            new_steps.append(s)
    plan = plan.model_copy(update={"steps": new_steps})
    storage.plans.put(plan.id, plan)
    await bus.publish("plan.steps.reordered", {
        "planId": plan.id, "stepIds": [s.id for s in plan.steps],
    })
    return plan
