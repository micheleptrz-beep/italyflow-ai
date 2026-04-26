"""
ItalyFlow AI - Visual asset selection service (Section 1.5). ASCII only.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.visuals import (
    AssetCategory,
    IfVisualAsset,
    Mood,
    Season,
    TimeOfDay,
)
from app.models.dashboard import UserVisualPreference

BREAKPOINTS = [
    ("mobile", 720),
    ("tablet", 1080),
    ("desktop", 1920),
    ("4k", 3840),
]
DEFAULT_OVERLAY = "rgba(15,23,42,0.55)"


@dataclass
class HeroContext:
    user_id: Optional[int] = None
    page: str = "dashboard"               # login, dashboard, wizard, audit, market, error
    region: Optional[str] = None          # Toscana, Sicilia...
    product_category: Optional[str] = None
    market: Optional[str] = None          # for "Mercati" page
    now_utc: Optional[datetime] = None


def _season_for(dt: datetime) -> Season:
    m = dt.month
    if m in (3, 4, 5):
        return Season.SPRING
    if m in (6, 7, 8):
        return Season.SUMMER
    if m in (9, 10, 11):
        return Season.AUTUMN
    return Season.WINTER


def _time_of_day_for(dt: datetime) -> TimeOfDay:
    h = dt.hour
    if 6 <= h < 11:
        return TimeOfDay.MORNING
    if 11 <= h < 15:
        return TimeOfDay.MIDDAY
    if 15 <= h < 20:
        return TimeOfDay.GOLDEN
    return TimeOfDay.NIGHT


def _category_for_page(page: str) -> AssetCategory:
    return {
        "login": AssetCategory.LANDSCAPE,
        "signup": AssetCategory.LANDSCAPE,
        "dashboard": AssetCategory.PRODUCT,
        "wizard": AssetCategory.CRAFT,
        "audit": AssetCategory.PRODUCT,
        "market": AssetCategory.MARKET,
        "error": AssetCategory.ABSTRACT,
    }.get(page, AssetCategory.LANDSCAPE)


class VisualsService:
    def __init__(self, db: Session):
        self.db = db

    def _user_mood(self, user_id: Optional[int]) -> Mood:
        if not user_id:
            return Mood.CLASSICO
        pref = self.db.get(UserVisualPreference, user_id)
        if not pref:
            return Mood.CLASSICO
        try:
            return Mood(pref.theme)
        except ValueError:
            return Mood.CLASSICO

    def select_hero(self, ctx: HeroContext) -> Optional[IfVisualAsset]:
        now = ctx.now_utc or datetime.now(timezone.utc)
        season = _season_for(now)
        tod = _time_of_day_for(now)
        target_cat = _category_for_page(ctx.page)
        mood = self._user_mood(ctx.user_id)

        candidates = list(
            self.db.scalars(
                select(IfVisualAsset).where(IfVisualAsset.enabled.is_(True))
            )
        )
        if not candidates:
            return None

        def score(a: IfVisualAsset) -> float:
            s = 0.0
            if a.category == target_cat:
                s += 3.0
            if ctx.region and a.region and a.region.lower() == ctx.region.lower():
                s += 4.0
            if ctx.product_category and a.product_category == ctx.product_category:
                s += 3.5
            if a.season in (season, Season.ANY):
                s += 1.5 if a.season == season else 0.4
            if a.time_of_day in (tod, TimeOfDay.ANY):
                s += 1.2 if a.time_of_day == tod else 0.3
            if a.mood == mood:
                s += 1.0
            s += float(a.quality_score or 0.0) * 2.0
            return s

        ranked = sorted(candidates, key=score, reverse=True)
        top = [a for a in ranked if score(a) >= score(ranked[0]) - 0.001]
        if len(top) == 1:
            return top[0]
        # deterministic daily rotation among top-tier
        seed = f"{ctx.user_id or 0}-{now.date().isoformat()}-{ctx.page}"
        h = int(hashlib.sha1(seed.encode("ascii")).hexdigest(), 16)
        return top[h % len(top)]

    def hero_payload(self, ctx: HeroContext) -> dict:
        a = self.select_hero(ctx)
        if a is None:
            return {
                "available": False,
                "fallback_color": "#1f2937",
                "overlay": DEFAULT_OVERLAY,
            }
        srcset = self._build_srcset(a)
        return {
            "available": True,
            "id": a.id,
            "slug": a.slug,
            "title": a.title,
            "credit": a.credit,
            "blurhash": a.blurhash,
            "dominant_color": a.dominant_color,
            "overlay": DEFAULT_OVERLAY,
            "sources": srcset,
            "fallback": f"/static/{a.base_path}/desktop.jpeg",
            "alt": a.title,
        }

    def _build_srcset(self, a: IfVisualAsset) -> list[dict]:
        out = []
        for fmt_key, mime, present in (
            ("avif", "image/avif", a.has_avif),
            ("webp", "image/webp", a.has_webp),
            ("jpeg", "image/jpeg", a.has_jpeg),
        ):
            if not present:
                continue
            entries = []
            for label, w in BREAKPOINTS:
                entries.append(
                    {
                        "url": f"/static/{a.base_path}/{label}.{fmt_key}",
                        "width": w,
                    }
                )
            out.append({"type": mime, "srcset": entries})
        return out
