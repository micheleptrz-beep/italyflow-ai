"""
ItalyFlow AI - Label editor models (Section 2.1). ASCII only.
Tables prefixed with 'if_'. ORM classes prefixed with 'If'.
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
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


class LabelStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class IfLabelTemplate(Base):
    """Pre-built starting templates per market (FDA, GB7718, etc.)."""
    __tablename__ = "if_label_templates"
    __table_args__ = (
        UniqueConstraint("market", "code", name="uq_if_label_templates_market_code"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    market = Column(String(40), nullable=False, index=True)   # US_FDA, CN_GB7718...
    code = Column(String(80), nullable=False)                 # nutrition-facts-us, gb7718-standard
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    width_mm = Column(Integer, default=100)
    height_mm = Column(Integer, default=60)
    layers = Column(JSON, default=list)                       # canonical layer JSON
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class IfLabel(Base):
    """A label belonging to a product, with multiple versions."""
    __tablename__ = "if_labels"
    __table_args__ = (
        Index("ix_if_labels_user_product", "user_id", "product_id"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("if_products.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    market = Column(String(40), nullable=False, index=True)
    status = Column(Enum(LabelStatus), default=LabelStatus.DRAFT, nullable=False, index=True)
    width_mm = Column(Integer, default=100)
    height_mm = Column(Integer, default=60)
    bleed_mm = Column(Integer, default=3)
    dpi = Column(Integer, default=300)
    current_version_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    versions = relationship("IfLabelVersion", back_populates="label",
                            cascade="all, delete-orphan", foreign_keys="IfLabelVersion.label_id")


class IfLabelVersion(Base):
    """Immutable snapshots of layer JSON for diff/audit."""
    __tablename__ = "if_label_versions"
    __table_args__ = (
        Index("ix_if_label_versions_label_v", "label_id", "version_no"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    label_id = Column(Integer, ForeignKey("if_labels.id", ondelete="CASCADE"), nullable=False, index=True)
    version_no = Column(Integer, nullable=False)
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    layers = Column(JSON, default=list)
    compliance_snapshot = Column(JSON, default=dict)          # last compliance check at save
    note = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    label = relationship("IfLabel", back_populates="versions", foreign_keys=[label_id])


# Backward-compat aliases
LabelTemplate = IfLabelTemplate
Label = IfLabel
LabelVersion = IfLabelVersion
