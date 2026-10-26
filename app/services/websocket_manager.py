"""WebSocket Connection and Real-Time Event Dispatch Manager."""

import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages active WebSockets for teachers and students per exam room."""

    def __init__(self):
        # room_code -> list of teacher WebSockets
        self.teacher_connections: dict[str, list[WebSocket]] = {}
        # room_code -> student_id -> list of student WebSockets
        self.student_connections: dict[str, dict[int, list[WebSocket]]] = {}

    async def connect_teacher(self, room_code: str, websocket: WebSocket):
        """Register a teacher WebSocket connection for live room monitoring."""
        await websocket.accept()
        if room_code not in self.teacher_connections:
            self.teacher_connections[room_code] = []
        self.teacher_connections[room_code].append(websocket)
        logger.info("Teacher connected to room %s", room_code)

    def disconnect_teacher(self, room_code: str, websocket: WebSocket):
        """Remove a teacher WebSocket connection."""
        if room_code in self.teacher_connections:
            if websocket in self.teacher_connections[room_code]:
                self.teacher_connections[room_code].remove(websocket)
            if not self.teacher_connections[room_code]:
                del self.teacher_connections[room_code]
        logger.info("Teacher disconnected from room %s", room_code)

    async def connect_student(self, room_code: str, student_id: int, websocket: WebSocket):
        """Register a student kiosk WebSocket connection."""
        await websocket.accept()
        if room_code not in self.student_connections:
            self.student_connections[room_code] = {}
        if student_id not in self.student_connections[room_code]:
            self.student_connections[room_code][student_id] = []
        self.student_connections[room_code][student_id].append(websocket)
        logger.info("Student %s connected to room %s", student_id, room_code)

    def disconnect_student(self, room_code: str, student_id: int, websocket: WebSocket):
        """Remove a student WebSocket connection."""
        if room_code in self.student_connections:
            if student_id in self.student_connections[room_code]:
                if websocket in self.student_connections[room_code][student_id]:
                    self.student_connections[room_code][student_id].remove(websocket)
                if not self.student_connections[room_code][student_id]:
                    del self.student_connections[room_code][student_id]
            if not self.student_connections[room_code]:
                del self.student_connections[room_code]
        logger.info("Student %s disconnected from room %s", student_id, room_code)

    async def broadcast_to_teachers(self, room_code: str, event_type: str, data: dict):
        """Send a real-time event to all teacher dashboards monitoring this room."""
        if room_code not in self.teacher_connections:
            return

        payload = {
            "event": event_type,
            "room_code": room_code,
            "data": data,
        }
        raw_message = json.dumps(payload, default=str)

        stale_sockets = []
        for ws in self.teacher_connections[room_code]:
            try:
                await ws.send_text(raw_message)
            except Exception as exc:
                logger.warning("Failed to send to teacher ws in room %s: %s", room_code, exc)
                stale_sockets.append(ws)

        for ws in stale_sockets:
            self.disconnect_teacher(room_code, ws)

    async def broadcast_to_room(self, room_code: str, event_type: str, data: dict):
        """Broadcast an event to both teachers and students in a room."""
        await self.broadcast_to_teachers(room_code, event_type, data)

        if room_code not in self.student_connections:
            return

        payload = {
            "event": event_type,
            "room_code": room_code,
            "data": data,
        }
        raw_message = json.dumps(payload, default=str)

        for student_id, ws_list in list(self.student_connections[room_code].items()):
            stale_sockets = []
            for ws in ws_list:
                try:
                    await ws.send_text(raw_message)
                except Exception as exc:
                    logger.warning("Failed to send to student %s ws: %s", student_id, exc)
                    stale_sockets.append(ws)
            for ws in stale_sockets:
                self.disconnect_student(room_code, student_id, ws)


websocket_manager = WebSocketManager()
