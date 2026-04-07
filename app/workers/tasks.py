"""Background tasks."""
import asyncio

from app.workers.celery_app import celery_app
from app.integrations.db_client import MongoDBClient, close_db
from app.integrations.llm_client import LLMClient, get_llm_client
from app.integrations.redis_client import close_redis
from app.services.ticket_service import TicketService
from app.core.logging import setup_logging


setup_logging()


@celery_app.task(bind=True, max_retries=3)
def process_ticket_task(self, ticket_id: str):
    """Process ticket with LLM asynchronously."""
    async def _process():
        # Initialize clients
        db_client = MongoDBClient()
        await db_client.connect()
        
        llm_client = await get_llm_client()
        
        try:
            service = TicketService(
                db=db_client.db,
                llm_client=llm_client,
                redis_client=None  # Workers don't need cache
            )
            
            await service.process_with_llm(ticket_id)
            return {"status": "completed", "ticket_id": ticket_id}
            
        except Exception as exc:
            # Retry with exponential backoff
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        finally:
            await close_db()
            await close_redis()
    
    # Run async code in Celery
    return asyncio.run(_process())