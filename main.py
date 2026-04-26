# -*- coding: utf-8 -*-
"""
ItalyFlow AI - Main Application v3.0
=====================================
Redesign: Modern SaaS Tech (Linear/Vercel/Stripe-inspired)
Features: Multi-market parallel audit, flag icons, comparative tabs
v3.0: Dashboard router integration
"""
import asyncio
import base64
import hashlib
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from datetime import datetime
from typing import List

from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from google import genai
from google.genai import types
from sqlalchemy.orm import Session

from config import settings
from database import get_db, AuditResult, AuditBatch
from schemas import MarketEnum


# ============================================================================
# LOGGING
# ============================================================================
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("italyflow")

# ============================================================================
# APP INIT
# ============================================================================
# ============================================================================
# ItalyFlow AI - Section 2 + Unified Home + Visuals (PASTE BLOCK)
# Place this AFTER the "app = FastAPI(...)" line in main.py.
# Replace any older Section 2 block you may have.
# ============================================================================

from pathlib import Path as _Path
from fastapi.staticfiles import StaticFiles as _StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware as _BHM
from starlette.responses import Response as _Resp

# --- Static mount for hero images and certificates ---
_static_dir = _Path(__file__).resolve().parent / "static"
_static_dir.mkdir(parents=True, exist_ok=True)
try:
    app.mount("/static", _StaticFiles(directory=str(_static_dir)), name="static")
except Exception as _e:
    print("WARN: /static mount skipped:", _e)

# --- Aggressive cache headers for /static/visuals/* ---
class _IfStaticCache(_BHM):
    async def dispatch(self, request, call_next):
        resp: _Resp = await call_next(request)
        if request.url.path.startswith("/static/visuals/"):
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp

try:
    app.add_middleware(_IfStaticCache)
except Exception:
    pass

# --- Unified home router ('/' landing) ---
from app.routers.home import router as if_home_router
app.include_router(if_home_router)

# --- Visuals API ---
from app.routers.visuals import api as if_visuals_api
app.include_router(if_visuals_api)

# --- Section 2: Labels, Compliance, Translation, Collaboration ---
from app.routers.labels import router as if_labels_router, api as if_labels_api
from app.routers.compliance import router as if_compliance_router, api as if_compliance_api
from app.routers.translation import api as if_translation_api
from app.routers.collaboration import api as if_collab_api

app.include_router(if_labels_router)
app.include_router(if_labels_api)
app.include_router(if_compliance_router)
app.include_router(if_compliance_api)
app.include_router(if_translation_api)
app.include_router(if_collab_api)

# --- Background scheduler (regulatory tracker) ---
from app.scheduler import start_scheduler as _if_start_sched, shutdown_scheduler as _if_stop_sched

@app.on_event("startup")
def _if_startup():
    try:
        _if_start_sched()
    except Exception as _e:
        print("WARN: scheduler not started:", _e)

@app.on_event("shutdown")
def _if_shutdown():
    try:
        _if_stop_sched()
    except Exception:
        pass

# ============================================================================
# END Section 2 + Visuals + Home block
# ============================================================================

from pathlib import Path
_static_dir = Path(__file__).resolve().parent / "static"
_static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

from app.routers.visuals import api as visuals_api
app.include_router(visuals_api)

# --- ItalyFlow AI Section 2 ---
from app.routers.labels import router as labels_router, api as labels_api
from app.routers.compliance import router as compliance_router, api as compliance_api
from app.routers.translation import api as translation_api
from app.routers.collaboration import api as collab_api

app.include_router(labels_router)
app.include_router(labels_api)
app.include_router(compliance_router)
app.include_router(compliance_api)
app.include_router(translation_api)
app.include_router(collab_api)

# --- Scheduler (regulatory tracker every 6h) ---
from app.scheduler import start_scheduler, shutdown_scheduler

@app.on_event("startup")
def _if_startup():
    start_scheduler()

@app.on_event("shutdown")
def _if_shutdown():
    shutdown_scheduler()


client = genai.Client(api_key=settings.GOOGLE_API_KEY)
executor = ThreadPoolExecutor(max_workers=5)



# ============================================================================
# CONSTANTS
# ============================================================================
MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_TYPES = set(settings.ALLOWED_CONTENT_TYPES)

# Bandiere con codice ISO per flagcdn.com
MARKETS = {
    "USA":       {"flag": "\U0001F1FA\U0001F1F8", "iso": "us", "law": "FDA 21 CFR 101",
                  "rules": "FDA 21 CFR 101 - Fair Packaging and Labeling Act. Required: product name in English, net quantity (oz/lbs), ingredient list (descending order), Nutrition Facts panel, allergen declaration (Big 9), manufacturer/distributor name and address, country of origin."},
    "Cina":      {"flag": "\U0001F1E8\U0001F1F3", "iso": "cn", "law": "GB 7718-2011",
                  "rules": "GB 7718-2011 National Food Safety Standard. Required: product name in Chinese, ingredient list in Chinese, net content (metric), production date, shelf life, storage conditions, manufacturer name/address in Chinese, product standard code, production license number (SC), importer info."},
    "Canada":    {"flag": "\U0001F1E8\U0001F1E6", "iso": "ca", "law": "CFIA / SFCR",
                  "rules": "CFIA Food and Drugs Act, Safe Food for Canadians Regulations. Required: bilingual (English/French) product name, net quantity (metric), ingredient list in both languages, Nutrition Facts table, allergen declaration, dealer name and address, country of origin, best before date."},
    "Giappone":  {"flag": "\U0001F1EF\U0001F1F5", "iso": "jp", "law": "Food Labeling Act",
                  "rules": "Food Labeling Act and Food Labeling Standards. Required: product name in Japanese, ingredient list in Japanese (with allergens), net content, best before date, storage method, manufacturer info in Japanese, country of origin, nutritional info."},
    "UK":        {"flag": "\U0001F1EC\U0001F1E7", "iso": "gb", "law": "FIR 2014",
                  "rules": "Food Information Regulations 2014. Required: product name in English, ingredient list with allergens emphasized, net quantity, best before/use by date, storage conditions, manufacturer/packer address, country of origin, nutritional declaration per 100g/ml, lot/batch number."},
    "Italia":    {"flag": "\U0001F1EE\U0001F1F9", "iso": "it", "law": "Reg. UE 1169/2011 + D.Lgs 231/2017",
                  "rules": "Reg. UE 1169/2011 + D.Lgs 231/2017. Obbligatori: denominazione alimento, ingredienti con allergeni evidenziati, quantita netta, TMC o data scadenza, condizioni conservazione, nome/sede operatore, paese origine, dichiarazione nutrizionale, lotto. Lingua: italiano."},
    "UE":        {"flag": "\U0001F1EA\U0001F1FA", "iso": "eu", "law": "Reg. UE 1169/2011",
                  "rules": "Reg. UE 1169/2011. Obbligatori: denominazione nella lingua dello stato membro, ingredienti con allergeni in evidenza, quantita netta, TMC/scadenza, condizioni conservazione, nome/indirizzo operatore, paese origine, dichiarazione nutrizionale per 100g/ml, lotto. Lingua: lingua ufficiale paese vendita."},
    "Corea":     {"flag": "\U0001F1F0\U0001F1F7", "iso": "kr", "law": "MFDS Food Labeling Standards",
                  "rules": "MFDS Food Labeling Standards. Obbligatori: denominazione coreano, tipo prodotto, indirizzo produttore, data produzione, scadenza, contenuto netto, ingredienti coreano, allergeni, valori nutrizionali formato coreano, conservazione, origine. Lingua: coreano."},
    "Argentina": {"flag": "\U0001F1E6\U0001F1F7", "iso": "ar", "law": "CAA + Ley 27.642",
                  "rules": "CAA Cap. V e Ley 27.642. Obbligatori: denominazione spagnolo, ingredienti, contenuto netto, fabbricante/importatore, origine, lotto, scadenza, conservazione, rotulado nutricional, sellos ottagonali neri (Ley 27.642), avvisi EDULCORANTES/CAFEINA. Lingua: spagnolo."},
    "Brasile":   {"flag": "\U0001F1E7\U0001F1F7", "iso": "br", "law": "RDC 429/2020 + IN 75/2020",
                  "rules": "ANVISA RDC 429/2020 e IN 75/2020. Obbligatori: denominazione portoghese, ingredienti con CONTEM allergeni, contenuto netto metrico, fabbricante/importatore, origine, lotto, validade, tabella nutrizionale per porzione e 100g, etiqueta frontal lente nera ALTO EM se supera limiti. Lingua: portoghese."},
}


