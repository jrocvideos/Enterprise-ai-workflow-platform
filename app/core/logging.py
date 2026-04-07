"""Structured JSON logging with request_id tracing."""
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict

import structlog


def setup_logging(log_level: str = "INFO", json_format: bool = True):
    """Configure structured logging."""
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if json_format:
        # Production: JSON logs
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    else:
        # Development: Pretty console
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer(colors=True)
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level),
    )
    
    return structlog.get_logger()


def get_logger_with_context(request_id: str = "N/A", **kwargs) -> Any:
    """Get logger bound with request context."""
    logger = structlog.get_logger()
    return logger.bind(request_id=request_id, **kwargs)