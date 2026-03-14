# app/api/endpoints/query.py
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from redis.asyncio import Redis
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Prefetch, FusionQuery, Fusion, SparseVector

from app.api.deps import get_qdrant, get_redis

from app.db.connections import db_clients
from app.core.embedding import get_embedding, get_sparse_embedding
from app.services.llm.rag_llm import generate_rag_answer, rewrite_query
from app.services.llm.memorize_chat import get_chat_history, save_chat_message
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    session_id: str = "default"
    top_k: int = 5  # Bumped up slightly to give the Fusion algorithm more to work with


@router.post("/")
async def ask_question(request: QueryRequest,
                       qdrant_client: AsyncQdrantClient = Depends(get_qdrant),
                       redis_client: Redis = Depends(get_redis)):
    try:
        logger.info(f"🔍 Processing hybrid query: '{request.question}' for session: '{request.session_id}'")

        # Grab the current running asyncio event loop
        loop = asyncio.get_event_loop()

        # ==========================================
        # RAG PIPELINE
        # ==========================================

        # 1. Fetch Chat History from Redis
        chat_history = await get_chat_history(redis_client, request.session_id)

        # REWRITE QUERY (Offloaded to a background thread)
        search_query = await loop.run_in_executor(
            None,
            rewrite_query,
            request.question,
            chat_history
        )

        # 2. Embed Question for Hybrid Search (Both Dense & Sparse)
        # Offload both to background threads
        dense_vector = await loop.run_in_executor(
            None,
            get_embedding,
            search_query
        )

        sparse_vector_dict = await loop.run_in_executor(
            None,
            get_sparse_embedding,
            search_query
        )

        # 3. Perform Hybrid Search with Reciprocal Rank Fusion (RRF)
        search_results = await qdrant_client.query_points(
            collection_name="manualmind_docs_v2",
            prefetch=[
                # Fetch top matches based on semantic meaning (Gemini)
                Prefetch(
                    query=dense_vector,
                    using="text-dense",
                    limit=request.top_k,
                ),
                # Fetch top matches based on exact keywords (BM25)
                Prefetch(
                    query=SparseVector(
                        indices=sparse_vector_dict["indices"],
                        values=sparse_vector_dict["values"]
                    ),
                    using="text-sparse",
                    limit=request.top_k,
                )
            ],
            # Fuse the results mathematically to get the absolute best chunks
            query=Fusion.RRF,
            limit=request.top_k,
        )

        # Extract contexts and sources from the fused points
        contexts = []
        sources = []
        if search_results and search_results.points:
            for hit in search_results.points:
                payload = hit.payload
                contexts.append(payload.get("text", ""))
                sources.append({
                    "filename": payload.get("filename", "Unknown"),
                    "chunk_index": payload.get("chunk_index"),
                    "score": round(hit.score, 4) if hit.score is not None else 0.0
                })

        # 4. Generate Answer (Offloaded generation to background thread)
        answer = await loop.run_in_executor(
            None,
            generate_rag_answer,
            request.question,
            contexts,
            chat_history
        )

        # 5. Save the new exchange to Redis asynchronously
        await save_chat_message(redis_client, request.session_id, "user", request.question)
        await save_chat_message(redis_client, request.session_id, "assistant", answer)

        return {
            "session_id": request.session_id,
            "question": request.question,
            "answer": answer,
            "sources": sources
        }

    except Exception as e:
        logger.error(f"❌ Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing your query.")