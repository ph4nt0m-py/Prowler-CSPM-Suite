from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.diff import DiffCategory, ScanDiff, ScanDiffItem
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.user import User
from app.schemas.diff import DiffItemOut, DiffOut

router = APIRouter(tags=["diff"])


@router.get("/scans/{scan_id}/diff", response_model=DiffOut)
def get_diff(scan_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> DiffOut:
    s = db.get(Scan, scan_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")

    diff_row = db.query(ScanDiff).filter(ScanDiff.scan_id == scan_id).first()
    if diff_row:
        items_db = db.query(ScanDiffItem).filter(ScanDiffItem.scan_diff_id == diff_row.id).all()
        counts: dict[str, int] = {c.value: 0 for c in DiffCategory}
        for it in items_db:
            counts[it.category.value] += 1

        finding_ids = [it.finding_id for it in items_db if it.finding_id]
        findings_map = (
            {f.id: f for f in db.query(Finding).filter(Finding.id.in_(finding_ids)).all()}
            if finding_ids
            else {}
        )

        items: list[DiffItemOut] = []
        for it in items_db:
            f = findings_map.get(it.finding_id) if it.finding_id else None
            rem_desc = rem_url = None
            if f:
                raw = f.raw_json or {}
                rem = raw.get("remediation") or {}
                if isinstance(rem, dict):
                    rem_desc = rem.get("desc")
                    refs = rem.get("references")
                    rem_url = refs[0] if isinstance(refs, list) and refs else None
            items.append(
                DiffItemOut(
                    fingerprint=it.fingerprint,
                    category=it.category,
                    finding_id=it.finding_id,
                    severity=f.severity.value if f else None,
                    service=f.service if f else None,
                    resource_id=f.resource_id if f else None,
                    description=f.description if f else None,
                    check_id=f.check_id if f else None,
                    remediation=rem_desc,
                    remediation_url=rem_url,
                )
            )
        return DiffOut(
            scan_id=scan_id,
            previous_scan_id=diff_row.previous_scan_id,
            counts=counts,
            items=items,
        )

    if not s.previous_scan_id:
        total = db.query(func.count(Finding.id)).filter(Finding.scan_id == scan_id).scalar() or 0
        return DiffOut(
            scan_id=scan_id,
            previous_scan_id=None,
            counts={"new": int(total), "open": 0, "closed": 0},
            items=[],
        )

    raise HTTPException(
        status_code=404,
        detail="Diff not available yet (previous scan comparison pending or scan incomplete)",
    )
