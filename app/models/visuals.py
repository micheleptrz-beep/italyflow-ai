"""
ItalyFlow AI - Visual Assets models (Section 1.5). ASCII only.
Tables prefixed with 'if_' to avoid clashes with legacy schema.
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
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from database import Base


class AssetCategory(str, enum.Enum):
    LANDSCAPE = "landscape"        # vigneti, uliveti, risaie, terrazzamenti
    PRODUCT = "product"            # parmigiano, vino, olio, mozzarella, prosciutto, tartufo
    CRAFT = "craft"                # mani al lavoro, vendemmia, pasta fresca, apicoltori
    MARKET = "market"              # container export, mercati internazionali
    ABSTRACT = "abstract"          # texture, gradienti, generici


class Season(str, enum.Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"
    ANY = "any"


class TimeOfDay(str, enum.Enum):
    MORNING = "morning"            # 06-11
    MIDDAY = "midday"              # 11-15
    GOLDEN = "golden"              # 15-20
    NIGHT = "night"                # 20-06
    ANY = "any"


class Mood(str, enum.Enum):
    CLASSICO = "classico"
    MODERNO = "moderno"
    RUSTICO = "rustico"
    MINIMAL = "minimal"
    LUSSO = "lusso"


class IfVisualAsset(Base):
    __tablename__ = "if_visual_assets"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_if_visual_assets_slug"),
        Index("ix_if_visual_assets_cat_region", "category", "region"),
        Index("ix_if_visual_assets_season_tod", "season", "time_of_day"),
        {"extend_existing": True},
    )

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(120), nullable=False)               # human-readable id
    title = Column(String(200), nullable=False)
    category = Column(Enum(AssetCategory), nullable=False, index=True)
    region = Column(String(80), nullable=True, index=True)   # Toscana, Sicilia, Puglia...
    product_category = Column(String(80), nullable=True)     # oil, wine, cheese, pasta, generic
    season = Column(Enum(Season), default=Season.ANY, nullable=False)
    time_of_day = Column(Enum(TimeOfDay), default=TimeOfDay.ANY, nullable=False)
    mood = Column(Enum(Mood), default=Mood.CLASSICO, nullable=False)

    # File system layout (served from /static/visuals/{slug}/{breakpoint}.{ext})
    base_path = Column(String(255), nullable=False)          # e.g. "visuals/tuscany-vineyard"
    has_avif = Column(Boolean, default=True)
    has_webp = Column(Boolean, default=True)
    has_jpeg = Column(Boolean, default=True)
    width_master = Column(Integer, default=0)
    height_master = Column(Integer, default=0)
    blurhash = Column(String(64), nullable=True)             # base64 LQIP placeholder
    dominant_color = Column(String(16), default="#1f2937")   # for overlay tuning
    quality_score = Column(Float, default=0.5)               # 0..1 curator rating
    license = Column(String(80), default="unsplash")         # unsplash, pexels, owned, partner
    credit = Column(String(200), nullable=True)              # photographer / source
    tags = Column(JSON, default=list)                        # ["dop","golden-hour","macro"]
    enabled = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# Backward-compat alias (consistent with dashboard models pattern)
VisualAsset = IfVisualAsset
