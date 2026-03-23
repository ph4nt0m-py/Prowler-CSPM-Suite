import json
from typing import Any
from uuid import UUID

import redis

from app.config import get_settings


def get_redis() -> redis.Redis:
    return redis.from_url(get_settings().redis_url, decode_responses=True)


def scan_progress_channel(scan_id: UUID) -> str:
    return f"scan:{scan_id}:progress"


def publish_scan_progress(scan_id: UUID, payload: dict[str, Any]) -> None:
    r = get_redis()
    r.publish(scan_progress_channel(scan_id), json.dumps(payload))


def cache_set_json(key: str, value: dict[str, Any], ttl_seconds: int) -> None:
    r = get_redis()
    r.setex(key, ttl_seconds, json.dumps(value))


def cache_get_json(key: str) -> dict[str, Any] | None:
    r = get_redis()
    raw = r.get(key)
    if not raw:
        return None
    return json.loads(raw)
