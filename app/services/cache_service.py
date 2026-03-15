import hashlib
import re
from app.db.connections import db_manager
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def _normalize_and_hash(question: str) -> str:
    """
    Normalizes the question (lowercase, strips extra spaces)
    and returns a SHA-256 hash to use as a safe Redis key.
    """
    # Lowercase and remove punctuation/extra whitespace
    normalized = re.sub(r'[^\w\s]', '', question.lower()).strip()
    normalized = re.sub(r'\s+', ' ', normalized)

    # Create a deterministic hash
    query_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    return f"rag_cache:{query_hash}"


async def get_cached_answer(question: str) -> str | None:
    """Checks Redis for a previously generated answer."""
    if not db_manager.redis:
        # logger.warning(f"Redis cache read error: Redis is not available.")
        return None

    cache_key = _normalize_and_hash(question)
    try:
        cached_data = await db_manager.redis.get(cache_key)
        if cached_data:
            logger.info("⚡ REDIS CACHE HIT: Bypassing LangGraph Agent!")
            return cached_data
    except Exception as e:
        logger.error(f"Redis cache read error: {e}")

    return None


async def set_cached_answer(question: str, answer: str):
    """Saves the Agent's answer to Redis with a Time-To-Live (TTL)."""
    if not db_manager.redis:
        return

    cache_key = _normalize_and_hash(question)
    try:
        # Save to Redis and set it to expire after 24 hours
        await db_manager.redis.setex(
            name=cache_key,
            time=settings.CACHE_TTL_SECONDS,
            value=answer
        )
        logger.info("💾 Saved Agent response to Redis cache.")
    except Exception as e:
        logger.error(f"Redis cache write error: {e}")