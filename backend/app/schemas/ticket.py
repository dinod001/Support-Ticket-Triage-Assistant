from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="Brief subject of the ticket")
    description: str = Field(..., min_length=5, description="Full explanation of the customer issue")
    customer_email: Optional[EmailStr] = Field(None, description="Customer contact email address")


class TicketUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Updated ticket status: open, in_progress, resolved, closed")
    category: Optional[str] = Field(None, description="Manually adjusted category")
    priority: Optional[str] = Field(None, description="Manually adjusted priority")
    draft_reply: Optional[str] = Field(None, description="Agent-reviewed and edited draft reply")
    agent_notes: Optional[str] = Field(None, description="Internal agent notes")


class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    customer_email: Optional[str] = None
    status: str
    category: Optional[str] = None
    priority: Optional[str] = None
    sentiment: Optional[str] = None
    summary: Optional[str] = None
    entities: Dict[str, Optional[str]] = {}
    draft_reply: Optional[str] = None
    cited_articles: List[str] = []
    agent_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketListResponse(BaseModel):
    total: int
    tickets: List[TicketResponse]
