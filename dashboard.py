# -*- coding: utf-8 -*-
"""
ItalyFlow AI - Dashboard Module v3.0
=====================================
Dashboard operativa: KPI, Timeline, Heatmap, Product Catalog
Stile ispirato a Stripe/Linear/Vercel.
"""
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import settings
from database import get_db, AuditResult, AuditBatch, Product

logger = logging.getLogger("italyflow.dashboard")

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ============================================================================
# IN-MEMORY CACHE (simple TTL cache per KPI)
# ============================================================================
_kpi_cache: dict = {}
_kpi_cache_ts: float = 0.0


def _get_cached_kpis(db: Session) -> dict:
    """KPI con cache in-memory TTL-based."""
    global _kpi_cache, _kpi_cache_ts
    now = time.time()
    if _kpi_cache and (now - _kpi_cache_ts) < settings.DASHBOARD_CACHE_TTL_S:
        return _kpi_cache

    total_audits = db.query(func.count(AuditResult.id)).scalar() or 0

    avg_score = db.query(func.avg(AuditResult.compliance_score)).scalar() or 0
    avg_score = round(avg_score, 1)

    compliant = db.query(func.count(AuditResult.id)).filter(
        AuditResult.compliance_score >= 80
    ).scalar() or 0
    compliance_rate = round((compliant / total_audits * 100) if total_audits else 0, 1)

    active_markets = db.query(func.count(func.distinct(AuditResult.market))).scalar() or 0

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    audits_this_week = db.query(func.count(AuditResult.id)).filter(
        AuditResult.created_at >= week_ago
    ).scalar() or 0

    two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)
    audits_last_week = db.query(func.count(AuditResult.id)).filter(
        AuditResult.created_at >= two_weeks_ago,
        AuditResult.created_at < week_ago,
    ).scalar() or 0

    if audits_last_week > 0:
        wow_trend = round(((audits_this_week - audits_last_week) / audits_last_week) * 100, 1)
    else:
        wow_trend = 100.0 if audits_this_week > 0 else 0.0

    sparkline_start = datetime.now(timezone.utc) - timedelta(days=settings.SPARKLINE_DAYS)
    daily_counts_raw = (
        db.query(
            func.date(AuditResult.created_at).label("day"),
            func.count(AuditResult.id).label("cnt"),
        )
        .filter(AuditResult.created_at >= sparkline_start)
        .group_by(func.date(AuditResult.created_at))
        .all()
    )
    daily_map = {str(row.day): row.cnt for row in daily_counts_raw}
    sparkline = []
    for i in range(settings.SPARKLINE_DAYS):
        d = (sparkline_start + timedelta(days=i)).strftime("%Y-%m-%d")
        sparkline.append(daily_map.get(d, 0))

    total_products = db.query(func.count(Product.id)).scalar() or 0
    estimated_saving = total_audits * 135

    _kpi_cache = {
        "total_audits": total_audits,
        "avg_score": avg_score,
        "compliance_rate": compliance_rate,
        "active_markets": active_markets,
        "audits_this_week": audits_this_week,
        "wow_trend": wow_trend,
        "sparkline": sparkline,
        "total_products": total_products,
        "estimated_saving": estimated_saving,
    }
    _kpi_cache_ts = now
    return _kpi_cache


# ============================================================================
# HEATMAP DATA
# ============================================================================
def _get_heatmap_data(db: Session) -> dict:
    """Matrice Prodotto x Mercato con score medio."""
    rows = (
        db.query(
            AuditResult.product_detected,
            AuditResult.market,
            func.avg(AuditResult.compliance_score).label("avg_score"),
            func.count(AuditResult.id).label("audit_count"),
        )
        .filter(AuditResult.product_detected.isnot(None))
        .group_by(AuditResult.product_detected, AuditResult.market)
        .having(func.count(AuditResult.id) >= settings.HEATMAP_MIN_AUDITS)
        .all()
    )

    products = sorted(set(r.product_detected for r in rows))
    markets = sorted(set(r.market for r in rows))
    matrix = {}
    for r in rows:
        key = f"{r.product_detected}|{r.market}"
        matrix[key] = {
            "score": round(r.avg_score, 1),
            "count": r.audit_count,
        }

    return {"products": products, "markets": markets, "matrix": matrix}


