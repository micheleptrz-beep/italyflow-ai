"""
ItalyFlow AI - Compliance hub service (Section 2.2). ASCII only.
Computes global score per product, gap analysis per market, and aggregates feed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.compliance import (
    IfComplianceScoreCache,
    IfRegulatoryChange,
)
from app.models.dashboard import Audit, AuditStatus, MarketCode, Product

# Required field set per market (can be moved to config or JSON).
REQUIRED_FIELDS = {
    "US_FDA": ["product_name", "ingredients", "allergens", "net_weight",
               "nutrition_facts", "manufacturer", "country_of_origin"],
    "CN_GB7718": ["product_name", "ingredients", "net_weight", "manufacturer",
                  "production_date", "shelf_life", "storage", "standard_code"],
    "CA_CFIA": ["product_name", "ingredients", "allergens", "net_weight",
                "nutrition_facts", "bilingual_en_fr", "country_of_origin"],
    "JP_FLA": ["product_name", "ingredients", "allergens", "net_weight",
               "nutrition_facts", "best_before", "manufacturer", "origin"],
    "EU_FIR2014": ["product_name", "ingredients", "allergens", "net_weight",
                   "nutrition_declaration", "best_before", "operator"],
    "UK_FIR": ["product_name", "ingredients", "allergens", "net_weight",
               "nutrition_declaration", "best_before", "operator", "uk_address"],
    "AE_ESMA": ["product_name", "ingredients", "allergens", "net_weight",
                "production_date", "expiry_date", "manufacturer", "halal_optional"],
}


class ComplianceHubService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- Global score ----------
    def compute_score(self, user_id: int, product_id: int) -> IfComplianceScoreCache:
        markets = [m.value for m in MarketCode]
        by_market: dict[str, float] = {}
        gaps: dict[str, list[str]] = {}
        for m in markets:
            latest = self.db.scalar(
                select(Audit).where(
                    and_(Audit.user_id == user_id,
                         Audit.product_id == product_id,
                         Audit.market == MarketCode(m))
                ).order_by(Audit.created_at.desc())
            )
            if latest is None:
                by_market[m] = 0.0
                gaps[m] = REQUIRED_FIELDS.get(m, [])
            else:
                by_market[m] = float(latest.score)
                gaps[m] = list(latest.missing_fields or [])
        global_score = sum(by_market.values()) / max(1, len(by_market))

        row = self.db.get(IfComplianceScoreCache, product_id)
        if row is None:
            row = IfComplianceScoreCache(product_id=product_id, user_id=user_id)
            self.db.add(row)
        row.user_id = user_id
        row.global_score = global_score
        row.by_market = by_market
        row.gaps = gaps
        row.refreshed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(row)
        return row

    def gap_analysis(self, user_id: int, product_id: int, market: str) -> dict:
        latest = self.db.scalar(
            select(Audit).where(
                and_(Audit.user_id == user_id,
                     Audit.product_id == product_id,
                     Audit.market == MarketCode(market))
            ).order_by(Audit.created_at.desc())
        )
        required = REQUIRED_FIELDS.get(market, [])
        if latest is None:
            return {"market": market, "missing": required, "score": 0.0,
                    "message": f"To sell this product in {market}, you need: " + ", ".join(required)}
        missing = list(latest.missing_fields or [])
        return {
            "market": market, "missing": missing, "score": float(latest.score),
            "message": (f"To improve compliance in {market}, address {len(missing)} gap(s): "
                        + ", ".join(missing)) if missing else f"Fully compliant in {market}.",
        }

    # ---------- Feed ----------
    def list_changes(self, market: Optional[str] = None,
                     since_days: int = 90, limit: int = 50) -> list[IfRegulatoryChange]:
        since = datetime.now(timezone.utc) - timedelta(days=since_days)
        stmt = select(IfRegulatoryChange).where(IfRegulatoryChange.detected_at >= since)
        if market:
            stmt = stmt.where(IfRegulatoryChange.market == market)
        stmt = stmt.order_by(IfRegulatoryChange.detected_at.desc()).limit(limit)
        return list(self.db.scalars(stmt))

    def impact_for_user(self, user_id: int, change_id: int) -> dict:
        change = self.db.get(IfRegulatoryChange, change_id)
        if change is None:
            return {}
        affected = []
        cats = set(change.affected_categories or [])
        products = list(self.db.scalars(select(Product).where(Product.user_id == user_id)))
        for p in products:
            if not cats or p.category in cats:
                affected.append({"product_id": p.id, "name": p.name, "category": p.category})
        return {
            "change": {
                "id": change.id, "title": change.title, "market": change.market,
                "severity": change.severity.value, "url": change.url,
            },
            "affected_products": affected,
        }
