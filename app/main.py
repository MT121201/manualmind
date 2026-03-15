# app/api/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.db.connections import connect_databases, close_databases

from app.api.v1.api import api_router
from app.api.health import router as health_router
from app.api.root import router as root_router

from dotenv import load_dotenv
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_databases()
    yield
    await close_databases()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION)
    app.include_router(api_router, prefix="/v1")
    app.include_router(health_router)
    app.include_router(root_router)
    return app
app =create_app()

