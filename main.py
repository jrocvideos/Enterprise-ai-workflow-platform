"""Application entry point."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware, ErrorHandlerMiddleware
from app.integrations.db_client import close_db
from app.integrations.redis_client import close_redis
from app.api.routes import tickets, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    settings = get_settings()
    setup_logging(settings.log_level, json_format=not settings.debug)
    
    # Initialize connections
    from app.integrations.db_client import get_db
    await get_db()
    
    from app.integrations.redis_client import get_redis
    await get_redis()
    
    print(f"🚀 {settings.app_name} started")
    yield
    
    # Shutdown
    await close_db()
    await close_redis()
    print("👋 Shutting down gracefully")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan
    )
    
    # Middleware
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Routes
    app.include_router(tickets.router)
    app.include_router(health.router)
    
    @app.get("/")
    async def root():
        return {
            "name": settings.app_name,
            "version": "0.1.0",
            "status": "running"
        }
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
