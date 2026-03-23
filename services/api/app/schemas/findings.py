from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.finding import FindingSeverity, FindingStatus
from app.models.triage import TriageState


class FindingOut(BaseModel):
    id: UUID
    scan_id: UUID
    fingerprint: str
    check_id: str
    resource_id: str
    region: str
    service: str
    severity: FindingSeverity
    status: FindingStatus
    description: str | None
    compliance_framework: str | None
    remediation: str | None = None
    remediation_url: str | None = None
    triage: TriageState | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedFindings(BaseModel):
    total: int
    items: list[FindingOut]
