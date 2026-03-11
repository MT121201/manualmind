from motor.motor_asyncio import AsyncIOMotorClient
from minio import Minio
import redis.asyncio as redis
from qdrant_client import AsyncQdrantClient
from backend.core.config import settings

# Global dictionary to hold our database clients
db_clients = {}

async def connect_databases():
    """Initialize all database connections."""
    try:
        # 1. MongoDB
        if "mongo" not in db_clients:
            db_clients["mongo"] = AsyncIOMotorClient(settings.MONGO_URI)
            await db_clients["mongo"].admin.command('ping')

        # 2. Redis
        if "redis" not in db_clients:
            db_clients["redis"] = redis.from_url(settings.REDIS_URL, decode_responses=True)
            await db_clients["redis"].ping()

        # 3. MinIO
        if "minio" not in db_clients:
            db_clients["minio"] = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            if not db_clients["minio"].bucket_exists(settings.MINIO_BUCKET_NAME):
                db_clients["minio"].make_bucket(settings.MINIO_BUCKET_NAME)

        # 4. Qdrant
        if "qdrant" not in db_clients:
            db_clients["qdrant"] = AsyncQdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT
            )
    except Exception as e:
        print(f"❌ Error connecting to databases: {e}")
        raise e

async def close_databases():
    """Gracefully close database connections."""
    if "mongo" in db_clients:
        db_clients["mongo"].close()
    if "redis" in db_clients:
        await db_clients["redis"].close()
    if "qdrant" in db_clients:
        await db_clients["qdrant"].close()
    db_clients.clear() # Clear the dictionary after closing
    print("🛑 Database connections closed.")