# ============================================================================
# DASHBOARD CSS
# ============================================================================
DASH_CSS = """
<style>
:root {
    --bg-primary: #09090b;
    --bg-secondary: #18181b;
    --bg-card: #1c1c1f;
    --bg-card-hover: #27272a;
    --border: #27272a;
    --border-subtle: #1f1f23;
    --text-primary: #fafafa;
    --text-secondary: #a1a1aa;
    --text-muted: #71717a;
    --accent: #16a34a;
    --accent-light: #4ade80;
    --accent-bg: rgba(22,163,74,.08);
    --accent-border: rgba(22,163,74,.15);
    --red: #ef4444;
    --yellow: #eab308;
    --blue: #3b82f6;
    --radius: 12px;
    --radius-sm: 8px;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
       background:var(--bg-primary); color:var(--text-primary); line-height:1.5;
       -webkit-font-smoothing:antialiased; }
a { color:var(--accent-light); text-decoration:none; }
a:hover { text-decoration:underline; }

.nav{position:sticky;top:0;z-index:100;background:rgba(9,9,11,.85);backdrop-filter:blur(12px);
     border-bottom:1px solid var(--border);}
.nav-inner{max-width:1280px;margin:0 auto;display:flex;align-items:center;
           justify-content:space-between;padding:0 24px;height:56px;}
.nav-brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:16px;color:var(--text-primary);}
.nav-logo{width:32px;height:32px;background:linear-gradient(135deg,var(--accent),var(--accent-light));
          border-radius:8px;display:flex;align-items:center;justify-content:center;}
.brand-ai{color:var(--accent-light);margin-left:1px;}
.nav-links{display:flex;gap:4px;}
.nav-link{padding:8px 14px;font-size:13px;font-weight:500;color:var(--text-secondary);
          border-radius:6px;transition:all .15s;}
.nav-link:hover{color:var(--text-primary);background:var(--bg-card);text-decoration:none;}
.nav-link.active{color:var(--text-primary);background:var(--bg-card);}
.nav-badge{background:var(--accent);color:white;font-size:11px;padding:1px 6px;
           border-radius:10px;margin-left:6px;}

.dash-container{max-width:1280px;margin:0 auto;padding:32px 24px;}
.dash-header{margin-bottom:32px;}
.dash-title{font-size:28px;font-weight:800;letter-spacing:-.03em;}
.dash-subtitle{font-size:14px;color:var(--text-secondary);margin-top:4px;}

.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-bottom:32px;}
.kpi-card{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);
          padding:24px;transition:border-color .2s,transform .15s;}
.kpi-card:hover{border-color:var(--accent);transform:translateY(-2px);}
.kpi-label{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;
           color:var(--text-muted);margin-bottom:8px;}
.kpi-value{font-size:32px;font-weight:800;letter-spacing:-.03em;line-height:1;}
.kpi-trend{display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:600;
           margin-top:8px;padding:2px 8px;border-radius:4px;}
.kpi-trend.up{color:#4ade80;background:rgba(74,222,128,.1);}
.kpi-trend.down{color:#ef4444;background:rgba(239,68,68,.1);}
.kpi-trend.neutral{color:var(--text-muted);background:var(--bg-secondary);}
.kpi-sparkline{margin-top:12px;height:32px;}

.section-title{font-size:18px;font-weight:700;margin-bottom:16px;display:flex;align-items:center;gap:8px;}
.section-count{font-size:12px;color:var(--text-muted);font-weight:500;
               background:var(--bg-secondary);padding:2px 8px;border-radius:4px;}

.timeline{display:flex;flex-direction:column;gap:8px;}
.timeline-item{display:flex;align-items:center;gap:16px;padding:16px 20px;
               background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-sm);
               transition:border-color .15s;}
.timeline-item:hover{border-color:var(--accent-border);}
.timeline-score{width:48px;height:48px;border-radius:50%;display:flex;align-items:center;
                justify-content:center;font-weight:800;font-size:14px;flex-shrink:0;}
.score-high{background:rgba(22,163,74,.15);color:#4ade80;border:2px solid rgba(22,163,74,.3);}
.score-mid{background:rgba(234,179,8,.15);color:#eab308;border:2px solid rgba(234,179,8,.3);}
.score-low{background:rgba(239,68,68,.15);color:#ef4444;border:2px solid rgba(239,68,68,.3);}
.timeline-info{flex:1;min-width:0;}
.timeline-product{font-weight:600;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.timeline-meta{font-size:12px;color:var(--text-muted);margin-top:2px;}
.timeline-pills{display:flex;gap:6px;flex-wrap:wrap;}
.pill{font-size:11px;font-weight:600;padding:3px 10px;border-radius:100px;}
.pill-market{background:var(--bg-secondary);color:var(--text-secondary);border:1px solid var(--border);}
.pill-status{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.03em;}
.pill-ok{background:rgba(22,163,74,.12);color:#4ade80;border:1px solid rgba(22,163,74,.2);}
.pill-warn{background:rgba(234,179,8,.12);color:#eab308;border:1px solid rgba(234,179,8,.2);}
.pill-fail{background:rgba(239,68,68,.12);color:#ef4444;border:1px solid rgba(239,68,68,.2);}
.timeline-date{font-size:12px;color:var(--text-muted);white-space:nowrap;}
.btn-sm{padding:6px 12px;font-size:12px;font-weight:600;border-radius:6px;border:1px solid var(--border);
        background:var(--bg-secondary);color:var(--text-secondary);cursor:pointer;transition:all .15s;}
.btn-sm:hover{border-color:var(--accent);color:var(--text-primary);}

.heatmap-wrap{overflow-x:auto;margin-bottom:32px;}
.heatmap{border-collapse:separate;border-spacing:3px;width:100%;}
.heatmap th{font-size:11px;font-weight:600;color:var(--text-muted);padding:8px;text-align:center;
            text-transform:uppercase;letter-spacing:.03em;}
.heatmap td{text-align:center;padding:12px 8px;border-radius:6px;font-size:13px;font-weight:700;
            cursor:pointer;transition:transform .1s;}
.heatmap td:hover{transform:scale(1.08);}
.hm-high{background:rgba(22,163,74,.2);color:#4ade80;}
.hm-mid{background:rgba(234,179,8,.2);color:#eab308;}
.hm-low{background:rgba(239,68,68,.2);color:#ef4444;}
.hm-empty{background:var(--bg-secondary);color:var(--text-muted);font-size:11px;}
.hm-product{text-align:left !important;font-weight:600;color:var(--text-primary);font-size:13px;}

.products-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;}
.product-card{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);
              padding:20px;transition:border-color .15s,transform .15s;}
.product-card:hover{border-color:var(--accent);transform:translateY(-2px);}
.product-name{font-size:16px;font-weight:700;margin-bottom:4px;}
.product-cat{font-size:12px;color:var(--text-muted);margin-bottom:12px;}
.product-certs{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:12px;}
.cert-badge{font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;
            background:rgba(59,130,246,.12);color:#60a5fa;border:1px solid rgba(59,130,246,.2);}
.product-markets{display:flex;gap:4px;flex-wrap:wrap;}
.product-score{display:flex;align-items:center;gap:6px;margin-top:12px;padding-top:12px;
               border-top:1px solid var(--border);}
.product-score-val{font-size:20px;font-weight:800;}
.product-score-label{font-size:11px;color:var(--text-muted);}

.empty-state{text-align:center;padding:80px 24px;color:var(--text-muted);}
.empty-icon{font-size:48px;margin-bottom:16px;opacity:.5;}
.empty-title{font-size:18px;font-weight:700;color:var(--text-secondary);margin-bottom:8px;}
.empty-desc{font-size:14px;max-width:400px;margin:0 auto 24px;}
.btn-primary{display:inline-flex;align-items:center;gap:6px;padding:10px 20px;
             background:var(--accent);color:white;font-weight:600;font-size:14px;
             border-radius:8px;border:none;cursor:pointer;transition:all .15s;}
.btn-primary:hover{background:#15803d;transform:translateY(-1px);text-decoration:none;}

.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);
               z-index:200;align-items:center;justify-content:center;}
.modal{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);
       padding:32px;width:90%;max-width:480px;}
.modal h2{font-size:18px;font-weight:700;margin-bottom:20px;}
.form-group{margin-bottom:16px;}
.form-label-modal{display:block;font-size:12px;font-weight:600;color:var(--text-muted);
            margin-bottom:6px;text-transform:uppercase;letter-spacing:.03em;}
.form-input,.form-select{width:100%;padding:10px 14px;font-size:14px;border-radius:6px;
                         border:1px solid var(--border);background:var(--bg-secondary);
                         color:var(--text-primary);outline:none;}
.form-input:focus,.form-select:focus{border-color:var(--accent);}
.form-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:24px;}
.btn-cancel{padding:8px 16px;font-size:13px;border-radius:6px;border:1px solid var(--border);
            background:var(--bg-secondary);color:var(--text-secondary);cursor:pointer;}

@media(max-width:768px){
    .kpi-grid{grid-template-columns:repeat(2,1fr);}
    .timeline-item{flex-wrap:wrap;gap:8px;}
    .products-grid{grid-template-columns:1fr;}
}
@media(max-width:480px){
    .kpi-grid{grid-template-columns:1fr;}
    .dash-title{font-size:22px;}
}
</style>
"""


