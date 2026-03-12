# backend/db/connections.py
from motor.motor_asyncio import AsyncIOMotorClient
from minio import Minio
import redis.asyncio as redis
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance  # <-- NEW IMPORTS
from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Global dictionary to hold our database clients
db_clients = {}


async def connect_databases():
    """Initialize all database connections and ensure schemas/collections exist."""
    try:
        # 1. MongoDB
        db_clients["mongo"] = AsyncIOMotorClient(settings.MONGO_URI)
        await db_clients["mongo"].admin.command('ping')

        # 2. Redis
        db_clients["redis"] = redis.from_url(settings.REDIS_URL, decode_responses=True)
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
        collection_name = "manualmind_docs"

        # Get all existing collections (Backwards-compatible check)
        existing_collections = await qdrant_client.get_collections()
        collection_names = [col.name for col in existing_collections.collections]

        # Check if our collection is in the list
        if collection_name not in collection_names:
            logger.info(f"🛠️ Qdrant collection '{collection_name}' not found. Creating it now...")
            await qdrant_client.create_collection(
                collection_name=collection_name,
                # Gemini embedding-001 outputs 768 dimensions
                vectors_config=VectorParams(size=768, distance=Distance.COSINE)
            )
            logger.info(f"✅ Created Qdrant collection: {collection_name}")
        else:
            logger.info(f"⚡ Qdrant collection '{collection_name}' already exists. Ready to go!")

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