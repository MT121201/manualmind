# app/db/connections.py
from motor.motor_asyncio import AsyncIOMotorClient
from minio import Minio
from redis.asyncio import Redis
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance, SparseVectorParams
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    def __init__(self):
        self.mongo: AsyncIOMotorClient = None
        self.redis: Redis = None
        self.minio: Minio = None
        self.qdrant: AsyncQdrantClient = None

    async def connect(self):
        """Lazy-initialize connections only when needed."""
        if not self.mongo:
            self.mongo = AsyncIOMotorClient(settings.MONGO_URI)
            await self.mongo.admin.command('ping')

        if not self.redis:
            self.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            await self.redis.ping()

        if not self.minio:
            self.minio = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            if not self.minio.bucket_exists(settings.MINIO_BUCKET_NAME):
                self.minio.make_bucket(settings.MINIO_BUCKET_NAME)

        if not self.qdrant:
            self.qdrant = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
            # Setup collection...
            await self._ensure_qdrant_collection()

        logger.info("🚀 All databases initialized.")

    async def _ensure_qdrant_collection(self):
        docs_collection = "manualmind_docs_v2"
        collections = await self.qdrant.get_collections()
        if docs_collection not in [c.name for c in collections.collections]:
            await self.qdrant.create_collection(
                collection_name=docs_collection,
                vectors_config={"text-dense": VectorParams(size=768, distance=Distance.COSINE)},
                sparse_vectors_config={"text-sparse": SparseVectorParams()}
            )

    async def close(self):
        if self.mongo: self.mongo.close()
        if self.redis: await self.redis.close()
        if self.qdrant: await self.qdrant.close()
        logger.info("🛑 Database connections closed.")


# Instantiate a single object to be imported across the app
db_manager = DatabaseManager()

async def connect_databases():
    await db_manager.connect()

async def close_databases():
    await db_manager.close()