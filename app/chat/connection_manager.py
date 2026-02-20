"""
In-memory connection manager for chat WebSocket: subscribe/unsubscribe/broadcast by room_id.
"""
import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks WebSocket connections per room and broadcasts events."""

    def __init__(self) -> None:
        # room_id -> set of WebSocket
        self._rooms: Dict[uuid.UUID, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, websocket: WebSocket, room_id: uuid.UUID) -> None:
        async with self._lock:
            if room_id not in self._rooms:
                self._rooms[room_id] = set()
            self._rooms[room_id].add(websocket)
        logger.debug("Subscribed ws to room %s", room_id)

    async def unsubscribe(self, websocket: WebSocket, room_id: uuid.UUID) -> None:
        async with self._lock:
            if room_id in self._rooms:
                self._rooms[room_id].discard(websocket)
                if not self._rooms[room_id]:
                    del self._rooms[room_id]
        logger.debug("Unsubscribed ws from room %s", room_id)

    async def unsubscribe_all(self, websocket: WebSocket, room_ids: Set[uuid.UUID]) -> None:
        for rid in list(room_ids):
            await self.unsubscribe(websocket, rid)

    async def broadcast_to_room(
        self,
        room_id: uuid.UUID,
        event: str,
        payload: Any,
        exclude_websocket: WebSocket | None = None,
    ) -> None:
        """Send JSON message to all connections subscribed to this room (except exclude_websocket)."""
        msg = json.dumps({
            "event": event,
            "room_id": str(room_id),
            "payload": payload,
        }, default=str)
        async with self._lock:
            sockets = set(self._rooms.get(room_id) or [])
        dead = []
        for ws in sockets:
            if ws is exclude_websocket:
                continue
            try:
                await ws.send_text(msg)
            except Exception as e:
                logger.warning("Broadcast send failed: %s", e)
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    if room_id in self._rooms:
                        self._rooms[room_id].discard(ws)
                if room_id in self._rooms and not self._rooms[room_id]:
                    del self._rooms[room_id]

    def broadcast_to_room_sync(
        self,
        room_id: uuid.UUID,
        event: str,
        payload: Any,
    ) -> None:
        """Fire-and-forget broadcast from sync code (e.g. after create message). Schedules async broadcast."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                self.broadcast_to_room(room_id, event, payload, exclude_websocket=None)
            )
        except RuntimeError:
            # No running loop (e.g. in tests); skip broadcast
            pass


connection_manager = ConnectionManager()