# ============================================================================
# NAV HTML
# ============================================================================
def _dash_nav(active: str = "dashboard", audit_count: int = 0) -> str:
    badge = f'<span class="nav-badge">{audit_count}</span>' if audit_count else ""

    def ac(n: str) -> str:
        return 'class="nav-link active"' if active == n else 'class="nav-link"'

    return (
        '<nav class="nav"><div class="nav-inner">'
        '<a href="/" class="nav-brand">'
        '<div class="nav-logo"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
        'stroke="white" stroke-width="2.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/>'
        '<path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg></div>'
        'ItalyFlow<span class="brand-ai">AI</span></a>'
        '<div class="nav-links">'
        f'<a href="/" {ac("home")}>Home</a>'
        f'<a href="/app" {ac("audit")}>Audit</a>'
        f'<a href="/dashboard" {ac("dashboard")}>Dashboard</a>'
        f'<a href="/dashboard/products" {ac("products")}>Prodotti</a>'
        f'<a href="/history" {ac("history")}>Storico{badge}</a>'
        '</div></div></nav>'
    )


# ============================================================================
# SPARKLINE SVG
# ============================================================================
def _sparkline_svg(data: list, color: str = "#4ade80", width: int = 200, height: int = 32) -> str:
    if not data or max(data) == 0:
        return f'<svg width="{width}" height="{height}"></svg>'

    max_val = max(data) or 1
    n = len(data)
    step = width / max(n - 1, 1)
    points = []
    for i, v in enumerate(data):
        x = round(i * step, 1)
        y = round(height - (v / max_val) * (height - 4) - 2, 1)
        points.append(f"{x},{y}")

    polyline = " ".join(points)
    area_points = f"0,{height} " + polyline + f" {width},{height}"

    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<polygon points="{area_points}" fill="{color}" opacity="0.1"/>'
        f'<polyline points="{polyline}" fill="none" stroke="{color}" '
        f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
        f'</svg>'
    )


