# app/agent/tools/rag_tool.py
import asyncio
from langchain_core.tools import tool
from qdrant_client import models
from app.db.connections import db_manager
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
        # Ensure database is connected
        if not db_manager.qdrant:
            await db_manager.connect()

        qdrant_client = db_manager.qdrant

        # 1. Generate embeddings using modern asyncio.to_thread
        raw_dense = await asyncio.to_thread(get_embedding, query)
        raw_sparse = await asyncio.to_thread(get_sparse_embedding, query)

        # Force strict Python types (Defensive Programming)
        if isinstance(raw_dense, list) and len(raw_dense) > 0 and isinstance(raw_dense[0], list):
            raw_dense = raw_dense[0]

        dense_query = [float(x) for x in raw_dense]
        sparse_indices = [int(x) for x in raw_sparse.get("indices", [])]
        sparse_values = [float(x) for x in raw_sparse.get("values", [])]

        # 2. THE ARCHITECT MOVE: Hybrid Search with Reciprocal Rank Fusion (RRF)
        # Dynamic Routing
        if sparse_indices and sparse_values:
            logger.info("🔍 Executing Hybrid Search (Dense + Sparse with RRF)...")
            search_results = await qdrant_client.query_points(
                collection_name="manualmind_docs_v2",
                prefetch=[
                    # Prefetch a slightly larger pool for the fusion algorithm to score
                    models.Prefetch(query=dense_query, using="text-dense", limit=5),
                    models.Prefetch(
                        query=models.SparseVector(indices=sparse_indices, values=sparse_values),
                        using="text-sparse",
                        limit=5
                    )
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=4,  # The final amount of chunks passed to the LLM
            )
        else:
            # DENSE ONLY FALLBACK
            logger.warning("⚠️ Sparse vector was empty. Falling back to Dense-Only search.")
            search_results = await qdrant_client.query_points(
                collection_name="manualmind_docs_v2",
                query=dense_query,
                using="text-dense",
                limit=4,
            )

        if not search_results.points:
            return "I searched the manuals but could not find any relevant information."

        # 3. Format contexts with Citations (Filenames)
        formatted_results = []
        for i, point in enumerate(search_results.points):
            text = point.payload.get("text", "")
            filename = point.payload.get("filename", "Unknown Document")

            # Including the filename helps the LLM cite its sources!
            formatted_results.append(f"--- Document: {filename} (Result {i + 1}) ---\n{text}")

        logger.info(f"✅ Search completed. Found {len(search_results.points)} highly relevant chunks.")
        return "\n\n".join(formatted_results)

    except Exception as e:
        logger.error(f"❌ Internal search tool failed: {e}", exc_info=True)
        return "Internal database error occurred while searching manuals."