# -*- coding: utf-8 -*-
"""
ItalyFlow AI -- Visual Identity Module v3.1
=============================================
Hero backgrounds system, asset catalog, seasonal/regional matching.
Ispirazione: Apple.com, Airbnb Luxe, Eataly.

Import in main.py:
    from visual_identity import visual_router, hero_background_html
    app.include_router(visual_router)
"""
import json
import logging
import random
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import settings
from database import get_db, VisualAsset, UserVisualPreference

logger = logging.getLogger("italyflow.visual")

visual_router = APIRouter(prefix="/visual", tags=["visual"])


# ============================================================================
# SEASON / TIME-OF-DAY DETECTION
# ============================================================================
def _get_current_season() -> str:
    """Stagione corrente basata su emisfero nord."""
    month = datetime.now(timezone.utc).month
    if month in (3, 4, 5):
        return "primavera"
    elif month in (6, 7, 8):
        return "estate"
    elif month in (9, 10, 11):
        return "autunno"
    else:
        return "inverno"


def _get_time_mood(hour: Optional[int] = None) -> str:
    """Mood basato sull'ora del giorno (UTC, l'utente puo passare la sua ora locale)."""
    if hour is None:
        hour = datetime.now(timezone.utc).hour
    if 5 <= hour < 10:
        return "golden_hour"  # mattina
    elif 10 <= hour < 17:
        return "midday"
    elif 17 <= hour < 21:
        return "golden_hour"  # sera
    else:
        return "evening"


# ============================================================================
# UNSPLASH URL BUILDER
# ============================================================================
def _unsplash_url(
    base_url: str,
    width: int = 1920,
    quality: int = 80,
    fmt: str = "auto",
    fit: str = "crop",
) -> str:
    """Costruisce URL Unsplash con parametri di trasformazione.

    Unsplash supporta: ?w=WIDTH&q=QUALITY&fm=FORMAT&fit=FIT&crop=entropy
    Formati: auto (WebP se supportato), webp, jpg
    """
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}w={width}&q={quality}&fm={fmt}&fit={fit}&crop=entropy&auto=format"


def _build_srcset(base_url: str, quality: int = 80) -> str:
    """Genera attributo srcset per responsive images."""
    breakpoints = [
        (settings.HERO_MOBILE_WIDTH, "720w"),
        (settings.HERO_TABLET_WIDTH, "1080w"),
        (settings.HERO_DESKTOP_WIDTH, "1920w"),
        (settings.HERO_4K_WIDTH, "3840w"),
    ]
    parts = []
    for w, descriptor in breakpoints:
        url = _unsplash_url(base_url, width=w, quality=quality)
        parts.append(f"{url} {descriptor}")
    return ", ".join(parts)


def _blur_placeholder_url(base_url: str) -> str:
    """URL per tiny blur-up placeholder (32px wide, bassa qualita)."""
    return _unsplash_url(base_url, width=settings.HERO_BLUR_PLACEHOLDER_WIDTH, quality=20)


# ============================================================================
# ASSET SELECTION ENGINE
# ============================================================================
_asset_cache: dict = {}
_asset_cache_ts: float = 0.0


def select_hero_asset(
    db: Session,
    page_context: str = "landing",
    region: Optional[str] = None,
    product_type: Optional[str] = None,
    mood: Optional[str] = None,
    market_context: Optional[str] = None,
    user_hour: Optional[int] = None,
) -> Optional[dict]:
    """Seleziona l'immagine hero migliore basandosi su contesto.

    Priorita di matching (cascade):
    1. page_context esatto + region + product_type + season
    2. page_context esatto + region + season
    3. page_context esatto + season
    4. page_context esatto (qualsiasi)
    5. Fallback a categoria 'landscape' generica
    """
    season = _get_current_season() if settings.ENABLE_SEASONAL_ROTATION else None
    time_mood = _get_time_mood(user_hour) if settings.ENABLE_TIME_AWARENESS else None

    # Base query: attivi
    base_q = db.query(VisualAsset).filter(VisualAsset.is_active == True)

    # Tentativo 1: match completo
    q = base_q.filter(VisualAsset.page_context == page_context)
    if region:
        q1 = q.filter(
            (VisualAsset.region == region) | (VisualAsset.region == "generic")
        )
        if product_type:
            q2 = q1.filter(
                (VisualAsset.product_type == product_type) | (VisualAsset.product_type == "generic")
            )
            if season:
                q3 = q2.filter(
                    (VisualAsset.season == season) | (VisualAsset.season == "all")
                )
                results = q3.all()
                if results:
                    return _pick_and_format(results, time_mood)

            results = q2.all()
            if results:
                return _pick_and_format(results, time_mood)

        results = q1.all()
        if results:
            return _pick_and_format(results, time_mood)

    # Tentativo con season
    if season:
        q_season = q.filter(
            (VisualAsset.season == season) | (VisualAsset.season == "all")
        )
        results = q_season.all()
        if results:
            return _pick_and_format(results, time_mood)

    # Tentativo solo page_context
    results = q.all()
    if results:
        return _pick_and_format(results, time_mood)

    # Market context (per pagina mercati)
    if market_context:
        q_market = base_q.filter(VisualAsset.market_context == market_context)
        results = q_market.all()
        if results:
            return _pick_and_format(results, time_mood)

    # Fallback: qualsiasi landscape
    results = base_q.filter(VisualAsset.category == "landscape").all()
    if results:
        return _pick_and_format(results, time_mood)

    return None


