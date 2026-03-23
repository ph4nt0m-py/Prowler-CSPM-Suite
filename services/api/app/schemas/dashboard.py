from uuid import UUID

from pydantic import BaseModel


class DashboardOut(BaseModel):
    scan_id: UUID | None
    total_findings: int
    by_severity: dict[str, int]
    by_service: dict[str, int]
    diff_counts: dict[str, int] | None = None
