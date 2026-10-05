"""api/ws.py — WebSocket hub for real-time updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, list[WebSocket]] = {}  # meeting_id → connections

    async def connect(self, meeting_id: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(meeting_id, []).append(ws)

    def disconnect(self, meeting_id: str, ws: WebSocket):
        conns = self.active.get(meeting_id, [])
        if ws in conns:
            conns.remove(ws)

    async def broadcast(self, meeting_id: str, message: dict):
        for ws in self.active.get(meeting_id, []):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                pass


manager = ConnectionManager()


@router.websocket("/meeting/{meeting_id}")
async def meeting_ws(meeting_id: str, ws: WebSocket):
    """WebSocket endpoint for a meeting workspace. Receives processing events."""
    await manager.connect(meeting_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            # Echo back with type acknowledgment (Phase 1 will handle routing)
            await ws.send_text(json.dumps({"type": "ACK", "original": msg}))
    except WebSocketDisconnect:
        manager.disconnect(meeting_id, ws)


@router.websocket("/overlay/{meeting_id}")
async def overlay_ws(meeting_id: str, ws: WebSocket):
    """WebSocket endpoint for the desktop overlay."""
    await manager.connect(meeting_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            event_type = msg.get("type", "")
            # Mark Moment events are forwarded to all meeting connections
            if event_type == "USER_MARK":
                await manager.broadcast(meeting_id, {
                    "type": "USER_MARK",
                    "payload": msg.get("payload", {}),
                })
            await ws.send_text(json.dumps({"type": "ACK", "event": event_type}))
    except WebSocketDisconnect:
        manager.disconnect(meeting_id, ws)
