"""
ItalyFlow AI - APScheduler bootstrap (used by Section 2.2 + 2.4 + 4). ASCII only.
Requires: pip install APScheduler
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal
from app.services.regulatory_tracker_service import RegulatoryTrackerService

log = logging.getLogger("if.scheduler")
_scheduler: BackgroundScheduler | None = None


def _job_refresh_regulatory():
    db = SessionLocal()
    try:
        result = RegulatoryTrackerService(db).refresh()
        log.info("Regulatory refresh: %s", result)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    sch = BackgroundScheduler(timezone="UTC")
    sch.add_job(_job_refresh_regulatory, "interval", hours=6,
                id="regulatory_refresh", replace_existing=True)
    sch.start()
    _scheduler = sch
    log.info("Scheduler started.")
    return sch


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
