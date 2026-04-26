"""
ItalyFlow AI - One-shot migration: creates dashboard tables. ASCII only.
Run:  python -m app.migrations.migrate_dashboard
Creates the namespaced if_* tables to coexist with legacy tables.
"""
from __future__ import annotations

from database import Base, engine
from app.models import dashboard as _m


def main() -> None:
    print("Creating ItalyFlow dashboard tables (if_*)...")
    Base.metadata.create_all(
        bind=engine,
        tables=[
            _m.Product.__table__,
            _m.Audit.__table__,
            _m.KpiCache.__table__,
            _m.UserVisualPreference.__table__,
        ],
    )
    print("Done.")


if __name__ == "__main__":
    main()
