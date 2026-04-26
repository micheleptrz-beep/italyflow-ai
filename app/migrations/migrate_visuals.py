"""
ItalyFlow AI - One-shot migration: creates if_visual_assets. ASCII only.
Run:  python -m app.migrations.migrate_visuals
"""
from __future__ import annotations

from database import Base, engine
from app.models import visuals as _visuals_models  # noqa: F401


def main() -> None:
    print("Creating if_visual_assets table...")
    Base.metadata.create_all(bind=engine, tables=[_visuals_models.IfVisualAsset.__table__])
    print("Done.")


if __name__ == "__main__":
    main()
