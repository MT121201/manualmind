# app/api/v1/endpoints/documents.py
import uuid
import asyncio
from functools import partial

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from minio import Minio
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.deps import get_mongo_db, get_minio
from app.workers.tasks import process_document_task
from app.core.logger import get_logger
from app.core.config import settings
from app.core.security import get_current_user
from app.db.models.user import UserRole
from app.db.models.document import DocumentModel

router = APIRouter()
logger = get_logger(__name__)


@router.post("/upload")
async def upload_document(
        file: UploadFile = File(...),
        current_user: dict = Depends(get_current_user),
        minio_client: Minio = Depends(get_minio),
        db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    try:
        # 1. 🔒 Determine RBAC permissions
        allowed_roles = [UserRole.ADMIN, UserRole.USER]
        if current_user["role"] == UserRole.ADMIN:
            allowed_roles = [UserRole.ADMIN]

        # 2. 🛡️ Instantiate the Pydantic Model FIRST
        # This automatically generates the `id` and `created_at` timestamps!
        new_doc = DocumentModel(
            filename=file.filename,
            s3_path="",  # Temporary placeholder
            owner_id=current_user["_id"],
            allowed_roles=allowed_roles
        )

        # 3. Build the MinIO path using the auto-generated ID
        doc_id = new_doc.id
        object_name = f"{doc_id}/{file.filename}"
        new_doc.s3_path = object_name  # Update the model with the real path

        # 4. Non-blocking upload to MinIO
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

        # 5. Save the VALIDATED model to MongoDB
        # .model_dump(by_alias=True) ensures 'id' becomes '_id' for Mongo!
        await db["documents"].insert_one(new_doc.model_dump(by_alias=True))

        # 6. Trigger background worker
        process_document_task.delay(doc_id, file.filename, object_name)

        return {"document_id": doc_id, "message": "Upload successful, processing started."}

    except Exception as e:
        logger.error(f"❌ Upload failed for {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )