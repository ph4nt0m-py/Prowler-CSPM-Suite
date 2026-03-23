"""Compare findings between two scans; persist ScanDiff + update Finding.status on the new scan."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.diff import DiffCategory, ScanDiff, ScanDiffItem
from app.models.finding import Finding, FindingStatus
from app.models.scan import Scan, ScanStatus


def run_diff_for_scan(db: Session, scan_id: uuid.UUID) -> ScanDiff | None:
    scan = db.get(Scan, scan_id)
    if not scan or scan.status != ScanStatus.completed:
        return None

    prev_id = scan.previous_scan_id

    diff_id_subq = select(ScanDiff.id).where(ScanDiff.scan_id == scan_id)
    db.execute(delete(ScanDiffItem).where(ScanDiffItem.scan_diff_id.in_(diff_id_subq)))
    db.execute(delete(ScanDiff).where(ScanDiff.scan_id == scan_id))
    db.commit()

    new_fps = {f[0] for f in db.query(Finding.fingerprint).filter(Finding.scan_id == scan_id).all()}

    if not prev_id:
        db.query(Finding).filter(Finding.scan_id == scan_id).update({Finding.status: FindingStatus.new})
        db.commit()
        return None

    prev_fps = {f[0] for f in db.query(Finding.fingerprint).filter(Finding.scan_id == prev_id).all()}

    new_set = new_fps - prev_fps
    closed_set = prev_fps - new_fps
    open_set = new_fps & prev_fps

    diff_row = ScanDiff(scan_id=scan_id, previous_scan_id=prev_id)
    db.add(diff_row)
    db.flush()

    fp_to_finding: dict[str, uuid.UUID] = {
        f[0]: f[1]
        for f in db.query(Finding.fingerprint, Finding.id).filter(Finding.scan_id == scan_id).all()
    }

    items: list[ScanDiffItem] = []
    for fp in new_set:
        items.append(
            ScanDiffItem(
                scan_diff_id=diff_row.id,
                fingerprint=fp,
                category=DiffCategory.new,
                finding_id=fp_to_finding.get(fp),
            )
        )
    for fp in open_set:
        items.append(
            ScanDiffItem(
                scan_diff_id=diff_row.id,
                fingerprint=fp,
                category=DiffCategory.open,
                finding_id=fp_to_finding.get(fp),
            )
        )
    for fp in closed_set:
        items.append(
            ScanDiffItem(
                scan_diff_id=diff_row.id,
                fingerprint=fp,
                category=DiffCategory.closed,
                finding_id=None,
            )
        )
    db.add_all(items)

    id_by_fp = fp_to_finding
    for fp in new_set:
        fid = id_by_fp.get(fp)
        if fid:
            db.query(Finding).filter(Finding.id == fid).update({Finding.status: FindingStatus.new})
    for fp in open_set:
        fid = id_by_fp.get(fp)
        if fid:
            db.query(Finding).filter(Finding.id == fid).update({Finding.status: FindingStatus.open})

    db.commit()
    db.refresh(diff_row)
    return diff_row
