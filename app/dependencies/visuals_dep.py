"""
ItalyFlow AI - Visuals dependency. ASCII only.
Provides a callable that any route can include with Depends() to obtain hero payload.
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from app.services.visuals_service import HeroContext, VisualsService


def hero_for(page: str):
    def _dep(
        request: Request,
        region: Optional[str] = None,
        product_category: Optional[str] = None,
        db: Session = Depends(get_db),
    ) -> dict:
        uid = None
        if hasattr(request, "session"):
            uid = request.session.get("user_id")
        if uid is None:
            hv = request.headers.get("X-User-Id")
            if hv and hv.isdigit():
                uid = int(hv)
        ctx = HeroContext(
            user_id=int(uid) if uid is not None else None,
            page=page,
            region=region,
            product_category=product_category,
        )
        return VisualsService(db).hero_payload(ctx)
    return _dep
