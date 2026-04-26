"""
ItalyFlow AI - Compliance hub & certificate models (Section 2.2). ASCII only.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, Column, DateTime, Enum, Float, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint,
)

from database import Base


class CertificateType(str, enum.Enum):
    BIO = "bio"
    DOP = "dop"
    IGP = "igp"
    HALAL = "halal"
    KOSHER = "kosher"
    GLUTEN_FREE = "gluten_free"
    NON_GMO = "non_gmo"
    OTHER = "other"


class ChangeSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IfCertificate(Base):
    __tablename__ = "if_certificates"
    __table_args__ = (
        Index("ix_if_certificates_user_type", "user_id", "type"),
        {"extend_existing": True},
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("if_products.id", ondelete="SET NULL"), nullable=True)
    type = Column(Enum(CertificateType), nullable=False)
    issuer = Column(String(200), nullable=True)
    serial = Column(String(120), nullable=True)
    file_path = Column(String(400), nullable=True)
    issued_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class IfRegulatoryChange(Base):
    """Detected updates from regulator feeds (FDA, GB7718, CFIA, RASFF, EFSA)."""
    __tablename__ = "if_regulatory_changes"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_if_reg_changes_src_ext"),
        Index("ix_if_reg_changes_market_pub", "market", "published_at"),
        {"extend_existing": True},
    )
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(40), nullable=False)         # fda, cfia, rasff, gb, efsa
    external_id = Column(String(200), nullable=False)
    market = Column(String(40), nullable=False, index=True)
    title = Column(String(400), nullable=False)
    summary = Column(Text, nullable=True)
    url = Column(String(800), nullable=True)
    severity = Column(Enum(ChangeSeverity), default=ChangeSeverity.INFO, nullable=False)
    affected_categories = Column(JSON, default=list)    # ["oil","cheese"]
    affected_fields = Column(JSON, default=list)        # ["allergens","origin"]
    published_at = Column(DateTime, nullable=True)
    detected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class IfComplianceScoreCache(Base):
    __tablename__ = "if_compliance_score_cache"
    __table_args__ = (
        UniqueConstraint("product_id", name="uq_if_compliance_score_product"),
        {"extend_existing": True},
    )
    product_id = Column(Integer, ForeignKey("if_products.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    global_score = Column(Float, default=0.0)
    by_market = Column(JSON, default=dict)              # {"US_FDA": 92.0, ...}
    gaps = Column(JSON, default=dict)                   # {"JP_FLA": ["allergens","origin"]}
    refreshed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Backward-compat
Certificate = IfCertificate
RegulatoryChange = IfRegulatoryChange
ComplianceScoreCache = IfComplianceScoreCache
