# app/api/root.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/", tags=["root"])
async def root():
    return {"message": "Welcome to the ManualMind API"}