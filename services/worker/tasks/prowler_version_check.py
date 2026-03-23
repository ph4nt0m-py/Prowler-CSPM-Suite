from __future__ import annotations

import os

import httpx
from celery_app import app

from app.config import get_settings
from app.redis_client import cache_set_json


@app.task(name="cloudaudit.prowler_version_check")
def prowler_version_check_task() -> dict:
    """Fetch latest Prowler release from GitHub API and cache in Redis.

    Optional host `docker pull` for PROWLER_IMAGE is a separate beat task
    (`cloudaudit.prowler_image_pull`) when PROWLER_AUTO_PULL=true.
    """
    token = os.environ.get("GITHUB_TOKEN") or get_settings().github_token
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = "https://api.github.com/repos/prowler-cloud/prowler/releases/latest"
    try:
        r = httpx.get(url, headers=headers, timeout=30.0)
        r.raise_for_status()
        data = r.json()
        payload = {
            "tag_name": data.get("tag_name"),
            "published_at": data.get("published_at"),
            "html_url": data.get("html_url"),
        }
    except Exception as e:  # noqa: BLE001
        payload = {"error": str(e)}

    cache_set_json("prowler:github_latest", payload, ttl_seconds=3600)
    return payload
