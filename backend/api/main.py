# backend/api/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.core.config import settings
from backend.db.connections import connect_databases, close_databases

from backend.api.routes import documents, query


@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs when the server starts
    await connect_databases()
    yield
    # This runs when the server stops
    await close_databases()


# Initialize the FastAPI application with the lifespan manager
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(query.router, prefix="/api/v1/query", tags=["query"])

@app.get("/")
async def root():
    return {"message": "Welcome to the ManualMind API"}

@app.get("/health")
async def health_check():
    from backend.db.connections import db_clients
    status = "ok" if "mongo" in db_clients else "disconnected"
    return {"api_status": "ok", "database_connections": status}