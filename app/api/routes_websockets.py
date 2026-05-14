"""
WebSocket Routes — /ws/chat /ws/sync
======================================
Enables real-time communication for discussion rooms and cross-device sync.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.websockets.chat_handler import manager
from app.websockets.sync_handler import sync_manager
from app.core.dependencies import get_current_user_from_token
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws/chat/{room_id}")
async def websocket_chat_endpoint(websocket: WebSocket, room_id: str):
    """
    WebSocket endpoint for real-time discussion rooms.
    URL: ws://backend/api/ws/chat/room_id
    """
    await manager.connect(websocket, room_id)
    try:
        while True:
            # Receive text or JSON
            data = await websocket.receive_text()
            # Broadcast to everyone in the same room
            await manager.broadcast(data, room_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        logger.info(f"Client disconnected from chat room: {room_id}")


@router.websocket("/ws/sync/{user_id}")
async def websocket_sync_endpoint(websocket: WebSocket, user_id: int):
    """
    WebSocket endpoint for multi-device reading sync.
    URL: ws://backend/api/ws/sync/user_id
    """
    await sync_manager.connect(websocket, user_id)
    try:
        while True:
            # Receive sync data (book_id, page_number)
            data = await websocket.receive_json()
            book_id = data.get("book_id")
            page_number = data.get("page_number")
            
            if book_id and page_number:
                # Sync to other devices
                await sync_manager.sync_page(user_id, book_id, page_number)
    except WebSocketDisconnect:
        sync_manager.disconnect(websocket, user_id)
        logger.info(f"Client disconnected from sync for user: {user_id}")