# ============================================================================
# SYSTEM PROMPT
# ============================================================================
SYSTEM_PROMPT = (
    "Sei un auditor certificato di conformita etichette alimentari internazionali.\n\n"
    "RUOLO: Analizza l'immagine dell'etichetta e verifica OGNI campo obbligatorio "
    "per il mercato indicato.\n\n"
    "REGOLE:\n"
    "1. Se un campo e parzialmente leggibile, status=\"partial\" con confidence <70\n"
    "2. Se l'immagine e sfocata/illeggibile, compliance_score=0 e segnala in critical_issues\n"
    "3. Per ogni campo mancante, CITA l'articolo di legge specifico\n"
    "4. Il compliance_score e la percentuale di campi obbligatori trovati con confidence>80\n"
    "5. Non inventare informazioni non visibili nell'immagine\n"
    "6. Se il prodotto non e alimentare, segnalalo e score=0\n\n"
    "OUTPUT: Rispondi ESCLUSIVAMENTE con JSON valido. Nessun testo prima o dopo.\n\n"
    '{\n'
    '  "compliance_score": <0-100>,\n'
    '  "product_detected": "<nome>",\n'
    '  "language_detected": "<lingue>",\n'
    '  "fields": [{"name":"<campo>","status":"found|missing|partial","confidence":<0-100>,"detail":"<desc>","law_reference":"<art>"}],\n'
    '  "critical_issues": [{"issue":"<problema>","severity":"high|medium|low","law_reference":"<art>"}],\n'
    '  "recommendations": [{"action":"<azione>","priority":"alta|media|bassa","reason":"<motivo>"}],\n'
    '  "summary": "<riassunto italiano 3-4 frasi>"\n'
    '}\n\n'
    "Analizza TUTTI i campi obbligatori. Cita riferimenti di legge specifici. Rispondi SOLO con il JSON."
)


# ============================================================================
# HELPERS
# ============================================================================
def clean_json(text: str) -> str:
    if not text:
        return "{}"
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _error_result(message: str, error_type: str = "generic") -> dict:
    return {
        "compliance_score": 0, "product_detected": "Errore",
        "language_detected": "N/A", "fields": [],
        "critical_issues": [{"issue": message, "severity": "high", "law_reference": "N/A"}],
        "recommendations": [{"action": "Riprova con una foto nitida", "priority": "alta", "reason": error_type}],
        "summary": f"Analisi non completata: {error_type}.",
    }


def save_audit(market: str, result: dict, img_b64: str,
               filename: str = "upload.jpg", batch_id: int = None) -> AuditResult:
    return AuditResult(
        batch_id=batch_id,
        market=market,
        compliance_score=result.get("compliance_score", 0),
        product_detected=result.get("product_detected", "N/A"),
        language_detected=result.get("language_detected", "N/A"),
        summary=result.get("summary", ""),
        fields_detail=json.dumps(result.get("fields", []), ensure_ascii=False),
        critical_issues=json.dumps(result.get("critical_issues", []), ensure_ascii=False),
        recommendations=json.dumps(result.get("recommendations", []), ensure_ascii=False),
        image_data=img_b64,
        image_hash=hashlib.sha256(img_b64.encode()).hexdigest(),
        filename=filename,
        result_json=json.dumps(result, ensure_ascii=False),
    )


def load_audit_data(audit: AuditResult) -> dict:
    if audit.result_json:
        try:
            return json.loads(audit.result_json)
        except (json.JSONDecodeError, TypeError):
            pass
    data = {
        "compliance_score": audit.compliance_score or 0,
        "product_detected": audit.product_detected or "N/A",
        "language_detected": audit.language_detected or "N/A",
        "summary": audit.summary or "",
        "fields": [], "critical_issues": [], "recommendations": [],
    }
    for key, col in [("fields", "fields_detail"), ("critical_issues", "critical_issues"), ("recommendations", "recommendations")]:
        raw = getattr(audit, col, None)
        if raw:
            try:
                data[key] = json.loads(raw) if isinstance(raw, str) else raw
            except (json.JSONDecodeError, TypeError):
                data[key] = []
    return data


# ============================================================================
# AI ANALYSIS
# ============================================================================
def analyze_label(image_bytes: bytes, market: str, content_type: str = "image/jpeg") -> dict:
    rules = MARKETS.get(market, {}).get("rules", "")
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=content_type)
    prompt_text = "Mercato: " + market + "\n\nNormativa:\n" + rules + "\n\nAnalizza questa etichetta alimentare in modo approfondito."
    start_time = time.time()
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt_text), image_part])],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=settings.GEMINI_TEMPERATURE,
            max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
            response_mime_type="application/json",
        ),
    )
    latency_ms = round((time.time() - start_time) * 1000)
    raw = response.text
    logger.info("gemini_response market=%s latency_ms=%d", market, latency_ms)
    try:
        return json.loads(clean_json(raw))
    except json.JSONDecodeError:
        logger.error("json_parse_error market=%s", market)
        return _error_result("Risposta non valida dal modello", "json_parse_error")


def analyze_label_safe(image_bytes: bytes, market: str, content_type: str = "image/jpeg") -> dict:
    for attempt in range(settings.GEMINI_MAX_RETRIES):
        try:
            return analyze_label(image_bytes, market, content_type)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                wait = 5 * (attempt + 1)
                logger.warning("rate_limited attempt=%d wait_s=%d", attempt + 1, wait)
                time.sleep(wait)
                continue
            if "SAFETY" in error_str or "blocked" in error_str.lower():
                return _error_result("Immagine bloccata dal filtro di sicurezza", "content_filter")
            if "DEADLINE_EXCEEDED" in error_str or "timeout" in error_str.lower():
                time.sleep(2)
                continue
            logger.error("unexpected_error market=%s error=%s", market, error_str[:300])
            return _error_result(error_str[:200], "unexpected")
    return _error_result("Troppe richieste \u2014 riprova tra 1 minuto", "rate_limit_exhausted")


def _get_audit_count(db: Session) -> int:
    return db.query(AuditResult).count()


def flag_img(iso: str, size: int = 20) -> str:
    return (
        '<img src="https://flagcdn.com/' + iso + '.svg" '
        'width="' + str(size) + '" height="' + str(int(size * 0.75)) + '" '
        'alt="' + iso + '" style="border-radius:2px;vertical-align:middle;object-fit:cover">'
    )


# ============================================================================
# NAV HTML — v2
# ============================================================================
def nav_html(active: str = "home", audit_count: int = 0) -> str:
    badge = '<span class="nav-badge">' + str(audit_count) + '</span>' if audit_count else ""
    def ac(n):
        return 'class="nav-link active"' if active == n else 'class="nav-link"'
    return (
        '<nav class="nav"><div class="nav-inner">'
        '<a href="/" class="nav-brand">'
        '<div class="nav-logo"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5">'
        '<path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg></div>'
        '<span class="brand-text">ItalyFlow<span class="brand-ai">AI</span></span>'
        '</a>'
        '<div class="nav-links">'
        '<a href="/" ' + ac("home") + '>Home</a>'
        '<a href="/app" ' + ac("audit") + '>Audit</a>'
        '<a href="/history" ' + ac("history") + '>Storico' + badge + '</a>'
        '</div></div></nav>'
    )


# ============================================================================
# CSS DESIGN SYSTEM v2 — Linear/Vercel/Stripe inspired
# ============================================================================
DESIGN_TOKENS = """
:root{
  --bg-primary:#09090b;--bg-secondary:#0c0c0e;--bg-tertiary:#111113;
  --bg-card:rgba(255,255,255,.03);--bg-card-hover:rgba(255,255,255,.05);
  --border:rgba(255,255,255,.06);--border-hover:rgba(255,255,255,.12);
  --text-primary:#fafafa;--text-secondary:#a1a1aa;--text-tertiary:#71717a;--text-muted:#52525b;
  --accent:#22c55e;--accent-light:#4ade80;--accent-bg:rgba(34,197,94,.08);--accent-border:rgba(34,197,94,.15);
  --danger:#ef4444;--warning:#eab308;--info:#3b82f6;
  --radius-sm:8px;--radius-md:12px;--radius-lg:16px;--radius-xl:20px;--radius-2xl:24px;
  --shadow-sm:0 1px 2px rgba(0,0,0,.3);--shadow-md:0 4px 16px rgba(0,0,0,.4);--shadow-lg:0 8px 32px rgba(0,0,0,.5);
  --font:'Inter',system-ui,-apple-system,sans-serif;
  --transition:all .2s cubic-bezier(.4,0,.2,1);
}
"""

