# app/core/llm_factory.py
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from app.core.config import settings

def get_reasoning_llm(temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    """Returns the primary agent model. Defaults to temp 0 for logic/routing."""
    return ChatGoogleGenerativeAI(
        model=settings.REASONING_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=temperature
    )

def get_fast_llm(temperature: float = 0.3) -> ChatGoogleGenerativeAI:
    """Returns the cheaper, faster model for summarization and memory tasks."""
    return ChatGoogleGenerativeAI(
        model=settings.FAST_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=temperature
    )

def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Returns the embedding model for vector search."""
    return GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        google_api_key=settings.GOOGLE_API_KEY
    )