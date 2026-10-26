"""WebSocket Endpoints for real-time live monitoring."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import websocket_manager

router = APIRouter()


@router.websocket("/ws/teacher/{room_code}")
async def teacher_websocket_endpoint(websocket: WebSocket, room_code: str):
    """
    Real-time WebSocket stream for Teacher Live Dashboard.
    Broadcasts student joins, test runs, hint quota changes, and Alt+Tab violation alarms.
    """
    await websocket_manager.connect_teacher(room_code, websocket)
    try:
        while True:
            # Keep socket open and accept incoming ping/heartbeat
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        websocket_manager.disconnect_teacher(room_code, websocket)
    except Exception:
        websocket_manager.disconnect_teacher(room_code, websocket)


@router.websocket("/ws/student/{room_code}/{student_id}")
async def student_websocket_endpoint(websocket: WebSocket, room_code: str, student_id: int):
    """
    Real-time WebSocket stream for Student Kiosk.
    Receives exam closing notifications, time reminders, or teacher broadcasts.
    """
    await websocket_manager.connect_student(room_code, student_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        websocket_manager.disconnect_student(room_code, student_id, websocket)
    except Exception:
        websocket_manager.disconnect_student(room_code, student_id, websocket)
