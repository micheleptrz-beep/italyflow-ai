# -*- coding: utf-8 -*-
"""
ItalyFlow AI -- Database Migration v3.1
Aggiunge: visual_assets, user_visual_preferences
Esegui una sola volta: python migrate_v31.py
"""
import sqlite3
import os

DB = "italyflow.db"

if not os.path.exists(DB):
    print(f"[INFO] Database {DB} non esiste. Verra creato al primo avvio.")
    raise SystemExit(0)

conn = sqlite3.connect(DB)
c = conn.cursor()

print("=" * 60)
print("ItalyFlow AI -- Migration v3.1 (Visual Identity)")
print("=" * 60)

# 1. visual_assets
print("\n[1/3] Creazione tabella visual_assets...")
c.execute("""
CREATE TABLE IF NOT EXISTS visual_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid VARCHAR(36) UNIQUE,
    title VARCHAR NOT NULL,
    description VARCHAR,
    source VARCHAR DEFAULT 'unsplash',
    source_id VARCHAR,
    photographer VARCHAR,
    license_type VARCHAR DEFAULT 'unsplash',
    url_original VARCHAR NOT NULL,
    url_thumb VARCHAR,
    category VARCHAR NOT NULL,
    subcategory VARCHAR,
    region VARCHAR,
    product_type VARCHAR,
    season VARCHAR,
    time_mood VARCHAR,
    mood VARCHAR,
    page_context VARCHAR,
    market_context VARCHAR,
    width INTEGER,
    height INTEGER,
    dominant_color VARCHAR,
    quality_score REAL DEFAULT 5.0,
    is_active BOOLEAN DEFAULT 1,
    usage_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
print("    OK")

# 2. user_visual_preferences
print("[2/3] Creazione tabella user_visual_preferences...")
c.execute("""
CREATE TABLE IF NOT EXISTS user_visual_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE REFERENCES user_profiles(id),
    visual_mood VARCHAR DEFAULT 'classico',
    preferred_region VARCHAR,
    enable_parallax BOOLEAN DEFAULT 1,
    enable_seasonal BOOLEAN DEFAULT 1,
    enable_time_aware BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
print("    OK")

# 3. Indexes
print("[3/3] Creazione indici...")
c.execute("CREATE INDEX IF NOT EXISTS idx_va_category ON visual_assets(category)")
c.execute("CREATE INDEX IF NOT EXISTS idx_va_region ON visual_assets(region)")
c.execute("CREATE INDEX IF NOT EXISTS idx_va_season ON visual_assets(season)")
c.execute("CREATE INDEX IF NOT EXISTS idx_va_page ON visual_assets(page_context)")
c.execute("CREATE INDEX IF NOT EXISTS idx_va_product ON visual_assets(product_type)")
c.execute("CREATE INDEX IF NOT EXISTS idx_va_market ON visual_assets(market_context)")
c.execute("CREATE INDEX IF NOT EXISTS idx_va_active ON visual_assets(is_active)")
print("    OK")

conn.commit()

# Verifica
print("\n=== VERIFICA SCHEMA visual_assets ===")
c.execute("PRAGMA table_info(visual_assets)")
for row in c.fetchall():
    print(f"  {row[1]:25s} {row[2]}")

print("\n=== VERIFICA SCHEMA user_visual_preferences ===")
c.execute("PRAGMA table_info(user_visual_preferences)")
for row in c.fetchall():
    print(f"  {row[1]:25s} {row[2]}")

conn.close()
print("\n[DONE] Migrazione v3.1 completata!")
print("Prossimi step:")
print("  1. python seed_visual_assets.py")
print("  2. Aggiungi in main.py: from visual_identity import visual_router")
print("     app.include_router(visual_router)")
print("  3. uvicorn main:app --reload")
