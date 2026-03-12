# backend/api/routes/query.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from backend.db.connections import db_clients
from backend.core.embedding import get_embedding
from backend.services.llm.rag_llm import generate_rag_answer
from backend.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Define the expected request body
class QueryRequest(BaseModel):
    question: str
    top_k: int = 3  # How many chunks to retrieve


@router.post("/")
async def ask_question(request: QueryRequest):
    """
    Full RAG Pipeline: Embed Question -> Search Qdrant -> Generate Answer
    """
    try:
        # 1. Embed the user's question
        logger.info(f"🔍 Processing query: '{request.question}'")
        query_vector = get_embedding(request.question)

        # 2. Search Qdrant for the most similar chunks
        qdrant_client = db_clients["qdrant"]
        search_results = await qdrant_client.search(
            collection_name="manualmind_docs",
            query_vector=query_vector,
            limit=request.top_k
        )

        if not search_results:
            return {"answer": "No relevant documents found in the database.", "sources": []}

        # 3. Extract the text and source metadata from the Qdrant results
        contexts = []
        sources = []
        for hit in search_results:
            payload = hit.payload
            contexts.append(payload.get("text", ""))

            # Keep track of where we got this info
            sources.append({
                "filename": payload.get("filename", "Unknown"),
                "chunk_index": payload.get("chunk_index"),
                "similarity_score": round(hit.score, 4)
            })

        # 4. Pass the contexts and question to the LLM
        answer = generate_rag_answer(request.question, contexts)

        # 5. Return the final answer along with the sources cited
        return {
            "question": request.question,
            "answer": answer,
            "sources": sources
        }

    except Exception as e:
        logger.error(f"❌ Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing your query.")