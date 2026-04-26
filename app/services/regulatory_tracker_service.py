"""
ItalyFlow AI - Regulatory change tracker (Section 2.2). ASCII only.
Pluggable adapters per source. Default 'demo' adapter so the system runs offline.
Run periodic refresh via app/scheduler.py (APScheduler).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.compliance import ChangeSeverity, IfRegulatoryChange


# ---------- Adapters ----------
class BaseAdapter:
    source: str = "base"
    market: str = "ANY"

    def fetch(self) -> Iterable[dict]:
        return []


class DemoFdaAdapter(BaseAdapter):
    source = "fda"
    market = "US_FDA"

    def fetch(self) -> Iterable[dict]:
        return [{
            "external_id": "FDA-IA-2026-001",
            "title": "Updated allergen labeling guidance for sesame",
            "summary": "FDA reiterates sesame as the 9th major allergen for imported products.",
            "url": "https://www.fda.gov/food/food-allergens",
            "severity": "high",
            "affected_categories": ["oil", "pasta", "cheese"],
            "affected_fields": ["allergens"],
            "published_at": datetime(2026, 4, 1, tzinfo=timezone.utc),
        }]


class DemoRasffAdapter(BaseAdapter):
    source = "rasff"
    market = "EU_FIR2014"

    def fetch(self) -> Iterable[dict]:
        return [{
            "external_id": "RASFF-2026-1234",
            "title": "Notification: undeclared milk in pasta product",
            "summary": "Undeclared milk allergen found in batch X of pasta product imported from IT.",
            "url": "https://webgate.ec.europa.eu/rasff-window/",
            "severity": "critical",
            "affected_categories": ["pasta"],
            "affected_fields": ["allergens"],
            "published_at": datetime(2026, 4, 10, tzinfo=timezone.utc),
        }]


DEFAULT_ADAPTERS: list[BaseAdapter] = [DemoFdaAdapter(), DemoRasffAdapter()]


class RegulatoryTrackerService:
    def __init__(self, db: Session, adapters: list[BaseAdapter] | None = None):
        self.db = db
        self.adapters = adapters or DEFAULT_ADAPTERS

    def refresh(self) -> dict:
        inserted = 0
        for ad in self.adapters:
            for item in ad.fetch():
                exists = self.db.query(IfRegulatoryChange).filter_by(
                    source=ad.source, external_id=item["external_id"]
                ).one_or_none()
                if exists:
                    continue
                row = IfRegulatoryChange(
                    source=ad.source,
                    external_id=item["external_id"],
                    market=ad.market,
                    title=item["title"],
                    summary=item.get("summary"),
                    url=item.get("url"),
                    severity=ChangeSeverity(item.get("severity", "info")),
                    affected_categories=item.get("affected_categories", []),
                    affected_fields=item.get("affected_fields", []),
                    published_at=item.get("published_at"),
                )
                self.db.add(row)
                inserted += 1
        self.db.commit()
        return {"inserted": inserted, "checked_at": datetime.now(timezone.utc).isoformat()}
