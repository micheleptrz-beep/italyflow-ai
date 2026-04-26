"""
ItalyFlow AI - Collaboration service (Section 2.4). ASCII only.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.collaboration import (
    ApprovalState, IfActivityLog, IfApproval, IfComment, IfWorkspaceMember, Role,
)


class CollaborationService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- RBAC ----------
    def role_of(self, workspace_owner_id: int, user_id: int) -> Role:
        if workspace_owner_id == user_id:
            return Role.OWNER
        m = self.db.scalar(
            select(IfWorkspaceMember).where(and_(
                IfWorkspaceMember.workspace_owner_id == workspace_owner_id,
                IfWorkspaceMember.user_id == user_id,
            ))
        )
        return m.role if m else Role.VIEWER

    def can(self, role: Role, action: str) -> bool:
        matrix = {
            Role.OWNER: {"read", "edit", "approve", "manage"},
            Role.EDITOR: {"read", "edit", "comment"},
            Role.VIEWER: {"read"},
            Role.AUDITOR: {"read", "comment", "approve"},
        }
        return action in matrix.get(role, set())

    def add_member(self, owner_id: int, user_id: int, role: Role) -> IfWorkspaceMember:
        m = self.db.scalar(
            select(IfWorkspaceMember).where(and_(
                IfWorkspaceMember.workspace_owner_id == owner_id,
                IfWorkspaceMember.user_id == user_id,
            ))
        )
        if m is None:
            m = IfWorkspaceMember(workspace_owner_id=owner_id, user_id=user_id, role=role)
            self.db.add(m)
        else:
            m.role = role
        self.db.commit(); self.db.refresh(m)
        return m

    # ---------- Comments ----------
    def add_comment(self, user_id: int, target_type: str, target_id: int,
                    body: str, anchor: Optional[dict] = None) -> IfComment:
        c = IfComment(user_id=user_id, target_type=target_type, target_id=target_id,
                      body=body, anchor=anchor or {})
        self.db.add(c); self.db.commit(); self.db.refresh(c)
        self.log(user_id, target_type, target_id, "commented", {"comment_id": c.id})
        return c

    def list_comments(self, target_type: str, target_id: int) -> list[IfComment]:
        return list(self.db.scalars(
            select(IfComment).where(and_(
                IfComment.target_type == target_type,
                IfComment.target_id == target_id,
            )).order_by(IfComment.created_at.desc())
        ))

    def resolve_comment(self, user_id: int, comment_id: int) -> IfComment:
        c = self.db.get(IfComment, comment_id)
        if c is None:
            raise ValueError("comment not found")
        c.resolved = True
        self.db.commit(); self.db.refresh(c)
        self.log(user_id, c.target_type, c.target_id, "comment_resolved", {"comment_id": c.id})
        return c

    # ---------- Approval workflow ----------
    def start_workflow(self, target_type: str, target_id: int,
                       steps: list[Role]) -> list[IfApproval]:
        out = []
        for i, role in enumerate(steps, start=1):
            a = IfApproval(target_type=target_type, target_id=target_id,
                           step_no=i, role_required=role,
                           state=ApprovalState.PENDING)
            self.db.add(a); out.append(a)
        self.db.commit()
        return out

    def decide(self, user_id: int, approval_id: int,
               approve: bool, note: Optional[str] = None) -> IfApproval:
        a = self.db.get(IfApproval, approval_id)
        if a is None:
            raise ValueError("approval not found")
        a.state = ApprovalState.APPROVED if approve else ApprovalState.REJECTED
        a.approver_user_id = user_id
        a.decided_at = datetime.now(timezone.utc)
        a.note = note
        self.db.commit(); self.db.refresh(a)
        self.log(user_id, a.target_type, a.target_id,
                 "approved" if approve else "rejected", {"approval_id": a.id})
        return a

    def workflow_state(self, target_type: str, target_id: int) -> dict:
        rows = list(self.db.scalars(
            select(IfApproval).where(and_(
                IfApproval.target_type == target_type,
                IfApproval.target_id == target_id,
            )).order_by(IfApproval.step_no.asc())
        ))
        states = [r.state.value for r in rows]
        overall = "approved" if rows and all(s == "approved" for s in states) else (
            "rejected" if "rejected" in states else "pending"
        )
        return {
            "overall": overall,
            "steps": [{"step_no": r.step_no, "role": r.role_required.value,
                       "state": r.state.value, "approver_user_id": r.approver_user_id,
                       "decided_at": r.decided_at, "note": r.note} for r in rows],
        }

    # ---------- Activity log ----------
    def log(self, user_id: int, target_type: str, target_id: int,
            action: str, payload: Optional[dict] = None) -> IfActivityLog:
        row = IfActivityLog(user_id=user_id, target_type=target_type,
                            target_id=target_id, action=action, payload=payload or {})
        self.db.add(row); self.db.commit(); self.db.refresh(row)
        return row

    def feed_for_user(self, user_id: int, limit: int = 50) -> list[IfActivityLog]:
        return list(self.db.scalars(
            select(IfActivityLog).where(IfActivityLog.user_id == user_id)
            .order_by(IfActivityLog.created_at.desc()).limit(limit)
        ))
