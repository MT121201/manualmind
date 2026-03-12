import google.generativeai as genai
from backend.core.config import settings

genai.configure(api_key=settings.GOOGLE_API_KEY)

# Use the current stable Gemini embedding model
EMBEDDING_MODEL = "models/gemini-embedding-001"

def get_text_chunks(text: str, chunk_size: int = 2000):
    """Splits text into chunks, keeping them small for RAG precision."""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def get_embedding(text: str):
    """Generates an embedding vector using Gemini's API."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document",
        output_dimensionality=768  # 👈 Tell Gemini to shrink it to match Qdrant!
    )
    return result['embedding']