# app/api/v1/endpoints/documents.py
import uuid
import asyncio
from functools import partial
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from minio import Minio
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_mongo_db, get_minio
from app.core.config import settings
from app.workers.tasks import process_document_task
from app.core.logger import get_logger

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from app.core.security import get_current_user
from app.db.models.user import UserRole

router = APIRouter()
logger = get_logger(__name__)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    minio_client: Minio = Depends(get_minio),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    doc_id = str(uuid.uuid4())
    object_name = f"{doc_id}/{file.filename}"
    """
    1. Generates a unique ID.
    2. Streams the file to MinIO (non-blocking).
    3. Saves metadata to MongoDB (with Owner ID!).
    4. Triggers the background Celery task for extraction.
    """
    doc_id = str(uuid.uuid4())
    object_name = f"{doc_id}/{file.filename}"

    try:

        # 1. Non-blocking upload to MinIO
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(
                minio_client.put_object,
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=object_name,
                data=file.file,
                length=-1,
                part_size=10 * 1024 * 1024
            )
        )

        # 🔒 NEW: Determine document permissions based on who uploaded it
        allowed_roles = [UserRole.ADMIN, UserRole.USER]
        if current_user["role"] == UserRole.ADMIN:
            # If an admin uploads it, let's assume it's an admin-only doc for now
            # (You can change this later to let them select it in the UI)
            allowed_roles = [UserRole.ADMIN]

        # 2. Save initial document status to MongoDB WITH RBAC
        doc_metadata = {
            "_id": doc_id,
            "filename": file.filename,
            "s3_path": object_name,
            "status": "pending",
            "owner_id": current_user["_id"],       # 🔒 NEW!
            "allowed_roles": allowed_roles,        # 🔒 NEW!
            "error": None
        }
        await db["documents"].insert_one(doc_metadata)

        # 3. Trigger background worker
        process_document_task.delay(doc_id, file.filename, object_name)

        return {"document_id": doc_id, "message": "Upload successful, processing started."}

    except Exception as e:
        logger.error(f"❌ Upload failed for {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )