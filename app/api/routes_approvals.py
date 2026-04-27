from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models.approvals import Approval, ApprovalPatch, RewriteRequest
from ..services import approval_service

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("", response_model=list[Approval])
async def list_approvals(status: str | None = None) -> list[Approval]:
    return approval_service.list_approvals(status)


@router.get("/{approval_id}", response_model=Approval)
async def get_approval(approval_id: str) -> Approval:
    a = approval_service.get_approval(approval_id)
    if not a:
        raise HTTPException(404, "approval not found")
    return a


@router.patch("/{approval_id}", response_model=Approval)
async def patch_approval(approval_id: str, body: ApprovalPatch) -> Approval:
    a = await approval_service.patch(approval_id, body)
    if not a:
        raise HTTPException(404, "approval not found")
    return a


@router.post("/{approval_id}/rewrite", response_model=Approval)
async def rewrite_approval(approval_id: str, body: RewriteRequest) -> Approval:
    a = await approval_service.rewrite(approval_id, body)
    if not a:
        raise HTTPException(404, "approval not found")
    return a


@router.post("/{approval_id}/approve", response_model=Approval)
async def approve_approval(approval_id: str) -> Approval:
    a = await approval_service.approve(approval_id)
    if not a:
        raise HTTPException(404, "approval not found")
    return a


@router.post("/{approval_id}/reject", response_model=Approval)
async def reject_approval(approval_id: str) -> Approval:
    a = await approval_service.reject(approval_id)
    if not a:
        raise HTTPException(404, "approval not found")
    return a
