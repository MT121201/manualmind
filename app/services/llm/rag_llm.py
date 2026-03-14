# app/services/llm.py
import google.generativeai as genai
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

genai.configure(api_key=settings.GOOGLE_API_KEY)
GENERATION_MODEL = "gemini-2.5-flash-lite"


def generate_rag_answer(question: str, contexts: list[str], chat_history: list[dict] = None) -> str:
    """
    Generates an answer using the retrieved contexts and the previous conversation history.
    """
    logger.info("🧠 Generating answer using Gemini...")
    model = genai.GenerativeModel(GENERATION_MODEL)

    # 1. Format the retrieved chunks
    context_text = "\n\n".join([f"--- Context {i + 1} ---\n{c}" for i, c in enumerate(contexts)])

    # 2. Format the chat history (if any)
    history_text = "No previous conversation."
    if chat_history:
        history_lines = []
        for msg in chat_history:
            role_name = "User" if msg["role"] == "user" else "Assistant"
            history_lines.append(f"{role_name}: {msg['content']}")
        history_text = "\n".join(history_lines)

    # 3. Inject everything into a strict prompt
    prompt = f"""
    You are a highly capable technical assistant for the 'ManualMind' platform.
    Your task is to answer the User's current question using ONLY the provided Contexts extracted from technical manuals.

    You have access to the Previous Conversation to understand context (e.g., if the user says "tell me more about that").

    Rules:
    1. If the answer is not contained in the Contexts or Previous Conversation, truthfully say "I cannot find the answer in the provided manuals." Do not guess.
    2. Be concise, clear, and professional.
    3. If applicable, mention which context provided the information.

    === Previous Conversation ===
    {history_text}

    === Contexts ===
    {context_text}

    === Current User Question ===
    {question}

    Answer:
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"❌ Failed to generate answer: {e}")
        raise e


def rewrite_query(question: str, chat_history: list[dict]) -> str:
    """
    Rewrites a conversational question into a standalone search query
    using the chat history for context.
    """
    if not chat_history:
        # No history? No need to rewrite! Save tokens.
        return question

    logger.info("✍️ Rewriting query based on chat history...")
    model = genai.GenerativeModel(GENERATION_MODEL)

    history_lines = []
    for msg in chat_history:
        role_name = "User" if msg["role"] == "user" else "Assistant"
        history_lines.append(f"{role_name}: {msg['content']}")
    history_text = "\n".join(history_lines)
    logger.info(history_lines)

    prompt = f"""
    Given the following conversation history and the user's latest question, 
    rewrite the question to be a standalone search query that can be used in a vector database.

    Do NOT answer the question. JUST output the rewritten query.
    If the question is already standalone, output it exactly as is.

    === History ===
    {history_text}

    === Latest Question ===
    {question}

    Standalone Query:
    """

    try:
        response = model.generate_content(prompt)
        rewritten_query = response.text.strip()
        logger.info(f"🔄 Rewrote: '{question}' -> '{rewritten_query}'")
        return rewritten_query
    except Exception as e:
        logger.error(f"❌ Failed to rewrite query: {e}")
        return question  # Fallback to original question if it fails