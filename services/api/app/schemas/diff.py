from uuid import UUID

from pydantic import BaseModel

from app.models.diff import DiffCategory


class DiffItemOut(BaseModel):
    fingerprint: str
    category: DiffCategory
    finding_id: UUID | None
    severity: str | None = None
    service: str | None = None
    resource_id: str | None = None
    title: str | None = None
    description: str | None = None
    check_description: str | None = None
    check_id: str | None = None
    remediation: str | None = None
    remediation_url: str | None = None
    triage: str | None = None


class DiffOut(BaseModel):
    scan_id: UUID
    previous_scan_id: UUID | None
    counts: dict[str, int]
    items: list[DiffItemOut]
