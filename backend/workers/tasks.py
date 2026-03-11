import uuid
import tempfile
import asyncio
import fitz  # PyMuPDF
from celery import shared_task
from backend.workers.celery_app import celery_app
from backend.core.config import settings
from backend.core.logger import get_logger
from backend.db.connections import db_clients, connect_databases
from backend.core.embedding import get_text_chunks, get_embedding


logger = get_logger(__name__)


async def run_process_document(document_id: str, filename: str, s3_path: str):
    """
    The actual async logic. Keeping it in one loop prevents 
    the 'Event loop is closed' error.
    """
    # 1. Ensure DB is connected
    if "mongo" not in db_clients:
        await connect_databases()

    db = db_clients["mongo"][settings.MONGO_DB_NAME]
    minio_client = db_clients["minio"]

    # 2. Update status to 'processing'
    await db["documents"].update_one(
        {"_id": document_id},
        {"$set": {"status": "processing"}}
    )

    try:
        # 3. Download from MinIO
        logger.info(f"🔄 Downloading {filename}...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            # Note: minio fget_object is blocking, that's okay here
            minio_client.fget_object(
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=s3_path,
                file_path=temp_pdf.name
            )
            temp_pdf_path = temp_pdf.name

        # 4. Extract text
        logger.info(f"📄 Extracting text...")
        extracted_text = ""
        with fitz.open(temp_pdf_path) as pdf_doc:
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                extracted_text += f"\n--- Page {page_num + 1} ---\n{page.get_text()}"

        # 5. Final Update
        await db["documents"].update_one(
            {"_id": document_id},
            {"$set": {"status": "text_extracted", "extracted_text": extracted_text}}
        )
        logger.info(f"✅ Completed {document_id}")
        return {"status": "success"}

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        await db["documents"].update_one(
            {"_id": document_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )
        raise e


@celery_app.task(bind=True, name="process_document_task")
def process_document_task(self, document_id: str, filename: str, s3_path: str):
    """
    Celery entry point (sync). 
    We run the entire async flow in ONE single loop execution.
    """
    return asyncio.run(run_process_document(document_id, filename, s3_path))


@celery_app.task(name="embed_document_task")
def embed_document_task(document_id: str, extracted_text: str):
    chunks = get_text_chunks(extracted_text)
    qdrant = db_clients["qdrant"]

    points = []
    for i, chunk in enumerate(chunks):
        vector = get_embedding(chunk)
        points.append({
            "id": str(uuid.uuid4()),  # Unique ID for each chunk
            "vector": vector,
            "payload": {"text": chunk, "document_id": document_id}
        })

    # Upsert into Qdrant collection
    qdrant.upsert(
        collection_name="manualmind_docs",
        points=points
    )
    return {"status": "indexed", "chunks": len(chunks)}