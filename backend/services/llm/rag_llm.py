# backend/services/rag_llm.py
import google.generativeai as genai
from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)


# Ensure API key is configured
genai.configure(api_key=settings.GOOGLE_API_KEY)

# Use the fast and cost-effective Flash model for generation #TODO: flex model choice
GENERATION_MODEL = "gemini-2.5-flash-lite"


def generate_rag_answer(question: str, contexts: list[str]) -> str:
    """
    Combines the retrieved contexts and the user's question into a strict prompt,
    then calls Gemini to generate an answer.
    """
    logger.info("🧠 Generating answer using Gemini...")
    model = genai.GenerativeModel(GENERATION_MODEL)

    # Format the retrieved chunks into a single string
    context_text = "\n\n".join([f"--- Context {i + 1} ---\n{c}" for i, c in enumerate(contexts)])

    # Create a strict prompt to prevent hallucinations
    prompt = f"""
    You are a highly capable technical assistant for the 'ManualMind' platform.
    Your task is to answer the user's question using ONLY the provided contexts extracted from technical manuals.

    Rules:
    1. If the answer is not contained in the Contexts, truthfully say "I cannot find the answer in the provided manuals." Do not guess.
    2. Be concise, clear, and professional.
    3. If applicable, mention which context provided the information.

    Contexts:
    {context_text}

    User Question: {question}

    Answer:
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"❌ Failed to generate answer: {e}")
        raise e