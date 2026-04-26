#!/usr/bin/env python
"""
ItalyFlow AI - Download seed Unsplash images for visual catalog. ASCII only.
Usage:  python -m scripts.download_seed_images
This downloads 50 royalty-free Unsplash images into data/raw_images/
matching the slugs declared in data/visual_catalog_seed.json.
"""
from __future__ import annotations

import sys
import time
import urllib.request
from pathlib import Path

OUT_DIR = Path("data/raw_images")

# Curated list: (filename, unsplash_photo_id, recommended_w)
# All images are royalty-free under the Unsplash license.
SEED = [
    # ---------- LANDSCAPE Toscana ----------
    ("toscana_01.jpg", "wAFNFqAdQAQ", 4000),  # tuscan vineyards golden hour
    ("toscana_02.jpg", "U5rMrSI7Pn4", 4000),  # tuscan hills with cypress
    ("toscana_03.jpg", "BbQLHCpVUZA", 4000),  # vineyard rows sunset
    # ---------- LANDSCAPE Puglia ----------
    ("puglia_01.jpg", "RZrFmIhRMrE", 4000),  # olive grove sunrise
    ("puglia_02.jpg", "FqRmJF7CzYM", 4000),  # olive trees field
    ("puglia_03.jpg", "rxN2MRdFJVg", 4000),  # mediterranean olive grove
    # ---------- LANDSCAPE Campania ----------
    ("amalfi_01.jpg", "lJUeGqJ-2nM", 4000),  # amalfi lemons
    ("amalfi_02.jpg", "AvhMzHwiE_0", 4000),  # lemon close up
    ("amalfi_03.jpg", "C2P9-FrN-Vs", 4000),  # amalfi coast
    # ---------- LANDSCAPE Piemonte ----------
    ("piemonte_01.jpg", "yC-Yzbqy7PY", 4000),  # rice paddy reflection
    ("piemonte_02.jpg", "ZcyW1A57nGg", 4000),  # piedmont vineyards
    ("piemonte_03.jpg", "g3PWzRkJgBM", 4000),  # langhe hills
    # ---------- LANDSCAPE Liguria ----------
    ("cinqueterre_01.jpg", "qUQNkKUjs3M", 4000),  # cinque terre terraces
    ("cinqueterre_02.jpg", "8s5l2sPvZF8", 4000),  # ligurian coast vineyards
    ("cinqueterre_03.jpg", "AJ7lAsJUFtw", 4000),  # terraced fields
    # ---------- LANDSCAPE Sicilia ----------
    ("sicilia_01.jpg", "oXJWUC0PjDw", 4000),  # sicilian wheat fields
    ("sicilia_02.jpg", "L_d4fNXdr7g", 4000),  # etna with vineyards
    ("sicilia_03.jpg", "okJjJBRYjDU", 4000),  # citrus orchard sicily
    # ---------- PRODUCT wine ----------
    ("barolo_01.jpg", "g_MmwT-ZN6E", 3500),    # wine cellar bottles
    ("vino_02.jpg",   "qnt8stiy8sE", 3500),    # red wine pour
    ("vino_03.jpg",   "ZJp1xX2Pwj4", 3500),    # vineyard wine glass
    # ---------- PRODUCT cheese ----------
    ("parmigiano_01.jpg", "_dKfeg7irBE", 3500),  # parmigiano wheels aging
    ("formaggio_02.jpg",  "EvYOOXq__y4", 3500),  # cheese assortment
    ("mozzarella_01.jpg", "VzJjPuCTcGY", 3500),  # mozzarella fresh
    # ---------- PRODUCT oil ----------
    ("olio_01.jpg", "fJxBVBkV-Bo", 3500),  # olive oil bottle
    ("olio_02.jpg", "gMgEd_uwilA", 3500),  # olive oil pour bruschetta
    ("olio_03.jpg", "mAcXOxA9-Eg", 3500),  # olives and oil
    # ---------- PRODUCT pasta ----------
    ("pasta_01.jpg", "67Mnq_Hk4y0", 3500),  # fresh pasta drying
    ("pasta_02.jpg", "kcA-c3f_3FE", 3500),  # spaghetti closeup
    # ---------- PRODUCT specialty ----------
    ("tartufo_01.jpg",   "QM3lGwWMYgA", 3500),  # truffle macro
    ("prosciutto_01.jpg","kcA-c3f_3FE", 3500),  # prosciutto slice
    ("balsamico_01.jpg", "JCIEswVfJYM", 3500),  # balsamic vinegar
    # ---------- CRAFT hands ----------
    ("casaro_01.jpg",  "rEM3cKOSBpk", 3500),  # cheesemaker hands
    ("raccolta_01.jpg","gFGCsfXkBlI", 3500),  # olive harvest hands
    ("vendemmia_01.jpg","9rFkfPwTI3I", 3500),  # grape harvest
    ("pasta_lab_01.jpg","BJaqPaH6AGQ", 3500),  # hands making pasta
    ("pasta_lab_02.jpg","oqStl2L5oxI", 3500),  # rolling pin pasta
    ("apicoltore_01.jpg","R6IIaOgWeP8", 3500), # beekeeper
    ("apicoltore_02.jpg","NrZ7eb2c-Sc", 3500), # honeycomb hands
    ("forno_01.jpg",   "ZuIDLSz3XLg", 3500),   # baker hands bread
    ("salumiere_01.jpg","Yui5vfKHuzs", 3500),  # cured meat slicing
    # ---------- MARKET export ----------
    ("export_01.jpg", "ZWqaJ4qXrcw", 3500),  # container ship
    ("export_02.jpg", "P5kLdcjnXJ4", 3500),  # cargo containers
    ("export_03.jpg", "mvbtVeRVJzg", 3500),  # logistics warehouse
    # ---------- MARKET retail ----------
    ("market_ny_01.jpg",   "i9w4Uy1pU-s", 3500),  # ny grocery
    ("market_tokyo_01.jpg","sciFqM4VUrs", 3500),  # tokyo market
    ("market_china_01.jpg","Q44_FFkDJjY", 3500),  # asian market produce
    # ---------- MARKET restaurant ----------
    ("ristorante_01.jpg","ZE-7yhOlGFE", 3500),  # restaurant plating
    ("ristorante_02.jpg","y3FkHW1cyBE", 3500),  # fine dining italian
    ("chef_01.jpg",      "fdlZBWIP0aM", 3500),  # chef hands plating
    ("ristorante_03.jpg","cckf4TsHAuw", 3500),  # restaurant ambiance
]

UNSPLASH_BASE = "https://images.unsplash.com/photo-{id}?auto=format&fit=crop&w={w}&q=85"

def download_one(filename: str, photo_id: str, w: int) -> bool:
    url = UNSPLASH_BASE.format(id=photo_id, w=w)
    out = OUT_DIR / filename
    if out.exists() and out.stat().st_size > 50_000:
        print(f"  SKIP  {filename} (already exists, {out.stat().st_size//1024} KB)")
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ItalyFlowAI/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        out.write_bytes(data)
        print(f"  OK    {filename} ({len(data)//1024} KB)")
        return True
    except Exception as exc:
        print(f"  FAIL  {filename}: {exc}")
        return False


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {len(SEED)} images to {OUT_DIR.resolve()}")
    print("(Unsplash free license - https://unsplash.com/license)\n")
    ok = 0
    for filename, pid, w in SEED:
        if download_one(filename, pid, w):
            ok += 1
        time.sleep(0.3)
    print(f"\nDone: {ok}/{len(SEED)} images downloaded.")
    print("Next step: python -m scripts.optimize_assets ingest data/raw_images --catalog data/visual_catalog_seed.json")
    return 0 if ok == len(SEED) else 1


if __name__ == "__main__":
    sys.exit(main())
