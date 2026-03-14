# app/api/deps.py
from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis
from qdrant_client import AsyncQdrantClient
from minio import Minio

# Import the new singleton manager
from app.db.connections import db_manager 
from app.core.config import settings

# 1. Get MongoDB Database
async def get_mongo_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    # Use the manager's connection
    yield db_manager.mongo[settings.MONGO_DB_NAME]

# 2. Get Redis
async def get_redis() -> AsyncGenerator[Redis, None]:
    yield db_manager.redis

# 3. Get Qdrant
async def get_qdrant() -> AsyncGenerator[AsyncQdrantClient, None]:
    yield db_manager.qdrant

# 4. Get MinIO
async def get_minio() -> AsyncGenerator[Minio, None]:
    yield db_manager.minio