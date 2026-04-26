"""
ItalyFlow AI - Label editor service: CRUD, versioning, layer diff. ASCII only.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.labels import IfLabel, IfLabelTemplate, IfLabelVersion, LabelStatus


class LabelEditorService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- Templates ----------
    def list_templates(self, market: Optional[str] = None) -> list[IfLabelTemplate]:
        stmt = select(IfLabelTemplate)
        if market:
            stmt = stmt.where(IfLabelTemplate.market == market)
        return list(self.db.scalars(stmt))

    def create_from_template(self, user_id: int, product_id: int, template_id: int,
                             name: str) -> IfLabel:
        tpl = self.db.get(IfLabelTemplate, template_id)
        if tpl is None:
            raise ValueError("template not found")
        label = IfLabel(
            user_id=user_id, product_id=product_id, name=name,
            market=tpl.market, width_mm=tpl.width_mm, height_mm=tpl.height_mm,
            status=LabelStatus.DRAFT,
        )
        self.db.add(label)
        self.db.flush()
        v = IfLabelVersion(
            label_id=label.id, version_no=1, author_user_id=user_id,
            layers=tpl.layers or [], note="from template",
        )
        self.db.add(v)
        self.db.flush()
        label.current_version_id = v.id
        self.db.commit()
        self.db.refresh(label)
        return label

    # ---------- Versions ----------
    def save_version(self, user_id: int, label_id: int, layers: list[dict],
                     compliance_snapshot: Optional[dict] = None,
                     note: Optional[str] = None) -> IfLabelVersion:
        label = self.db.get(IfLabel, label_id)
        if label is None or label.user_id != user_id:
            raise ValueError("label not found")
        next_no = (
            self.db.scalar(
                select(IfLabelVersion.version_no)
                .where(IfLabelVersion.label_id == label_id)
                .order_by(IfLabelVersion.version_no.desc())
            ) or 0
        ) + 1
        v = IfLabelVersion(
            label_id=label_id, version_no=next_no, author_user_id=user_id,
            layers=layers, compliance_snapshot=compliance_snapshot or {}, note=note,
        )
        self.db.add(v)
        self.db.flush()
        label.current_version_id = v.id
        label.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(v)
        return v

    def get_current(self, label_id: int) -> Optional[IfLabelVersion]:
        label = self.db.get(IfLabel, label_id)
        if label is None or label.current_version_id is None:
            return None
        return self.db.get(IfLabelVersion, label.current_version_id)

    def get_version(self, label_id: int, version_no: int) -> Optional[IfLabelVersion]:
        return self.db.scalar(
            select(IfLabelVersion).where(
                IfLabelVersion.label_id == label_id,
                IfLabelVersion.version_no == version_no,
            )
        )

    # ---------- Diff ----------
    @staticmethod
    def diff_layers(a: list[dict], b: list[dict]) -> dict:
        """Returns added/removed/modified layer ids with field-level changes."""
        a_idx = {l.get("id"): l for l in a}
        b_idx = {l.get("id"): l for l in b}
        added = [b_idx[k] for k in b_idx if k not in a_idx]
        removed = [a_idx[k] for k in a_idx if k not in b_idx]
        modified = []
        for k in a_idx.keys() & b_idx.keys():
            la, lb = a_idx[k], b_idx[k]
            field_changes = {}
            for f in set(la.keys()) | set(lb.keys()):
                if la.get(f) != lb.get(f):
                    field_changes[f] = {"from": la.get(f), "to": lb.get(f)}
            if field_changes:
                modified.append({"id": k, "changes": field_changes})
        return {"added": added, "removed": removed, "modified": modified}
