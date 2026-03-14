# app/db/connections.py
from motor.motor_asyncio import AsyncIOMotorClient
from minio import Minio
from redis.asyncio import Redis
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance, SparseVectorParams
from typing import TypedDict, Optional

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

# Global dictionary to hold our database clients
class DatabaseClients(TypedDict):
    mongo: Optional[AsyncIOMotorClient]
    redis: Optional[Redis]
    minio: Optional[Minio]
    qdrant: Optional[AsyncQdrantClient]

db_clients: DatabaseClients = {
    "mongo": None,
    "redis": None,
    "minio": None,
    "qdrant": None
}


async def connect_databases():
    """Initialize all database connections and ensure schemas/collections exist."""
    try:
        # 1. MongoDB
        db_clients["mongo"] = AsyncIOMotorClient(settings.MONGO_URI)
        await db_clients["mongo"].admin.command('ping')

        # 2. Redis
        db_clients["redis"] = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        await db_clients["redis"].ping()

        # 3. MinIO
        db_clients["minio"] = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        if not db_clients["minio"].bucket_exists(settings.MINIO_BUCKET_NAME):
            db_clients["minio"].make_bucket(settings.MINIO_BUCKET_NAME)
            logger.info(f"🪣 Created MinIO bucket: {settings.MINIO_BUCKET_NAME}")

        # 4. Qdrant
        qdrant_client = AsyncQdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )
        db_clients["qdrant"] = qdrant_client

        # --- PRODUCTION AUTOMATION: Qdrant Setup ---
        docs_collection = "manualmind_docs_v2"

        # Get all existing collections (Backwards-compatible check)
        existing_collections = await qdrant_client.get_collections()
        collection_names = [col.name for col in existing_collections.collections]

        # Check if our collection is in the list
        if docs_collection not in collection_names:
            logger.info(f"🛠️ Creating Hybrid Qdrant collection: {docs_collection}...")
            await qdrant_client.create_collection(
                collection_name=docs_collection,
                # 1. The Dense Vector (Gemini 1.5 is 768 dims)
                vectors_config={
                    "text-dense": VectorParams(size=768, distance=Distance.COSINE)
                },
                # 2. The Sparse Vector (BM25 for exact keywords)
                sparse_vectors_config={
                    "text-sparse": SparseVectorParams()
                }
            )
            logger.info(f"✅ Created Qdrant collection: {docs_collection}")
        else:
            logger.info(f"⚡ Qdrant collection '{docs_collection}' already exists. Ready to go!")

        logger.info("🚀 All databases connected successfully.")
    except Exception as e:
        logger.error(f"❌ Error connecting to databases: {e}")
        raise e


async def close_databases():
    """Gracefully close database connections."""
    if "mongo" in db_clients:
        db_clients["mongo"].close()
    if "redis" in db_clients:
        await db_clients["redis"].close()
    if "qdrant" in db_clients:
        await db_clients["qdrant"].close()
    logger.info("🛑 Database connections closed.")