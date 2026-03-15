# app/api/v1/endpoints/query.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from redis.asyncio import Redis
from langchain_core.messages import HumanMessage, AIMessage

from app.api.deps import get_redis
from app.core.security import get_current_user
from app.services.memorize_service import get_chat_history, save_chat_message
from app.services.cache_service import get_cached_answer, set_cached_answer  # 👈 NEW IMPORT
from app.agent.graph import manual_mind_agent
from app.core.logger import get_logger
from app.workers.tasks.memory_task import archive_chat_task

logger = get_logger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"


@router.post("/")
async def ask_question(
        request: QueryRequest,
        redis_client: Redis = Depends(get_redis),
        current_user: dict = Depends(get_current_user)  # 🔒 Lock down the endpoint!
):
    try:
        user_email = current_user.get("email", "Unknown User")
        logger.info(f"🤖 Received query from {user_email}: '{request.question}'")

        # 1. Fetch Chat History from Redis (Needed for both Cache Hit and Agent Run)
        raw_history = await get_chat_history(redis_client, request.session_id)

        # ==========================================
        # 2. 🛑 THE EARLY EXIT (Check Global Cache First)
        # ==========================================
        cached_answer = await get_cached_answer(request.question)

        if cached_answer:
            logger.info("⚡ REDIS CACHE HIT")

            # Even if we bypass the Agent, we MUST save this exchange to the user's
            # personal session history so the Agent remembers it for future questions!
            await save_chat_message(redis_client, request.session_id, "user", request.question)
            await save_chat_message(redis_client, request.session_id, "assistant", cached_answer)

            # Trigger archiver if needed
            if len(raw_history) >= 2:
                archive_chat_task.delay(request.session_id)

            return {
                "session_id": request.session_id,
                "question": request.question,
                "answer": cached_answer,
                "agent_routed": False,  # False means we saved API money!
                "source": "cache"
            }

        # ==========================================
        # 3. THE HEAVY LIFT: Prepare LangGraph Inputs
        # ==========================================
        logger.info("🧠 CACHE MISS: Waking up LangGraph Agent...")

        # 🛡️ Keep only the last 10 messages so Gemini doesn't crash on long chats
        MAX_MESSAGES = 10
        recent_history = raw_history[-MAX_MESSAGES:] if len(raw_history) > MAX_MESSAGES else raw_history

        # Convert the raw Redis history into LangChain message formats
        messages = []
        for msg in recent_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        # Append the current user question
        messages.append(HumanMessage(content=request.question))

        # ==========================================
        # 4. Invoke the LangGraph Agent
        # ==========================================
        # We pass metadata so LangSmith knows exactly WHO asked the question
        run_config = {
            "configurable": {
                "session_id": request.session_id,
            },
            "metadata": {
                "user_email": current_user.get("email", "unknown"),
                "environment": "production"
            },
            "tags": ["manual_query", f"user:{current_user.get('email', 'unknown')}"]
        }

        import os
        logger.info(f"🔎 DEBUG LANGSMITH - Tracing On: {os.getenv('LANGCHAIN_TRACING_V2')}")
        logger.info(f"🔎 DEBUG LANGSMITH - Project: {os.getenv('LANGCHAIN_PROJECT')}")

        result_state = await manual_mind_agent.ainvoke(
            {"messages": messages},
            config=run_config
        )

        # Extract the Agent's final answer
        final_answer_raw = result_state["messages"][-1].content

        # Force LangChain's multipart output into a single string
        if isinstance(final_answer_raw, list):
            # Extract only the text parts (ignore tool call metadata)
            text_blocks = [
                block["text"] for block in final_answer_raw
                if isinstance(block, dict) and "text" in block
            ]
            final_answer = "\n".join(text_blocks) if text_blocks else str(final_answer_raw)
        else:
            final_answer = str(final_answer_raw)


        # ==========================================
        # 5. Save Data (Global Cache + Session Memory)
        # ==========================================
        # Save to Global Cache for the next user who asks this
        await set_cached_answer(request.question, final_answer)

        # Save to Personal Session Memory
        await save_chat_message(redis_client, request.session_id, "user", request.question)
        await save_chat_message(redis_client, request.session_id, "assistant", final_answer)

        # ==========================================
        # 6. 🧹 TRIGGER THE COLD MEMORY ARCHIVER
        # ==========================================
        if len(recent_history) >= 2:
            archive_chat_task.delay(request.session_id)

        return {
            "session_id": request.session_id,
            "question": request.question,
            "answer": final_answer,
            "agent_routed": True,
            "source": "agent"
        }

    except Exception as e:
        logger.error(f"❌ Agent execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="The AI encountered an error while processing your request.")