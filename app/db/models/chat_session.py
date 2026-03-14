# app/db/models/chat_session.py
import uuid
from enum import Enum
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, EmailStr

from app.db.models.user import UserRole


# --- 1. COLD MEMORY MODEL ---
class ChatSessionModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    session_id: str
    user_id: str
    summary: Optional[str] = None # LLM generated summary of the chat
    messages: List[dict] = []     # The archived conversation from Redis
    archived_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))