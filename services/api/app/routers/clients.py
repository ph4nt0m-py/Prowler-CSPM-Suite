from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.client import Client
from app.models.user import User
from app.schemas.clients import ClientCreate, ClientOut, ClientUpdate
from app.security.audit_log import write_audit_log

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientOut])
def list_clients(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Client]:
    return db.query(Client).order_by(Client.created_at.desc()).all()


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    body: ClientCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Client:
    c = Client(name=body.name, description=body.description)
    db.add(c)
    db.commit()
    db.refresh(c)
    write_audit_log(
        db,
        actor_user_id=user.id,
        action="client.create",
        resource_type="client",
        resource_id=str(c.id),
        ip=request.client.host if request.client else None,
    )
    return c


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Client:
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client not found")
    return c


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: UUID,
    body: ClientUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Client:
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client not found")
    if body.name is not None:
        c.name = body.name
    if body.description is not None:
        c.description = body.description
    db.commit()
    db.refresh(c)
    write_audit_log(
        db,
        actor_user_id=user.id,
        action="client.update",
        resource_type="client",
        resource_id=str(c.id),
        ip=request.client.host if request.client else None,
    )
    return c


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(c)
    db.commit()
    write_audit_log(
        db,
        actor_user_id=user.id,
        action="client.delete",
        resource_type="client",
        resource_id=str(client_id),
        ip=request.client.host if request.client else None,
    )
