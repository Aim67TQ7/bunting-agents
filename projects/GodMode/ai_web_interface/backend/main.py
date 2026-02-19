from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json
from typing import Dict, Any, Optional
import sys
import os

# Add parent directory to path to import practical_ai_system
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from practical_ai_system import PracticalAIMaster

app = FastAPI(title="AI Orchestra API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI system
ai_master = PracticalAIMaster()

class ProblemRequest(BaseModel):
    description: str
    requirements: Optional[Dict[str, Any]] = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                pass

manager = ConnectionManager()

@app.post("/api/solve")
async def solve_problem(request: ProblemRequest):
    """Submit a problem to the AI orchestras"""
    task_id = await ai_master.solve_problem(request.description, request.requirements)
    
    # Broadcast task started
    await manager.broadcast({
        "type": "task_started",
        "data": {"task_id": task_id, "description": request.description}
    })
    
    return {"task_id": task_id, "status": "submitted"}

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a task"""
    result = await ai_master.get_task_status(task_id)
    return result

@app.get("/api/orchestras")
async def list_orchestras():
    """Get all AI orchestras and their status"""
    status = ai_master.get_system_status()
    return status["orchestras"]

@app.get("/api/system/status")
async def get_system_status():
    """Get overall system status"""
    return ai_master.get_system_status()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Send periodic system updates
            await asyncio.sleep(5)
            status = ai_master.get_system_status()
            await websocket.send_text(json.dumps({
                "type": "system_status",
                "data": status
            }))
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)