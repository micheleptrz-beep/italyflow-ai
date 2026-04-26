
"""
ItalyFlow AI - Translation models (Section 2.3). ASCII only.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint,
)

from database import Base


class IfTranslation(Base):
    __tablename__ = "if_translations"
    __table_args__ = (
        UniqueConstraint("user_id", "src_lang", "tgt_lang", "src_hash",
                         name="uq_if_translations_unique"),
        Index("ix_if_translations_user_tgt", "user_id", "tgt_lang"),
        {"extend_existing": True},
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    src_lang = Column(String(8), nullable=False)
    tgt_lang = Column(String(8), nullable=False)
    src_hash = Column(String(64), nullable=False, index=True)
    src_text = Column(Text, nullable=False)
    tgt_text = Column(Text, nullable=False)
    back_translation = Column(Text, nullable=True)
    quality_score = Column(Integer, default=0)            # 0-100
    glossary_used = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class IfGlossaryTerm(Base):
    __tablename__ = "if_glossary_terms"
    __table_args__ = (
        UniqueConstraint("user_id", "src_lang", "tgt_lang", "term_src",
                         name="uq_if_glossary_unique"),
        {"extend_existing": True},
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    src_lang = Column(String(8), nullable=False)
    tgt_lang = Column(String(8), nullable=False)
    term_src = Column(String(200), nullable=False)
    term_tgt = Column(String(200), nullable=False)
    notes = Column(Text, nullable=True)


Translation = IfTranslation
GlossaryTerm = IfGlossaryTerm
