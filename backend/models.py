# backend/models.py - API request/response schemas

from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=1000)
    session_id: Optional[str] = Field(None, max_length=64)
    use_fallback: bool = True


class ChatResponse(BaseModel):
    message: str
    intent: str
    confidence: float
    timestamp: str
    session_id: str
    source: Optional[str] = None  # pokedex | llm | database | default
    used_fallback: bool = False
    fallback_reason: Optional[str] = None