COMMON_CSS = DESIGN_TOKENS + """
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:var(--font);background:var(--bg-primary);color:var(--text-primary);min-height:100vh;overflow-x:hidden;-webkit-font-smoothing:antialiased;}
::selection{background:rgba(34,197,94,.3);color:#fff;}

/* NAV */
.nav{position:fixed;top:0;left:0;right:0;z-index:100;background:rgba(9,9,11,.8);backdrop-filter:blur(20px) saturate(1.4);border-bottom:1px solid var(--border);}
.nav-inner{max-width:1200px;margin:0 auto;padding:0 24px;height:56px;display:flex;align-items:center;justify-content:space-between;}
.nav-brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--text-primary);}
.nav-logo{width:32px;height:32px;background:linear-gradient(135deg,#16a34a,var(--accent));border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.brand-text{font-size:16px;font-weight:700;letter-spacing:-.03em;}
.brand-ai{font-size:9px;font-weight:800;color:var(--accent);background:var(--accent-bg);padding:2px 5px;border-radius:4px;margin-left:3px;letter-spacing:.06em;vertical-align:super;border:1px solid var(--accent-border);}
.nav-links{display:flex;gap:2px;}
.nav-link{color:var(--text-tertiary);text-decoration:none;padding:6px 14px;border-radius:var(--radius-sm);font-size:13px;font-weight:500;transition:var(--transition);}
.nav-link:hover{color:var(--text-primary);background:var(--bg-card);}
.nav-link.active{color:var(--accent);background:var(--accent-bg);}
.nav-badge{background:var(--accent);color:#fff;font-size:10px;padding:1px 6px;border-radius:10px;margin-left:4px;font-weight:700;}
.content{position:relative;z-index:1;padding-top:56px;}

/* UTILS */
.fade-up{opacity:0;transform:translateY(20px);transition:opacity .6s ease,transform .6s ease;}
.fade-up.visible{opacity:1;transform:translateY(0);}
.container{max-width:1200px;margin:0 auto;padding:0 24px;}
.glass{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-xl);backdrop-filter:blur(12px);}
.glass:hover{border-color:var(--border-hover);}

/* BUTTONS */
.btn-primary{display:inline-flex;align-items:center;gap:8px;background:var(--accent);color:#fff;padding:12px 24px;border-radius:var(--radius-md);font-size:14px;font-weight:600;text-decoration:none;transition:var(--transition);border:none;cursor:pointer;font-family:var(--font);}
.btn-primary:hover{background:var(--accent-light);transform:translateY(-1px);box-shadow:0 4px 24px rgba(34,197,94,.25);}
.btn-ghost{display:inline-flex;align-items:center;gap:8px;background:transparent;border:1px solid var(--border);color:var(--text-secondary);padding:12px 24px;border-radius:var(--radius-md);font-size:14px;font-weight:500;text-decoration:none;transition:var(--transition);cursor:pointer;font-family:var(--font);}
.btn-ghost:hover{background:var(--bg-card);color:var(--text-primary);border-color:var(--border-hover);}

/* RESPONSIVE */
@media(max-width:768px){.nav-inner{padding:0 16px;}.container{padding:0 16px;}}
"""

BG_CSS = """
.bg-gradient{position:fixed;top:0;left:0;right:0;bottom:0;z-index:0;pointer-events:none;}
.bg-gradient::before{content:'';position:absolute;top:-200px;left:50%;transform:translateX(-50%);width:800px;height:600px;background:radial-gradient(ellipse,rgba(34,197,94,.06) 0%,transparent 70%);filter:blur(60px);}
.bg-gradient::after{content:'';position:absolute;top:0;left:0;right:0;bottom:0;background:linear-gradient(180deg,rgba(9,9,11,.5) 0%,var(--bg-primary) 60%);}
.bg-grid{position:fixed;top:0;left:0;right:0;bottom:0;z-index:0;pointer-events:none;background-image:linear-gradient(rgba(255,255,255,.02) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.02) 1px,transparent 1px);background-size:64px 64px;mask-image:linear-gradient(180deg,rgba(0,0,0,.3) 0%,transparent 50%);}
"""

BG_HTML = '<div class="bg-gradient"></div><div class="bg-grid"></div>'

FADE_IN_JS = """
<script>
(function(){var els=document.querySelectorAll('.fade-up');
var obs=new IntersectionObserver(function(entries){entries.forEach(function(e){
if(e.isIntersecting){e.target.classList.add('visible');obs.unobserve(e.target);}});},
{threshold:0.1});els.forEach(function(el){obs.observe(el);});})();
</script>
"""

COUNTUP_JS = """
<script>
(function(){var els=document.querySelectorAll('.countup');
var obs=new IntersectionObserver(function(entries){entries.forEach(function(e){
if(e.isIntersecting){var el=e.target,t=parseInt(el.dataset.target),s=el.dataset.suffix||'',
d=Math.max(1,Math.floor(2000/t)),c=0;var iv=setInterval(function(){c+=Math.ceil(t/60);
if(c>=t){c=t;clearInterval(iv);}el.textContent=c.toLocaleString()+s;},d);
obs.unobserve(el);}});},{threshold:0.3});els.forEach(function(el){obs.observe(el);});})();
</script>
"""


