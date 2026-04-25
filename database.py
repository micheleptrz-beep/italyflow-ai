# -*- coding: utf-8 -*-
"""
ItalyFlow AI -- Database Models v3.1
======================================
Aggiunto: VisualAsset, UserVisualPreference
Mantenuto: tutto v3.0
"""
import uuid
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float, DateTime,
    ForeignKey, Boolean, JSON,
)
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session, relationship

from config import settings


engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


# ============================================================================
# EXISTING MODELS (v2.0)
# ============================================================================

class AuditBatch(Base):
    """Raggruppa piu audit della stessa immagine su mercati diversi."""
    __tablename__ = "audit_batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    filename = Column(String, nullable=False)
    image_data = Column(Text)
    image_hash = Column(String(64), index=True)
    markets_requested = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    audits = relationship("AuditResult", back_populates="batch", lazy="joined")


class AuditResult(Base):
    __tablename__ = "audit_results"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("audit_batches.id"), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    filename = Column(String, nullable=False)
    image_data = Column(Text)
    image_hash = Column(String(64), index=True)
    market = Column(String, nullable=False, index=True)
    compliance_score = Column(Float)
    product_detected = Column(String)
    language_detected = Column(String)
    summary = Column(Text)
    fields_detail = Column(Text)
    critical_issues = Column(Text)
    recommendations = Column(Text)
    result_json = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    batch = relationship("AuditBatch", back_populates="audits")
    product = relationship("Product", back_populates="audits")


# ============================================================================
# MODELS v3.0 -- Dashboard & UX
# ============================================================================

class Product(Base):
    """Catalogo prodotti del produttore."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)
    name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=True)
    subcategory = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    certifications = Column(Text, nullable=True)
    target_markets = Column(Text, nullable=True)
    region = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    audits = relationship("AuditResult", back_populates="product", lazy="dynamic")


class UserProfile(Base):
    """Profilo utente/produttore."""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True)
    company_name = Column(String, nullable=True)
    region = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    onboarding_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    preferences = relationship("DashboardPreference", back_populates="user", uselist=False)
    visual_prefs = relationship("UserVisualPreference", back_populates="user", uselist=False)


class DashboardPreference(Base):
    """Preferenze dashboard per utente."""
    __tablename__ = "dashboard_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False, unique=True)
    theme = Column(String, default="light")
    default_markets = Column(Text, nullable=True)
    kpi_layout = Column(String, default="standard")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("UserProfile", back_populates="preferences")


# ============================================================================
# MODELS v3.1 -- Visual Identity
# ============================================================================

class VisualAsset(Base):
    """Catalogo immagini per sfondi immersivi."""
    __tablename__ = "visual_assets"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True)

    # --- Metadata ---
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    source = Column(String, default="unsplash")  # unsplash, pexels, custom, ai_generated
    source_id = Column(String, nullable=True)  # Unsplash photo ID
    photographer = Column(String, nullable=True)
    license_type = Column(String, default="unsplash")  # unsplash, cc0, custom, royalty_free

    # --- URLs ---
    url_original = Column(String, nullable=False)  # URL base (Unsplash raw)
    url_thumb = Column(String, nullable=True)  # Placeholder basso (blur-up)

    # --- Categorization ---
    category = Column(String, nullable=False, index=True)
    # landscape, product, artisan, market, abstract
    subcategory = Column(String, nullable=True)
    # vigneto, uliveto, caseificio, frantoio, container, etc.

    # --- Matching Dimensions ---
    region = Column(String, nullable=True, index=True)
    # Toscana, Puglia, Sicilia, Campania, Piemonte, Liguria, Emilia-Romagna, generic
    product_type = Column(String, nullable=True, index=True)
    # olio, vino, formaggio, pasta, salumi, conserve, dolci, caffe, generic
    season = Column(String, nullable=True, index=True)
    # primavera, estate, autunno, inverno, all
    time_mood = Column(String, nullable=True)
    # golden_hour, midday, evening, night, all
    mood = Column(String, nullable=True)
    # classico, moderno, rustico, minimal, lusso

    # --- Usage Context ---
    page_context = Column(String, nullable=True, index=True)
    # landing, login, dashboard, audit, onboarding, report, markets, error, loading, empty
    market_context = Column(String, nullable=True)
    # USA, Cina, Giappone, UK, generic (per pagina mercati)

    # --- Quality ---
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    dominant_color = Column(String, nullable=True)  # hex, per placeholder
    quality_score = Column(Float, default=5.0)  # 1-10, curato manualmente

    # --- Status ---
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class UserVisualPreference(Base):
    """Preferenze visive dell'utente."""
    __tablename__ = "user_visual_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"), nullable=False, unique=True)
    visual_mood = Column(String, default="classico")
    # classico, moderno, rustico, minimal, lusso
    preferred_region = Column(String, nullable=True)
    # override regione per immagini
    enable_parallax = Column(Boolean, default=True)
    enable_seasonal = Column(Boolean, default=True)
    enable_time_aware = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("UserProfile", back_populates="visual_prefs")


# ============================================================================
# CREATE ALL TABLES
# ============================================================================
Base.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
