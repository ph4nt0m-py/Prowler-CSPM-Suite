from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.scan import ScanStatus


class ScanCreate(BaseModel):
    credential_id: str
    label: str | None = Field(None, max_length=255)
    previous_scan_id: str | None = None


class ScanUpdate(BaseModel):
    label: str | None = Field(None, max_length=255)


class ScanOut(BaseModel):
    id: UUID
    client_id: UUID
    credential_id: UUID
    label: str | None
    celery_task_id: str | None = None
    status: ScanStatus
    progress_pct: int
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    prowler_version: str | None
    previous_scan_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ScanDetailOut(ScanOut):
    """GET /scans/{id} includes DB finding count for ingest troubleshooting."""

    findings_count: int = 0
