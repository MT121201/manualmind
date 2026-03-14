# app/workers/tasks.py
import uuid
import tempfile
import asyncio
import fitz  # PyMuPDF
from celery import shared_task
from qdrant_client.models import PointStruct  # Required for Qdrant uploads

from app.workers.celery_app import celery_app
from app.core.config import settings
from app.core.logger import get_logger
from app.db.connections import db_clients, connect_databases

# Import your awesome Gemini embedding logic!
from app.core.embedding import get_embedding, get_sparse_embedding, get_text_chunks

logger = get_logger(__name__)


async def run_process_document(document_id: str, filename: str, s3_path: str):
    """
    The complete Async Ingestion Pipeline:
    MinIO Download -> PyMuPDF Extract -> Gemini Embed -> Qdrant Upsert
    """
    # 1. Ensure databases are connected
    if "mongo" not in db_clients or "qdrant" not in db_clients:
        await connect_databases()

    db = db_clients["mongo"][settings.MONGO_DB_NAME]
    minio_client = db_clients["minio"]
    qdrant_client = db_clients["qdrant"]

    # 2. Update status to 'processing'
    await db["documents"].update_one(
        {"_id": document_id},
        {"$set": {"status": "processing"}}
    )

    try:
        # 3. Download from MinIO
        logger.info(f"🔄 Downloading {filename}...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            minio_client.fget_object(
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=s3_path,
                file_path=temp_pdf.name
            )
            temp_pdf_path = temp_pdf.name

        # 4. Extract text
        logger.info("📄 Extracting text...")
        extracted_text = ""
        with fitz.open(temp_pdf_path) as pdf_doc:
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                extracted_text += f"\n--- Page {page_num + 1} ---\n{page.get_text()}"

        await db["documents"].update_one(
            {"_id": document_id},
            {"$set": {"status": "text_extracted"}}
        )

        # 5. Chunk text
        logger.info("🧩 Chunking text...")
        chunks = get_text_chunks(extracted_text)

        # 6. Generate Gemini Embeddings
        logger.info(f"🧠 Generating {len(chunks)} Gemini embeddings...")
        points = []
        for i, chunk in enumerate(chunks):
            # 1. Generate the Dense Vector (Gemini - Semantic Meaning)
            dense_vector = get_embedding(chunk)

            # 2. Generate the Sparse Vector (BM25 - Exact Keywords)
            sparse_vector = get_sparse_embedding(chunk)

            # 3. Create the Hybrid Point
            point_id = str(uuid.uuid4())
            points.append(
                PointStruct(
                    id=point_id,
                    vector={
                        "text-dense": dense_vector,
                        "text-sparse": sparse_vector
                    },
                    payload={
                        "text": chunk,
                        "filename": filename,
                        "chunk_index": i
                    }
                )
            )

        # 7. Upsert into Qdrant (Properly awaited!)
        logger.info("💾 Uploading vectors to Qdrant...")
        await qdrant_client.upsert(
            collection_name="manualmind_docs_v2",
            points=points
        )

        # 8. Final Status Update
        await db["documents"].update_one(
            {"_id": document_id},
            {"$set": {"status": "completed"}}
        )

        logger.info(f"✅ Successfully processed and embedded {document_id}")
        return {"status": "success", "chunks_indexed": len(chunks)}

    except Exception as e:
        logger.error(f"❌ Error processing {document_id}: {e}", exc_info=True)
        await db["documents"].update_one(
            {"_id": document_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )
        raise e


@celery_app.task(bind=True, name="process_document_task")
def process_document_task(self, document_id: str, filename: str, s3_path: str):
    """
    Celery entry point. Runs the entire async flow in ONE single loop execution.
    """
    return asyncio.run(run_process_document(document_id, filename, s3_path))