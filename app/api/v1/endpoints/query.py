# app/api/endpoints/query.py
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from redis.asyncio import Redis
from langchain_core.messages import HumanMessage, AIMessage

from app.api.deps import get_redis
from app.services.rag_services.memorize_chat import get_chat_history, save_chat_message
from app.agent.graph import manual_mind_agent
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"


@router.post("/")
async def ask_question(request: QueryRequest, redis_client: Redis = Depends(get_redis)):
    try:
        logger.info(f"🤖 Routing query to LangGraph Agent: '{request.question}'")

        # 1. Fetch Chat History from Redis
        raw_history = await get_chat_history(redis_client, request.session_id)

        # Convert the raw Redis history into LangChain message formats
        messages = []
        for msg in raw_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        # 2. Append the current user question
        messages.append(HumanMessage(content=request.question))

        # ==========================================
        # 3. THE MAGIC: Invoke the LangGraph Agent!
        # ==========================================
        # This one line triggers the LLM, makes it think, loops through
        # the Qdrant/Web tools if needed, and writes the final response.
        result_state = await manual_mind_agent.ainvoke({"messages": messages})

        # 4. Extract the Agent's final answer
        # The agent updates the state with the full conversation, so the last message is the answer.
        final_answer = result_state["messages"][-1].content

        # 5. Save the new exchange to Redis
        await save_chat_message(redis_client, request.session_id, "user", request.question)
        await save_chat_message(redis_client, request.session_id, "assistant", final_answer)

        return {
            "session_id": request.session_id,
            "question": request.question,
            "answer": final_answer,
            "agent_routed": True  # A little flag to confirm the graph is working!
        }

    except Exception as e:
        logger.error(f"❌ Agent execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="The AI encountered an error while processing your request.")