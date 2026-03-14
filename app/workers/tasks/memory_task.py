# app/workers/tasks/memory_task.py
import asyncio
import json
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
import redis.asyncio as aioredis

from app.workers.celery_app import celery_app
from app.core.config import settings
from app.core.logger import get_logger
from app.core.llm_factory import get_fast_llm
from app.db.connections import db_manager

logger = get_logger(__name__)


@celery_app.task(bind=True, name="archive_chat_task")
def archive_chat_task(self, session_id: str):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(run_archive_chat(session_id))


async def run_archive_chat(session_id: str):
    logger.info(f"🗄️ Starting Cold Memory Archive for session: {session_id}")
    db = db_manager.mongo[settings.MONGO_DB_NAME]
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    try:
        # 👇 FIX 1: Match the prefix from memorize_service.py exactly!
        redis_key = f"chat_session:{session_id}"

        raw_data = await redis_client.lrange(redis_key, 0, -1)
        if not raw_data:
            return {"status": "skipped", "reason": "No messages found."}

        messages = [json.loads(msg) for msg in raw_data]

        # Keep this at 2 just for this rapid test
        MAX_HOT_MEMORY = 2
        if len(messages) <= MAX_HOT_MEMORY:
            return {"status": "skipped", "reason": "Chat not long enough to archive."}

        old_messages = messages[:-MAX_HOT_MEMORY]
        conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in old_messages])

        logger.info(f"🧠 Summarizing {len(old_messages)} old messages...")

        # TEMPORARILY mock the Gemini API call to bypass rate limits!
        # llm = get_fast_llm()
        # summary_prompt = (
        #     "You are an AI memory manager. Summarize the following conversation briefly. "
        #     "Focus on the main topics discussed, user goals, and any conclusions reached. "
        #     "Do not exceed 3 sentences.\n\n"
        #     f"Conversation:\n{conversation_text}"
        # )
        # summary_response = await llm.ainvoke(summary_prompt)
        # summary = summary_response.content

        # Use a fake string for now just to prove MongoDB gets the data
        summary = f"Fake summary of {len(old_messages)} messages for testing MongoDB."

        # 6. Save to MongoDB (Cold Memory)
        await db["chat_sessions"].update_one(
            {"session_id": session_id},
            {
                "$set": {"updated_at": datetime.utcnow()},
                "$push": {
                    "history_summaries": {
                        "summary": summary,
                        "archived_at": datetime.utcnow(),
                        "messages_archived": len(old_messages)
                    }
                }
            },
            upsert=True
        )

        # 7. Delete the old messages from Redis
        await redis_client.ltrim(redis_key, -MAX_HOT_MEMORY, -1)
        logger.info(f"✅ Successfully archived session {session_id} to MongoDB.")
        return {"status": "success", "archived_count": len(old_messages)}

    except Exception as e:
        logger.error(f"❌ Failed to archive chat session {session_id}: {e}", exc_info=True)
        raise e
    finally:
        await redis_client.close()