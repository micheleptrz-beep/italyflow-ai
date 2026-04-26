"""
ItalyFlow AI - One-shot migration: Section 2 tables. ASCII only.
Run:  python -m app.migrations.migrate_section2
"""
from __future__ import annotations

from database import Base, engine

from app.models import labels as _labels
from app.models import compliance as _compliance
from app.models import i18n as _i18n
from app.models import collaboration as _collab


def main() -> None:
    print("Creating Section 2 tables...")
    Base.metadata.create_all(bind=engine, tables=[
        _labels.IfLabelTemplate.__table__,
        _labels.IfLabel.__table__,
        _labels.IfLabelVersion.__table__,
        _compliance.IfCertificate.__table__,
        _compliance.IfRegulatoryChange.__table__,
        _compliance.IfComplianceScoreCache.__table__,
        _i18n.IfTranslation.__table__,
        _i18n.IfGlossaryTerm.__table__,
        _collab.IfWorkspaceMember.__table__,
        _collab.IfComment.__table__,
        _collab.IfApproval.__table__,
        _collab.IfActivityLog.__table__,
    ])
    print("Done.")


if __name__ == "__main__":
    main()
