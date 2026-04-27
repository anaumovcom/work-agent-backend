from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from ..core.event_bus import bus
from ..models.agents import AgentTask, Plan, PlanStep, Risk
from ..models.approvals import Approval
from ..storage.repositories import storage
from . import agent_service, approval_service, history_service


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- триггеры по тексту ---

def _looks_like_link_to_epics(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ["эпик", "epic", "привяж", "маппинг"])


async def handle_user_message(text: str) -> None:
    """Реакция mock-агента на пользовательское сообщение."""
    if storage.status.agents_paused:
        await agent_service.push_message(
            author="agent",
            text="Агенты на паузе. Снимите паузу, чтобы продолжить.",
        )
        return

    await asyncio.sleep(0.4)
    await agent_service.push_message(author="agent", text="Принял, начинаю обработку.")

    if _looks_like_link_to_epics(text):
        asyncio.create_task(_simulate_link_to_epics(text))
    else:
        asyncio.create_task(_simulate_generic(text))


async def _simulate_generic(text: str) -> None:
    # создаём задачу + минимальный план
    task = await agent_service.create_task_from_text(text)  # type: ignore[attr-defined]
    plan = storage.plans.get(task.plan_id or "")
    if not plan:
        return
    steps_titles = [
        ("Понять запрос", "Supervisor"),
        ("Собрать контекст из памяти", "Memory"),
        ("Составить ответ", "LLM"),
        ("Показать пользователю", "Supervisor"),
    ]
    for title, agent in steps_titles:
        await agent_service.add_step(
            plan.id,
            _make_new_step(title=title, agent=agent),
        )
    await asyncio.sleep(0.6)
    plan = storage.plans.get(plan.id)
    if plan and plan.steps:
        await agent_service.patch_step(
            plan.id, plan.steps[0].id,
            _make_step_patch(status="done"),
        )
    await asyncio.sleep(0.6)
    plan = storage.plans.get(plan.id)
    if plan and len(plan.steps) > 1:
        await agent_service.patch_step(
            plan.id, plan.steps[1].id,
            _make_step_patch(status="active"),
        )


async def _simulate_link_to_epics(text: str) -> None:
    # создаём задачу + детальный план
    task = await agent_service.create_task_from_text(  # type: ignore[attr-defined]
        text, title="Привязать новые задачи к эпикам", agent="Task Agent",
        context=[
            "пользователь — Иван Петров, тимлид GAMES",
            "доска: tracker.company.local/board/GAMES",
        ],
        sources=["Память: эпики GP-12, GP-22, GP-30, GP-45"],
        risks=[Risk(tone="warn", text="Неоднозначный маппинг для GAMES-1239")],
    )
    plan_id = task.plan_id
    if not plan_id:
        return

    seed_steps = [
        ("Открыть доску команды", "VDI Agent"),
        ("Найти новые задачи", "Task Agent"),
        ("Распознать карточки", "Vision"),
        ("Сопоставить с эпиками", "Task Agent"),
        ("Показать маппинг пользователю", "Supervisor"),
        ("Заполнить Epic Link", "VDI Agent"),
        ("Проверить результат", "VDI Agent"),
    ]
    for title, agent in seed_steps:
        await agent_service.add_step(plan_id, _make_new_step(title=title, agent=agent))

    plan = storage.plans.get(plan_id)
    if not plan or len(plan.steps) < 5:
        return

    # шаги 1-2: done
    for i in (0, 1):
        await asyncio.sleep(0.6)
        await agent_service.patch_step(plan_id, plan.steps[i].id,
                                       _make_step_patch(status="done"))

    # шаг 3: active
    await asyncio.sleep(0.6)
    await agent_service.patch_step(plan_id, plan.steps[2].id,
                                   _make_step_patch(status="active"))

    # карточка-предложение в чат
    await asyncio.sleep(0.6)
    await agent_service.push_message(
        author="agent",
        card={
            "seen": ["открыт трекер задач", "8 карточек в To Do",
                     "3 задачи без эпика"],
            "proposal": ["распознать карточки",
                         "сопоставить с эпиками из памяти",
                         "показать маппинг для подтверждения"],
            "actions": ["Начать", "Изменить план", "Отмена"],
        },
    )

    # шаг 3: done, шаг 4: active
    await asyncio.sleep(0.8)
    await agent_service.patch_step(plan_id, plan.steps[2].id,
                                   _make_step_patch(status="done"))
    await agent_service.patch_step(plan_id, plan.steps[3].id,
                                   _make_step_patch(status="active"))

    # создаём approval с маппингом
    await asyncio.sleep(0.8)
    await agent_service.patch_step(plan_id, plan.steps[3].id,
                                   _make_step_patch(status="done"))
    await agent_service.patch_step(plan_id, plan.steps[4].id,
                                   _make_step_patch(status="waiting_approval"))
    await approval_service.create(
        type_="Привязка задач к эпикам",
        target="GAMES board",
        content="GAMES-1234 → GP-45 (Профиль)\nGAMES-1235 → GP-12 (Календарь)\nGAMES-1239 → ?",
        risk="medium",
        agent="Task Agent",
        expected="Epic Link обновлён в трекере",
        related_entities=["GAMES-1234", "GAMES-1235", "GAMES-1239"],
        plan_id=plan_id,
        step_id=plan.steps[4].id,
    )


async def on_approval_resolved(approval: Approval, *, approved: bool) -> None:
    """Колбэк из approval_service.approve/reject — продолжаем mock-план."""
    if not approval.plan_id:
        return
    plan = storage.plans.get(approval.plan_id)
    if not plan:
        return

    if approved:
        # текущий step approval → done, следующий → active, дальше done
        await agent_service.patch_step(
            plan.id, approval.step_id or plan.steps[-1].id,
            _make_step_patch(status="done"),
        )
        plan = storage.plans.get(plan.id)
        if not plan:
            return
        # активируем следующие
        idx = next((i for i, s in enumerate(plan.steps) if s.id == approval.step_id), -1)
        for j in range(idx + 1, len(plan.steps)):
            await asyncio.sleep(0.7)
            await agent_service.patch_step(plan.id, plan.steps[j].id,
                                           _make_step_patch(status="active"))
            await asyncio.sleep(0.7)
            await agent_service.patch_step(plan.id, plan.steps[j].id,
                                           _make_step_patch(status="done"))
        # завершаем задачу
        if plan.task_id:
            t = storage.tasks.get(plan.task_id)
            if t:
                t = t.model_copy(update={"status": "done"})
                storage.tasks.put(t.id, t)
                await bus.publish("agent.task.updated",
                                  t.model_dump(mode="json", by_alias=True))
        await agent_service.push_message(
            author="agent",
            text="Готово. Все задачи привязаны к эпикам.",
        )
    else:
        await agent_service.patch_step(
            plan.id, approval.step_id or plan.steps[-1].id,
            _make_step_patch(status="cancelled"),
        )
        if plan.task_id:
            t = storage.tasks.get(plan.task_id)
            if t:
                t = t.model_copy(update={"status": "waiting"})
                storage.tasks.put(t.id, t)
                await bus.publish("agent.task.updated",
                                  t.model_dump(mode="json", by_alias=True))
        await agent_service.push_message(
            author="agent",
            text="Понял, остановился. Жду уточнений.",
        )


# --- утилиты внутри модуля ---

def _make_step_patch(**kwargs):
    from ..models.agents import StepPatch
    return StepPatch(**kwargs)


def _make_new_step(*, title: str, agent: str | None = None,
                   description: str | None = None):
    from ..models.agents import NewStep
    return NewStep(title=title, agent=agent, description=description)
