#app/api/health.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["health"])
async def health_check():
    from app.db.connections import db_clients
    status = "ok" if "mongo" in db_clients else "disconnected"
    return {"api_status": "ok", "database_connections": status}