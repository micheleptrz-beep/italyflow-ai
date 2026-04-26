"""
ItalyFlow AI - Labels router (Section 2.1). ASCII only.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from app.services.label_editor_service import LabelEditorService
from app.services.label_render_service import LabelRenderService
from app.services.label_pdf_service import LabelPdfService

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/labels", tags=["labels"])
api = APIRouter(prefix="/api/v1/labels", tags=["labels-api"])


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
@router.get("/editor/{label_id}", response_class=HTMLResponse)
def page_editor(label_id: int, request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    svc = LabelEditorService(db)
    v = svc.get_current(label_id)
    if v is None:
        raise HTTPException(404, "label/version not found")
    return templates.TemplateResponse("labels/editor.html", {
        "request": request, "label_id": label_id, "version": v, "active": "labels",
    })


# ---------- API ----------
class TemplateOut(BaseModel):
    id: int
    market: str
    code: str
    name: str
    width_mm: int
    height_mm: int


class CreateFromTemplateIn(BaseModel):
    template_id: int
    product_id: int
    name: str


class SaveVersionIn(BaseModel):
    layers: list[dict]
    note: Optional[str] = None
    compliance_snapshot: Optional[dict] = None


@api.get("/templates", response_model=list[TemplateOut])
def list_templates(market: Optional[str] = None, db: Session = Depends(get_db)):
    rows = LabelEditorService(db).list_templates(market)
    return [TemplateOut(id=r.id, market=r.market, code=r.code, name=r.name,
                        width_mm=r.width_mm, height_mm=r.height_mm) for r in rows]


@api.post("/from-template")
def create_from_template(body: CreateFromTemplateIn, request: Request,
                         db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    label = LabelEditorService(db).create_from_template(
        user_id=uid, product_id=body.product_id, template_id=body.template_id, name=body.name)
    return {"label_id": label.id, "current_version_id": label.current_version_id}


@api.post("/{label_id}/versions")
def save_version(label_id: int, body: SaveVersionIn, request: Request,
                 db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    v = LabelEditorService(db).save_version(
        user_id=uid, label_id=label_id, layers=body.layers,
        compliance_snapshot=body.compliance_snapshot, note=body.note,
    )
    return {"version_id": v.id, "version_no": v.version_no}


@api.get("/{label_id}/diff")
def diff_versions(label_id: int, a: int, b: int, db: Session = Depends(get_db)):
    svc = LabelEditorService(db)
    va = svc.get_version(label_id, a)
    vb = svc.get_version(label_id, b)
    if not va or not vb:
        raise HTTPException(404, "version(s) not found")
    return svc.diff_layers(va.layers or [], vb.layers or [])


@api.get("/{label_id}/preview.png")
def preview_png(label_id: int, version_no: Optional[int] = None,
                db: Session = Depends(get_db)):
    svc = LabelEditorService(db)
    v = svc.get_version(label_id, version_no) if version_no else svc.get_current(label_id)
    if v is None:
        raise HTTPException(404, "version not found")
    label = svc.db.get  # type: ignore
    lbl = svc.db.get(__import__("app.models.labels", fromlist=["IfLabel"]).IfLabel, label_id)
    png = LabelRenderService.render_png(lbl.width_mm, lbl.height_mm, lbl.dpi, v.layers or [])
    return Response(content=png, media_type="image/png")


@api.get("/{label_id}/export.pdf")
def export_pdf(label_id: int, version_no: Optional[int] = None,
               db: Session = Depends(get_db)):
    svc = LabelEditorService(db)
    v = svc.get_version(label_id, version_no) if version_no else svc.get_current(label_id)
    if v is None:
        raise HTTPException(404, "version not found")
    from app.models.labels import IfLabel
    lbl = svc.db.get(IfLabel, label_id)
    pdf = LabelPdfService.render_pdf(lbl.width_mm, lbl.height_mm, lbl.bleed_mm, v.layers or [])
    headers = {"Content-Disposition": f'attachment; filename="label_{label_id}_v{v.version_no}.pdf"'}
    return Response(content=pdf, media_type="application/pdf", headers=headers)
