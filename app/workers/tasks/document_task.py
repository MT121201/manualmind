# app/workers/task/document_task.py
import uuid
import tempfile
import fitz  # PyMuPDF
import os

from qdrant_client.models import PointStruct

from app.core.config import settings
from app.core.logger import get_logger
from app.core.embedding import get_embedding, get_sparse_embedding, get_text_chunks
from app.db.connections import db_manager
from app.workers.celery_app import celery_app, worker_loop

logger = get_logger(__name__)


# --- Task Pipeline ---
@celery_app.task(bind=True, name="process_document_task")
def process_document_task(self, document_id: str, filename: str, s3_path: str):
    # Use the persistent loop instead of starting/stopping one
    return worker_loop.run_until_complete(run_process_document(document_id, filename, s3_path))


# --- Task Pipeline ---
async def run_process_document(document_id: str, filename: str, s3_path: str):
    # Ensure connections are active
    # await db_manager.connect() #The worker init do that now

    # Access via the manager
    db = db_manager.mongo[settings.MONGO_DB_NAME]
    minio_client = db_manager.minio
    qdrant_client = db_manager.qdrant

    await db["documents"].update_one({"_id": document_id}, {"$set": {"status": "processing"}})

    temp_pdf_path = None
    try:
        # 1. Download
        logger.info(f"🔄 Downloading {filename}...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf_path = temp_pdf.name
            minio_client.fget_object(settings.MINIO_BUCKET_NAME, s3_path, temp_pdf_path)

        # 2. Extract
        logger.info("📄 Extracting text...")
        extracted_text = ""
        with fitz.open(temp_pdf_path) as pdf_doc:
            for page in pdf_doc:
                extracted_text += page.get_text()

        # 3. Chunk & Embed
        chunks = get_text_chunks(extracted_text)
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector={"text-dense": get_embedding(c), "text-sparse": get_sparse_embedding(c)},
                payload={"text": c, "filename": filename, "chunk_index": i}
            ) for i, c in enumerate(chunks)
        ]

        # 4. Upload
        await qdrant_client.upsert(collection_name="manualmind_docs_v2", points=points)
        await db["documents"].update_one({"_id": document_id}, {"$set": {"status": "completed"}})

        return {"status": "success", "chunks_indexed": len(chunks)}

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        await db["documents"].update_one({"_id": document_id}, {"$set": {"status": "failed", "error": str(e)}})
        raise e
    finally:
        # CRITICAL: Clean up temp file
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
