import uuid
import asyncio
from functools import partial
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from backend.db.connections import db_clients
from backend.core.config import settings
from backend.workers.tasks import process_document_task
from backend.core.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    1. Generates a unique ID.
    2. Streams the file to MinIO (non-blocking).
    3. Saves metadata to MongoDB.
    4. Triggers the background Celery task for extraction.
    """
    doc_id = str(uuid.uuid4())
    object_name = f"{doc_id}/{file.filename}"

    try:
        minio_client = db_clients.get("minio")
        mongo_db = db_clients["mongo"][settings.MONGO_DB_NAME]

        # 1. Non-blocking upload to MinIO
        # Since MinIO SDK is synchronous, we offload it to a thread
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(
                minio_client.put_object,
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=object_name,
                data=file.file,
                length=-1,
                part_size=10 * 1024 * 1024  # 10MB parts for memory efficiency
            )
        )

        # 2. Save initial document status to MongoDB
        doc_metadata = {
            "_id": doc_id,
            "filename": file.filename,
            "s3_path": object_name,
            "status": "pending",
            "error": None
        }
        await mongo_db["documents"].insert_one(doc_metadata)

        # 3. Trigger background worker
        process_document_task.delay(doc_id, file.filename, object_name)

        return {"document_id": doc_id, "message": "Upload successful, processing started."}

    except Exception as e:
        logger.error(f"❌ Upload failed for {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )