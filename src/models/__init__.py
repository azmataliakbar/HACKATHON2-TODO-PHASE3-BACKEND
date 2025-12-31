from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func
import uuid


class User(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    email: str = Field(unique=True, nullable=False)
    name: str
    password_hash: str
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class TaskBase(SQLModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    completed: bool = Field(default=False)


class Task(TaskBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)


class Conversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    conversation_id: int = Field(foreign_key="conversation.id")
    role: str = Field(regex="^(user|assistant)$")
    content: str = Field(max_length=10000)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


# Request/Response models for API
class TaskCreate(SQLModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    completed: bool = Field(default=False)


class TaskUpdate(SQLModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    completed: Optional[bool] = None


class TaskRead(TaskBase):
    id: int
    user_id: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class ConversationCreate(SQLModel):
    user_id: str


class MessageCreate(SQLModel):
    user_id: str
    conversation_id: int
    role: str = Field(regex="^(user|assistant)$")
    content: str = Field(max_length=10000)


class ChatRequest(SQLModel):
    conversation_id: Optional[str] = None
    message: str = Field(min_length=1, max_length=1000)


class ChatResponse(SQLModel):
    conversation_id: str
    response: str
    tool_calls: list = []


# ============================================
# ALIASES for backward compatibility
# ============================================
TaskResponse = TaskRead  # ← ADD THIS LINE


# ============================================
# EXPORTS
# ============================================
__all__ = [
    # Database models
    "User",
    "Task",
    "TaskBase",
    "Conversation",
    "Message",
    # Request/Response schemas
    "TaskCreate",
    "TaskUpdate",
    "TaskRead",
    "TaskResponse",  # ← ADD THIS
    "ConversationCreate",
    "MessageCreate",
    "ChatRequest",
    "ChatResponse",
]
