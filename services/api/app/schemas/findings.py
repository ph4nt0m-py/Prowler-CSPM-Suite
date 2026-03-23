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


class ResourceInstance(BaseModel):
    id: UUID
    resource_id: str
    region: str
    status: FindingStatus
    triage: TriageState | None = None
    fingerprint: str


class GroupedFinding(BaseModel):
    check_id: str
    description: str | None
    severity: FindingSeverity
    service: str
    remediation: str | None = None
    remediation_url: str | None = None
    count: int
    resources: list[ResourceInstance]


class PaginatedGroupedFindings(BaseModel):
    total_groups: int
    groups: list[GroupedFinding]
