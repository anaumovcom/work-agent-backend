from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

ApprovalStatus = Literal["pending", "approved", "rejected", "cancelled"]
RiskLevel = Literal["low", "medium", "high"]


class Approval(BaseModel):
    id: str
    type: str
    target: str
    content: str
    risk: RiskLevel = "low"
    agent: str
    expected: Optional[str] = None
    status: ApprovalStatus = "pending"
    editable: bool = True
    related_entities: list[str] = []
    created_at: str
    plan_id: Optional[str] = None
    step_id: Optional[str] = None


class ApprovalPatch(BaseModel):
    content: Optional[str] = None
    expected: Optional[str] = None


class RewriteRequest(BaseModel):
    content: str
