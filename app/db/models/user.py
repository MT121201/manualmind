# app/db/models/user.py
import uuid
from enum import Enum
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, EmailStr

# --- 1. ROLES ---
class UserRole(str, Enum):
    ADMIN = "admin"     # Can see/query all company docs
    USER = "user"       # Can only see/query standard docs or their own

# --- 2. USER MODEL ---
class UserModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    email: EmailStr
    hashed_password: str
    role: UserRole = UserRole.USER
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