# ============================================================================
# DASHBOARD HOME
# ============================================================================
@dashboard_router.get("", response_class=HTMLResponse)
@dashboard_router.get("/", response_class=HTMLResponse)
async def dashboard_home(db: Session = Depends(get_db)):
    kpis = _get_cached_kpis(db)
    audit_count = kpis["total_audits"]

    trend_val = kpis["wow_trend"]
    if trend_val > 0:
        trend_cls = "up"
        trend_icon = "&#8593;"
        trend_text = f"+{trend_val}%"
    elif trend_val < 0:
        trend_cls = "down"
        trend_icon = "&#8595;"
        trend_text = f"{trend_val}%"
    else:
        trend_cls = "neutral"
        trend_icon = "&#8212;"
        trend_text = "0%"

    sparkline = _sparkline_svg(kpis["sparkline"])

    score = kpis["avg_score"]
    score_color = "#4ade80" if score >= 80 else ("#eab308" if score >= 50 else "#ef4444")

    recent = (
        db.query(AuditResult)
        .order_by(AuditResult.created_at.desc())
        .limit(10)
        .all()
    )

    timeline_html = ""
    for a in recent:
        sc = a.compliance_score or 0
        sc_cls = "score-high" if sc >= 80 else ("score-mid" if sc >= 50 else "score-low")
        status_text = "Conforme" if sc >= 80 else ("Warning" if sc >= 50 else "Non conforme")
        status_cls = "pill-ok" if sc >= 80 else ("pill-warn" if sc >= 50 else "pill-fail")
        date_str = a.created_at.strftime("%d/%m %H:%M") if a.created_at else ""
        product = a.product_detected or "Prodotto"
        market = a.market or ""

        timeline_html += (
            f'<div class="timeline-item">'
            f'<div class="timeline-score {sc_cls}">{int(sc)}</div>'
            f'<div class="timeline-info">'
            f'<div class="timeline-product">{product}</div>'
            f'<div class="timeline-meta">{a.filename or ""}</div>'
            f'</div>'
            f'<div class="timeline-pills">'
            f'<span class="pill pill-market">{market}</span>'
            f'<span class="pill pill-status {status_cls}">{status_text}</span>'
            f'</div>'
            f'<div class="timeline-date">{date_str}</div>'
            f'<div class="timeline-actions">'
            f'<a href="/pdf/{a.id}" class="btn-sm">PDF</a>'
            f'</div>'
            f'</div>'
        )

    if not timeline_html:
        timeline_html = (
            '<div class="empty-state">'
            '<div class="empty-icon">&#128203;</div>'
            '<div class="empty-title">Nessun audit ancora</div>'
            '<div class="empty-desc">Il tuo viaggio nell\'export inizia qui. '
            'Carica la tua prima etichetta per ottenere un report.</div>'
            '<a href="/app" class="btn-primary">&#8594; Primo Audit</a>'
            '</div>'
        )

    # Heatmap
    hm = _get_heatmap_data(db)
    heatmap_html = ""
    if hm["products"] and hm["markets"]:
        heatmap_html = '<div class="heatmap-wrap"><table class="heatmap"><thead><tr><th></th>'
        for m in hm["markets"]:
            heatmap_html += f'<th>{m}</th>'
        heatmap_html += '</tr></thead><tbody>'
        for p in hm["products"]:
            heatmap_html += f'<tr><td class="hm-product">{p}</td>'
            for m in hm["markets"]:
                key = f"{p}|{m}"
                cell = hm["matrix"].get(key)
                if cell:
                    sc = cell["score"]
                    cls = "hm-high" if sc >= 80 else ("hm-mid" if sc >= 50 else "hm-low")
                    heatmap_html += (
                        f'<td class="{cls}" title="{p} x {m}: {sc}% '
                        f'({cell["count"]} audit)">{sc}</td>'
                    )
                else:
                    heatmap_html += '<td class="hm-empty">-</td>'
            heatmap_html += '</tr>'
        heatmap_html += '</tbody></table></div>'
    else:
        heatmap_html = (
            '<div class="empty-state" style="padding:40px">'
            '<div class="empty-title">Heatmap non disponibile</div>'
            '<div class="empty-desc">Esegui audit su piu prodotti e mercati '
            'per visualizzare la matrice di compliance.</div>'
            '</div>'
        )

    saving_fmt = f"{kpis['estimated_saving']:,}".replace(",", ".")

    page = (
        '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Dashboard - {settings.APP_NAME}</title>'
        + DASH_CSS
        + '</head><body>'
        + _dash_nav("dashboard", audit_count)
        + '<div class="dash-container">'
        + '<div class="dash-header">'
        + '<div class="dash-title">Dashboard</div>'
        + '<div class="dash-subtitle">Panoramica compliance e audit</div>'
        + '</div>'

        # KPI Cards
        + '<div class="kpi-grid">'
        + '<div class="kpi-card">'
        + '<div class="kpi-label">Audit Completati</div>'
        + f'<div class="kpi-value">{kpis["total_audits"]}</div>'
        + f'<div class="kpi-trend {trend_cls}">{trend_icon} {trend_text} vs sett. prec.</div>'
        + f'<div class="kpi-sparkline">{sparkline}</div>'
        + '</div>'
        + '<div class="kpi-card">'
        + '<div class="kpi-label">Compliance Rate</div>'
        + f'<div class="kpi-value" style="color:{score_color}">{kpis["compliance_rate"]}%</div>'
        + f'<div style="font-size:12px;color:var(--text-muted);margin-top:8px">Score medio: {kpis["avg_score"]}</div>'
        + '</div>'
        + '<div class="kpi-card">'
        + '<div class="kpi-label">Mercati Attivi</div>'
        + f'<div class="kpi-value">{kpis["active_markets"]}</div>'
        + '<div style="font-size:12px;color:var(--text-muted);margin-top:8px">su 10 disponibili</div>'
        + '</div>'
        + '<div class="kpi-card">'
        + '<div class="kpi-label">Risparmio vs Consulente</div>'
        + f'<div class="kpi-value" style="color:var(--accent-light)">EUR {saving_fmt}</div>'
        + '<div style="font-size:12px;color:var(--text-muted);margin-top:8px">basato su EUR 150/audit tradizionale</div>'
        + '</div>'
        + '</div>'

        # Heatmap
        + '<div class="section-title">Compliance Heatmap '
        + '<span class="section-count">Prodotto x Mercato</span></div>'
        + heatmap_html

        # Timeline
        + '<div class="section-title">Audit Recenti '
        + f'<span class="section-count">{min(len(recent), 10)} piu recenti</span></div>'
        + '<div class="timeline">'
        + timeline_html
        + '</div>'
        + '</div>'
        + '</body></html>'
    )

    return HTMLResponse(content=page)


# ============================================================================
# PRODUCT CATALOG PAGE
# ============================================================================
@dashboard_router.get("/products", response_class=HTMLResponse)
async def products_page(db: Session = Depends(get_db)):
    audit_count = db.query(func.count(AuditResult.id)).scalar() or 0
    products = db.query(Product).order_by(Product.created_at.desc()).all()

    products_html = ""
    for p in products:
        certs = json.loads(p.certifications) if p.certifications else []
        markets = json.loads(p.target_markets) if p.target_markets else []

        certs_html = "".join(f'<span class="cert-badge">{c}</span>' for c in certs)
        markets_html = "".join(f'<span class="pill pill-market">{m}</span>' for m in markets)

        avg = (
            db.query(func.avg(AuditResult.compliance_score))
            .filter(AuditResult.product_id == p.id)
            .scalar()
        )
        avg_score = round(avg, 1) if avg else None
        score_color = "#4ade80" if (avg_score or 0) >= 80 else (
            "#eab308" if (avg_score or 0) >= 50 else "#ef4444"
        )

        score_html = ""
        if avg_score is not None:
            score_html = (
                f'<div class="product-score">'
                f'<span class="product-score-val" style="color:{score_color}">{avg_score}</span>'
                f'<span class="product-score-label">compliance medio</span>'
                f'</div>'
            )

        products_html += (
            f'<div class="product-card">'
            f'<div class="product-name">{p.name}</div>'
            f'<div class="product-cat">{p.category or "Non categorizzato"} - {p.region or "Italia"}</div>'
            f'<div class="product-certs">{certs_html}</div>'
            f'<div class="product-markets">{markets_html}</div>'
            f'{score_html}'
            f'</div>'
        )

    if not products_html:
        products_html = (
            '<div class="empty-state">'
            '<div class="empty-icon">&#128230;</div>'
            '<div class="empty-title">Nessun prodotto nel catalogo</div>'
            '<div class="empty-desc">Aggiungi i tuoi prodotti per tracciare la compliance.</div>'
            '<button class="btn-primary" onclick="document.getElementById(\'addModal\').style.display=\'flex\'">'
            '+ Aggiungi Prodotto</button>'
            '</div>'
        )

    cat_options = "".join(
        f'<option value="{c}">{c}</option>' for c in settings.PRODUCT_CATEGORIES
    )

    page = (
        '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Prodotti - {settings.APP_NAME}</title>'
        + DASH_CSS
        + '</head><body>'
        + _dash_nav("products", audit_count)
        + '<div class="dash-container">'
        + '<div class="dash-header" style="display:flex;justify-content:space-between;align-items:center">'
        + '<div><div class="dash-title">Catalogo Prodotti</div>'
        + f'<div class="dash-subtitle">{len(products)} prodotti registrati</div></div>'
        + '<button class="btn-primary" onclick="document.getElementById(\'addModal\').style.display=\'flex\'">'
        + '+ Nuovo Prodotto</button>'
        + '</div>'
        + f'<div class="products-grid">{products_html}</div>'

        # Modal
        + '<div class="modal-overlay" id="addModal">'
        + '<div class="modal">'
        + '<h2>Aggiungi Prodotto</h2>'
        + '<form method="POST" action="/dashboard/products/add">'
        + '<div class="form-group"><label class="form-label-modal">Nome Prodotto</label>'
        + '<input class="form-input" name="name" required placeholder="es. Olio EVO Nocellara"></div>'
        + '<div class="form-group"><label class="form-label-modal">Categoria</label>'
        + f'<select class="form-select" name="category">{cat_options}</select></div>'
        + '<div class="form-group"><label class="form-label-modal">Brand</label>'
        + '<input class="form-input" name="brand" placeholder="es. Frantoio Ferraro"></div>'
        + '<div class="form-group"><label class="form-label-modal">Regione</label>'
        + '<input class="form-input" name="region" placeholder="es. Sicilia"></div>'
        + '<div class="form-group"><label class="form-label-modal">Certificazioni (separate da virgola)</label>'
        + '<input class="form-input" name="certifications" placeholder="DOP, BIO, IGP"></div>'
        + '<div class="form-actions">'
        + '<button type="button" class="btn-cancel" '
        + 'onclick="document.getElementById(\'addModal\').style.display=\'none\'">Annulla</button>'
        + '<button type="submit" class="btn-primary">Salva</button>'
        + '</div></form></div></div>'
        + '</div>'
        + '</body></html>'
    )

    return HTMLResponse(content=page)


