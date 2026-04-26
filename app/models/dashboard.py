"""
ItalyFlow AI - Dashboard models (P0).
ASCII-only source. Integrates with the existing Base in database.py.

Tables are namespaced with the "if_" prefix to avoid clashes with legacy
tables on the same MetaData (e.g. an existing "products" table). The Python
class names also use the "If" prefix so SQLAlchemy class registry does not
collide with any legacy "Product" / "Audit" classes already declared on the
same Base.

Backward-compatible aliases (Product, Audit, KpiCache, UserVisualPreference)
are exported at the bottom so existing imports keep working.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from database import Base  # existing declarative Base from database.py


class AuditStatus(str, enum.Enum):
    COMPLIANT = "compliant"
    WARNING = "warning"
    NON_COMPLIANT = "non_compliant"
    PENDING = "pending"
    FAILED = "failed"


class MarketCode(str, enum.Enum):
    US_FDA = "US_FDA"
    CN_GB7718 = "CN_GB7718"
    CA_CFIA = "CA_CFIA"
    JP_FLA = "JP_FLA"
    EU_FIR2014 = "EU_FIR2014"
    UK_FIR = "UK_FIR"
    AE_ESMA = "AE_ESMA"


class IfProduct(Base):
    __tablename__ = "if_products"
    __table_args__ = (
        Index("ix_if_products_user_category", "user_id", "category"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(80), nullable=False, default="generic")
    sku = Column(String(80), nullable=True, index=True)
    region = Column(String(80), nullable=True)
    is_dop = Column(Boolean, default=False)
    is_igp = Column(Boolean, default=False)
    is_bio = Column(Boolean, default=False)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    audits = relationship(
        "IfAudit",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class IfAudit(Base):
    __tablename__ = "if_audits"
    __table_args__ = (
        Index("ix_if_audits_user_created", "user_id", "created_at"),
        Index("ix_if_audits_user_market_status", "user_id", "market", "status"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    product_id = Column(
        Integer,
        ForeignKey("if_products.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    market = Column(Enum(MarketCode), nullable=False)
    status = Column(
        Enum(AuditStatus),
        default=AuditStatus.PENDING,
        nullable=False,
        index=True,
    )
    score = Column(Float, default=0.0)
    missing_fields = Column(JSON, default=list)
    warnings = Column(JSON, default=list)
    raw_payload = Column(JSON, default=dict)
    duration_ms = Column(Integer, default=0)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    product = relationship("IfProduct", back_populates="audits")


class IfKpiCache(Base):
    __tablename__ = "if_kpi_cache"
    __table_args__ = ({"extend_existing": True},)

    user_id = Column(Integer, primary_key=True)
    audits_total = Column(Integer, default=0)
    audits_last_7d = Column(Integer, default=0)
    compliance_rate = Column(Float, default=0.0)
    active_markets = Column(Integer, default=0)
    estimated_savings_eur = Column(Float, default=0.0)
    sparkline_7d = Column(JSON, default=list)
    refreshed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class IfUserVisualPreference(Base):
    """Used by 1.5 (Visual Identity). Created here so dashboard can preload theme."""
    __tablename__ = "if_user_visual_preferences"
    __table_args__ = ({"extend_existing": True},)

    user_id = Column(Integer, primary_key=True)
    theme = Column(String(20), default="classico")
    dark_mode = Column(Boolean, default=False)
    accent_color = Column(String(16), default="#0f766e")
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# Backward-compatible aliases so existing imports keep working.
Product = IfProduct
Audit = IfAudit
KpiCache = IfKpiCache
UserVisualPreference = IfUserVisualPreference
