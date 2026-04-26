"""
ItalyFlow AI - Compliance hub router (Section 2.2). ASCII only.
Exports: router (HTML pages), api (JSON endpoints).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from app.services.certificate_service import CertificateService
from app.services.compliance_hub_service import ComplianceHubService
from app.services.regulatory_tracker_service import RegulatoryTrackerService

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/compliance", tags=["compliance"])
api = APIRouter(prefix="/api/v1/compliance", tags=["compliance-api"])


def get_current_user_id(request: Request) -> int:
    if hasattr(request, "session"):
        uid = request.session.get("user_id")
        if uid is not None:
            return int(uid)
    hv = request.headers.get("X-User-Id")
    if hv and hv.isdigit():
        return int(hv)
    raise HTTPException(status_code=401, detail="Not authenticated")


# ---------- HTML ----------
@router.get("/hub", response_class=HTMLResponse)
def page_hub(request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    changes = ComplianceHubService(db).list_changes(limit=20)
    certs = CertificateService(db).list_for_user(uid)
    expiring = CertificateService(db).expiring_soon(uid, days=60)
    return templates.TemplateResponse("compliance/hub.html", {
        "request": request, "active": "compliance",
        "changes": changes, "certs": certs, "expiring": expiring,
    })


# ---------- API ----------
class ComputeIn(BaseModel):
    product_id: int


class CheckIn(BaseModel):
    label_id: Optional[int] = None
    layers: Optional[list[dict]] = None
    text: Optional[str] = None
    market: Optional[str] = None


@api.post("/score")
def compute_score(body: ComputeIn, request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    row = ComplianceHubService(db).compute_score(uid, body.product_id)
    return {
        "product_id": row.product_id,
        "global_score": row.global_score,
        "by_market": row.by_market,
        "gaps": row.gaps,
        "refreshed_at": row.refreshed_at,
    }


@api.get("/gap")
def gap(product_id: int, market: str, request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    return ComplianceHubService(db).gap_analysis(uid, product_id, market)


@api.post("/check")
def check(body: CheckIn, request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    text = body.text or ""
    if body.layers:
        text = " ".join(
            str(l.get("text", "")) for l in body.layers if l.get("type") == "text"
        )
    text = text.lower()
    keywords = (
        "ingredients", "allergens", "net weight", "best before",
        "manufacturer", "origin",
    )
    missing = [k for k in keywords if k not in text]
    score = max(0.0, 100.0 - 12.0 * len(missing))
    status = "compliant" if score >= 90 else ("warning" if score >= 60 else "non_compliant")
    return {"status": status, "score": score, "missing": missing}


@api.get("/changes")
def feed(market: Optional[str] = None, since_days: int = 90, db: Session = Depends(get_db)):
    rows = ComplianceHubService(db).list_changes(market=market, since_days=since_days)
    return [
        {
            "id": r.id, "source": r.source, "market": r.market, "title": r.title,
            "summary": r.summary, "url": r.url, "severity": r.severity.value,
            "categories": r.affected_categories, "fields": r.affected_fields,
            "published_at": r.published_at, "detected_at": r.detected_at,
        }
        for r in rows
    ]


@api.get("/changes/{change_id}/impact")
def impact(change_id: int, request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    return ComplianceHubService(db).impact_for_user(uid, change_id)


@api.post("/refresh")
def refresh(db: Session = Depends(get_db)):
    return RegulatoryTrackerService(db).refresh()


# ---------- Certificates ----------
@api.post("/certificates")
async def upload_cert(
    request: Request,
    type: str = Form(...),
    file: UploadFile = File(...),
    product_id: Optional[int] = Form(None),
    issuer: Optional[str] = Form(None),
    serial: Optional[str] = Form(None),
    expires_at: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    uid = get_current_user_id(request)
    content = await file.read()
    exp = datetime.fromisoformat(expires_at) if expires_at else None
    cert = CertificateService(db).upload(
        user_id=uid, type_=type, filename=file.filename, content=content,
        product_id=product_id, issuer=issuer, serial=serial, expires_at=exp,
    )
    return {"id": cert.id, "type": cert.type.value, "expires_at": cert.expires_at}


@api.get("/certificates")
def list_certs(request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    rows = CertificateService(db).list_for_user(uid)
    return [
        {
            "id": c.id, "type": c.type.value, "issuer": c.issuer, "serial": c.serial,
            "expires_at": c.expires_at, "product_id": c.product_id,
        }
        for c in rows
    ]
