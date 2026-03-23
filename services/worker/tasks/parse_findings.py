from __future__ import annotations

import logging
import uuid
from pathlib import Path

from celery_app import app
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.finding import Finding, FindingStatus
from app.models.scan import Scan, ScanStatus
from app.redis_client import publish_scan_progress
from app.services.finding_parser import build_findings_for_scan

logger = logging.getLogger(__name__)
_LOG_MAX = 512_000


@app.task(name="cloudaudit.parse_findings")
def parse_findings_task(scan_id: str) -> None:
    sid = uuid.UUID(scan_id)
    db = SessionLocal()
    try:
        scan = db.get(Scan, sid)
        if not scan or scan.status != ScanStatus.completed:
            return
        out = Path(scan.output_directory or "")
        if not out.exists():
            scan.status = ScanStatus.failed
            scan.error_message = "Output directory missing after scan"
            db.commit()
            publish_scan_progress(sid, {"pct": 0, "stage": "failed", "status": "failed"})
            return

        db.execute(delete(Finding).where(Finding.scan_id == sid))
        db.commit()

        default_status = FindingStatus.new
        rows = build_findings_for_scan(sid, out, default_status)
        json_n = len(list(out.rglob("*.json")))
        if len(rows) == 0:
            if json_n > 0:
                logger.warning("parse_findings scan=%s: 0 findings from %s json file(s)", sid, json_n)
                note = (
                    f"\n[ingest] WARNING: parsed 0 findings from {json_n} JSON file(s); "
                    "check worker logs (JSON parse errors) and Prowler json-ocsf format.\n"
                )
            else:
                all_files = list(out.rglob("*"))
                file_names = [f.name for f in all_files[:20]] if all_files else []
                logger.warning(
                    "parse_findings scan=%s: no JSON files in %s (files: %s)",
                    sid, out, file_names,
                )
                note = (
                    f"\n[ingest] WARNING: no JSON files found in output dir {out} "
                    f"({len(all_files)} total files: {file_names}); "
                    "Prowler may not have produced output — check volume mounts "
                    "and Prowler container logs.\n"
                )
            scan_row = db.get(Scan, sid)
            if scan_row:
                scan_row.logs = ((scan_row.logs or "") + note)[-_LOG_MAX:]
                db.commit()
        for row in rows:
            db.add(row)
        db.commit()
        publish_scan_progress(sid, {"pct": 85, "stage": "diff", "status": "running"})

        from tasks.run_diff import run_diff_task

        run_diff_task.delay(scan_id)
    finally:
        db.close()
