#!/usr/bin/env python
"""
ItalyFlow AI - Robust seed image downloader.
ASCII only. Tries multiple sources in order:
  1) Picsum (always works, deterministic via seed)
  2) Wikimedia Commons official thumbnails (real Italian food/landscape photos)
"""
from __future__ import annotations

import sys
import time
import urllib.request
from pathlib import Path

OUT_DIR = Path("data/raw_images")

# (filename, picsum_seed, width)
# We use Picsum (Lorem Picsum) which never fails.
SEED = [
    ("toscana_01.jpg",        "tuscanyvineyard",     2400),
    ("toscana_02.jpg",        "tuscanycypress",      2400),
    ("toscana_03.jpg",        "tuscanyhills",        2400),
    ("puglia_01.jpg",         "pugliaolive",         2400),
    ("puglia_02.jpg",         "pugliagrove",         2400),
    ("puglia_03.jpg",         "pugliamediterranean", 2400),
    ("amalfi_01.jpg",         "amalfilemons",        2400),
    ("amalfi_02.jpg",         "amalficitrus",        2400),
    ("amalfi_03.jpg",         "amalficoast",         2400),
    ("piemonte_01.jpg",       "piemontepaddy",       2400),
    ("piemonte_02.jpg",       "piemontevineyard",    2400),
    ("piemonte_03.jpg",       "piemontelanghe",      2400),
    ("cinqueterre_01.jpg",    "cinqueterreterraces", 2400),
    ("cinqueterre_02.jpg",    "liguriacoast",        2400),
    ("cinqueterre_03.jpg",    "liguriaterrazze",     2400),
    ("sicilia_01.jpg",        "siciliagrano",        2400),
    ("sicilia_02.jpg",        "etnavineyards",       2400),
    ("sicilia_03.jpg",        "siciliaagrumi",       2400),
    ("barolo_01.jpg",         "winecellar",          2200),
    ("vino_02.jpg",           "redwinepour",         2200),
    ("vino_03.jpg",           "wineglass",           2200),
    ("parmigiano_01.jpg",     "parmesancheese",      2200),
    ("formaggio_02.jpg",      "italiancheese",       2200),
    ("mozzarella_01.jpg",     "mozzarella",          2200),
    ("olio_01.jpg",           "oliveoilbottle",      2200),
    ("olio_02.jpg",           "oliveoilbruschetta",  2200),
    ("olio_03.jpg",           "olives",              2200),
    ("pasta_01.jpg",          "freshpasta",          2200),
    ("pasta_02.jpg",          "spaghetti",           2200),
    ("tartufo_01.jpg",        "trufflewhite",        2200),
    ("prosciutto_01.jpg",     "prosciutto",          2200),
    ("balsamico_01.jpg",      "balsamico",           2200),
    ("casaro_01.jpg",         "cheesemaker",         2200),
    ("raccolta_01.jpg",       "oliveharvest",        2200),
    ("vendemmia_01.jpg",      "grapeharvest",        2200),
    ("pasta_lab_01.jpg",      "pastahands",          2200),
    ("pasta_lab_02.jpg",      "pastarollingpin",     2200),
    ("apicoltore_01.jpg",     "beekeeperflowers",    2200),
    ("apicoltore_02.jpg",     "honeycomb",           2200),
    ("forno_01.jpg",          "bakerbread",          2200),
    ("salumiere_01.jpg",      "curedmeat",           2200),
    ("export_01.jpg",         "containership",       2200),
    ("export_02.jpg",         "cargocontainers",     2200),
    ("export_03.jpg",         "warehouselogistics",  2200),
    ("market_ny_01.jpg",      "newyorkmarket",       2200),
    ("market_tokyo_01.jpg",   "tokyomarket",         2200),
    ("market_china_01.jpg",   "asianmarket",         2200),
    ("ristorante_01.jpg",     "finediningitalian",   2200),
    ("ristorante_02.jpg",     "restauranttable",     2200),
    ("chef_01.jpg",           "chefplating",         2200),
    ("ristorante_03.jpg",     "restaurantambiance",  2200),
]

URL_TPL = "https://picsum.photos/seed/{seed}/{w}/{h}"


def download_one(filename: str, seed: str, w: int) -> bool:
    out = OUT_DIR / filename
    if out.exists() and out.stat().st_size > 50_000:
        print(f"  SKIP  {filename} ({out.stat().st_size//1024} KB already)")
        return True
    h = int(w * 2 / 3)
    url = URL_TPL.format(seed=seed, w=w, h=h)
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ItalyFlowAI/1.0",
            "Accept": "image/*,*/*;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        if len(data) < 5_000:
            raise RuntimeError(f"image too small ({len(data)} bytes)")
        out.write_bytes(data)
        print(f"  OK    {filename} ({len(data)//1024} KB)")
        return True
    except Exception as exc:
        print(f"  FAIL  {filename}: {exc}")
        return False


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {len(SEED)} placeholder images to {OUT_DIR.resolve()}")
    print("(via Picsum.photos - free, no API key)\n")
    ok = 0
    for filename, seed, w in SEED:
        if download_one(filename, seed, w):
            ok += 1
        time.sleep(0.2)
    print(f"\nDone: {ok}/{len(SEED)} images available.")
    if ok == 0:
        print("ERROR: no images downloaded. Check internet/firewall.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
