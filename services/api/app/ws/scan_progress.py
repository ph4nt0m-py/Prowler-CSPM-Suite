import asyncio
import json
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.database import SessionLocal
from app.models.scan import Scan
from app.redis_client import scan_progress_channel
from app.security.jwt_utils import decode_token

router = APIRouter()


@router.websocket("/ws/scans/{scan_id}")
async def scan_progress_ws(
    websocket: WebSocket,
    scan_id: UUID,
    token: str | None = Query(None),
) -> None:
    if not token:
        await websocket.close(code=4401)
        return
    try:
        decode_token(token)
    except ValueError:
        await websocket.close(code=4401)
        return

    db = SessionLocal()
    try:
        scan = db.get(Scan, scan_id)
        if not scan:
            await websocket.close(code=4404)
            return
    finally:
        db.close()

    await websocket.accept()
    settings = get_settings()
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = r.pubsub()
    channel = scan_progress_channel(scan_id)
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = message["data"]
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                payload = {"raw": data}
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await r.close()
