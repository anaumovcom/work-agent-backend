from __future__ import annotations

from ..models.agents import AgentMessage, AgentTask, Plan
from ..models.approvals import Approval
from ..models.history import HistoryEvent
from ..models.memory import MemoryItem
from ..models.scenarios import Scenario
from ..models.status import SystemStatus
from .db import Counter, Repository


class Storage:
    def __init__(self) -> None:
        self.status: SystemStatus = SystemStatus()
        self.tasks: Repository[AgentTask] = Repository()
        self.plans: Repository[Plan] = Repository()
        self.approvals: Repository[Approval] = Repository()
        self.memory: Repository[MemoryItem] = Repository()
        self.history: Repository[HistoryEvent] = Repository()
        self.scenarios: Repository[Scenario] = Repository()
        self.messages: list[AgentMessage] = []

        self.task_counter = Counter()
        self.plan_counter = Counter()
        self.step_counter = Counter()
        self.approval_counter = Counter()
        self.memory_counter = Counter()
        self.history_counter = Counter()
        self.message_counter = Counter()
        self.scenario_counter = Counter()
        self.frame_counter = Counter()


storage = Storage()
