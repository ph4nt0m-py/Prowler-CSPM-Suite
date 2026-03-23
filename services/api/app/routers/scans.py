from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from sqlalchemy import func

from app.celery_client import revoke_task, send_parse_findings
from app.database import get_db
from app.deps import get_current_user
from app.models.client import Client
from app.models.finding import Finding
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.redis_client import publish_scan_progress
from app.schemas.scans import ScanCreate, ScanDetailOut, ScanOut, ScanUpdate
from app.security.audit_log import write_audit_log
from app.services.scan_service import create_scan_record, enqueue_execute_scan

router = APIRouter(tags=["scans"])


@router.get("/clients/{client_id}/scans", response_model=list[ScanOut])
def list_scans_for_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Scan]:
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client not found")
    return db.query(Scan).filter(Scan.client_id == client_id).order_by(Scan.created_at.desc()).all()


@router.post("/clients/{client_id}/scans", response_model=ScanOut, status_code=status.HTTP_201_CREATED)
def start_scan(
    client_id: UUID,
    body: ScanCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Scan:
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client not found")
    try:
        cred_uuid = UUID(body.credential_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="credential_id must be a valid UUID. Pick a credential from the list in the UI, not its label.",
        ) from None
    if body.previous_scan_id:
        try:
            prev = UUID(body.previous_scan_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="previous_scan_id must be a valid UUID when provided.",
            ) from None
    else:
        prev = None
    try:
        scan = create_scan_record(
            db,
            client_id=client_id,
            credential_id=cred_uuid,
            label=body.label,
            previous_scan_id=prev,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    enqueue_execute_scan(db, scan.id)
    db.refresh(scan)
    write_audit_log(
        db,
        actor_user_id=user.id,
        action="scan.start",
        resource_type="scan",
        resource_id=str(scan.id),
        metadata={"client_id": str(client_id)},
        ip=request.client.host if request.client else None,
    )
    return scan


@router.post("/scans/{scan_id}/cancel", response_model=ScanOut)
def cancel_scan(
    scan_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Scan:
    s = db.get(Scan, scan_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")
    if s.status not in (ScanStatus.pending, ScanStatus.running):
        raise HTTPException(
            status_code=400,
            detail="Only pending or running scans can be cancelled.",
        )
    task_id = s.celery_task_id
    terminate_worker = s.status == ScanStatus.running
    now = datetime.now(timezone.utc)
    n = (
        db.query(Scan)
        .filter(
            Scan.id == scan_id,
            Scan.status.in_([ScanStatus.pending, ScanStatus.running]),
        )
        .update(
            {
                Scan.status: ScanStatus.cancelled,
                Scan.finished_at: now,
                Scan.error_message: "Cancelled by user",
                Scan.progress_pct: 0,
            },
            synchronize_session=False,
        )
    )
    db.commit()
    if n == 0:
        raise HTTPException(status_code=400, detail="Scan could not be cancelled (state changed).")
    db.refresh(s)
    revoke_task(task_id or "", terminate=terminate_worker)
    publish_scan_progress(scan_id, {"pct": 0, "stage": "cancelled", "status": "cancelled"})
    write_audit_log(
        db,
        actor_user_id=user.id,
        action="scan.cancel",
        resource_type="scan",
        resource_id=str(scan_id),
        ip=request.client.host if request.client else None,
    )
    return s


@router.get("/scans/{scan_id}", response_model=ScanDetailOut)
def get_scan(scan_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ScanDetailOut:
    s = db.get(Scan, scan_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")
    n = db.query(func.count(Finding.id)).filter(Finding.scan_id == scan_id).scalar() or 0
    base = ScanOut.model_validate(s)
    return ScanDetailOut(**base.model_dump(), findings_count=int(n))


@router.post("/scans/{scan_id}/reparse")
def reparse_scan_findings(
    scan_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Re-enqueue ``parse_findings`` for a completed scan (e.g. after parser upgrade or empty ingest)."""
    s = db.get(Scan, scan_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")
    if s.status != ScanStatus.completed:
        raise HTTPException(
            status_code=400,
            detail="Reparse is only allowed when the scan status is completed.",
        )
    send_parse_findings(scan_id)
    publish_scan_progress(scan_id, {"pct": 70, "stage": "parsing", "status": "running"})
    write_audit_log(
        db,
        actor_user_id=user.id,
        action="scan.reparse",
        resource_type="scan",
        resource_id=str(scan_id),
        ip=request.client.host if request.client else None,
    )
    return {"ok": True, "detail": "parse_findings task enqueued"}


@router.patch("/scans/{scan_id}", response_model=ScanOut)
def patch_scan(
    scan_id: UUID,
    body: ScanUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Scan:
    s = db.get(Scan, scan_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")
    if body.label is not None:
        s.label = body.label
    db.commit()
    db.refresh(s)
    write_audit_log(
        db,
        actor_user_id=user.id,
        action="scan.update",
        resource_type="scan",
        resource_id=str(scan_id),
        ip=request.client.host if request.client else None,
    )
    return s


@router.get("/scans/{scan_id}/logs")
def get_scan_logs(
    scan_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    s = db.get(Scan, scan_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")
    return {"logs": s.logs or ""}
