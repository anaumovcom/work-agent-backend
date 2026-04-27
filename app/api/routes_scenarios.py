from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..core.event_bus import bus
from ..models.scenarios import Scenario, ScenarioPatch
from ..services import agent_service, history_service
from ..storage.repositories import storage

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("", response_model=list[Scenario])
async def list_scenarios() -> list[Scenario]:
    return storage.scenarios.all()


@router.get("/{scenario_id}", response_model=Scenario)
async def get_scenario(scenario_id: str) -> Scenario:
    sc = storage.scenarios.get(scenario_id)
    if not sc:
        raise HTTPException(404, "scenario not found")
    return sc


@router.patch("/{scenario_id}", response_model=Scenario)
async def patch_scenario(scenario_id: str, body: ScenarioPatch) -> Scenario:
    sc = storage.scenarios.get(scenario_id)
    if not sc:
        raise HTTPException(404, "scenario not found")
    update = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    sc = sc.model_copy(update=update)
    storage.scenarios.put(sc.id, sc)
    await bus.publish("scenario.updated", sc.model_dump(mode="json"))
    return sc


@router.post("/{scenario_id}/run")
async def run_scenario(scenario_id: str) -> dict:
    sc = storage.scenarios.get(scenario_id)
    if not sc:
        raise HTTPException(404, "scenario not found")
    task = await agent_service.create_task_from_text(
        sc.name, title=sc.name, agent="Supervisor",
    )
    await history_service.quick("user", "scenario.run",
                                f"Сценарий запущен: {sc.name}")
    await bus.publish("scenario.started", {"id": sc.id, "taskId": task.id})
    return {"taskId": task.id, "scenarioId": sc.id}