# ============================================================================
# LANDING PAGE v2
# ============================================================================
@app.get("/", response_class=HTMLResponse)
async def landing(db: Session = Depends(get_db)):
    count = _get_audit_count(db)

    # Market pills
    market_pills = ""
    for code, info in MARKETS.items():
        market_pills += (
            '<div class="mkt-pill">' + flag_img(info["iso"], 18)
            + ' <span class="mkt-pill-name">' + code + '</span>'
            + '<span class="mkt-pill-law">' + info["law"] + '</span></div>'
        )

    page_css = COMMON_CSS + BG_CSS + """
    .hero{text-align:center;padding:120px 24px 60px;position:relative;z-index:1;}
    .hero-eyebrow{display:inline-flex;align-items:center;gap:8px;background:var(--accent-bg);border:1px solid var(--accent-border);padding:6px 16px;border-radius:100px;font-size:12px;font-weight:600;color:var(--accent-light);margin-bottom:28px;}
    .hero-dot{width:6px;height:6px;background:var(--accent);border-radius:50%;animation:pulse 2s ease infinite;}
    @keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.7)}}
    h1{font-size:clamp(40px,6vw,68px);font-weight:800;line-height:1.05;letter-spacing:-.045em;margin-bottom:20px;color:var(--text-primary);}
    h1 .accent{background:linear-gradient(135deg,#16a34a,#4ade80);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
    .hero-sub{font-size:clamp(16px,1.8vw,19px);color:var(--text-tertiary);max-width:560px;margin:0 auto 36px;line-height:1.7;}
    .hero-actions{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;}

    /* STATS */
    .stats-strip{max-width:800px;margin:60px auto 0;display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden;background:var(--bg-card);}
    .stat{padding:24px 16px;text-align:center;border-right:1px solid var(--border);}
    .stat:last-child{border-right:none;}
    .stat-val{font-size:28px;font-weight:800;letter-spacing:-.03em;color:var(--text-primary);}
    .stat-val.green{color:var(--accent);}
    .stat-lbl{font-size:11px;color:var(--text-muted);margin-top:4px;font-weight:500;}

    /* SECTIONS */
    .section{padding:100px 0;position:relative;z-index:1;}
    .section-header{text-align:center;margin-bottom:56px;}
    .section-eyebrow{font-size:12px;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.1em;margin-bottom:12px;}
    .section-title{font-size:clamp(28px,3.5vw,40px);font-weight:800;letter-spacing:-.03em;margin-bottom:12px;}
    .section-sub{font-size:15px;color:var(--text-tertiary);max-width:500px;margin:0 auto;line-height:1.6;}

    /* MODULES */
    .mod-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}
    .mod-card{padding:28px 24px;border-radius:var(--radius-lg);background:var(--bg-card);border:1px solid var(--border);transition:var(--transition);position:relative;overflow:hidden;}
    .mod-card:hover{border-color:var(--accent-border);background:var(--bg-card-hover);transform:translateY(-2px);}
    .mod-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--accent-border),transparent);opacity:0;transition:opacity .3s;}
    .mod-card:hover::before{opacity:1;}
    .mod-icon{font-size:24px;margin-bottom:14px;}
    .mod-name{font-size:15px;font-weight:700;margin-bottom:6px;letter-spacing:-.01em;}
    .mod-desc{font-size:13px;color:var(--text-tertiary);line-height:1.5;}
    .mod-tag{display:inline-block;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;margin-top:12px;text-transform:uppercase;letter-spacing:.04em;}
    .mod-tag.live{background:var(--accent-bg);color:var(--accent);border:1px solid var(--accent-border);}
    .mod-tag.soon{background:rgba(234,179,8,.08);color:#eab308;border:1px solid rgba(234,179,8,.15);}

    /* MARKETS GRID */
    .mkt-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;}
    .mkt-pill{display:flex;align-items:center;gap:8px;padding:14px 16px;border-radius:var(--radius-md);background:var(--bg-card);border:1px solid var(--border);transition:var(--transition);flex-wrap:wrap;}
    .mkt-pill:hover{border-color:var(--accent-border);background:var(--bg-card-hover);}
    .mkt-pill-name{font-size:13px;font-weight:700;color:var(--text-primary);}
    .mkt-pill-law{font-size:10px;color:var(--text-muted);width:100%;margin-top:2px;padding-left:26px;}

    /* CTA */
    .cta{text-align:center;padding:100px 24px 120px;position:relative;z-index:1;}
    .cta h2{font-size:clamp(28px,4vw,42px);font-weight:800;letter-spacing:-.03em;margin-bottom:14px;}
    .cta h2 .accent{background:linear-gradient(135deg,#16a34a,#4ade80);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
    .cta p{color:var(--text-tertiary);font-size:16px;margin-bottom:32px;line-height:1.6;}

    @media(max-width:768px){.stats-strip{grid-template-columns:repeat(2,1fr);}.mod-grid{grid-template-columns:1fr;}.mkt-grid{grid-template-columns:repeat(2,1fr);}.hero-actions{flex-direction:column;align-items:center;}}
    """

    return HTMLResponse(
        "<!DOCTYPE html><html lang='it'><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>ItalyFlow AI \u2014 Compliance, engineered for export.</title>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap' rel='stylesheet'>"
        "<style>" + page_css + "</style></head><body>"
        + nav_html("home", count) + BG_HTML
        + '<div class="content">'

        # HERO
        + '<section class="hero">'
        + '<div class="hero-eyebrow fade-up"><div class="hero-dot"></div>Export Intelligence Platform</div>'
        + '<h1 class="fade-up">Porta il <span class="accent">Made in Italy</span><br>nel mondo. Senza rischi.</h1>'
        + '<p class="hero-sub fade-up">Verifica la conformit\u00e0 delle tue etichette alimentari su 10+ mercati internazionali in 2 secondi. Un\'unica analisi, tutti i mercati.</p>'
        + '<div class="hero-actions fade-up">'
        + '<a href="/app" class="btn-primary">\u2192 Inizia Audit Gratuito</a>'
        + '<a href="#markets" class="btn-ghost">Scopri i mercati</a>'
        + '</div>'

        # STATS
        + '<div class="stats-strip fade-up">'
        + '<div class="stat"><div class="stat-val green countup" data-target="10" data-suffix="+">0</div><div class="stat-lbl">Mercati</div></div>'
        + '<div class="stat"><div class="stat-val countup" data-target="90" data-suffix="%">0</div><div class="stat-lbl">Automation rate</div></div>'
        + '<div class="stat"><div class="stat-val green countup" data-target="2" data-suffix="s">0</div><div class="stat-lbl">Latenza audit</div></div>'
        + '<div class="stat"><div class="stat-val countup" data-target="20000" data-suffix="">0</div><div class="stat-lbl">PMI target 2030</div></div>'
        + '</div></section>'

        # MODULES
        + '<section class="section"><div class="container">'
        + '<div class="section-header fade-up"><div class="section-eyebrow">Moduli</div>'
        + '<div class="section-title">Una piattaforma. Tutto l\'export.</div>'
        + '<div class="section-sub">Ogni modulo risolve un pezzo della catena. Inizia con l\'audit, scala con l\'AI.</div></div>'
        + '<div class="mod-grid fade-up">'
        + '<div class="mod-card"><div class="mod-icon">\U0001F50D</div><div class="mod-name">AI Label Audit</div><div class="mod-desc">Verifica conformit\u00e0 etichette su 10+ mercati con visione artificiale. Multi-mercato in parallelo.</div><div class="mod-tag live">Live</div></div>'
        + '<div class="mod-card"><div class="mod-icon">\U0001F91D</div><div class="mod-name">Buyer Matchmaking</div><div class="mod-desc">Matching predittivo con buyer internazionali verificati per il tuo prodotto.</div><div class="mod-tag soon">Q4 2026</div></div>'
        + '<div class="mod-card"><div class="mod-icon">\U0001F30D</div><div class="mod-name">Localizzazione AI</div><div class="mod-desc">Adattamento culturale automatico di packaging e comunicazione per ogni mercato.</div><div class="mod-tag soon">2027</div></div>'
        + '<div class="mod-card"><div class="mod-icon">\u2696\uFE0F</div><div class="mod-name">Compliance Dinamica</div><div class="mod-desc">Monitoraggio continuo normative con alert automatici su cambiamenti.</div><div class="mod-tag soon">2027</div></div>'
        + '<div class="mod-card"><div class="mod-icon">\u2744\uFE0F</div><div class="mod-name">Cold Chain AI</div><div class="mod-desc">Monitoraggio IoT catena del freddo con predizione anomalie in tempo reale.</div><div class="mod-tag soon">2028</div></div>'
        + '<div class="mod-card"><div class="mod-icon">\U0001F4E6</div><div class="mod-name">Dynamic Batching</div><div class="mod-desc">Ottimizzazione logistica con batching intelligente delle spedizioni.</div><div class="mod-tag soon">2028</div></div>'
        + '</div></div></section>'

        # MARKETS
        + '<section class="section" id="markets"><div class="container">'
        + '<div class="section-header fade-up"><div class="section-eyebrow">Mercati</div>'
        + '<div class="section-title">10 normative. Un click.</div>'
        + '<div class="section-sub">Ogni mercato con le sue regole specifiche, coperte dal nostro motore di compliance.</div></div>'
        + '<div class="mkt-grid fade-up">' + market_pills + '</div>'
        + '</div></section>'

        # CTA
        + '<section class="cta fade-up">'
        + '<h2>Pronto a <span class="accent">esportare</span>?</h2>'
        + '<p>Carica la tua etichetta, seleziona i mercati target, ottieni un report comparativo in 2 secondi.</p>'
        + '<a href="/app" class="btn-primary">\u2192 Lancia il tuo primo Audit</a>'
        + '</section>'

        + '</div>' + FADE_IN_JS + COUNTUP_JS + "</body></html>"
    )