# ============================================================================
# ADD PRODUCT (POST)
# ============================================================================
@dashboard_router.post("/products/add")
async def add_product(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    name = form.get("name", "").strip()
    if not name:
        raise HTTPException(400, "Nome prodotto obbligatorio")

    certs_raw = form.get("certifications", "")
    certs = [c.strip() for c in certs_raw.split(",") if c.strip()] if certs_raw else []

    product = Product(
        name=name,
        category=form.get("category", ""),
        brand=form.get("brand", ""),
        region=form.get("region", ""),
        certifications=json.dumps(certs) if certs else None,
    )
    db.add(product)
    db.commit()
    logger.info("product_created name=%s id=%d", name, product.id)

    return RedirectResponse(url="/dashboard/products", status_code=303)


# ============================================================================
# JSON API ENDPOINTS
# ============================================================================
@dashboard_router.get("/api/kpis")
async def api_kpis(db: Session = Depends(get_db)):
    return JSONResponse(content=_get_cached_kpis(db))


@dashboard_router.get("/api/heatmap")
async def api_heatmap(db: Session = Depends(get_db)):
    return JSONResponse(content=_get_heatmap_data(db))


@dashboard_router.get("/api/timeline")
async def api_timeline(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, le=100),
    market: Optional[str] = Query(default=None),
    min_score: Optional[float] = Query(default=None),
    max_score: Optional[float] = Query(default=None),
):
    q = db.query(AuditResult).order_by(AuditResult.created_at.desc())
    if market:
        q = q.filter(AuditResult.market == market)
    if min_score is not None:
        q = q.filter(AuditResult.compliance_score >= min_score)
    if max_score is not None:
        q = q.filter(AuditResult.compliance_score <= max_score)

    audits = q.limit(limit).all()
    results = []
    for a in audits:
        results.append({
            "id": a.id,
            "filename": a.filename,
            "market": a.market,
            "compliance_score": a.compliance_score,
            "product_detected": a.product_detected,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })

    return JSONResponse(content={"audits": results, "count": len(results)})


@dashboard_router.get("/api/products")
async def api_products(db: Session = Depends(get_db)):
    products = db.query(Product).order_by(Product.name).all()
    results = []
    for p in products:
        results.append({
            "id": p.id,
            "uid": p.uid,
            "name": p.name,
            "category": p.category,
            "brand": p.brand,
            "region": p.region,
            "certifications": json.loads(p.certifications) if p.certifications else [],
            "target_markets": json.loads(p.target_markets) if p.target_markets else [],
            "status": p.status,
        })
    return JSONResponse(content={"products": results, "count": len(results)})
