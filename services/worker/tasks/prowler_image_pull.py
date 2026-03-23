"""Optional periodic `docker pull` for PROWLER_IMAGE (host daemon via mounted socket)."""

from __future__ import annotations

import logging
import subprocess

from celery_app import app

from app.config import get_settings
from prowler.runner import _docker_bin

logger = logging.getLogger(__name__)


@app.task(name="cloudaudit.prowler_image_pull")
def prowler_image_pull_task(force: bool = False) -> dict:
    """Pull scan image on the worker host when PROWLER_AUTO_PULL is true, or when force=True (admin)."""
    s = get_settings()
    if not force and not s.prowler_auto_pull:
        return {"skipped": True, "reason": "PROWLER_AUTO_PULL is false (pass force for admin pull)"}
    if not s.docker_available:
        return {"skipped": True, "reason": "DOCKER_AVAILABLE is false"}
    img = s.prowler_image
    try:
        docker = _docker_bin()
    except FileNotFoundError as e:
        logger.warning("prowler_image_pull: %s", e)
        return {"image": img, "ok": False, "error": str(e)}
    try:
        proc = subprocess.run(
            [docker, "pull", img],
            capture_output=True,
            text=True,
            timeout=3600,
        )
        ok = proc.returncode == 0
        if not ok:
            logger.warning(
                "prowler_image_pull failed rc=%s stderr=%s",
                proc.returncode,
                (proc.stderr or "")[-500:],
            )
        return {
            "image": img,
            "returncode": proc.returncode,
            "ok": ok,
            "stderr_tail": (proc.stderr or "")[-2000:],
        }
    except subprocess.TimeoutExpired:
        logger.warning("prowler_image_pull timeout for %s", img)
        return {"image": img, "ok": False, "error": "timeout"}
    except Exception as e:  # noqa: BLE001
        logger.exception("prowler_image_pull")
        return {"image": img, "ok": False, "error": str(e)}