# ============================================================================
# AUDIT PAGE v2 — Multi-market select
# ============================================================================
@app.get("/app", response_class=HTMLResponse)
async def audit_page(db: Session = Depends(get_db)):
    count = _get_audit_count(db)

    # Market checkboxes con bandiere
    market_checks = ""
    for code, info in MARKETS.items():
        market_checks += (
            '<label class="mkt-check" data-market="' + code + '">'
            '<input type="checkbox" name="markets" value="' + code + '">'
            '<div class="mkt-check-inner">'
            + flag_img(info["iso"], 24)
            + '<div class="mkt-check-info">'
            + '<span class="mkt-check-name">' + code + '</span>'
            + '<span class="mkt-check-law">' + info["law"] + '</span>'
            + '</div></div></label>'
        )

    page_css = COMMON_CSS + BG_CSS + """
    .audit-wrap{max-width:880px;margin:0 auto;padding:48px 24px;}
    .audit-card{padding:48px 40px;position:relative;overflow:hidden;}
    .audit-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--accent),transparent);}
    .audit-header{margin-bottom:36px;}
    .audit-title{font-size:24px;font-weight:800;letter-spacing:-.03em;margin-bottom:6px;}
    .audit-title .accent{color:var(--accent);}
    .audit-sub{color:var(--text-tertiary);font-size:14px;}

    /* MARKET SELECTOR */
    .mkt-selector{margin-bottom:28px;}
    .mkt-selector-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;}
    .form-label{font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em;}
    .mkt-count{font-size:12px;color:var(--accent);font-weight:600;}
    .mkt-grid-select{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;}
    .mkt-check{cursor:pointer;display:block;}
    .mkt-check input{display:none;}
    .mkt-check-inner{display:flex;align-items:center;gap:12px;padding:12px 16px;border-radius:var(--radius-md);border:1px solid var(--border);background:var(--bg-card);transition:var(--transition);}
    .mkt-check:hover .mkt-check-inner{border-color:var(--border-hover);background:var(--bg-card-hover);}
    .mkt-check input:checked+.mkt-check-inner{border-color:var(--accent);background:var(--accent-bg);box-shadow:0 0 0 1px var(--accent-border);}
    .mkt-check-info{display:flex;flex-direction:column;gap:1px;}
    .mkt-check-name{font-size:14px;font-weight:600;color:var(--text-primary);}
    .mkt-check-law{font-size:11px;color:var(--text-muted);}
    .select-actions{display:flex;gap:8px;margin-top:10px;}
    .select-actions button{font-size:11px;color:var(--text-tertiary);background:none;border:1px solid var(--border);padding:4px 12px;border-radius:6px;cursor:pointer;font-family:var(--font);font-weight:500;transition:var(--transition);}
    .select-actions button:hover{color:var(--text-primary);border-color:var(--border-hover);}

    /* UPLOAD */
    .upload-zone{border:2px dashed var(--border);border-radius:var(--radius-lg);padding:40px 24px;text-align:center;cursor:pointer;transition:var(--transition);margin-bottom:28px;}
    .upload-zone:hover,.upload-zone.dragover{border-color:var(--accent);background:var(--accent-bg);}
    .upload-zone.has-file{border-color:var(--accent-border);border-style:solid;background:var(--accent-bg);}
    .upload-icon{font-size:32px;margin-bottom:10px;opacity:.3;}
    .upload-text{color:var(--text-tertiary);font-size:13px;}
    .upload-text strong{color:var(--text-secondary);}
    .file-info{display:none;align-items:center;gap:10px;padding:10px 14px;background:var(--accent-bg);border:1px solid var(--accent-border);border-radius:var(--radius-sm);margin-top:10px;font-size:13px;color:var(--accent);}
    .file-info.visible{display:flex;}
    .submit-btn{width:100%;padding:16px;background:var(--accent);color:#fff;border:none;border-radius:var(--radius-md);font-size:15px;font-weight:700;cursor:pointer;transition:var(--transition);font-family:var(--font);}
    .submit-btn:hover:not(:disabled){background:var(--accent-light);transform:translateY(-1px);box-shadow:0 4px 24px rgba(34,197,94,.25);}
    .submit-btn:disabled{opacity:.4;cursor:not-allowed;}

    /* RESULTS */
    #resultArea{margin-top:32px;}
    .results-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;}
    .results-title{font-size:18px;font-weight:700;}
    .tab-bar{display:flex;gap:4px;overflow-x:auto;padding-bottom:4px;border-bottom:1px solid var(--border);margin-bottom:24px;}
    .tab{display:flex;align-items:center;gap:6px;padding:8px 16px;border-radius:var(--radius-sm) var(--radius-sm) 0 0;font-size:13px;font-weight:600;color:var(--text-tertiary);cursor:pointer;transition:var(--transition);white-space:nowrap;border:none;background:none;font-family:var(--font);border-bottom:2px solid transparent;}
    .tab:hover{color:var(--text-primary);background:var(--bg-card);}
    .tab.active{color:var(--accent);border-bottom-color:var(--accent);background:var(--accent-bg);}
    .tab-panel{display:none;}
    .tab-panel.active{display:block;}
    .result-card{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-lg);padding:24px;margin-bottom:12px;}
    .result-card h3{font-size:12px;font-weight:700;margin-bottom:16px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;}
    .score-ring{text-align:center;padding:24px;}
    .score-big{font-size:56px;font-weight:900;letter-spacing:-.04em;}
    .score-lbl{font-size:13px;color:var(--text-tertiary);margin-top:2px;}
    .meta-row{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:14px;}
    .meta-box{background:var(--bg-secondary);border-radius:var(--radius-sm);padding:12px;text-align:center;}
    .meta-val{font-size:13px;font-weight:600;color:var(--text-primary);}
    .meta-lbl{font-size:10px;color:var(--text-muted);margin-top:2px;}
    .field-row{display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border);}
    .field-row:last-child{border-bottom:none;}
    .field-name{font-size:13px;color:var(--text-secondary);}
    .field-tag{font-size:10px;padding:2px 8px;border-radius:4px;font-weight:700;text-transform:uppercase;}
    .field-tag.found{background:var(--accent-bg);color:var(--accent);}
    .field-tag.missing{background:rgba(239,68,68,.08);color:var(--danger);}
    .field-tag.partial{background:rgba(234,179,8,.08);color:var(--warning);}
    .issue-row{padding:10px 12px;background:rgba(239,68,68,.04);border-left:3px solid var(--danger);border-radius:0 var(--radius-sm) var(--radius-sm) 0;margin-bottom:6px;font-size:12px;color:#fca5a5;}
    .issue-row.medium{background:rgba(234,179,8,.04);border-left-color:var(--warning);color:#fde68a;}
    .issue-row.low{background:rgba(34,197,94,.04);border-left-color:var(--accent);color:#86efac;}
    .rec-row{padding:8px 12px;background:rgba(59,130,246,.04);border-radius:var(--radius-sm);margin-bottom:6px;font-size:12px;color:#93c5fd;border:1px solid rgba(59,130,246,.08);}
    .pdf-btn{display:inline-flex;align-items:center;gap:6px;background:var(--bg-card);border:1px solid var(--border);color:var(--text-secondary);padding:10px 20px;border-radius:var(--radius-md);font-size:13px;font-weight:600;cursor:pointer;transition:var(--transition);text-decoration:none;font-family:var(--font);}
    .pdf-btn:hover{background:var(--bg-card-hover);border-color:var(--accent-border);color:var(--text-primary);}

    /* PROGRESS */
    .progress-wrap{margin-top:20px;}
    .progress-item{display:flex;align-items:center;gap:12px;padding:10px 14px;background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-md);margin-bottom:6px;font-size:13px;transition:var(--transition);}
    .progress-item.done{border-color:var(--accent-border);}
    .progress-item.error{border-color:rgba(239,68,68,.3);}
    .progress-spinner{width:16px;height:16px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .6s linear infinite;}
    .progress-check{color:var(--accent);font-size:14px;}
    @keyframes spin{to{transform:rotate(360deg)}}

    @media(max-width:768px){.mkt-grid-select{grid-template-columns:1fr;}.meta-row{grid-template-columns:1fr;}}
    """

    return HTMLResponse(
        "<!DOCTYPE html><html lang='it'><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Audit \u2014 ItalyFlow AI</title>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap' rel='stylesheet'>"
        "<style>" + page_css + "</style></head><body>"
        + nav_html("audit", count) + BG_HTML
        + '<div class="content"><div class="audit-wrap"><div class="audit-card glass">'
        + '<div class="audit-header"><div class="audit-title">\U0001F50D Audit <span class="accent">Multi-Mercato</span></div>'
        + '<div class="audit-sub">Carica un\'immagine, seleziona uno o pi\u00f9 mercati, ottieni un\'analisi comparativa.</div></div>'

        # MARKET SELECTOR
        + '<div class="mkt-selector">'
        + '<div class="mkt-selector-header"><span class="form-label">Seleziona mercati</span><span class="mkt-count" id="mktCount">0 selezionati</span></div>'
        + '<div class="mkt-grid-select">' + market_checks + '</div>'
        + '<div class="select-actions">'
        + '<button onclick="toggleAll(true)">Seleziona tutti</button>'
        + '<button onclick="toggleAll(false)">Deseleziona</button>'
        + '</div></div>'

        # UPLOAD
        + '<div class="form-label" style="margin-bottom:8px">Immagine etichetta</div>'
        + '<div class="upload-zone" id="dropZone" onclick="document.getElementById(\'fileInput\').click()">'
        + '<div class="upload-icon">\U0001F4F7</div>'
        + '<div class="upload-text"><strong>Clicca o trascina</strong> un\'immagine</div>'
        + '<div class="upload-text" style="font-size:11px;margin-top:4px;color:var(--text-muted)">JPG, PNG, WebP \u2014 max ' + str(settings.MAX_FILE_SIZE_MB) + 'MB</div>'
        + '</div>'
        + '<input type="file" id="fileInput" accept="image/*" style="display:none">'
        + '<div class="file-info" id="fileInfo">\u2705 <span id="fileName"></span></div>'

        # SUBMIT
        + '<button class="submit-btn" id="submitBtn" disabled onclick="submitMultiAudit()">\u2192 Analizza Conformit\u00e0</button>'
        + '<div id="resultArea"></div>'
        + '</div></div></div>'
        + BG_HTML
        + """
<script>
var fileInput=document.getElementById('fileInput'),dropZone=document.getElementById('dropZone'),
fileInfo=document.getElementById('fileInfo'),fileName=document.getElementById('fileName'),
submitBtn=document.getElementById('submitBtn'),mktCount=document.getElementById('mktCount');
var MAX_SIZE=""" + str(MAX_FILE_SIZE) + """;

function updateState(){
  var checks=document.querySelectorAll('input[name=markets]:checked');
  mktCount.textContent=checks.length+' selezionat'+(checks.length===1?'o':'i');
  submitBtn.disabled=!(fileInput.files[0]&&checks.length>0);
}
document.querySelectorAll('input[name=markets]').forEach(function(cb){cb.addEventListener('change',updateState);});

function toggleAll(state){
  document.querySelectorAll('input[name=markets]').forEach(function(cb){cb.checked=state;});
  updateState();
}

fileInput.addEventListener('change',function(){if(this.files[0])handleFile(this.files[0]);});
dropZone.addEventListener('dragover',function(e){e.preventDefault();this.classList.add('dragover');});
dropZone.addEventListener('dragleave',function(){this.classList.remove('dragover');});
dropZone.addEventListener('drop',function(e){e.preventDefault();this.classList.remove('dragover');if(e.dataTransfer.files[0]){fileInput.files=e.dataTransfer.files;handleFile(e.dataTransfer.files[0]);}});

function handleFile(f){
  if(f.size>MAX_SIZE){alert('File troppo grande. Max """ + str(settings.MAX_FILE_SIZE_MB) + """MB');return;}
  fileName.textContent=f.name+' ('+Math.round(f.size/1024)+'KB)';
  fileInfo.classList.add('visible');dropZone.classList.add('has-file');
  updateState();
}

function submitMultiAudit(){
  var f=fileInput.files[0];if(!f)return;
  var checks=document.querySelectorAll('input[name=markets]:checked');
  var markets=Array.from(checks).map(function(c){return c.value;});
  if(!markets.length){alert('Seleziona almeno un mercato');return;}

  submitBtn.disabled=true;submitBtn.textContent='Analisi in corso...';

  // Show progress
  var prog='<div class="progress-wrap">';
  markets.forEach(function(m){prog+='<div class="progress-item" id="prog-'+m+'"><div class="progress-spinner"></div><span>'+m+' \u2014 analisi in corso...</span></div>';});
  prog+='</div>';
  document.getElementById('resultArea').innerHTML=prog;

  var fd=new FormData();
  fd.append('file',f);
  markets.forEach(function(m){fd.append('markets',m);});

  fetch('/analyze',{method:'POST',body:fd}).then(function(r){return r.json();}).then(function(d){showMultiResult(d,markets);})
  .catch(function(e){alert('Errore: '+e.message);submitBtn.disabled=false;submitBtn.textContent='\\u2192 Analizza Conformit\\u00e0';});
}

function showMultiResult(d,markets){
  var results=d.results||{};var batchId=d.batch_id||0;
  var h='<div class="results-header"><div class="results-title">Risultati Audit</div>';
  h+='<button class="pdf-btn" onclick="window.open(\\'/pdf/batch/'+batchId+'\\',\\'_blank\\')">\\uD83D\\uDCC4 Report PDF Comparativo</button></div>';

  // Tab bar
  h+='<div class="tab-bar">';
  var idx=0;
  for(var m in results){
    var sc=results[m].compliance_score||0;
    var col=sc>=80?'var(--accent)':(sc>=50?'var(--warning)':'var(--danger)');
    h+='<button class="tab'+(idx===0?' active':'')+'" onclick="switchTab(this,\\'panel-'+m+'\\')" data-market="'+m+'">';
    h+='<img src="https://flagcdn.com/'+(d.isos[m]||'')+'.svg" width="16" height="12" style="border-radius:2px"> ';
    h+=m+' <span style="color:'+col+';font-weight:800">'+sc+'</span></button>';
    idx++;
  }
  h+='</div>';

  // Tab panels
  idx=0;
  for(var m in results){
    var r=results[m];
    var sc=r.compliance_score||0;
    var col=sc>=80?'var(--accent)':(sc>=50?'var(--warning)':'var(--danger)');
    h+='<div class="tab-panel'+(idx===0?' active':'')+'" id="panel-'+m+'">';
    h+='<div class="result-card"><div class="score-ring"><div class="score-big" style="color:'+col+'">'+sc+'</div><div class="score-lbl">Compliance Score \u2014 '+m+'</div></div>';
    h+='<div class="meta-row"><div class="meta-box"><div class="meta-val">'+(r.product_detected||'N/A')+'</div><div class="meta-lbl">Prodotto</div></div>';
    h+='<div class="meta-box"><div class="meta-val">'+(r.language_detected||'N/A')+'</div><div class="meta-lbl">Lingua</div></div>';
    h+='<div class="meta-box"><div class="meta-val">'+m+'</div><div class="meta-lbl">Mercato</div></div></div></div>';

    if(r.summary){h+='<div class="result-card"><h3>Sommario</h3><p style="font-size:13px;color:var(--text-secondary);line-height:1.6">'+r.summary+'</p></div>';}

    if(r.fields&&r.fields.length){h+='<div class="result-card"><h3>Campi Analizzati</h3>';
      r.fields.forEach(function(f){
        h+='<div class="field-row"><div><div class="field-name">'+f.name+'</div></div>';
        h+='<span class="field-tag '+(f.status||'missing')+'">'+(f.status||'missing')+'</span></div>';
      });h+='</div>';}

    if(r.critical_issues&&r.critical_issues.length){h+='<div class="result-card"><h3>Problemi Critici</h3>';
      r.critical_issues.forEach(function(ci){
        h+='<div class="issue-row '+ci.severity+'"><strong>['+ci.severity.toUpperCase()+']</strong> '+ci.issue+' <span style="opacity:.5">('+ci.law_reference+')</span></div>';
      });h+='</div>';}

    if(r.recommendations&&r.recommendations.length){h+='<div class="result-card"><h3>Raccomandazioni</h3>';
      r.recommendations.forEach(function(rec){
        h+='<div class="rec-row"><strong>['+rec.priority+']</strong> '+rec.action+' \\u2014 '+rec.reason+'</div>';
      });h+='</div>';}
    h+='</div>';
    idx++;
  }

  document.getElementById('resultArea').innerHTML=h;
  submitBtn.disabled=false;submitBtn.textContent='\\u2192 Analizza Conformit\\u00e0';
}

function switchTab(btn,panelId){
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  document.querySelectorAll('.tab-panel').forEach(function(p){p.classList.remove('active');});
  btn.classList.add('active');
  document.getElementById(panelId).classList.add('active');
}
</script>
"""
        + "</body></html>"
    )


