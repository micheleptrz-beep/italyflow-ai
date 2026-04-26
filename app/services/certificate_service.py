"""
ItalyFlow AI - Certificate manager service (Section 2.2). ASCII only.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.compliance import CertificateType, IfCertificate

CERT_DIR = Path("static/certificates")


class CertificateService:
    def __init__(self, db: Session):
        self.db = db
        CERT_DIR.mkdir(parents=True, exist_ok=True)

    def upload(self, user_id: int, type_: str, filename: str, content: bytes,
               product_id: Optional[int] = None, issuer: Optional[str] = None,
               serial: Optional[str] = None,
               issued_at: Optional[datetime] = None,
               expires_at: Optional[datetime] = None,
               notes: Optional[str] = None) -> IfCertificate:
        safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")
        out_dir = CERT_DIR / str(user_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / safe_name
        out_path.write_bytes(content)
        cert = IfCertificate(
            user_id=user_id, product_id=product_id,
            type=CertificateType(type_), issuer=issuer, serial=serial,
            file_path=str(out_path), issued_at=issued_at, expires_at=expires_at,
            notes=notes,
        )
        self.db.add(cert); self.db.commit(); self.db.refresh(cert)
        return cert

    def list_for_user(self, user_id: int) -> list[IfCertificate]:
        return list(self.db.scalars(
            select(IfCertificate).where(IfCertificate.user_id == user_id)
            .order_by(IfCertificate.expires_at.asc().nulls_last())
        ))

    def expiring_soon(self, user_id: int, days: int = 30) -> list[IfCertificate]:
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(days=days)
        return list(self.db.scalars(
            select(IfCertificate).where(and_(
                IfCertificate.user_id == user_id,
                IfCertificate.expires_at.is_not(None),
                IfCertificate.expires_at <= deadline,
                IfCertificate.expires_at >= now,
            ))
        ))
