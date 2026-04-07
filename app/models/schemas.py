"""Data models."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Status(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TicketRequest(BaseModel):
    """Incoming ticket creation request."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    priority: Priority = Field(default=Priority.MEDIUM)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    user_id: str = Field(..., alias="userId")


class LLMOutputSchema(BaseModel):
    """Structured LLM output example."""
    category: str = Field(..., description="Ticket category")
    sentiment: str = Field(..., description="Sentiment analysis")
    urgency_score: int = Field(..., ge=1, le=10)
    suggested_actions: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)


class Ticket(BaseModel):
    """Ticket database model."""
    id: Optional[str] = Field(None, alias="_id")
    title: str
    description: Optional[str] = None
    priority: Priority
    status: Status = Status.PENDING
    user_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    llm_analysis: Optional[LLMOutputSchema] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class TicketResponse(BaseModel):
    """API response model."""
    id: str
    title: str
    status: Status
    priority: Priority
    llm_analysis: Optional[LLMOutputSchema] = None
    created_at: datetime


class HealthCheck(BaseModel):
    """Health check response."""
    status: str
    services: Dict[str, bool]
    version: str