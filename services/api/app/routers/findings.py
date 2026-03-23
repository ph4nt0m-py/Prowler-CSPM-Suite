from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.finding import Finding, FindingSeverity, FindingStatus
from app.models.scan import Scan
from app.models.triage import FindingTriage, TriageState
from app.models.user import User
from app.schemas.findings import (
    FindingOut,
    GroupedFinding,
    PaginatedFindings,
    PaginatedGroupedFindings,
    ResourceInstance,
)

router = APIRouter(tags=["findings"])


def _remediation(f: Finding) -> tuple[str | None, str | None]:
    raw = f.raw_json or {}
    rem = raw.get("remediation") or {}
    desc = rem.get("desc") if isinstance(rem, dict) else None
    refs = rem.get("references") if isinstance(rem, dict) else None
    url = refs[0] if isinstance(refs, list) and refs else None
    return desc, url


def _title_and_desc(f: Finding) -> tuple[str | None, str | None, str | None]:
    """Return (check_title, check_description, status_detail) from raw_json."""
    raw = f.raw_json or {}
    finfo = raw.get("finding_info") or raw.get("findingInfo") or {}
    title = finfo.get("title") if isinstance(finfo, dict) else None
    desc = finfo.get("desc") if isinstance(finfo, dict) else None
    msg = raw.get("message") or raw.get("status_detail")
    if not desc:
        desc = msg
    return title, desc, msg


_SEVERITY_ORDER = {
    FindingSeverity.critical: 0,
    FindingSeverity.high: 1,
    FindingSeverity.medium: 2,
    FindingSeverity.low: 3,
}


@router.get("/scans/{scan_id}/findings", response_model=PaginatedFindings)
def list_findings(
    scan_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    severity: FindingSeverity | None = Query(None),
    status: FindingStatus | None = Query(None),
    service: str | None = Query(None),
    triage: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> PaginatedFindings:
    s = db.get(Scan, scan_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")

    q = db.query(Finding).filter(Finding.scan_id == scan_id)
    if severity:
        q = q.filter(Finding.severity == severity)
    if status:
        q = q.filter(Finding.status == status)
    if service:
        q = q.filter(Finding.service == service)

    triage_map = {
        t.fingerprint: t.state
        for t in db.query(FindingTriage).filter(FindingTriage.client_id == s.client_id).all()
    }

    want_triage: TriageState | None = None
    want_none = False
    if triage == "none":
        want_none = True
    elif triage is not None:
        try:
            want_triage = TriageState(triage)
        except ValueError:
            pass

    if want_none or want_triage is not None:
        triaged_fps = set(triage_map.keys())
        if want_none:
            q = q.filter(Finding.fingerprint.notin_(triaged_fps) if triaged_fps else True)
        else:
            matching_fps = {fp for fp, st in triage_map.items() if st == want_triage}
            q = q.filter(Finding.fingerprint.in_(matching_fps) if matching_fps else False)

    total = q.count()
    rows = q.order_by(Finding.severity.desc()).offset(offset).limit(limit).all()

    items: list[FindingOut] = []
    for f in rows:
        rem_desc, rem_url = _remediation(f)
        f_title, f_check_desc, f_msg = _title_and_desc(f)
        items.append(
            FindingOut(
                id=f.id,
                scan_id=f.scan_id,
                fingerprint=f.fingerprint,
                check_id=f.check_id,
                resource_id=f.resource_id,
                region=f.region,
                service=f.service,
                severity=f.severity,
                status=f.status,
                title=f_title,
                description=f.description,
                check_description=f_check_desc,
                status_detail=f_msg,
                compliance_framework=f.compliance_framework,
                remediation=rem_desc,
                remediation_url=rem_url,
                triage=triage_map.get(f.fingerprint),
                created_at=f.created_at,
            )
        )
    items.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity, 99))
    return PaginatedFindings(total=total, items=items)


@router.get("/scans/{scan_id}/findings/services", response_model=list[str])
def list_finding_services(
    scan_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[str]:
    s = db.get(Scan, scan_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")
    return [
        r[0]
        for r in db.query(Finding.service)
        .filter(Finding.scan_id == scan_id)
        .distinct()
        .order_by(Finding.service)
        .all()
    ]


@router.get("/scans/{scan_id}/findings/grouped", response_model=PaginatedGroupedFindings)
def list_findings_grouped(
    scan_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    severity: FindingSeverity | None = Query(None),
    service: str | None = Query(None),
    triage: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> PaginatedGroupedFindings:
    s = db.get(Scan, scan_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")

    q = db.query(Finding).filter(Finding.scan_id == scan_id)
    if severity:
        q = q.filter(Finding.severity == severity)
    if service:
        q = q.filter(Finding.service == service)

    triage_map = {
        t.fingerprint: t.state
        for t in db.query(FindingTriage).filter(FindingTriage.client_id == s.client_id).all()
    }

    if triage == "none":
        triaged_fps = set(triage_map.keys())
        q = q.filter(Finding.fingerprint.notin_(triaged_fps) if triaged_fps else True)
    elif triage is not None:
        try:
            want = TriageState(triage)
            matching_fps = {fp for fp, st in triage_map.items() if st == want}
            q = q.filter(Finding.fingerprint.in_(matching_fps) if matching_fps else False)
        except ValueError:
            pass

    rows = q.all()

    buckets: dict[str, list[Finding]] = {}
    for f in rows:
        buckets.setdefault(f.check_id, []).append(f)

    groups: list[GroupedFinding] = []
    for check_id, findings in buckets.items():
        rep = findings[0]
        rem_desc, rem_url = _remediation(rep)
        rep_title, rep_check_desc, rep_msg = _title_and_desc(rep)
        resources = [
            ResourceInstance(
                id=f.id,
                resource_id=f.resource_id,
                region=f.region,
                status=f.status,
                triage=triage_map.get(f.fingerprint),
                fingerprint=f.fingerprint,
            )
            for f in findings
        ]
        groups.append(
            GroupedFinding(
                check_id=check_id,
                title=rep_title,
                description=rep.description,
                check_description=rep_check_desc,
                status_detail=rep_msg,
                severity=rep.severity,
                service=rep.service,
                remediation=rem_desc,
                remediation_url=rem_url,
                count=len(findings),
                resources=resources,
            )
        )

    groups.sort(key=lambda g: (_SEVERITY_ORDER.get(g.severity, 99), -g.count))
    total_groups = len(groups)
    page = groups[offset : offset + limit]
    return PaginatedGroupedFindings(total_groups=total_groups, groups=page)


@router.get("/findings/{finding_id}", response_model=FindingOut)
def get_finding(finding_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> FindingOut:
    f = db.get(Finding, finding_id)
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found")
    s = db.get(Scan, f.scan_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")
    tr_row = (
        db.query(FindingTriage)
        .filter(FindingTriage.client_id == s.client_id, FindingTriage.fingerprint == f.fingerprint)
        .first()
    )
    rem_desc, rem_url = _remediation(f)
    f_title, f_check_desc, f_msg = _title_and_desc(f)
    return FindingOut(
        id=f.id,
        scan_id=f.scan_id,
        fingerprint=f.fingerprint,
        check_id=f.check_id,
        resource_id=f.resource_id,
        region=f.region,
        service=f.service,
        severity=f.severity,
        status=f.status,
        title=f_title,
        description=f.description,
        check_description=f_check_desc,
        status_detail=f_msg,
        compliance_framework=f.compliance_framework,
        remediation=rem_desc,
        remediation_url=rem_url,
        triage=tr_row.state if tr_row else None,
        created_at=f.created_at,
    )
