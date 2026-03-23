from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from celery_app import app
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models.credential import Credential, CredentialProvider
from app.models.scan import Scan, ScanStatus
from app.redis_client import publish_scan_progress
from app.services.aws_creds import resolve_aws_env_for_credential
from prowler.runner import ProwlerAwsOptions, run_prowler_aws

_LOG_MAX = 512_000


def _append_log(db: Session, scan_id: uuid.UUID, chunk: str) -> None:
    scan = db.get(Scan, scan_id)
    if not scan:
        return
    prev = scan.logs or ""
    scan.logs = (prev + chunk)[-_LOG_MAX:]
    db.commit()


def _fail_pending(db: Session, sid: uuid.UUID, message: str) -> None:
    now = datetime.now(timezone.utc)
    n = db.query(Scan).filter(Scan.id == sid, Scan.status == ScanStatus.pending).update(
        {
            Scan.status: ScanStatus.failed,
            Scan.error_message: message[:4000],
            Scan.finished_at: now,
        },
        synchronize_session=False,
    )
    db.commit()
    if n:
        publish_scan_progress(sid, {"pct": 0, "stage": "failed", "status": "failed", "error": message})


def _fail_running(db: Session, sid: uuid.UUID, message: str) -> None:
    now = datetime.now(timezone.utc)
    n = db.query(Scan).filter(Scan.id == sid, Scan.status == ScanStatus.running).update(
        {
            Scan.status: ScanStatus.failed,
            Scan.error_message: message[:4000],
            Scan.finished_at: now,
            Scan.progress_pct: 0,
        },
        synchronize_session=False,
    )
    db.commit()
    if n:
        publish_scan_progress(sid, {"pct": 0, "stage": "failed", "status": "failed", "error": message})


@app.task(name="cloudaudit.execute_scan")
def execute_scan_task(scan_id: str) -> None:
    sid = uuid.UUID(scan_id)
    db = SessionLocal()
    try:
        scan = db.get(Scan, sid)
        if not scan or scan.status == ScanStatus.cancelled:
            return

        cred = db.get(Credential, scan.credential_id)
        if not cred:
            _fail_pending(db, sid, "Credential not found")
            return

        if cred.provider != CredentialProvider.aws:
            _fail_pending(db, sid, "Only AWS scans are supported in this build")
            return

        settings = get_settings()
        out_dir = Path(settings.scan_output_dir) / str(sid)
        now = datetime.now(timezone.utc)
        u = db.query(Scan).filter(Scan.id == sid, Scan.status == ScanStatus.pending).update(
            {
                Scan.output_directory: str(out_dir),
                Scan.status: ScanStatus.running,
                Scan.started_at: now,
                Scan.progress_pct: 5,
            },
            synchronize_session=False,
        )
        db.commit()
        if u == 0:
            return
        publish_scan_progress(sid, {"pct": 5, "stage": "starting_container", "status": "running"})

        try:
            aws_env = resolve_aws_env_for_credential(cred.ciphertext, cred.auth_method)
        except Exception as e:  # noqa: BLE001
            _fail_running(db, sid, str(e))
            return

        if not settings.docker_available:
            _fail_running(db, sid, "DOCKER_AVAILABLE is false; cannot run Prowler container")
            return

        scan_row = db.get(Scan, sid)
        if not scan_row or scan_row.status == ScanStatus.cancelled:
            publish_scan_progress(sid, {"pct": 0, "stage": "cancelled", "status": "cancelled"})
            return

        publish_scan_progress(sid, {"pct": 15, "stage": "running_prowler", "status": "running"})
        db.query(Scan).filter(Scan.id == sid, Scan.status == ScanStatus.running).update(
            {Scan.progress_pct: 15},
            synchronize_session=False,
        )
        db.commit()

        def _stream_log(chunk: str) -> None:
            if chunk:
                _append_log(db, sid, chunk)

        code, _log = run_prowler_aws(
            image=settings.prowler_image,
            host_output_dir=out_dir,
            aws_env=aws_env,
            options=ProwlerAwsOptions(),
            on_log_chunk=_stream_log,
        )

        scan_row = db.get(Scan, sid)
        if not scan_row or scan_row.status == ScanStatus.cancelled:
            publish_scan_progress(sid, {"pct": 0, "stage": "cancelled", "status": "cancelled"})
            return
        db.query(Scan).filter(Scan.id == sid, Scan.status == ScanStatus.running).update(
            {Scan.prowler_version: settings.prowler_image},
            synchronize_session=False,
        )
        db.commit()

        if code != 0:
            _fail_running(db, sid, f"Prowler exited with code {code}")
            return

        fin = datetime.now(timezone.utc)
        n = db.query(Scan).filter(Scan.id == sid, Scan.status == ScanStatus.running).update(
            {
                Scan.status: ScanStatus.completed,
                Scan.progress_pct: 70,
                Scan.finished_at: fin,
            },
            synchronize_session=False,
        )
        db.commit()
        if n == 0:
            return
        publish_scan_progress(sid, {"pct": 70, "stage": "parsing", "status": "running"})

        from tasks.parse_findings import parse_findings_task

        parse_findings_task.delay(scan_id)
    finally:
        db.close()
