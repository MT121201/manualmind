# app/api/endpoints/query.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from redis.asyncio import Redis
from langchain_core.messages import HumanMessage, AIMessage

from app.api.deps import get_redis
from app.core.security import get_current_user
from app.services.memorize_service import get_chat_history, save_chat_message
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
        # Now we know exactly who is asking the question!
        user_email = current_user.get("email", "Unknown User")
        logger.info(f"🤖 Routing query from {user_email} to LangGraph Agent: '{request.question}'")

        # 1. Fetch Chat History from Redis
        raw_history = await get_chat_history(redis_client, request.session_id)

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

        # 2. Append the current user question
        messages.append(HumanMessage(content=request.question))

        # ==========================================
        # 3. THE MAGIC: Invoke the LangGraph Agent!
        # ==========================================
        result_state = await manual_mind_agent.ainvoke({"messages": messages})

        # 4. Extract the Agent's final answer
        final_answer = result_state["messages"][-1].content

        # 5. Save the new exchange to Redis
        await save_chat_message(redis_client, request.session_id, "user", request.question)
        await save_chat_message(redis_client, request.session_id, "assistant", final_answer)

        # ==========================================
        # 6. 🧹 TRIGGER THE COLD MEMORY ARCHIVER
        # ==========================================
        # We use .delay() to fire off the Celery task in the background.
        # The user doesn't have to wait for this to finish!
        if len(recent_history) >= 2:
            archive_chat_task.delay(request.session_id)

        return {
            "session_id": request.session_id,
            "question": request.question,
            "answer": final_answer,
            "agent_routed": True
        }

    except Exception as e:
        logger.error(f"❌ Agent execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="The AI encountered an error while processing your request.")