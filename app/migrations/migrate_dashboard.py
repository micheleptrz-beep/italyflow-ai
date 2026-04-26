"""
ItalyFlow AI - One-shot migration: creates dashboard tables. ASCII only.
Run:  python -m app.migrations.migrate_dashboard
"""
from __future__ import annotations

from database import Base, engine
from app.models import dashboard as _dashboard_models  # noqa: F401  (register tables)


def main() -> None:
    print("Creating dashboard tables...")
    Base.metadata.create_all(bind=engine, tables=[
        _dashboard_models.Product.__table__,
        _dashboard_models.Audit.__table__,
        _dashboard_models.KpiCache.__table__,
        _dashboard_models.UserVisualPreference.__table__,
    ])
    print("Done.")


if __name__ == "__main__":
    main()
