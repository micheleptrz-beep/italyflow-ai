"""
ItalyFlow AI - Translation router (Section 2.3). ASCII only.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from app.models.i18n import IfGlossaryTerm
from app.services.translation_service import TranslationService

api = APIRouter(prefix="/api/v1/i18n", tags=["i18n"])


def get_current_user_id(request: Request) -> int:
    if hasattr(request, "session"):
        uid = request.session.get("user_id")
        if uid is not None:
            return int(uid)
    hv = request.headers.get("X-User-Id")
    if hv and hv.isdigit():
        return int(hv)
    raise HTTPException(status_code=401, detail="Not authenticated")


class TranslateIn(BaseModel):
    text: str = Field(min_length=1)
    src: str = "it"
    tgt: str = "en"
    back_check: bool = True


class GlossaryIn(BaseModel):
    src: str = "it"
    tgt: str = "en"
    term_src: str
    term_tgt: str
    notes: str | None = None


@api.post("/translate")
def translate(body: TranslateIn, request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    return TranslationService(db).translate(uid, body.text, body.src, body.tgt,
                                            back_check=body.back_check)


@api.post("/glossary")
def add_term(body: GlossaryIn, request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    row = db.query(IfGlossaryTerm).filter_by(
        user_id=uid, src_lang=body.src, tgt_lang=body.tgt, term_src=body.term_src
    ).one_or_none()
    if row is None:
        row = IfGlossaryTerm(user_id=uid, src_lang=body.src, tgt_lang=body.tgt,
                             term_src=body.term_src, term_tgt=body.term_tgt,
                             notes=body.notes)
        db.add(row)
    else:
        row.term_tgt = body.term_tgt
        row.notes = body.notes
    db.commit()
    return {"id": row.id, "term_src": row.term_src, "term_tgt": row.term_tgt}


@api.get("/glossary")
def list_terms(request: Request, db: Session = Depends(get_db)):
    uid = get_current_user_id(request)
    rows = db.query(IfGlossaryTerm).filter_by(user_id=uid).all()
    return [{"id": r.id, "src": r.src_lang, "tgt": r.tgt_lang,
             "term_src": r.term_src, "term_tgt": r.term_tgt, "notes": r.notes}
            for r in rows]
