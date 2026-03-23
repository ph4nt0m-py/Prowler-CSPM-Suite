from __future__ import annotations

import uuid

from celery_app import app
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.scan import Scan, ScanStatus
from app.redis_client import publish_scan_progress
from app.services.diff_service import run_diff_for_scan


@app.task(name="cloudaudit.run_diff")
def run_diff_task(scan_id: str) -> None:
    sid = uuid.UUID(scan_id)
    db = SessionLocal()
    try:
        scan = db.get(Scan, sid)
        if not scan or scan.status != ScanStatus.completed:
            return
        run_diff_for_scan(db, sid)
        scan = db.get(Scan, sid)
        if scan:
            scan.progress_pct = 100
            db.commit()
        publish_scan_progress(sid, {"pct": 100, "stage": "completed", "status": "completed"})
    finally:
        db.close()
