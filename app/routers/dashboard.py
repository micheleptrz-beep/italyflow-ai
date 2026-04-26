"""
ItalyFlow AI - Dashboard router (P0). ASCII only.
HTML (Jinja2 + HTMX) + JSON API endpoints.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db  # existing dependency in database.py
from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import (
    HeatmapOut,
    KpiCardOut,
    WizardStep1,
    WizardStep2,
    WizardResultOut,
)

# Templates dir lives at <repo>/app/templates
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
api = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard-api"])


# --- AUTH STUB --------------------------------------------------------------
# Replace with the real dependency from your auth module (e.g. get_current_user).
def get_current_user_id(request: Request) -> int:
    user_id = request.session.get("user_id") if hasattr(request, "session") else None
    if user_id is None:
        # Dev fallback: header X-User-Id; in prod raise 401.
        hv = request.headers.get("X-User-Id")
        if hv and hv.isdigit():
            return int(hv)
        raise HTTPException(status_code=401, detail="Not authenticated")
    return int(user_id)


# --- COMPLIANCE RUNNER WIRE -------------------------------------------------
def _compliance_runner_factory():
    """
    Returns a callable(label_text, market) -> dict with keys:
      status, score, missing, warnings, raw, duration_ms
    Wires to your existing engine in main.py / services. Falls back to a stub
    so the dashboard works end-to-end even before integration.
    """
    try:
        from app.services.compliance import run_compliance  # type: ignore
        return run_compliance
    except Exception:
        def _stub(label_text: str, market: str) -> dict:
            text = (label_text or "").lower()
            missing = []
            for kw in ("ingredients", "allergens", "net weight", "best before"):
                if kw not in text:
                    missing.append(kw)
            score = max(0.0, 100.0 - 15.0 * len(missing))
            status = "compliant" if score >= 90 else ("warning" if score >= 60 else "non_compliant")
            return {
                "status": status,
                "score": score,
                "missing": missing,
                "warnings": [],
                "raw": {"market": market, "len": len(label_text)},
                "duration_ms": 42,
            }
        return _stub


COMPLIANCE_RUNNER = _compliance_runner_factory()


# ============================ HTML PAGES ====================================
@router.get("/", response_class=HTMLResponse)
def page_home(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    svc = DashboardService(db)
    kpi = svc.get_kpi(user_id)
    return templates.TemplateResponse(
        "dashboard/home.html",
        {"request": request, "kpi": kpi, "active": "home"},
    )


@router.get("/timeline", response_class=HTMLResponse)
def page_timeline(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    svc = DashboardService(db)
    audits = svc.list_audits(user_id, limit=100)
    return templates.TemplateResponse(
        "dashboard/timeline.html",
        {"request": request, "audits": audits, "active": "timeline"},
    )


@router.get("/catalog", response_class=HTMLResponse)
def page_catalog(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    svc = DashboardService(db)
    products = svc.list_products(user_id)
    return templates.TemplateResponse(
        "dashboard/catalog.html",
        {"request": request, "products": products, "active": "catalog"},
    )


@router.get("/heatmap", response_class=HTMLResponse)
def page_heatmap(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    svc = DashboardService(db)
    data = svc.heatmap(user_id)
    return templates.TemplateResponse(
        "dashboard/heatmap.html",
        {"request": request, "data": data, "active": "heatmap"},
    )


@router.get("/wizard", response_class=HTMLResponse)
def page_wizard(request: Request):
    return templates.TemplateResponse(
        "dashboard/wizard.html",
        {"request": request, "active": "wizard"},
    )


# ============================ JSON API ======================================
@api.get("/kpi", response_model=KpiCardOut)
def api_kpi(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    kpi = DashboardService(db).get_kpi(user_id)
    return KpiCardOut(
        audits_total=kpi.audits_total,
        audits_last_7d=kpi.audits_last_7d,
        compliance_rate=kpi.compliance_rate,
        active_markets=kpi.active_markets,
        estimated_savings_eur=kpi.estimated_savings_eur,
        sparkline_7d=kpi.sparkline_7d or [],
        refreshed_at=kpi.refreshed_at,
    )


@api.get("/audits")
def api_audits(
    request: Request,
    market: Optional[str] = None,
    product_id: Optional[int] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    user_id = get_current_user_id(request)
    rows = DashboardService(db).list_audits(
        user_id, market=market, product_id=product_id, status=status, q=q, limit=limit, offset=offset
    )
    return JSONResponse(content={"items": rows, "count": len(rows)})


@api.get("/heatmap", response_model=HeatmapOut)
def api_heatmap(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    return DashboardService(db).heatmap(user_id)


@api.post("/wizard", response_model=WizardResultOut)
def api_wizard(
    request: Request,
    step1: WizardStep1,
    step2: WizardStep2,
    db: Session = Depends(get_db),
):
    user_id = get_current_user_id(request)
    result = DashboardService(db).wizard_create(
        user_id=user_id,
        product_name=step1.product_name,
        category=step1.category,
        region=step1.region,
        label_text=step1.label_text,
        markets=step2.markets,
        compliance_runner=COMPLIANCE_RUNNER,
    )
    return WizardResultOut(**result)
