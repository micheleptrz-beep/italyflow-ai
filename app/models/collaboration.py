"""
ItalyFlow AI - Collaboration models (Section 2.4). ASCII only.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint,
)

from database import Base


class Role(str, enum.Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    AUDITOR = "auditor"


class ApprovalState(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELED = "canceled"


class IfWorkspaceMember(Base):
    __tablename__ = "if_workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_owner_id", "user_id",
                         name="uq_if_ws_members_owner_user"),
        Index("ix_if_ws_members_owner", "workspace_owner_id"),
        {"extend_existing": True},
    )
    id = Column(Integer, primary_key=True)
    workspace_owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(Role), default=Role.VIEWER, nullable=False)
    invited_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class IfComment(Base):
    __tablename__ = "if_comments"
    __table_args__ = (
        Index("ix_if_comments_target", "target_type", "target_id"),
        {"extend_existing": True},
    )
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type = Column(String(40), nullable=False)   # "label", "audit", "product"
    target_id = Column(Integer, nullable=False)
    anchor = Column(JSON, default=dict)                # {"layer_id":"l1","field":"text"}
    body = Column(Text, nullable=False)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class IfApproval(Base):
    __tablename__ = "if_approvals"
    __table_args__ = (
        Index("ix_if_approvals_target", "target_type", "target_id", "step_no"),
        {"extend_existing": True},
    )
    id = Column(Integer, primary_key=True)
    target_type = Column(String(40), nullable=False)
    target_id = Column(Integer, nullable=False)
    step_no = Column(Integer, nullable=False)
    role_required = Column(Enum(Role), default=Role.EDITOR, nullable=False)
    approver_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    state = Column(Enum(ApprovalState), default=ApprovalState.PENDING, nullable=False, index=True)
    decided_at = Column(DateTime, nullable=True)
    note = Column(Text, nullable=True)


class IfActivityLog(Base):
    __tablename__ = "if_activity_log"
    __table_args__ = (
        Index("ix_if_activity_user_time", "user_id", "created_at"),
        {"extend_existing": True},
    )
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_type = Column(String(40), nullable=False)
    target_id = Column(Integer, nullable=False)
    action = Column(String(40), nullable=False)        # created, edited, approved, commented
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


WorkspaceMember = IfWorkspaceMember
Comment = IfComment
Approval = IfApproval
ActivityLog = IfActivityLog
