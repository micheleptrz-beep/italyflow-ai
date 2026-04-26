"""
ItalyFlow AI - Asset optimization pipeline (Section 1.5). ASCII only.

Usage:
  python -m scripts.optimize_assets ingest path/to/raw_images --catalog catalog.json
  python -m scripts.optimize_assets reprocess --slug tuscany-vineyard

Reads a JSON catalog with metadata, produces optimized variants under
static/visuals/<slug>/<breakpoint>.<ext> and inserts/updates IfVisualAsset rows.

Catalog JSON entry shape:
{
  "slug": "tuscany-vineyard-golden",
  "source": "raw/tuscany_vineyard_001.jpg",
  "title": "Tuscan vineyard at golden hour",
  "category": "landscape",
  "region": "Toscana",
  "product_category": null,
  "season": "autumn",
  "time_of_day": "golden",
  "mood": "classico",
  "license": "unsplash",
  "credit": "John Doe / Unsplash",
  "quality_score": 0.92,
  "tags": ["vineyard","golden-hour","wide"]
}
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageFilter

from database import SessionLocal, Base, engine
from app.models.visuals import (
    AssetCategory,
    IfVisualAsset,
    Mood,
    Season,
    TimeOfDay,
)

BREAKPOINTS = [("mobile", 720), ("tablet", 1080), ("desktop", 1920), ("4k", 3840)]
STATIC_ROOT = Path("static")
TARGET_DIR = STATIC_ROOT / "visuals"

JPEG_QUALITY = {"mobile": 78, "tablet": 80, "desktop": 82, "4k": 84}
WEBP_QUALITY = {"mobile": 72, "tablet": 75, "desktop": 78, "4k": 80}
AVIF_QUALITY = {"mobile": 45, "tablet": 50, "desktop": 55, "4k": 60}


def _ensure_avif_support() -> bool:
    try:
        import pillow_avif  # noqa: F401
        return True
    except Exception:
        print("WARN: pillow-avif-plugin not installed; skipping AVIF.", file=sys.stderr)
        return False


def _resize_keep_aspect(img: Image.Image, target_w: int) -> Image.Image:
    if img.width <= target_w:
        return img.copy()
    ratio = target_w / float(img.width)
    new_h = int(round(img.height * ratio))
    return img.resize((target_w, new_h), Image.LANCZOS)


def _dominant_color(img: Image.Image) -> str:
    small = img.convert("RGB").resize((32, 32), Image.LANCZOS)
    pixels = list(small.getdata())
    common = Counter(pixels).most_common(1)[0][0]
    return "#{:02x}{:02x}{:02x}".format(*common)


def _lqip_blur(img: Image.Image) -> str:
    """Tiny base64 JPEG used as blur-up placeholder (LQIP)."""
    small = _resize_keep_aspect(img, 24).filter(ImageFilter.GaussianBlur(2))
    buf = io.BytesIO()
    small.convert("RGB").save(buf, "JPEG", quality=40, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _save_variants(img: Image.Image, out_dir: Path, want_avif: bool) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = {"avif": False, "webp": False, "jpeg": False}
    for label, w in BREAKPOINTS:
        variant = _resize_keep_aspect(img, w).convert("RGB")
        # JPEG
        variant.save(out_dir / f"{label}.jpeg", "JPEG",
                     quality=JPEG_QUALITY[label], optimize=True, progressive=True)
        saved["jpeg"] = True
        # WEBP
        variant.save(out_dir / f"{label}.webp", "WEBP",
                     quality=WEBP_QUALITY[label], method=6)
        saved["webp"] = True
        # AVIF
        if want_avif:
            try:
                variant.save(out_dir / f"{label}.avif", "AVIF",
                             quality=AVIF_QUALITY[label])
                saved["avif"] = True
            except Exception as exc:
                print(f"WARN: AVIF failed for {out_dir}/{label}: {exc}", file=sys.stderr)
    return saved


def _enum_or(value, enum_cls, default):
    if not value:
        return default
    try:
        return enum_cls(value)
    except ValueError:
        return default


def ingest(raw_dir: Path, catalog_path: Path) -> int:
    if not catalog_path.exists():
        print(f"ERROR: catalog not found: {catalog_path}", file=sys.stderr)
        return 2
    items = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        print("ERROR: catalog must be a JSON list", file=sys.stderr)
        return 2

    Base.metadata.create_all(bind=engine, tables=[IfVisualAsset.__table__])
    want_avif = _ensure_avif_support()
    db = SessionLocal()
    try:
        count = 0
        for entry in items:
            slug = entry["slug"].strip().lower().replace(" ", "-")
            src = (raw_dir / entry["source"]).resolve()
            if not src.exists():
                print(f"SKIP {slug}: source missing {src}", file=sys.stderr)
                continue
            with Image.open(src) as raw:
                raw.load()
                base_path = f"visuals/{slug}"
                out_dir = STATIC_ROOT / base_path
                saved = _save_variants(raw, out_dir, want_avif)
                dom = _dominant_color(raw)
                lqip = _lqip_blur(raw)
                w, h = raw.size

            row = db.query(IfVisualAsset).filter_by(slug=slug).one_or_none()
            if row is None:
                row = IfVisualAsset(slug=slug)
                db.add(row)
            row.title = entry.get("title", slug)
            row.category = _enum_or(entry.get("category"), AssetCategory, AssetCategory.LANDSCAPE)
            row.region = entry.get("region")
            row.product_category = entry.get("product_category")
            row.season = _enum_or(entry.get("season"), Season, Season.ANY)
            row.time_of_day = _enum_or(entry.get("time_of_day"), TimeOfDay, TimeOfDay.ANY)
            row.mood = _enum_or(entry.get("mood"), Mood, Mood.CLASSICO)
            row.base_path = base_path
            row.has_avif = saved["avif"]
            row.has_webp = saved["webp"]
            row.has_jpeg = saved["jpeg"]
            row.width_master = w
            row.height_master = h
            row.blurhash = lqip
            row.dominant_color = dom
            row.quality_score = float(entry.get("quality_score", 0.5))
            row.license = entry.get("license", "unsplash")
            row.credit = entry.get("credit")
            row.tags = entry.get("tags", [])
            row.enabled = True
            count += 1
            print(f"OK  {slug}  ({w}x{h})  -> {out_dir}")
        db.commit()
        print(f"Ingested/updated {count} assets.")
        return 0
    finally:
        db.close()


def reprocess(slug: str) -> int:
    db = SessionLocal()
    try:
        row = db.query(IfVisualAsset).filter_by(slug=slug).one_or_none()
        if not row:
            print(f"Asset not found: {slug}", file=sys.stderr)
            return 1
        master = STATIC_ROOT / row.base_path / "desktop.jpeg"
        if not master.exists():
            print(f"Master not found: {master}", file=sys.stderr)
            return 1
        want_avif = _ensure_avif_support()
        with Image.open(master) as raw:
            raw.load()
            saved = _save_variants(raw, STATIC_ROOT / row.base_path, want_avif)
        row.has_avif = saved["avif"]
        row.has_webp = saved["webp"]
        row.has_jpeg = saved["jpeg"]
        db.commit()
        print(f"Reprocessed {slug}")
        return 0
    finally:
        db.close()


def main(argv: Iterable[str]) -> int:
    p = argparse.ArgumentParser(prog="optimize_assets")
    sub = p.add_subparsers(dest="cmd", required=True)
    p_ing = sub.add_parser("ingest")
    p_ing.add_argument("raw_dir", type=Path)
    p_ing.add_argument("--catalog", type=Path, required=True)
    p_re = sub.add_parser("reprocess")
    p_re.add_argument("--slug", type=str, required=True)
    args = p.parse_args(list(argv))
    if args.cmd == "ingest":
        return ingest(args.raw_dir, args.catalog)
    if args.cmd == "reprocess":
        return reprocess(args.slug)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
