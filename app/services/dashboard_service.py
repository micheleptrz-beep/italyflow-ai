"""
ItalyFlow AI - Dashboard service (P0). ASCII only.
Pure-Python aggregations on top of SQLAlchemy. Cached KPI with TTL.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.dashboard import (
    Audit,
    AuditStatus,
    KpiCache,
    MarketCode,
    Product,
)

KPI_TTL_SECONDS = 60
TRADITIONAL_CONSULTANT_COST_PER_AUDIT_EUR = 350.0  # benchmark used for ROI


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- KPI ----------
    def get_kpi(self, user_id: int, force: bool = False) -> KpiCache:
        cache = self.db.get(KpiCache, user_id)
        now = datetime.now(timezone.utc)
        if cache and not force:
            age = (now - cache.refreshed_at).total_seconds()
            if age < KPI_TTL_SECONDS:
                return cache
        return self.refresh_kpi(user_id)

    def refresh_kpi(self, user_id: int) -> KpiCache:
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)

        total = self.db.scalar(
            select(func.count(Audit.id)).where(Audit.user_id == user_id)
        ) or 0

        last_7d = self.db.scalar(
            select(func.count(Audit.id)).where(
                and_(Audit.user_id == user_id, Audit.created_at >= seven_days_ago)
            )
        ) or 0

        compliant = self.db.scalar(
            select(func.count(Audit.id)).where(
                and_(
                    Audit.user_id == user_id,
                    Audit.status == AuditStatus.COMPLIANT,
                )
            )
        ) or 0
        compliance_rate = (compliant / total) if total else 0.0

        active_markets = self.db.scalar(
            select(func.count(func.distinct(Audit.market))).where(Audit.user_id == user_id)
        ) or 0

        savings = float(total) * TRADITIONAL_CONSULTANT_COST_PER_AUDIT_EUR

        # sparkline last 7 days
        rows = self.db.execute(
            select(
                func.date(Audit.created_at).label("d"),
                func.count(Audit.id),
            )
            .where(and_(Audit.user_id == user_id, Audit.created_at >= seven_days_ago))
            .group_by("d")
        ).all()
        per_day = {str(r[0]): int(r[1]) for r in rows}
        spark = []
        for i in range(6, -1, -1):
            d = (now - timedelta(days=i)).date().isoformat()
            spark.append(per_day.get(d, 0))

        cache = self.db.get(KpiCache, user_id)
        if cache is None:
            cache = KpiCache(user_id=user_id)
            self.db.add(cache)
        cache.audits_total = int(total)
        cache.audits_last_7d = int(last_7d)
        cache.compliance_rate = float(compliance_rate)
        cache.active_markets = int(active_markets)
        cache.estimated_savings_eur = float(savings)
        cache.sparkline_7d = spark
        cache.refreshed_at = now
        self.db.commit()
        self.db.refresh(cache)
        return cache

    # ---------- Timeline ----------
    def list_audits(
        self,
        user_id: int,
        market: Optional[str] = None,
        product_id: Optional[int] = None,
        status: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        stmt = (
            select(Audit, Product.name)
            .join(Product, Product.id == Audit.product_id)
            .where(Audit.user_id == user_id)
            .order_by(Audit.created_at.desc())
        )
        if market:
            stmt = stmt.where(Audit.market == MarketCode(market))
        if product_id:
            stmt = stmt.where(Audit.product_id == product_id)
        if status:
            stmt = stmt.where(Audit.status == AuditStatus(status))
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(func.lower(Product.name).like(like))
        stmt = stmt.limit(limit).offset(offset)
        out: list[dict] = []
        for audit, product_name in self.db.execute(stmt).all():
            out.append(
                {
                    "id": audit.id,
                    "product_id": audit.product_id,
                    "product_name": product_name,
                    "market": audit.market.value,
                    "status": audit.status.value,
                    "score": audit.score,
                    "missing_fields": audit.missing_fields or [],
                    "warnings": audit.warnings or [],
                    "duration_ms": audit.duration_ms,
                    "created_at": audit.created_at,
                }
            )
        return out

    # ---------- Catalog ----------
    def list_products(self, user_id: int) -> list[Product]:
        return list(
            self.db.scalars(
                select(Product).where(Product.user_id == user_id).order_by(Product.created_at.desc())
            )
        )

    # ---------- Heatmap ----------
    def heatmap(self, user_id: int) -> dict:
        products = self.list_products(user_id)
        markets = [m.value for m in MarketCode]
        latest_per_pair: dict[tuple[int, str], Audit] = {}
        rows = self.db.execute(
            select(Audit)
            .where(Audit.user_id == user_id)
            .order_by(Audit.created_at.desc())
        ).scalars()
        for a in rows:
            key = (a.product_id, a.market.value)
            if key not in latest_per_pair:
                latest_per_pair[key] = a
        cells = []
        for p in products:
            for m in markets:
                a = latest_per_pair.get((p.id, m))
                cells.append(
                    {
                        "product_id": p.id,
                        "product_name": p.name,
                        "market": m,
                        "status": a.status.value if a else "missing",
                        "score": float(a.score) if a else 0.0,
                        "missing_fields": (a.missing_fields or []) if a else [],
                    }
                )
        return {
            "products": [p.name for p in products],
            "markets": markets,
            "cells": cells,
        }

    # ---------- Wizard ----------
    def wizard_create(
        self,
        user_id: int,
        product_name: str,
        category: str,
        region: Optional[str],
        label_text: str,
        markets: Iterable[str],
        compliance_runner,  # callable(label_text, market) -> dict
    ) -> dict:
        product = Product(
            user_id=user_id,
            name=product_name,
            category=category,
            region=region,
        )
        self.db.add(product)
        self.db.flush()

        audit_ids: list[int] = []
        scores: list[float] = []
        by_market: dict[str, dict] = {}

        for m in markets:
            result = compliance_runner(label_text, m)  # MUST return dict with score, status, missing, warnings
            audit = Audit(
                user_id=user_id,
                product_id=product.id,
                market=MarketCode(m),
                status=AuditStatus(result.get("status", "pending")),
                score=float(result.get("score", 0.0)),
                missing_fields=result.get("missing", []),
                warnings=result.get("warnings", []),
                raw_payload=result.get("raw", {}),
                duration_ms=int(result.get("duration_ms", 0)),
            )
            self.db.add(audit)
            self.db.flush()
            audit_ids.append(audit.id)
            scores.append(audit.score)
            by_market[m] = {
                "audit_id": audit.id,
                "status": audit.status.value,
                "score": audit.score,
                "missing": audit.missing_fields,
            }
        self.db.commit()
        self.refresh_kpi(user_id)
        overall = sum(scores) / len(scores) if scores else 0.0
        return {"audit_ids": audit_ids, "overall_score": overall, "by_market": by_market}
