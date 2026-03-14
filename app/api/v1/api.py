# app/api/v1/api.py
from fastapi import APIRouter

from app.api.v1.endpoints import documents, query, auth

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(query.router, tags=["query"])