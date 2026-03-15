# app/workers/tasks/document_task.py
import uuid
import tempfile
import fitz  # PyMuPDF
import os
import asyncio

from qdrant_client.models import PointStruct

from app.core.config import settings
from app.core.logger import get_logger
from app.core.embedding import get_embedding, get_sparse_embedding, get_text_chunks
from app.db.connections import db_manager
from app.workers.celery_app import celery_app, worker_loop

logger = get_logger(__name__)


@celery_app.task(bind=True, name="process_document_task")
def process_document_task(self, document_id: str, filename: str, s3_path: str):
    """Sync wrapper for Celery to run the async pipeline."""
    return worker_loop.run_until_complete(run_process_document(document_id, filename, s3_path))


async def run_process_document(document_id: str, filename: str, s3_path: str):
    db = db_manager.mongo[settings.MONGO_DB_NAME]
    minio_client = db_manager.minio
    qdrant_client = db_manager.qdrant

    await db["documents"].update_one({"_id": document_id}, {"$set": {"status": "processing"}})
    temp_pdf_path = None

    try:
        # 1. Download from MinIO
        logger.info(f"🔄 Downloading {filename} from storage...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf_path = temp_pdf.name
            # run_in_executor prevents MinIO's sync SDK from blocking the async loop
            await asyncio.to_thread(
                minio_client.fget_object, settings.MINIO_BUCKET_NAME, s3_path, temp_pdf_path
            )

        # 2. Extract Text via PyMuPDF
        logger.info(f"📄 Extracting text from {filename}...")
        extracted_text = ""
        with fitz.open(temp_pdf_path) as pdf_doc:
            for page in pdf_doc:
                extracted_text += page.get_text()

        # 3. Chunk the text
        chunks = get_text_chunks(extracted_text)
        logger.info(f"🧩 Created {len(chunks)} chunks. Beginning embedding process...")

        # 4. 🛡️ BATCHING & RATE LIMITING PIPELINE
        BATCH_SIZE = 50  # Qdrant loves batches of 50-100
        points_batch = []
        total_indexed = 0

        for i, chunk in enumerate(chunks):
            # Using to_thread so the sync embedding calls don't freeze the worker
            dense_vector = await asyncio.to_thread(get_embedding, chunk)
            sparse_vector = await asyncio.to_thread(get_sparse_embedding, chunk)

            points_batch.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector={"text-dense": dense_vector, "text-sparse": sparse_vector},
                    payload={
                        "text": chunk,
                        "filename": filename,
                        "document_id": document_id,  # Crucial for filtering later!
                        "chunk_index": i
                    }
                )
            )

            # Once batch is full, upload to Qdrant and sleep
            if len(points_batch) >= BATCH_SIZE:
                await qdrant_client.upsert(
                    collection_name="manualmind_docs_v2",
                    points=points_batch
                )
                total_indexed += len(points_batch)
                logger.info(f"✅ Upserted batch of {len(points_batch)}. Total: {total_indexed}/{len(chunks)}")
                points_batch = []  # Reset batch

                # RATE LIMIT PROTECTION: Sleep for 1 second between batches
                await asyncio.sleep(1)

        # Upload any remaining points in the final partial batch
        if points_batch:
            await qdrant_client.upsert(collection_name="manualmind_docs_v2", points=points_batch)
            total_indexed += len(points_batch)
            logger.info(f"✅ Upserted final batch. Total: {total_indexed}/{len(chunks)}")

        # 5. Mark Complete
        await db["documents"].update_one(
            {"_id": document_id},
            {"$set": {"status": "completed", "total_chunks": total_indexed}}
        )
        return {"status": "success", "chunks_indexed": total_indexed}

    except Exception as e:
        logger.error(f"❌ Error processing document: {e}", exc_info=True)
        await db["documents"].update_one(
            {"_id": document_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )
        raise e
    finally:
        # CRITICAL: Clean up temp file so your Docker container doesn't run out of disk space
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
            logger.info("🧹 Cleaned up temporary PDF file.")