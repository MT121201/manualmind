# app/db/models/document.py
import uuid
from enum import Enum
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, EmailStr

from app.db.models.user import UserRole


# --- 1. DOCUMENT MODEL (With RBAC) ---
class DocumentModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    filename: str
    s3_path: str
    status: str = "pending"
    owner_id: str  # Links to UserModel._id
    allowed_roles: List[UserRole] = [UserRole.ADMIN, UserRole.USER] # Who can RAG this?
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
