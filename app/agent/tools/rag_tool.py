# app/agent/tools/rag_tool.py
import asyncio
from langchain_core.tools import tool
from qdrant_client import models  # 👈 Import all models at once
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
        await db_manager.connect()
        qdrant_client = db_manager.qdrant
        loop = asyncio.get_event_loop()

        # 1. Generate embeddings
        raw_dense = await loop.run_in_executor(None, get_embedding, query)
        raw_sparse = await loop.run_in_executor(None, get_sparse_embedding, query)

        # 🛡️ Force strict Python types
        if isinstance(raw_dense, list) and len(raw_dense) > 0 and isinstance(raw_dense[0], list):
            raw_dense = raw_dense[0]

        dense_query = [float(x) for x in raw_dense]
        sparse_indices = [int(x) for x in raw_sparse.get("indices", [])]
        sparse_values = [float(x) for x in raw_sparse.get("values", [])]

        # 🛡️ Dynamic Routing
        if sparse_indices and sparse_values:
            # HYBRID SEARCH
            search_results = await qdrant_client.query_points(
                collection_name="manualmind_docs_v2",
                prefetch=[
                    models.Prefetch(query=dense_query, using="text-dense", limit=3),
                    models.Prefetch(
                        query=models.SparseVector(indices=sparse_indices, values=sparse_values),
                        using="text-sparse",
                        limit=3
                    )
                ],
                # 👇 THE FIX IS HERE: Wrap the Fusion command in a FusionQuery object
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=3,
            )
        else:
            # DENSE ONLY FALLBACK
            logger.warning("⚠️ Sparse vector was empty. Falling back to Dense-Only search.")
            search_results = await qdrant_client.query_points(
                collection_name="manualmind_docs_v2",
                query=dense_query,
                using="text-dense",
                limit=3,
            )

        # Format contexts
        contexts = [hit.payload.get("text", "") for hit in search_results.points] if search_results else []

        if not contexts:
            return "No relevant documentation found."

        return "\n\n---\n\n".join(contexts)

    except Exception as e:
        logger.error(f"❌ Internal search tool failed: {e}", exc_info=True)
        return "Internal database error."