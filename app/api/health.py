#app/api/health.py
from fastapi import APIRouter
from app.db.connections import db_manager

router = APIRouter()

# app/api/health.py
@router.get("/ready")
async def readiness_check():
    # A simple check to ensure key databases are initialized
    if db_manager.mongo and db_manager.qdrant:
        return {"status": "ok"}
    return {"status": "error", "message": "Databases not initialized"}, 503