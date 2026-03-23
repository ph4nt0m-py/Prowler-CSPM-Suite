from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.triage import TriageState


class TriageUpdate(BaseModel):
    state: TriageState
    notes: str | None = Field(None, max_length=8000)


class TriageOut(BaseModel):
    id: UUID
    client_id: UUID
    fingerprint: str
    state: TriageState
    notes: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}
