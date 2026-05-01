"""
WebSocket — Multi-Device Reading Sync Handler
================================================
Keeps reading position synchronized across browser, tablet, and phone.
"""

from fastapi import WebSocket
from typing import Dict, List


class SyncManager:
    """Manages reading position sync per user across devices."""

    def __init__(self):
        self.user_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.user_connections:
            self.user_connections[user_id].remove(websocket)

    async def sync_page(self, user_id: int, book_id: int, page_number: int):
        """Broadcast page change to all other devices for this user."""
        if user_id in self.user_connections:
            import json
            message = json.dumps({"book_id": book_id, "page": page_number})
            for ws in self.user_connections[user_id]:
                await ws.send_text(message)


sync_manager = SyncManager()