def _pick_and_format(assets: list, time_mood: Optional[str] = None) -> dict:
    """Seleziona un asset pesato per quality_score e formatta la risposta."""
    # Weighted random: quality_score come peso
    weights = [a.quality_score or 5.0 for a in assets]
    total = sum(weights)
    weights = [w / total for w in weights]

    chosen = random.choices(assets, weights=weights, k=1)[0]

    # Time-of-day overlay adjustment
    if time_mood == "golden_hour":
        overlay_opacity = 0.35
        overlay_color = "rgba(15, 10, 5, {op})"
    elif time_mood == "evening":
        overlay_opacity = 0.55
        overlay_color = "rgba(5, 5, 15, {op})"
    else:  # midday
        overlay_opacity = 0.40
        overlay_color = "rgba(9, 9, 11, {op})"

    return {
        "id": chosen.id,
        "uid": chosen.uid,
        "title": chosen.title,
        "url": chosen.url_original,
        "srcset": _build_srcset(chosen.url_original),
        "placeholder": _blur_placeholder_url(chosen.url_original),
        "url_mobile": _unsplash_url(chosen.url_original, width=settings.HERO_MOBILE_WIDTH),
        "url_desktop": _unsplash_url(chosen.url_original, width=settings.HERO_DESKTOP_WIDTH),
        "dominant_color": chosen.dominant_color or "#09090b",
        "photographer": chosen.photographer,
        "source": chosen.source,
        "overlay_opacity": overlay_opacity,
        "overlay_color": overlay_color.format(op=overlay_opacity),
        "category": chosen.category,
        "region": chosen.region,
        "season": chosen.season,
    }


# ============================================================================
# HERO BACKGROUND HTML GENERATOR
# ============================================================================
def hero_background_html(
    db: Session,
    page_context: str = "landing",
    height: str = "100vh",
    region: Optional[str] = None,
    product_type: Optional[str] = None,
    market_context: Optional[str] = None,
    user_hour: Optional[int] = None,
    show_credit: bool = True,
    extra_class: str = "",
) -> str:
    """Genera HTML completo per hero background con:
    - Adaptive loading (srcset + picture element)
    - Blur-up placeholder
    - Parallax subtile
    - Overlay gradient dinamico
    - Credit fotografo

    Ritorna stringa HTML da inserire in qualsiasi pagina.
    Se nessun asset trovato, ritorna il gradient CSS di fallback attuale.
    """
    asset = select_hero_asset(
        db,
        page_context=page_context,
        region=region,
        product_type=product_type,
        market_context=market_context,
        user_hour=user_hour,
    )

    if not asset:
        # Fallback: gradient CSS esistente (identico a BG_CSS di main.py v3.0)
        return (
            '<div class="hero-bg-fallback" style="position:absolute;inset:0;z-index:0;'
            'background:radial-gradient(ellipse at 50% 0%,rgba(34,197,94,.06),transparent 70%);'
            'pointer-events:none;"></div>'
        )

    parallax_style = "background-attachment:fixed;" if settings.ENABLE_PARALLAX else ""
    overlay_color = asset["overlay_color"]
    dominant = asset["dominant_color"]
    placeholder = asset["placeholder"]
    srcset = asset["srcset"]
    url_desktop = asset["url_desktop"]

    credit_html = ""
    if show_credit and asset.get("photographer"):
        credit_html = (
            f'<div class="hero-credit">Foto: {asset["photographer"]}'
            f' / {asset["source"].capitalize()}</div>'
        )

    return f'''
<div class="hero-bg {extra_class}" style="position:absolute;inset:0;z-index:0;
     overflow:hidden;height:{height};">

  <!-- Blur-up placeholder (inline, caricamento istantaneo) -->
  <div class="hero-bg-placeholder" style="
    position:absolute;inset:0;
    background:url('{placeholder}') center/cover no-repeat;
    background-color:{dominant};
    filter:blur(20px);
    transform:scale(1.1);
    transition:opacity 0.6s ease;
    z-index:1;
  "></div>

  <!-- Immagine principale con srcset -->
  <img
    class="hero-bg-img"
    src="{url_desktop}"
    srcset="{srcset}"
    sizes="100vw"
    alt=""
    loading="eager"
    decoding="async"
    onload="this.style.opacity='1';
            this.previousElementSibling.style.opacity='0';"
    style="
      position:absolute;inset:0;
      width:100%;height:100%;
      object-fit:cover;
      object-position:center;
      opacity:0;
      transition:opacity 0.8s ease;
      z-index:2;
      {parallax_style}
    "
  />

  <!-- Overlay gradient (WCAG AAA contrast) -->
  <div class="hero-bg-overlay" style="
    position:absolute;inset:0;z-index:3;
    background:linear-gradient(
      180deg,
      {overlay_color} 0%,
      rgba(9,9,11,0.5) 40%,
      rgba(9,9,11,0.85) 75%,
      rgba(9,9,11,0.98) 100%
    );
    pointer-events:none;
  "></div>

  {credit_html}
</div>
'''


