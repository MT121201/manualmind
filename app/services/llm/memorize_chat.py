# app/services/memorize_chat.py
import json
from redis.asyncio import Redis
from app.core.logger import get_logger

logger = get_logger(__name__)


async def get_chat_history(redis_client: Redis, session_id: str, limit: int = 6) -> list[dict]:
    """Retrieves the last N messages using the provided redis_client."""
    if not redis_client:
        return []

    key = f"chat_session:{session_id}"
    raw_history = await redis_client.lrange(key, -limit, -1)

    history = []
    for item in raw_history:
        try:
            history.append(json.loads(item))
        except Exception as e:
            logger.error(f"Failed to parse history item: {e}")
    return history


async def save_chat_message(redis_client: Redis, session_id: str, role: str, content: str):
    """Saves a message using the provided redis_client."""
    if not redis_client:
        return

    key = f"chat_session:{session_id}"
    message = json.dumps({"role": role, "content": content})

    await redis_client.rpush(key, message)
    await redis_client.expire(key, 3600)