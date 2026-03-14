from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from redis.asyncio import Redis
from qdrant_client import AsyncQdrantClient
from minio import Minio

from app.db.connections import db_clients
from app.core.config import settings

# 1. Get MongoDB Database
async def get_mongo_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    client: AsyncIOMotorClient = db_clients.get("mongo")
    # This returns the specific database (e.g., 'manualmind_db')
    yield client[settings.MONGO_DB_NAME]

# 2. Get Redis
async def get_redis() -> AsyncGenerator[Redis, None]:
    yield db_clients.get("redis")

# 3. Get Qdrant
async def get_qdrant() -> AsyncGenerator[AsyncQdrantClient, None]:
    yield db_clients.get("qdrant")

# 4. Get MinIO
async def get_minio() -> AsyncGenerator[Minio, None]:
    yield db_clients.get("minio")