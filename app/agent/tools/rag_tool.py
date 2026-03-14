# app/agent/tools/rag_tool.py
import asyncio
from langchain_core.tools import tool
from qdrant_client.models import Prefetch, Fusion, SparseVector
from app.db.connections import db_manager  # Use the singleton
from app.core.embedding import get_embedding, get_sparse_embedding
from app.core.logger import get_logger

logger = get_logger(__name__)


@tool
async def internal_manuals_tool(query: str) -> str:
    """
    Use this tool FIRST when the user asks questions about hardware, troubleshooting,
    device operation, or company policies. It searches our internal Qdrant database of manuals.
    """
    logger.info(f"📚 Agent triggered Internal Manual Search for: '{query}'")

    try:
        # Ensure connection exists
        await db_manager.connect()
        qdrant_client = db_manager.qdrant

        loop = asyncio.get_event_loop()

        # 1. Generate embeddings
        dense_vector = await loop.run_in_executor(None, get_embedding, query)
        sparse_vec_dict = await loop.run_in_executor(None, get_sparse_embedding, query)

        # 2. Hybrid Search using RRF
        search_results = await qdrant_client.query_points(
            collection_name="manualmind_docs_v2",
            prefetch=[
                Prefetch(query=dense_vector, using="text-dense", limit=3),
                Prefetch(
                    query=SparseVector(indices=sparse_vec_dict["indices"], values=sparse_vec_dict["values"]),
                    using="text-sparse",
                    limit=3
                )
            ],
            query=Fusion.RRF,
            limit=3,
        )

        # 3. Format contexts
        contexts = [hit.payload.get("text", "") for hit in search_results.points] if search_results else []

        if not contexts:
            return "No relevant documentation found."

        return "\n\n---\n\n".join(contexts)

    except Exception as e:
        logger.error(f"❌ Internal search tool failed: {e}", exc_info=True)
        return "Internal database error."