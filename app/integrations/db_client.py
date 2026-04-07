"""MongoDB client with connection pooling and indexes."""
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, OperationFailure

from app.core.config import get_settings
from app.core.logging import get_logger_with_context


class MongoDBClient:
    """Production MongoDB client with health checks."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.logger = get_logger_with_context()
    
    async def connect(self):
        """Initialize connection with proper settings."""
        try:
            self.client = AsyncIOMotorClient(
                self.settings.mongodb_url,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=45000,
                serverSelectionTimeoutMS=5000
            )
            self.db = self.client[self.settings.mongodb_db_name]
            
            # Verify connection
            await self.client.admin.command('ping')
            self.logger.info("mongodb_connected", db=self.settings.mongodb_db_name)
            
            # Create indexes
            await self._create_indexes()
            
        except ConnectionFailure as e:
            self.logger.error("mongodb_connection_failed", error=str(e))
            raise
    
    async def _create_indexes(self):
        """Ensure indexes for performance."""
        try:
            # Tickets collection
            await self.db.tickets.create_index("createdAt")
            await self.db.tickets.create_index("priority")
            await self.db.tickets.create_index("status")
            await self.db.tickets.create_index([("userId", 1), ("createdAt", -1)])
            
            self.logger.info("mongodb_indexes_created")
        except OperationFailure as e:
            self.logger.error("mongodb_index_creation_failed", error=str(e))
            # Non-critical, continue without indexes
    
    async def disconnect(self):
        """Graceful shutdown."""
        if self.client:
            self.client.close()
            self.logger.info("mongodb_disconnected")
    
    async def health_check(self) -> bool:
        """Check connectivity."""
        try:
            await self.client.admin.command('ping')
            return True
        except Exception:
            return False


# Singleton
_db_client: Optional[MongoDBClient] = None

async def get_db() -> AsyncIOMotorDatabase:
    """Get database instance."""
    global _db_client
    if _db_client is None:
        _db_client = MongoDBClient()
        await _db_client.connect()
    return _db_client.db

async def close_db():
    """Cleanup on shutdown."""
    global _db_client
    if _db_client:
        await _db_client.disconnect()
        _db_client = None