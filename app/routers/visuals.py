"""
ItalyFlow AI - Visuals router (Section 1.5). ASCII only.
Endpoints:
  GET  /api/v1/visuals/hero            -> selected hero asset payload (JSON)
  GET  /api/v1/visuals/preferences     -> current user visual preferences
  POST /api/v1/visuals/preferences     -> update preferences (theme, dark, accent)
  GET  /api/v1/visuals/                -> list assets (admin/debug)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from app.models.dashboard import UserVisualPreference
from app.models.visuals import IfVisualAsset
from app.services.visuals_service import HeroContext, VisualsService

api = APIRouter(prefix="/api/v1/visuals", tags=["visuals"])


def get_current_user_id(request: Request) -> Optional[int]:
    user_id = None
    if hasattr(request, "session"):
        user_id = request.session.get("user_id")
    if user_id is None:
        hv = request.headers.get("X-User-Id")
        if hv and hv.isdigit():
            user_id = int(hv)
    return int(user_id) if user_id is not None else None


class PrefsIn(BaseModel):
    theme: str = Field(default="classico", pattern="^(classico|moderno|rustico|minimal|lusso)$")
    dark_mode: bool = False
    accent_color: str = Field(default="#0f766e", pattern="^#[0-9a-fA-F]{6}$")


class PrefsOut(PrefsIn):
    pass


@api.get("/hero")
def get_hero(
    request: Request,
    page: str = "dashboard",
    region: Optional[str] = None,
    product_category: Optional[str] = None,
    market: Optional[str] = None,
    db: Session = Depends(get_db),
):
    uid = get_current_user_id(request)
    ctx = HeroContext(
        user_id=uid,
        page=page,
        region=region,
        product_category=product_category,
        market=market,
    )
    payload = VisualsService(db).hero_payload(ctx)
    return payload


@api.get("/preferences", response_model=PrefsOut)
def get_prefs(request: Request, db: Session = Depends(get_db)) -> PrefsOut:
    uid = get_current_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    pref = db.get(UserVisualPreference, uid)
    if pref is None:
        return PrefsOut()
    return PrefsOut(
        theme=pref.theme or "classico",
        dark_mode=bool(pref.dark_mode),
        accent_color=pref.accent_color or "#0f766e",
    )


@api.post("/preferences", response_model=PrefsOut)
def set_prefs(request: Request, body: PrefsIn, db: Session = Depends(get_db)) -> PrefsOut:
    uid = get_current_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    pref = db.get(UserVisualPreference, uid)
    if pref is None:
        pref = UserVisualPreference(user_id=uid)
        db.add(pref)
    pref.theme = body.theme
    pref.dark_mode = body.dark_mode
    pref.accent_color = body.accent_color
    db.commit()
    return PrefsOut(**body.model_dump())


@api.get("/")
def list_assets(db: Session = Depends(get_db), enabled_only: bool = True) -> list[dict]:
    stmt = select(IfVisualAsset)
    if enabled_only:
        stmt = stmt.where(IfVisualAsset.enabled.is_(True))
    rows = list(db.scalars(stmt))
    return [
        {
            "id": r.id,
            "slug": r.slug,
            "title": r.title,
            "category": r.category.value,
            "region": r.region,
            "product_category": r.product_category,
            "season": r.season.value,
            "time_of_day": r.time_of_day.value,
            "mood": r.mood.value,
            "base_path": r.base_path,
            "quality_score": r.quality_score,
            "credit": r.credit,
            "tags": r.tags,
        }
        for r in rows
    ]
