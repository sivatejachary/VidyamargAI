import json
from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Maps user_id (str) or "admin" to active websocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)

    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            if websocket in self.active_connections[client_id]:
                self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(message))

    async def broadcast_to_user(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            for connection in self.active_connections[client_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    pass

    async def broadcast_to_admins(self, message: dict):
        # Admins connect with client_id starting with "admin" or role equal to admin
        for client_id, connections in self.active_connections.items():
            if client_id == "admin" or client_id.startswith("admin_"):
                for connection in connections:
                    try:
                        await connection.send_text(json.dumps(message))
                    except Exception:
                        pass

    async def broadcast_global(self, message: dict):
        for client_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception:
                    pass

manager = ConnectionManager()
