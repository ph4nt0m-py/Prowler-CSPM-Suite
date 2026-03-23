from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.scan import Scan
from app.models.user import User
from app.services.export_xlsx import build_findings_xlsx

router = APIRouter(tags=["exports"])


@router.get("/scans/{scan_id}/export.xlsx")
def export_scan_xlsx(
    scan_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    s = db.get(Scan, scan_id)
    if not s:
        raise HTTPException(status_code=404, detail="Scan not found")
    try:
        data = build_findings_xlsx(db, scan_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="scan-{scan_id}.xlsx"'},
    )
