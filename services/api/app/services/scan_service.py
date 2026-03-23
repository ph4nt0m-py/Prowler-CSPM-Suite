"""Enqueue scan execution (Celery)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.celery_client import send_execute_scan
from app.models.credential import Credential
from app.models.scan import Scan, ScanStatus
from app.redis_client import publish_scan_progress


def create_scan_record(
    db: Session,
    *,
    client_id: uuid.UUID,
    credential_id: uuid.UUID,
    label: str | None,
    previous_scan_id: uuid.UUID | None,
) -> Scan:
    cred = db.get(Credential, credential_id)
    if not cred or cred.client_id != client_id:
        raise ValueError("Invalid credential for client")
    if previous_scan_id:
        prev = db.get(Scan, previous_scan_id)
        if not prev or prev.client_id != client_id or prev.status != ScanStatus.completed:
            raise ValueError("previous_scan_id must be a completed scan for the same client")

    scan = Scan(
        client_id=client_id,
        credential_id=credential_id,
        label=label,
        status=ScanStatus.pending,
        progress_pct=0,
        previous_scan_id=previous_scan_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    publish_scan_progress(scan.id, {"pct": 0, "stage": "queued", "status": "pending"})
    return scan


def enqueue_execute_scan(db: Session, scan_id: uuid.UUID) -> str:
    """Dispatch Celery task and persist task id for cancel/revoke."""
    task_id = send_execute_scan(scan_id)
    scan = db.get(Scan, scan_id)
    if scan:
        scan.celery_task_id = task_id
        db.commit()
        db.refresh(scan)
    return task_id
