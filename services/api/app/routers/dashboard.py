from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.client import Client
from app.models.diff import DiffCategory, ScanDiff, ScanDiffItem
from app.models.finding import Finding
from app.models.scan import Scan, ScanStatus
from app.models.user import User
from app.schemas.dashboard import DashboardOut

router = APIRouter(tags=["dashboard"])


@router.get("/clients/{client_id}/dashboard", response_model=DashboardOut)
def client_dashboard(
    client_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    scan_id: UUID | None = Query(None, description="Specific scan; default latest completed"),
) -> DashboardOut:
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client not found")

    if scan_id:
        s = db.get(Scan, scan_id)
        if not s or s.client_id != client_id:
            raise HTTPException(status_code=404, detail="Scan not found for client")
    else:
        s = (
            db.query(Scan)
            .filter(Scan.client_id == client_id, Scan.status == ScanStatus.completed)
            .order_by(Scan.created_at.desc())
            .first()
        )

    if not s:
        return DashboardOut(scan_id=None, total_findings=0, by_severity={}, by_service={}, diff_counts=None)

    sid = s.id
    total = db.query(func.count(Finding.id)).filter(Finding.scan_id == sid).scalar() or 0

    sev_rows = (
        db.query(Finding.severity, func.count(Finding.id)).filter(Finding.scan_id == sid).group_by(Finding.severity).all()
    )
    by_severity = {r[0].value: int(r[1]) for r in sev_rows}

    svc_rows = (
        db.query(Finding.service, func.count(Finding.id)).filter(Finding.scan_id == sid).group_by(Finding.service).all()
    )
    by_service = {r[0]: int(r[1]) for r in svc_rows}

    diff_counts: dict[str, int] | None = None
    dr = db.query(ScanDiff).filter(ScanDiff.scan_id == sid).first()
    if dr:
        items = db.query(ScanDiffItem).filter(ScanDiffItem.scan_diff_id == dr.id).all()
        diff_counts = {c.value: 0 for c in DiffCategory}
        for it in items:
            diff_counts[it.category.value] += 1

    return DashboardOut(
        scan_id=sid,
        total_findings=int(total),
        by_severity=by_severity,
        by_service=by_service,
        diff_counts=diff_counts,
    )
