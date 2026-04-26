"""
ItalyFlow AI - Home router (unified landing). ASCII only.
Exports: router (HTML pages at /).
Provides:
  GET /            -> unified homepage with hero, KPI, feature grid
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from app.services.dashboard_service import DashboardService

# Visuals are optional - degrade gracefully if module not present yet
try:
    from app.services.visuals_service import HeroContext, VisualsService
    _VISUALS_OK = True
except Exception:
    _VISUALS_OK = False

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["home"])


def _user_id(request: Request) -> int:
    if hasattr(request, "session"):
        uid = request.session.get("user_id")
        if uid is not None:
            return int(uid)
    hv = request.headers.get("X-User-Id")
    if hv and hv.isdigit():
        return int(hv)
    return 1  # dev fallback


def _hero(db: Session, user_id: int, page: str = "dashboard") -> Optional[dict]:
    if not _VISUALS_OK:
        return None
    try:
        return VisualsService(db).hero_payload(HeroContext(user_id=user_id, page=page))
    except Exception:
        return None


@router.get("/", response_class=HTMLResponse)
def homepage(request: Request, db: Session = Depends(get_db)):
    uid = _user_id(request)
    kpi = None
    try:
        kpi = DashboardService(db).get_kpi(uid)
    except Exception:
        pass
    hero = _hero(db, uid, page="dashboard")
    return templates.TemplateResponse("italyflow_home.html", {
        "request": request, "active": "home", "kpi": kpi, "hero": hero,
    })
