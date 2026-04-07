"""Ticket endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List

from app.integrations.db_client import get_db
from app.models.schemas import TicketRequest, TicketResponse, HealthCheck
from app.services.ticket_service import TicketService, get_ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("/", response_model=TicketResponse, status_code=201)
async def create_ticket(
    request: TicketRequest,
    db=Depends(get_db)
):
    """Create new ticket."""
    service = await get_ticket_service(db)
    ticket = await service.create_ticket(request)
    
    # Trigger async processing (queue job)
    from app.workers.tasks import process_ticket_task
    process_ticket_task.delay(ticket.id)
    
    return ticket


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, db=Depends(get_db)):
    """Get ticket by ID."""
    service = await get_ticket_service(db)
    ticket = await service.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket