# backend/api/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.core.config import settings
from backend.db.connections import connect_databases, close_databases


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


@app.get("/")
async def root():
    """Root endpoint to verify the API is running."""
    return {
        "message": "Welcome to the ManualMind API",
        "status": "Healthy",
        "project": settings.PROJECT_NAME
    }


@app.get("/health")
async def health_check():
    """Health check endpoint to verify database connections."""
    from backend.db.connections import db_clients

    # Simple check to see if clients are populated
    status = "ok" if "mongo" in db_clients else "disconnected"

    return {
        "api_status": "ok",
        "database_connections": status
    }