from dotenv import load_dotenv
load_dotenv()
import google.generativeai as genai
from app.core.config import settings
from fastembed import SparseTextEmbedding
from app.core.logger import get_logger


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


logger = get_logger(__name__)

# Initialize the model once in memory
logger.info("Loading BM25 Sparse Embedding model...")
sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")


def get_sparse_embedding(text: str):
    """Generates a BM25 sparse vector for exact keyword matching."""
    # fastembed returns a generator, we just need the first item
    result = list(sparse_model.embed([text]))[0]

    # Qdrant expects a specific format for sparse vectors: indices and values
    return {
        "indices": result.indices.tolist(),
        "values": result.values.tolist()
    }