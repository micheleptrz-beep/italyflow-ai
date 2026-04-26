"""
ItalyFlow AI - Dashboard Pydantic schemas (P0). ASCII only.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class KpiCardOut(BaseModel):
    audits_total: int
    audits_last_7d: int
    compliance_rate: float = Field(ge=0.0, le=1.0)
    active_markets: int
    estimated_savings_eur: float
    sparkline_7d: list[int]
    refreshed_at: datetime


class ProductOut(BaseModel):
    id: int
    name: str
    category: str
    sku: Optional[str] = None
    region: Optional[str] = None
    is_dop: bool = False
    is_igp: bool = False
    is_bio: bool = False
    tags: list[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class AuditOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    market: str
    status: str
    score: float
    missing_fields: list[str] = []
    warnings: list[str] = []
    duration_ms: int
    created_at: datetime


class TimelineFilter(BaseModel):
    market: Optional[str] = None
    product_id: Optional[int] = None
    status: Optional[str] = None
    q: Optional[str] = None
    limit: int = 50
    offset: int = 0


class HeatmapCell(BaseModel):
    product_id: int
    product_name: str
    market: str
    status: str
    score: float
    missing_fields: list[str] = []


class HeatmapOut(BaseModel):
    products: list[str]
    markets: list[str]
    cells: list[HeatmapCell]


class WizardStep1(BaseModel):
    product_name: str = Field(min_length=2, max_length=200)
    category: str
    region: Optional[str] = None
    label_text: str = Field(min_length=10)


class WizardStep2(BaseModel):
    markets: list[str] = Field(min_length=1, max_length=8)


class WizardResultOut(BaseModel):
    audit_ids: list[int]
    overall_score: float
    by_market: dict[str, Any]
