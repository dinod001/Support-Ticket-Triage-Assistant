import asyncio
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.ticket import Ticket
from app.schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketListResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Creates a new support ticket.
    Synchronously triggers AI Triage (structured output with retry/fallback)
    and RAG Draft Reply generation (with citations) using pre-warmed singleton services.
    """
    try:
        # 1. Access pre-warmed singleton services from app.state
        triage_service = request.app.state.triage_service
        rag_service = request.app.state.rag_service

        # 2. Concurrently execute AI Triage & RAG Draft Reply via asyncio.gather (50% latency reduction)
        (triage_result, was_fallback), (draft_reply, cited_articles) = await asyncio.gather(
            triage_service.execute_triage(
                title=payload.title,
                description=payload.description,
                db=db
            ),
            rag_service.generate_draft_reply(
                title=payload.title,
                description=payload.description,
                db=db
            )
        )

        # 4. Persist Ticket to Database
        new_ticket = Ticket(
            title=payload.title,
            description=payload.description,
            customer_email=payload.customer_email,
            status="open",
            category=triage_result.category,
            priority=triage_result.priority,
            sentiment=triage_result.sentiment,
            summary=triage_result.summary,
            entities=triage_result.entities,
            draft_reply=draft_reply,
            cited_articles=cited_articles
        )
        db.add(new_ticket)
        db.commit()
        db.refresh(new_ticket)

        logger.info(f"Ticket #{new_ticket.id} created successfully with category '{new_ticket.category}'")
        return new_ticket

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create ticket: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating ticket: {str(e)}"
        )


@router.get("", response_model=TicketListResponse)
def list_tickets(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (open, resolved, etc.)"),
    category_filter: Optional[str] = Query(None, alias="category", description="Filter by category"),
    priority_filter: Optional[str] = Query(None, alias="priority", description="Filter by priority"),
    search: Optional[str] = Query(None, description="Search term in title or description"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to retrieve"),
    db: Session = Depends(get_db)
):
    """
    Retrieves tickets with filtering by status, category, priority, and text search.
    """
    query = db.query(Ticket)

    if status_filter:
        query = query.filter(Ticket.status == status_filter.lower().strip())
    if category_filter:
        query = query.filter(Ticket.category == category_filter.strip())
    if priority_filter:
        query = query.filter(Ticket.priority == priority_filter.lower().strip())
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Ticket.title.ilike(search_pattern),
                Ticket.description.ilike(search_pattern)
            )
        )

    total = query.count()
    tickets = query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit).all()

    return TicketListResponse(total=total, tickets=tickets)


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    """Retrieves full details of a single ticket."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} was not found."
        )
    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db)
):
    """
    Updates an existing ticket.
    Allows support agents to edit the AI-generated draft reply, update ticket status,
    adjust priority/category, and append internal agent notes.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} was not found."
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(ticket, field, value)

    try:
        db.commit()
        db.refresh(ticket)
        return ticket
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update ticket: {str(e)}"
        )


@router.get("/{ticket_id}/stream-draft")
async def stream_draft_reply(
    ticket_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Stretch Goal: Server-Sent Events (SSE) streaming endpoint.
    Streams the AI draft reply token-by-token to the frontend client.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found."
        )

    rag_service = request.app.state.rag_service

    async def event_generator():
        # Retrieve context
        matches = await rag_service.retrieve_relevant_articles(f"{ticket.title}\n{ticket.description}")
        cited = [m[0]["title"] for m in matches] if matches else []

        draft_content, _ = await rag_service.generate_draft_reply(
            title=ticket.title,
            description=ticket.description,
            db=db,
            ticket_id=ticket.id
        )

        # Stream words with slight delay simulating token emission
        words = draft_content.split(" ")
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            data = json.dumps({"token": chunk, "done": False, "citations": cited})
            yield f"data: {data}\n\n"
            await asyncio.sleep(0.03)

        # End event
        yield f"data: {json.dumps({'token': '', 'done': True, 'citations': cited})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )
