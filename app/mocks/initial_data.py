from __future__ import annotations

from datetime import datetime, timezone

from ..models.agents import AgentMessage, AgentTask, Plan, PlanStep, Risk
from ..models.approvals import Approval
from ..models.history import HistoryEvent
from ..models.memory import MemoryItem
from ..models.scenarios import Scenario
from ..storage.repositories import storage


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed() -> None:
    s = storage
    now = _now_iso()

    # ----- plan + task -----
    plan_id = f"plan_{s.plan_counter.next():03d}"
    plan_steps = [
        PlanStep(id="s1", title="Открыть доску команды", description="Перейти на доску GAMES в трекере",
                 status="done", agent="VDI Agent", confidence=0.98,
                 expected="Доска открыта", actual="Доска открыта"),
        PlanStep(id="s2", title="Найти новые задачи", description="Сканировать колонку To Do",
                 status="done", agent="Task Agent", confidence=0.94,
                 expected="Список карточек", actual="Найдено 8 карточек"),
        PlanStep(id="s3", title="Распознать карточки", description="OCR + извлечение полей",
                 status="active", agent="Vision", confidence=0.86),
        PlanStep(id="s4", title="Сопоставить с эпиками", status="waiting", agent="Task Agent"),
        PlanStep(id="s5", title="Показать маппинг пользователю", status="approval", agent="Supervisor"),
        PlanStep(id="s6", title="Заполнить Epic Link", status="waiting", agent="VDI Agent"),
        PlanStep(id="s7", title="Проверить результат", status="waiting", agent="VDI Agent"),
    ]
    s.step_counter = type(s.step_counter)(start=100)
    s.plans.put(plan_id, Plan(id=plan_id, taskId="task_001", steps=plan_steps))

    task_id = f"task_{s.task_counter.next():03d}"
    s.tasks.put(
        task_id,
        AgentTask(
            id=task_id,
            title="Привязать новые задачи к эпикам",
            agent="Task Agent",
            status="running",
            planId=plan_id,
            context=[
                "пользователь — Иван Петров, тимлид GAMES",
                "доска: tracker.company.local/board/GAMES",
                "стиль командных чатов — менее формальный",
            ],
            sources=[
                "Память: эпики GP-12, GP-22, GP-30, GP-45",
                "Чат GAMES (Telegram): обсуждение релиза 1.4",
                "Встреча 22.04: договорённость о ревью",
            ],
            risks=[
                Risk(tone="warn", text="Неоднозначный маппинг для GAMES-1239 (confidence 0.42)"),
                Risk(tone="success", text="Все действия отменимы"),
                Risk(tone="danger", text="Риск массовой ошибки при автозаполнении"),
            ],
            createdAt=now,
        ),
    )
    # синхронизируем planId/taskId
    p = s.plans.get(plan_id)
    if p:
        s.plans.put(plan_id, Plan(id=p.id, taskId=task_id, steps=p.steps))
        s.tasks.put(task_id, s.tasks.get(task_id).model_copy(update={"plan_id": plan_id}))  # type: ignore[union-attr]

    # вторая задача
    plan2_id = f"plan_{s.plan_counter.next():03d}"
    s.plans.put(
        plan2_id,
        Plan(
            id=plan2_id,
            taskId="placeholder",
            steps=[
                PlanStep(id="t2-1", title="Собрать события за день", status="waiting", agent="Memory"),
                PlanStep(id="t2-2", title="Сформировать summary", status="waiting", agent="LLM"),
                PlanStep(id="t2-3", title="Показать на подтверждение", status="waiting", agent="Supervisor"),
            ],
        ),
    )
    task2_id = f"task_{s.task_counter.next():03d}"
    s.tasks.put(
        task2_id,
        AgentTask(
            id=task2_id,
            title="Подготовить ежедневный статус",
            agent="Message Writer",
            status="waiting",
            planId=plan2_id,
            context=["канал: #games-status", "стиль: короткие bullet-ы"],
            sources=["История чата за сегодня", "Trello GAMES board"],
            risks=[Risk(tone="success", text="Низкий риск — только черновик")],
            createdAt=now,
        ),
    )
    p2 = s.plans.get(plan2_id)
    if p2:
        s.plans.put(plan2_id, Plan(id=p2.id, taskId=task2_id, steps=p2.steps))

    # ----- approvals -----
    approvals_seed = [
        Approval(id="a1", type="Сообщение в Telegram", target="Чат: Команда GAMES",
                 content="Привет! Я завёл новые задачи в To Do и собираюсь привязать их к эпикам. Если есть пожелания — напишите.",
                 risk="low", agent="Message Writer",
                 expected="Сообщение будет отправлено в групповой чат",
                 status="pending", related_entities=["GAMES board"], created_at=now),
        Approval(id="a2", type="Сохранение задачи", target="GAMES-1234",
                 content="Установить Epic Link = GP-45 (Профиль)",
                 risk="medium", agent="Task Agent",
                 expected="Задача обновлена в трекере",
                 status="pending", related_entities=["GAMES-1234", "GP-45"],
                 created_at=now, plan_id=plan_id, step_id="s5"),
        Approval(id="a3", type="Создание встречи", target="Календарь Иван П.",
                 content="Встреча по ПСИ, 28.04 в 14:00, 30 минут",
                 risk="medium", agent="Calendar Agent", status="pending", created_at=now),
        Approval(id="a4", type="Email", target="ivan@company.local",
                 content="Подготовил черновик ответа по релизу 1.4",
                 risk="high", agent="Mail Agent", status="pending", created_at=now),
        Approval(id="a5", type="Сохранение задачи", target="GAMES-1235",
                 content="Установить Epic Link = GP-12",
                 risk="low", agent="Task Agent", status="pending",
                 related_entities=["GAMES-1235", "GP-12"], created_at=now),
    ]
    for a in approvals_seed:
        s.approvals.put(a.id, a)
        s.approval_counter.next()

    # ----- memory -----
    memory_seed = [
        MemoryItem(id="t1", type="task", title="GAMES-1234", meta="epic GP-45 • Иван П.",
                   summary="Похожа на задачи по эпику Профиль", created_at=now, updated_at=now),
        MemoryItem(id="t2", type="task", title="GAMES-1235", meta="epic GP-12 • Мария К.",
                   summary="Связана с календарём", created_at=now, updated_at=now),
        MemoryItem(id="e1", type="epic", title="GP-45 Профиль",
                   summary="Эпик по работе с профилями игроков", created_at=now, updated_at=now),
        MemoryItem(id="e2", type="epic", title="GP-12 Календарь",
                   summary="Эпик по календарным фичам", created_at=now, updated_at=now),
        MemoryItem(id="p1", type="person", title="Иван Петров", meta="Тимлид GAMES",
                   summary="Отвечает за фильтрацию и поиск", created_at=now, updated_at=now),
        MemoryItem(id="p2", type="person", title="Мария Климова", meta="Frontend",
                   summary="Берёт UI-задачи", created_at=now, updated_at=now),
        MemoryItem(id="d1", type="decision", title="Релиз 1.4 — 30 апреля",
                   summary="Зафиксировано на встрече 24.04", created_at=now, updated_at=now),
        MemoryItem(id="d2", type="decision", title="Не использовать внешние LLM для писем",
                   summary="Подтверждено пользователем 22.04", created_at=now, updated_at=now),
        MemoryItem(id="m1", type="message", title="Иван П. в Telegram",
                   summary="Просит короткие сообщения без воды", created_at=now, updated_at=now),
        MemoryItem(id="pref1", type="preference", title="Стиль сообщений в чат",
                   content="Пользователь предпочитает короткие сообщения без воды",
                   source="conversation", confidence=0.92, created_at=now, updated_at=now),
        MemoryItem(id="pref2", type="preference", title="Авто-маппинг при confidence > 0.9",
                   content="Подтверждено пользователем 22.04",
                   source="conversation", confidence=0.95, created_at=now, updated_at=now),
    ]
    for m in memory_seed:
        s.memory.put(m.id, m)
        s.memory_counter.next()

    # ----- history -----
    history_seed = [
        HistoryEvent(id="h1", timestamp=now, actor="system", type="screen.analyzed",
                     summary="Screen analyzed", status="info"),
        HistoryEvent(id="h2", timestamp=now, actor="user", type="vdi.click",
                     summary="User clicked 640, 320", status="success",
                     metadata={"x": 640, "y": 320}),
        HistoryEvent(id="h3", timestamp=now, actor="agent", type="vision.detect",
                     summary="Agent detected task board", status="info"),
        HistoryEvent(id="h4", timestamp=now, actor="agent", type="approval.created",
                     summary="Draft создан для GAMES-1234", status="info"),
        HistoryEvent(id="h5", timestamp=now, actor="user", type="approval.edited",
                     summary="User edited draft", status="info"),
        HistoryEvent(id="h6", timestamp=now, actor="agent", type="memory.saved",
                     summary="Сохранено решение: Релиз 1.4 — 30 апреля", status="info"),
        HistoryEvent(id="h7", timestamp=now, actor="agent", type="vision.error",
                     summary="Не удалось распознать форму справа", status="error"),
    ]
    for h in history_seed:
        s.history.put(h.id, h)
        s.history_counter.next()

    # ----- scenarios -----
    scenarios_seed = [
        Scenario(id="sc1", name="Привязать задачи к эпикам",
                 description="Сканирует доску, сопоставляет задачи с эпиками, заполняет Epic Link",
                 trigger="По расписанию: 9:00, 14:00", steps=7,
                 last_run="сегодня, 09:02", success_rate=0.94, enabled=True),
        Scenario(id="sc2", name="Подготовить ежедневный статус",
                 description="Собирает изменения за день и формирует summary в чат",
                 trigger="Каждый день в 18:00", steps=5,
                 last_run="вчера, 18:00", success_rate=0.97, enabled=True),
        Scenario(id="sc3", name="Проверить почту",
                 description="Смотрит inbox, выделяет важные письма, готовит черновики",
                 trigger="Каждый час", steps=4,
                 last_run="сегодня, 10:00", success_rate=0.89, enabled=True),
        Scenario(id="sc4", name="Собрать договорённости из Telegram",
                 description="Сканирует чаты, извлекает решения и задачи",
                 trigger="По запросу", steps=6,
                 last_run="24.04, 19:14", success_rate=0.78, enabled=False),
        Scenario(id="sc5", name="Подготовить повестку встречи",
                 description="Берёт встречу из календаря, собирает контекст из памяти",
                 trigger="За 1 час до встречи", steps=5,
                 last_run="сегодня, 13:00", success_rate=0.92, enabled=True),
    ]
    for sc in scenarios_seed:
        s.scenarios.put(sc.id, sc)
        s.scenario_counter.next()

    # ----- messages -----
    s.messages.extend([
        AgentMessage(id="m1", author="agent", time="10:14",
                     text="Привет! Я готов помочь. Что нужно сделать?"),
        AgentMessage(id="m2", author="user", time="10:14",
                     text="Завезли задачи на команду в трекере, привяжи их к эпикам."),
        AgentMessage(id="m3", author="agent", time="10:15",
                     card={
                         "seen": ["открыт трекер задач", "вижу 8 карточек в To Do",
                                  "3 задачи без эпика"],
                         "proposal": ["прочитать новые задачи",
                                      "сопоставить с эпиками из памяти",
                                      "показать маппинг для подтверждения",
                                      "заполнить Epic Link и сохранить"],
                         "actions": ["Начать", "Изменить план", "Отмена"],
                     }),
    ])
    for _ in range(3):
        s.message_counter.next()