# ============================================================================
# ANALYZE API v2 — Multi-market parallel
# ============================================================================
@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    markets: List[str] = Form(...),
    db: Session = Depends(get_db),
):
    # Validate content type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Tipo file non supportato: {file.content_type}")

    image_bytes = await file.read()
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File troppo grande. Max: {settings.MAX_FILE_SIZE_MB}MB")

    # Validate markets
    valid_markets = [m for m in markets if m in MARKETS]
    if not valid_markets:
        raise HTTPException(400, "Nessun mercato valido selezionato")
    if len(valid_markets) > settings.MAX_MARKETS_PER_AUDIT:
        raise HTTPException(400, f"Massimo {settings.MAX_MARKETS_PER_AUDIT} mercati per audit")

    content_type = file.content_type or "image/jpeg"
    img_b64 = base64.b64encode(image_bytes).decode()
    img_hash = hashlib.sha256(img_b64.encode()).hexdigest()

    logger.info("multi_audit_start markets=%s filename=%s", valid_markets, file.filename)

    # Create batch
    batch = AuditBatch(
        filename=file.filename or "upload.jpg",
        image_data=img_b64,
        image_hash=img_hash,
        markets_requested=json.dumps(valid_markets),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    # Run analyses in parallel using ThreadPoolExecutor
    loop = asyncio.get_event_loop()
    tasks = []
    for market in valid_markets:
        task = loop.run_in_executor(
            executor,
            analyze_label_safe, image_bytes, market, content_type,
        )
        tasks.append((market, task))

    results = {}
    isos = {}
    for market, task in tasks:
        result = await task
        results[market] = result
        isos[market] = MARKETS[market]["iso"]

        # Save individual audit
        audit = save_audit(market, result, img_b64,
                          filename=file.filename or "upload.jpg",
                          batch_id=batch.id)
        db.add(audit)

    db.commit()

    logger.info("multi_audit_complete batch_id=%d markets=%d", batch.id, len(results))

    return JSONResponse(content={
        "batch_id": batch.id,
        "results": results,
        "isos": isos,
    })


# ============================================================================
# HISTORY PAGE v2
# ============================================================================
@app.get("/history", response_class=HTMLResponse)
async def history_page(db: Session = Depends(get_db)):
    audits = db.query(AuditResult).order_by(AuditResult.created_at.desc()).all()
    total = len(audits)
    scores = [a.compliance_score or 0 for a in audits]
    avg_score = round(sum(scores) / total, 1) if total else 0
    compliant = sum(1 for s in scores if s >= 80)
    rate = round(compliant / total * 100) if total else 0

    rows = ""
    for a in audits:
        sc = a.compliance_score or 0
        color = "var(--accent)" if sc >= 80 else ("var(--warning)" if sc >= 50 else "var(--danger)")
        date_str = a.created_at.strftime("%d/%m/%Y %H:%M") if a.created_at else "N/A"
        mkt = a.market or "N/A"
        iso = MARKETS.get(mkt, {}).get("iso", "")
        flag = flag_img(iso, 16) + " " if iso else ""
        product = a.product_detected or "N/A"
        rows += (
            '<tr><td>' + date_str + '</td><td>' + flag + mkt + '</td><td>' + product
            + '</td><td><span style="color:' + color + ';font-weight:700">' + str(int(sc))
            + '</span></td><td>'
            + '<a href="/pdf/' + str(a.id) + '" class="act-btn" target="_blank">\U0001F4C4 PDF</a> '
            + '<button class="act-btn del" onclick="deleteAudit(' + str(a.id) + ',this)">\U0001F5D1</button>'
            + '</td></tr>'
        )

    page_css = COMMON_CSS + BG_CSS + """
    .hist-wrap{max-width:1100px;margin:0 auto;padding:48px 24px;}
    .hist-header{margin-bottom:32px;}
    .hist-title{font-size:24px;font-weight:800;letter-spacing:-.03em;margin-bottom:4px;}
    .hist-title .accent{color:var(--accent);}
    .hist-sub{color:var(--text-tertiary);font-size:14px;}
    .hist-stats{display:grid;grid-template-columns:repeat(3,1fr);border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden;margin-bottom:28px;background:var(--bg-card);}
    .hs{padding:20px;text-align:center;}
    .hs-val{font-size:24px;font-weight:800;letter-spacing:-.02em;}
    .hs-lbl{font-size:11px;color:var(--text-muted);margin-top:2px;}
    .hist-table{width:100%;border-collapse:collapse;background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden;}
    .hist-table th{padding:12px 16px;text-align:left;font-size:10px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid var(--border);background:var(--bg-secondary);}
    .hist-table td{padding:12px 16px;font-size:13px;color:var(--text-secondary);border-bottom:1px solid var(--border);}
    .hist-table tr:hover td{background:var(--bg-card-hover);}
    .hist-table tr:last-child td{border-bottom:none;}
    .act-btn{display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;transition:var(--transition);text-decoration:none;color:var(--text-tertiary);background:var(--bg-card);border:1px solid var(--border);font-family:var(--font);}
    .act-btn:hover{background:var(--bg-card-hover);color:var(--text-primary);}
    .act-btn.del:hover{background:rgba(239,68,68,.08);color:var(--danger);border-color:rgba(239,68,68,.2);}
    .empty{text-align:center;padding:80px 24px;color:var(--text-muted);}
    .empty-icon{font-size:40px;margin-bottom:14px;opacity:.3;}
    """

    return HTMLResponse(
        "<!DOCTYPE html><html lang='it'><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Storico \u2014 ItalyFlow AI</title>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap' rel='stylesheet'>"
        "<style>" + page_css + "</style></head><body>"
        + nav_html("history", total) + BG_HTML
        + '<div class="content"><div class="hist-wrap">'
        + '<div class="hist-header"><div class="hist-title">\U0001F4CB Storico <span class="accent">Audit</span></div>'
        + '<div class="hist-sub">Tutti gli audit effettuati con risultati e report.</div></div>'
        + '<div class="hist-stats">'
        + '<div class="hs"><div class="hs-val" style="color:var(--text-primary)">' + str(total) + '</div><div class="hs-lbl">Audit totali</div></div>'
        + '<div class="hs"><div class="hs-val" style="color:var(--accent)">' + str(avg_score) + '</div><div class="hs-lbl">Score medio</div></div>'
        + '<div class="hs"><div class="hs-val" style="color:var(--accent)">' + str(rate) + '%</div><div class="hs-lbl">Tasso conformit\u00e0</div></div>'
        + '</div>'
        + (
            '<table class="hist-table"><thead><tr><th>Data</th><th>Mercato</th><th>Prodotto</th><th>Score</th><th>Azioni</th></tr></thead><tbody>'
            + rows + '</tbody></table>'
            if audits else
            '<div class="empty"><div class="empty-icon">\U0001F4CB</div>'
            '<div style="font-size:15px">Nessun audit ancora.</div>'
            '<a href="/app" class="btn-primary" style="margin-top:16px;display:inline-flex">\u2192 Inizia ora</a></div>'
        )
        + '</div></div>' + BG_HTML
        + """
<script>
function deleteAudit(id,btn){
  if(!confirm('Eliminare questo audit?'))return;
  fetch('/delete/'+id,{method:'DELETE'}).then(function(r){
    if(r.status===404){alert('Audit non trovato');return;}
    return r.json();
  }).then(function(d){if(d&&d.ok)location.reload();});
}
</script>
"""
        + "</body></html>"
    )


# ============================================================================
# DELETE API
# ============================================================================
@app.delete("/delete/{audit_id}")
async def delete_audit(audit_id: int, db: Session = Depends(get_db)):
    audit = db.query(AuditResult).filter(AuditResult.id == audit_id).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit non trovato")
    db.delete(audit)
    db.commit()
    logger.info("audit_deleted audit_id=%d", audit_id)
    return JSONResponse(content={"ok": True, "deleted_id": audit_id})


# ============================================================================
# PDF — Single audit
# ============================================================================
@app.get("/pdf/{audit_id}")
async def download_pdf(audit_id: int, db: Session = Depends(get_db)):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

    audit = db.query(AuditResult).filter(AuditResult.id == audit_id).first()
    if not audit:
        raise HTTPException(404, "Audit non trovato")

    data = load_audit_data(audit)
    score = data.get("compliance_score", 0)
    market = audit.market or "N/A"
    law = MARKETS.get(market, {}).get("law", "N/A")
    date_str = audit.created_at.strftime("%d/%m/%Y %H:%M") if audit.created_at else "N/A"

    GREEN, RED, YELLOW = HexColor("#16a34a"), HexColor("#dc2626"), HexColor("#ca8a04")
    DARK, GRAY, GRAY_L = HexColor("#09090b"), HexColor("#71717a"), HexColor("#f4f4f5")

    def sc_color(s):
        return GREEN if s >= 80 else (YELLOW if s >= 50 else RED)

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("BrandTitle", fontName="Helvetica-Bold", fontSize=22, textColor=DARK, spaceAfter=2*mm))
    styles.add(ParagraphStyle("BrandSub", fontName="Helvetica", fontSize=10, textColor=GRAY, spaceAfter=6*mm))
    styles.add(ParagraphStyle("SH", fontName="Helvetica-Bold", fontSize=14, textColor=DARK, spaceBefore=8*mm, spaceAfter=4*mm))
    styles.add(ParagraphStyle("B2", fontName="Helvetica", fontSize=10, textColor=DARK, leading=14, spaceAfter=2*mm))

    story = []
    story.append(Paragraph("ItalyFlow AI", styles["BrandTitle"]))
    story.append(Paragraph("Report Audit \u2014 " + market + " \u2014 " + law, styles["BrandSub"]))
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY_L))
    story.append(Spacer(1, 4*mm))

    meta = [["Prodotto", data.get("product_detected", "N/A")], ["Lingua", data.get("language_detected", "N/A")], ["Data", date_str]]
    mt = Table(meta, colWidths=[30*mm, 135*mm])
    mt.setStyle(TableStyle([("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 10), ("TEXTCOLOR", (0,0), (0,-1), GRAY), ("BOTTOMPADDING", (0,0), (-1,-1), 4)]))
    story.append(mt)
    story.append(Spacer(1, 6*mm))

    sc_c = sc_color(score)
    sc_bg = HexColor("#dcfce7") if score >= 80 else (HexColor("#fefce8") if score >= 50 else HexColor("#fef2f2"))
    st = Table([[Paragraph('<font size="28"><b>' + str(int(score)) + '/100</b></font>', ParagraphStyle("sc", alignment=1, textColor=sc_c, fontName="Helvetica-Bold"))]], colWidths=[170*mm])
    st.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), sc_bg), ("ALIGN", (0,0), (-1,-1), "CENTER"), ("TOPPADDING", (0,0), (-1,-1), 10), ("BOTTOMPADDING", (0,0), (-1,-1), 10)]))
    story.append(st)

    if data.get("summary"):
        story.append(Paragraph("Sommario", styles["SH"]))
        story.append(Paragraph(data["summary"], styles["B2"]))

    fields = data.get("fields", [])
    if fields:
        story.append(Paragraph("Campi Analizzati", styles["SH"]))
        fd = [["Campo", "Stato", "Conf.", "Riferimento"]]
        for f in fields:
            fd.append([f.get("name", ""), f.get("status", "").upper(), str(f.get("confidence", "")), f.get("law_reference", "")])
        ft = Table(fd, colWidths=[55*mm, 25*mm, 20*mm, 70*mm])
        ft.setStyle(TableStyle([("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 9), ("BACKGROUND", (0,0), (-1,0), GRAY_L), ("GRID", (0,0), (-1,-1), 0.5, GRAY_L), ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4)]))
        story.append(ft)

    for iss in data.get("critical_issues", []):
        sev = iss.get("severity", "medium")
        c = RED if sev == "high" else (YELLOW if sev == "medium" else GREEN)
        story.append(Paragraph('<font color="' + c.hexval() + '"><b>[' + sev.upper() + ']</b></font> ' + iss.get("issue", ""), styles["B2"]))

    for r in data.get("recommendations", []):
        story.append(Paragraph('<b>[' + r.get("priority", "") + ']</b> ' + r.get("action", "") + ' \u2014 ' + r.get("reason", ""), styles["B2"]))

    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("Generato da ItalyFlow AI \u2014 " + date_str, ParagraphStyle("ft", fontName="Helvetica", fontSize=7, textColor=GRAY, alignment=TA_CENTER)))
    doc.build(story)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="audit_{audit_id}_{market}.pdf"'})


# ============================================================================
# PDF — Batch comparative report
# ============================================================================
@app.get("/pdf/batch/{batch_id}")
async def download_batch_pdf(batch_id: int, db: Session = Depends(get_db)):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak

    batch = db.query(AuditBatch).filter(AuditBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch non trovato")

    audits = db.query(AuditResult).filter(AuditResult.batch_id == batch_id).all()
    if not audits:
        raise HTTPException(404, "Nessun audit trovato per questo batch")

    GREEN, RED, YELLOW = HexColor("#16a34a"), HexColor("#dc2626"), HexColor("#ca8a04")
    DARK, GRAY, GRAY_L = HexColor("#09090b"), HexColor("#71717a"), HexColor("#f4f4f5")
    GREEN_L, YELLOW_L, RED_L = HexColor("#dcfce7"), HexColor("#fefce8"), HexColor("#fef2f2")

    def sc_color(s):
        return GREEN if s >= 80 else (YELLOW if s >= 50 else RED)
    def sc_bg(s):
        return GREEN_L if s >= 80 else (YELLOW_L if s >= 50 else RED_L)

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("BT", fontName="Helvetica-Bold", fontSize=22, textColor=DARK, spaceAfter=2*mm))
    styles.add(ParagraphStyle("BS", fontName="Helvetica", fontSize=10, textColor=GRAY, spaceAfter=6*mm))
    styles.add(ParagraphStyle("SH", fontName="Helvetica-Bold", fontSize=14, textColor=DARK, spaceBefore=6*mm, spaceAfter=4*mm))
    styles.add(ParagraphStyle("B2", fontName="Helvetica", fontSize=10, textColor=DARK, leading=14, spaceAfter=2*mm))

    date_str = batch.created_at.strftime("%d/%m/%Y %H:%M") if batch.created_at else "N/A"

    story = []
    story.append(Paragraph("ItalyFlow AI", styles["BT"]))
    story.append(Paragraph("Report Comparativo Multi-Mercato \u2014 " + date_str, styles["BS"]))
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY_L))
    story.append(Spacer(1, 4*mm))

    # Comparative summary table
    story.append(Paragraph("Riepilogo Comparativo", styles["SH"]))
    comp_data = [["Mercato", "Normativa", "Score", "Prodotto"]]
    for a in audits:
        law = MARKETS.get(a.market, {}).get("law", "N/A")
        sc = int(a.compliance_score or 0)
        comp_data.append([a.market, law, str(sc) + "/100", a.product_detected or "N/A"])

    comp_table = Table(comp_data, colWidths=[30*mm, 60*mm, 25*mm, 55*mm])
    comp_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), GRAY_L),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAY_L),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    # Color-code scores
    for i, a in enumerate(audits, 1):
        sc = a.compliance_score or 0
        comp_table.setStyle(TableStyle([
            ("TEXTCOLOR", (2, i), (2, i), sc_color(sc)),
            ("FONTNAME", (2, i), (2, i), "Helvetica-Bold"),
        ]))
    story.append(comp_table)

    # Detail per market
    for a in audits:
        story.append(PageBreak())
        data = load_audit_data(a)
        sc = data.get("compliance_score", 0)
        law = MARKETS.get(a.market, {}).get("law", "N/A")

        story.append(Paragraph(a.market + " \u2014 " + law, styles["SH"]))

        # Score box
        st = Table([[Paragraph('<font size="24"><b>' + str(int(sc)) + '/100</b></font>',
            ParagraphStyle("sc", alignment=1, textColor=sc_color(sc), fontName="Helvetica-Bold"))]], colWidths=[170*mm])
        st.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), sc_bg(sc)), ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8)]))
        story.append(st)

        if data.get("summary"):
            story.append(Spacer(1, 3*mm))
            story.append(Paragraph(data["summary"], styles["B2"]))

        fields = data.get("fields", [])
        if fields:
            story.append(Paragraph("Campi", styles["SH"]))
            fd = [["Campo", "Stato", "Rif."]]
            for f in fields:
                fd.append([f.get("name", ""), f.get("status", "").upper(), f.get("law_reference", "")])
            ft = Table(fd, colWidths=[60*mm, 25*mm, 85*mm])
            ft.setStyle(TableStyle([("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"), ("FONTSIZE", (0,0), (-1,-1), 9),
                ("BACKGROUND", (0,0), (-1,0), GRAY_L), ("GRID", (0,0), (-1,-1), 0.5, GRAY_L),
                ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3)]))
            story.append(ft)

        for iss in data.get("critical_issues", []):
            sev = iss.get("severity", "medium")
            c = RED if sev == "high" else (YELLOW if sev == "medium" else GREEN)
            story.append(Paragraph('<font color="' + c.hexval() + '"><b>[' + sev.upper() + ']</b></font> ' + iss.get("issue", ""), styles["B2"]))

    story.append(Spacer(1, 10*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_L))
    story.append(Paragraph("Generato da ItalyFlow AI \u2014 " + date_str + " \u2014 Report indicativo, non sostituisce consulenza legale.",
        ParagraphStyle("ft", fontName="Helvetica", fontSize=7, textColor=GRAY, alignment=TA_CENTER)))

    doc.build(story)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="ItalyFlow_Comparative_{batch_id}.pdf"'})

