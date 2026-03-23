from fastapi import APIRouter, Depends

from app.celery_client import send_prowler_image_pull, send_prowler_version_check
from app.deps import get_current_admin
from app.models.user import User
from app.redis_client import cache_get_json

router = APIRouter(prefix="/admin/prowler", tags=["admin"])


@router.get("/version")
def prowler_version(_admin: User = Depends(get_current_admin)) -> dict:
    cached = cache_get_json("prowler:github_latest")
    return {"cached": cached}


@router.post("/refresh")
def prowler_refresh(_admin: User = Depends(get_current_admin)) -> dict:
    send_prowler_version_check()
    return {"status": "enqueued"}


@router.post("/pull-image")
def prowler_pull_image(_admin: User = Depends(get_current_admin)) -> dict:
    """Enqueue `docker pull` for PROWLER_IMAGE on the worker (runs even if PROWLER_AUTO_PULL is false)."""
    send_prowler_image_pull(force=True)
    return {"status": "enqueued"}
