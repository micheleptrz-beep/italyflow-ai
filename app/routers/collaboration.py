"""
ItalyFlow AI - Collaboration router (Section 2.4). ASCII only.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from app.models.collaboration import Role
from app.services.collaboration_service import CollaborationService

api = APIRouter(prefix="/api/v1/collab", tags=["collaboration"])


def get_current_user_id(request: Request) -> int:
    if hasattr(request, "session"):
        uid = request.session.get("user_id")
        if uid is not None:
            return int(uid)
    hv = request.headers.get("X-User-Id")
    if hv and hv.isdigit():
        return int(hv)
    raise HTTPException(status_code=401, detail="Not authenticated")


class CommentIn(BaseModel):
    target_type: str = Field(pattern="^(label|audit|product)$")
    target_id: int
    body: str = Field(min_length=1, max_length=4000)
    anchor: Optional[dict] = None


class MemberIn(BaseModel):
    user_id: int
    role: str = Field(pattern="^(owner|editor|viewer|auditor)$")


class WorkflowIn(BaseModel):
    target_type: str
    target_id: int
    steps: list[str]


class DecisionIn(BaseModel):
    approve: bool
    note: Optional[str] = None


@api.post("/comments")
def add_comment(body: CommentIn, request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    c = CollaborationService(db).add_comment(
        uid, body.target_type, body.target_id, body.body, body.anchor)
    return {"id": c.id, "created_at": c.created_at}


@api.get("/comments")
def list_comments(target_type: str, target_id: int, db: Session = Depends(get_db)):
    rows = CollaborationService(db).list_comments(target_type, target_id)
    return [{"id": c.id, "user_id": c.user_id, "body": c.body, "anchor": c.anchor,
             "resolved": c.resolved, "created_at": c.created_at} for c in rows]


@api.post("/comments/{comment_id}/resolve")
def resolve_comment(comment_id: int, request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    c = CollaborationService(db).resolve_comment(uid, comment_id)
    return {"id": c.id, "resolved": c.resolved}


@api.post("/members")
def add_member(body: MemberIn, request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)  # workspace owner = current user
    m = CollaborationService(db).add_member(uid, body.user_id, Role(body.role))
    return {"id": m.id, "role": m.role.value}


@api.post("/workflow/start")
def start_workflow(body: WorkflowIn, request: Request, db: Session = Depends(get_db)):
    _ = get_current_user_id(request)
    steps = [Role(s) for s in body.steps]
    rows = CollaborationService(db).start_workflow(body.target_type, body.target_id, steps)
    return {"approval_ids": [r.id for r in rows]}


@api.post("/approvals/{approval_id}/decide")
def decide(approval_id: int, body: DecisionIn, request: Request,
           db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    a = CollaborationService(db).decide(uid, approval_id, body.approve, body.note)
    return {"id": a.id, "state": a.state.value}


@api.get("/workflow")
def workflow_state(target_type: str, target_id: int, db: Session = Depends(get_db)):
    return CollaborationService(db).workflow_state(target_type, target_id)


@api.get("/activity")
def activity(request: Request, limit: int = 50, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    rows = CollaborationService(db).feed_for_user(uid, limit=limit)
    return [{"id": r.id, "target_type": r.target_type, "target_id": r.target_id,
             "action": r.action, "payload": r.payload, "created_at": r.created_at}
            for r in rows]
