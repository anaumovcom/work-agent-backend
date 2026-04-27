from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..core.event_bus import bus
from ..models.approvals import Approval, ApprovalPatch, RewriteRequest
from ..storage.repositories import storage
from . import history_service


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_approvals(status: Optional[str] = None) -> list[Approval]:
    items = storage.approvals.all()
    if status:
        items = [a for a in items if a.status == status]
    return items


def get_approval(approval_id: str) -> Approval | None:
    return storage.approvals.get(approval_id)


async def create(
    *,
    type_: str,
    target: str,
    content: str,
    risk: str = "low",
    agent: str = "Supervisor",
    expected: str | None = None,
    related_entities: list[str] | None = None,
    plan_id: str | None = None,
    step_id: str | None = None,
) -> Approval:
    n = storage.approval_counter.next()
    a = Approval(
        id=f"approval_{n:03d}",
        type=type_,
        target=target,
        content=content,
        risk=risk,  # type: ignore[arg-type]
        agent=agent,
        expected=expected,
        status="pending",
        editable=True,
        related_entities=related_entities or [],
        created_at=_now_iso(),
        plan_id=plan_id,
        step_id=step_id,
    )
    storage.approvals.put(a.id, a)
    await bus.publish("approval.created", a.model_dump(mode="json"))
    await history_service.quick("agent", "approval.created",
                                f"Approval создан: {a.target or a.type}")
    return a


async def patch(approval_id: str, body: ApprovalPatch) -> Approval | None:
    a = storage.approvals.get(approval_id)
    if not a:
        return None
    update = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    a = a.model_copy(update=update)
    storage.approvals.put(a.id, a)
    await bus.publish("approval.updated", a.model_dump(mode="json"))
    return a


async def rewrite(approval_id: str, body: RewriteRequest) -> Approval | None:
    a = storage.approvals.get(approval_id)
    if not a:
        return None
    a = a.model_copy(update={"content": body.content})
    storage.approvals.put(a.id, a)
    await bus.publish("approval.updated", a.model_dump(mode="json"))
    await history_service.quick("user", "approval.rewritten",
                                f"Approval переписан: {a.id}")
    return a


async def approve(approval_id: str) -> Approval | None:
    a = storage.approvals.get(approval_id)
    if not a:
        return None
    a = a.model_copy(update={"status": "approved"})
    storage.approvals.put(a.id, a)
    await bus.publish("approval.updated", a.model_dump(mode="json"))
    await history_service.quick("user", "approval.approved",
                                f"Подтверждено: {a.id} — {a.target}")
    # передаём в mock runtime
    from .mock_runtime import on_approval_resolved
    await on_approval_resolved(a, approved=True)
    return a


async def reject(approval_id: str) -> Approval | None:
    a = storage.approvals.get(approval_id)
    if not a:
        return None
    a = a.model_copy(update={"status": "rejected"})
    storage.approvals.put(a.id, a)
    await bus.publish("approval.updated", a.model_dump(mode="json"))
    await history_service.quick("user", "approval.rejected",
                                f"Отклонено: {a.id} — {a.target}")
    from .mock_runtime import on_approval_resolved
    await on_approval_resolved(a, approved=False)
    return a


