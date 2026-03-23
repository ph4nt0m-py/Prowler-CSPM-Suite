from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.client import Client
from app.models.triage import FindingTriage
from app.models.user import User
from app.schemas.triage import TriageOut, TriageUpdate
from app.security.audit_log import write_audit_log

router = APIRouter(tags=["triage"])


@router.put("/clients/{client_id}/triage/{fingerprint}", response_model=TriageOut)
def upsert_triage(
    client_id: UUID,
    fingerprint: str,
    body: TriageUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FindingTriage:
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client not found")
    row = (
        db.query(FindingTriage)
        .filter(FindingTriage.client_id == client_id, FindingTriage.fingerprint == fingerprint)
        .first()
    )
    if row:
        row.state = body.state
        row.notes = body.notes
        row.updated_by = user.id
    else:
        row = FindingTriage(
            client_id=client_id,
            fingerprint=fingerprint,
            state=body.state,
            notes=body.notes,
            updated_by=user.id,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    write_audit_log(
        db,
        actor_user_id=user.id,
        action="triage.upsert",
        resource_type="finding_triage",
        resource_id=fingerprint[:64],
        metadata={"client_id": str(client_id), "state": body.state.value},
        ip=request.client.host if request.client else None,
    )
    return row


@router.get("/clients/{client_id}/triage", response_model=list[TriageOut])
def list_triage(
    client_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[FindingTriage]:
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client not found")
    return db.query(FindingTriage).filter(FindingTriage.client_id == client_id).all()
