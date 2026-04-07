"""Ticket business logic."""
from datetime import datetime
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.logging import get_logger_with_context
from app.integrations.llm_client import LLMClient, get_llm_client
from app.integrations.redis_client import RedisClient, get_redis
from app.models.schemas import (
    LLMOutputSchema, 
    Ticket, 
    TicketRequest, 
    Status, 
    Priority
)


class TicketService:
    """Ticket processing service."""
    
    def __init__(
        self, 
        db: AsyncIOMotorDatabase, 
        llm_client: Optional[LLMClient] = None,
        redis_client: Optional[RedisClient] = None
    ):
        self.db = db
        self.llm = llm_client
        self.redis = redis_client
        self.logger = get_logger_with_context()
    
    async def create_ticket(self, request: TicketRequest) -> Ticket:
        """Create ticket and trigger async processing."""
        # Create document
        ticket = Ticket(
            title=request.title,
            description=request.description,
            priority=request.priority,
            user_id=request.user_id,
            metadata=request.metadata,
            status=Status.PENDING
        )
        
        # Insert to DB
        result = await self.db.tickets.insert_one(
            ticket.model_dump(by_alias=True, exclude={"id"})
        )
        ticket.id = str(result.inserted_id)
        
        self.logger.info(
            "ticket_created",
            ticket_id=ticket.id,
            priority=ticket.priority,
            user_id=ticket.user_id
        )
        
        # Cache result (best effort)
        if self.redis:
            await self.redis.set(
                f"ticket:{ticket.id}", 
                ticket.model_dump_json(),
                ttl=300
            )
        
        return ticket
    
    async def process_with_llm(self, ticket_id: str) -> Ticket:
        """Process ticket with LLM (called by worker)."""
        if not self.llm:
            raise ValueError("LLM client not configured")
        
        # Fetch ticket
        doc = await self.db.tickets.find_one({"_id": ObjectId(ticket_id)})
        if not doc:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        ticket = Ticket(**doc)
        
        # Update status
        await self.db.tickets.update_one(
            {"_id": ObjectId(ticket_id)},
            {"$set": {"status": Status.PROCESSING, "updated_at": datetime.utcnow()}}
        )
        
        try:
            # Structured LLM analysis
            prompt = f"""
            Analyze this support ticket:
            Title: {ticket.title}
            Description: {ticket.description or "N/A"}
            Priority: {ticket.priority}
            """
            
            analysis = await self.llm.generate_structured(
                prompt=prompt,
                schema=LLMOutputSchema,
                system_prompt="You are a support ticket analyzer. Categorize and assess urgency."
            )
            
            # Update ticket with analysis
            await self.db.tickets.update_one(
                {"_id": ObjectId(ticket_id)},
                {
                    "$set": {
                        "llm_analysis": analysis.model_dump(),
                        "status": Status.COMPLETED,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Update cache
            if self.redis:
                await self.redis.delete(f"ticket:{ticket_id}")
            
            self.logger.info(
                "ticket_processed",
                ticket_id=ticket_id,
                category=analysis.category,
                confidence=analysis.confidence
            )
            
            # Return updated ticket
            doc = await self.db.tickets.find_one({"_id": ObjectId(ticket_id)})
            return Ticket(**doc)
            
        except Exception as e:
            # Mark as failed
            await self.db.tickets.update_one(
                {"_id": ObjectId(ticket_id)},
                {
                    "$set": {
                        "status": Status.FAILED,
                        "error": str(e),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            self.logger.error("ticket_processing_failed", ticket_id=ticket_id, error=str(e))
            raise
    
    async def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Get ticket with caching."""
        # Try cache first
        if self.redis:
            cached = await self.redis.get(f"ticket:{ticket_id}")
            if cached:
                self.logger.debug("ticket_cache_hit", ticket_id=ticket_id)
                return Ticket.model_validate_json(cached)
        
        # Fetch from DB
        doc = await self.db.tickets.find_one({"_id": ObjectId(ticket_id)})
        if doc:
            ticket = Ticket(**doc)
            # Update cache
            if self.redis:
                await self.redis.set(
                    f"ticket:{ticket_id}",
                    ticket.model_dump_json(),
                    ttl=300
                )
            return ticket
        return None


async def get_ticket_service(db) -> TicketService:
    """Factory for dependency injection."""
    llm = await get_llm_client()
    redis = await get_redis()
    return TicketService(db=db, llm_client=llm, redis_client=redis)