# ============================================================================
# HERO CSS (aggiungere al CSS della pagina)
# ============================================================================
HERO_CSS = """
/* Hero Background System */
.hero-bg { pointer-events:none; }
.hero-bg-img { will-change:opacity; }
.hero-credit {
    position:absolute; bottom:12px; right:16px; z-index:5;
    font-size:10px; color:rgba(255,255,255,.3);
    font-family:-apple-system,sans-serif;
    pointer-events:auto;
}

/* Parallax on scroll (subtle, 3D transform) */
@supports (transform: translate3d(0,0,0)) {
    .hero-bg-parallax .hero-bg-img {
        will-change:transform;
    }
}

/* Prefers reduced motion */
@media (prefers-reduced-motion: reduce) {
    .hero-bg-img { transition:none !important; }
    .hero-bg-placeholder { transition:none !important; }
}
"""


# ============================================================================
# PARALLAX JS (script inline da aggiungere alla pagina)
# ============================================================================
PARALLAX_JS = """
<script>
(function(){
  if(window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  var hero = document.querySelector('.hero-bg-img');
  if(!hero) return;
  var ticking = false;
  window.addEventListener('scroll', function(){
    if(!ticking){
      window.requestAnimationFrame(function(){
        var scrolled = window.pageYOffset;
        var rate = scrolled * 0.3;
        hero.style.transform = 'translate3d(0,' + rate + 'px,0) scale(1.05)';
        ticking = false;
      });
      ticking = true;
    }
  }, {passive:true});
})();
</script>
"""


# ============================================================================
# PRELOAD LINK GENERATOR
# ============================================================================
def hero_preload_link(db: Session, page_context: str = "landing") -> str:
    """Genera tag <link rel=preload> per l'immagine hero.
    Da inserire nel <head> della pagina per precaricamento."""
    asset = select_hero_asset(db, page_context=page_context)
    if not asset:
        return ""
    url = asset["url_desktop"]
    return (
        f'<link rel="preload" as="image" href="{url}" '
        f'imagesrcset="{asset["srcset"]}" imagesizes="100vw">'
    )


# ============================================================================
# MARKET BACKGROUNDS MAP (per pagina mercati)
# ============================================================================
MARKET_SKYLINES = {
    "USA": {"query": "new york skyline", "fallback_color": "#1a1a2e"},
    "Cina": {"query": "great wall china", "fallback_color": "#2d1b00"},
    "Canada": {"query": "toronto skyline", "fallback_color": "#0d2137"},
    "Giappone": {"query": "tokyo skyline night", "fallback_color": "#1a0a2e"},
    "UK": {"query": "london skyline", "fallback_color": "#1a1a1a"},
    "Italia": {"query": "rome colosseum", "fallback_color": "#2e1a00"},
    "UE": {"query": "brussels eu parliament", "fallback_color": "#001a3a"},
    "Corea": {"query": "seoul skyline", "fallback_color": "#0a1a2e"},
    "Argentina": {"query": "buenos aires obelisk", "fallback_color": "#1a2e1a"},
    "Brasile": {"query": "sao paulo skyline", "fallback_color": "#1a2e00"},
}


# ============================================================================
# ENDPOINT: Asset Catalog Management
# ============================================================================
@visual_router.get("/assets", response_class=HTMLResponse)
async def asset_catalog_page(db: Session = Depends(get_db)):
    """Pagina gestione catalogo immagini (admin)."""
    assets = db.query(VisualAsset).order_by(VisualAsset.created_at.desc()).all()
    total = len(assets)
    active = sum(1 for a in assets if a.is_active)

    rows_html = ""
    for a in assets:
        thumb = _unsplash_url(a.url_original, width=120, quality=60)
        status = "Attivo" if a.is_active else "Inattivo"
        status_cls = "pill-ok" if a.is_active else "pill-fail"
        rows_html += (
            f'<tr>'
            f'<td><img src="{thumb}" style="width:80px;height:50px;object-fit:cover;border-radius:4px;"></td>'
            f'<td>{a.title}</td>'
            f'<td><span class="pill pill-market">{a.category}</span></td>'
            f'<td>{a.region or "-"}</td>'
            f'<td>{a.season or "all"}</td>'
            f'<td>{a.page_context or "-"}</td>'
            f'<td><span class="pill pill-status {status_cls}">{status}</span></td>'
            f'<td>{a.quality_score}</td>'
            f'</tr>'
        )

    if not rows_html:
        rows_html = (
            '<tr><td colspan="8" style="text-align:center;padding:40px;color:#71717a;">'
            'Nessun asset. Esegui seed_visual_assets.py per popolare il catalogo.'
            '</td></tr>'
        )

    # Reuse dashboard CSS
    page = (
        '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Visual Assets -- {settings.APP_NAME}</title>'
        '<style>'
        ':root{--bg-primary:#09090b;--bg-secondary:#18181b;--bg-card:#1c1c1f;'
        '--border:#27272a;--text-primary:#fafafa;--text-secondary:#a1a1aa;'
        '--text-muted:#71717a;--accent:#16a34a;--accent-light:#4ade80;}'
        '*{margin:0;padding:0;box-sizing:border-box;}'
        'body{font-family:-apple-system,sans-serif;background:var(--bg-primary);'
        'color:var(--text-primary);}'
        '.container{max-width:1280px;margin:0 auto;padding:32px 24px;}'
        'h1{font-size:24px;font-weight:800;margin-bottom:8px;}'
        '.subtitle{color:var(--text-secondary);font-size:14px;margin-bottom:24px;}'
        'table{width:100%;border-collapse:collapse;background:var(--bg-card);'
        'border:1px solid var(--border);border-radius:8px;overflow:hidden;}'
        'th{padding:12px 16px;text-align:left;font-size:11px;font-weight:700;'
        'color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em;'
        'background:var(--bg-secondary);border-bottom:1px solid var(--border);}'
        'td{padding:10px 16px;font-size:13px;border-bottom:1px solid var(--border);}'
        'tr:hover td{background:#27272a;}'
        '.pill{font-size:11px;font-weight:600;padding:2px 8px;border-radius:100px;'
        'display:inline-block;}'
        '.pill-market{background:#18181b;color:#a1a1aa;border:1px solid #27272a;}'
        '.pill-ok{background:rgba(22,163,74,.12);color:#4ade80;}'
        '.pill-fail{background:rgba(239,68,68,.12);color:#ef4444;}'
        '.stats{display:flex;gap:24px;margin-bottom:24px;}'
        '.stat{font-size:14px;color:var(--text-secondary);}'
        '.stat b{color:var(--text-primary);font-size:20px;margin-right:4px;}'
        '</style></head><body>'
        '<div class="container">'
        f'<h1>Visual Asset Catalog</h1>'
        f'<div class="subtitle">Gestione immagini per sfondi immersivi Made in Italy</div>'
        f'<div class="stats">'
        f'<div class="stat"><b>{total}</b> totali</div>'
        f'<div class="stat"><b>{active}</b> attivi</div>'
        f'</div>'
        '<table><thead><tr>'
        '<th>Preview</th><th>Titolo</th><th>Categoria</th><th>Regione</th>'
        '<th>Stagione</th><th>Pagina</th><th>Stato</th><th>Score</th>'
        f'</tr></thead><tbody>{rows_html}</tbody></table>'
        '</div></body></html>'
    )

    return HTMLResponse(content=page)


@visual_router.get("/api/hero")
async def api_hero(
    db: Session = Depends(get_db),
    page: str = Query(default="landing"),
    region: Optional[str] = Query(default=None),
    product_type: Optional[str] = Query(default=None),
    market: Optional[str] = Query(default=None),
    hour: Optional[int] = Query(default=None, ge=0, le=23),
):
    """API per ottenere l'asset hero per un contesto specifico."""
    asset = select_hero_asset(
        db,
        page_context=page,
        region=region,
        product_type=product_type,
        market_context=market,
        user_hour=hour,
    )
    if not asset:
        return JSONResponse(content={"found": False, "fallback": "gradient"})

    return JSONResponse(content={"found": True, "asset": asset})


@visual_router.get("/preview/{asset_uid}", response_class=HTMLResponse)
async def preview_asset(asset_uid: str, db: Session = Depends(get_db)):
    """Preview di un singolo asset con hero background."""
    asset_row = db.query(VisualAsset).filter(VisualAsset.uid == asset_uid).first()
    if not asset_row:
        raise HTTPException(404, "Asset non trovato")

    url_full = _unsplash_url(asset_row.url_original, width=1920)
    placeholder = _blur_placeholder_url(asset_row.url_original)

    page = (
        '<!DOCTYPE html><html><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Preview: {asset_row.title}</title>'
        '<style>'
        '*{margin:0;padding:0;box-sizing:border-box;}'
        'body{background:#09090b;color:#fafafa;font-family:-apple-system,sans-serif;}'
        '.hero{position:relative;height:70vh;overflow:hidden;display:flex;'
        'align-items:center;justify-content:center;}'
        '.hero img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;}'
        '.hero-overlay{position:absolute;inset:0;background:linear-gradient(180deg,'
        'rgba(9,9,11,.3) 0%,rgba(9,9,11,.7) 70%,rgba(9,9,11,.95) 100%);z-index:2;}'
        '.hero-content{position:relative;z-index:3;text-align:center;padding:24px;}'
        'h1{font-size:48px;font-weight:800;letter-spacing:-.03em;margin-bottom:8px;}'
        '.meta{color:#a1a1aa;font-size:14px;}'
        '.info{max-width:800px;margin:40px auto;padding:24px;}'
        '.info-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;}'
        '.info-item{background:#1c1c1f;border:1px solid #27272a;border-radius:8px;padding:16px;}'
        '.info-label{font-size:11px;color:#71717a;text-transform:uppercase;margin-bottom:4px;}'
        '.info-value{font-size:14px;font-weight:600;}'
        '</style></head><body>'
        f'<div class="hero">'
        f'<img src="{url_full}" alt="{asset_row.title}">'
        f'<div class="hero-overlay"></div>'
        f'<div class="hero-content">'
        f'<h1>{asset_row.title}</h1>'
        f'<div class="meta">{asset_row.photographer or ""} / {asset_row.source}</div>'
        f'</div></div>'
        f'<div class="info"><div class="info-grid">'
        f'<div class="info-item"><div class="info-label">Categoria</div>'
        f'<div class="info-value">{asset_row.category}</div></div>'
        f'<div class="info-item"><div class="info-label">Regione</div>'
        f'<div class="info-value">{asset_row.region or "generic"}</div></div>'
        f'<div class="info-item"><div class="info-label">Stagione</div>'
        f'<div class="info-value">{asset_row.season or "all"}</div></div>'
        f'<div class="info-item"><div class="info-label">Pagina</div>'
        f'<div class="info-value">{asset_row.page_context or "-"}</div></div>'
        f'<div class="info-item"><div class="info-label">Prodotto</div>'
        f'<div class="info-value">{asset_row.product_type or "generic"}</div></div>'
        f'<div class="info-item"><div class="info-label">Mood</div>'
        f'<div class="info-value">{asset_row.mood or "-"}</div></div>'
        f'<div class="info-item"><div class="info-label">Quality Score</div>'
        f'<div class="info-value">{asset_row.quality_score}/10</div></div>'
        f'<div class="info-item"><div class="info-label">Colore Dominante</div>'
        f'<div class="info-value" style="display:flex;align-items:center;gap:8px;">'
        f'<span style="width:16px;height:16px;border-radius:4px;'
        f'background:{asset_row.dominant_color or "#09090b"};display:inline-block;"></span>'
        f'{asset_row.dominant_color or "N/A"}</div></div>'
        f'</div></div></body></html>'
    )

    return HTMLResponse(content=page)
