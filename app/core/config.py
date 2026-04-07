"""Pydantic settings with env validation."""
from functools import lru_cache
from typing import Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # App
    app_name: str = "enterprise-ai-workflow-platform"
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # MongoDB
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    mongodb_db_name: str = Field(default="workflow_db", env="MONGODB_DB_NAME")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_ttl: int = Field(default=3600, env="REDIS_TTL")
    
    # LLM
    llm_api_key: Optional[str] = Field(default=None, env="LLM_API_KEY")
    llm_model: str = Field(default="gpt-4", env="LLM_MODEL")
    llm_timeout: int = Field(default=30, env="LLM_TIMEOUT")
    
    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/0", env="CELERY_RESULT_BACKEND")
    
    @validator("log_level")
    def validate_log_level(cls, v):
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v.upper()


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()