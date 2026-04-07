"""Structured LLM client with JSON output validation."""
import json
from typing import Any, Dict, Optional, Type

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.logging import get_logger_with_context


class LLMResponseError(Exception):
    """Raised when LLM response is invalid."""
    pass


class LLMClient:
    """Production-grade LLM client with structured output."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.timeout = settings.llm_timeout
        self.base_url = "https://api.openai.com/v1"  # Adjust for your provider
        
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        self.logger = get_logger_with_context()
    
    async def generate_structured(
        self,
        prompt: str,
        schema: Type[BaseModel],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1
    ) -> BaseModel:
        """
        Generate structured output validated against Pydantic schema.
        Zero regex parsing - only JSON validation.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Instruct model to return JSON
        json_instruction = f"""
        Respond ONLY with valid JSON matching this schema:
        {schema.model_json_schema()}
        
        Rules:
        - No markdown code blocks
        - No explanatory text
        - Only the JSON object
        """
        
        messages.append({
            "role": "user", 
            "content": f"{prompt}\n\n{json_instruction}"
        })
        
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "response_format": {"type": "json_object"}
                }
            )
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            
            # Validate against Pydantic schema
            validated = schema.model_validate(parsed)
            
            self.logger.info(
                "llm_request_success",
                model=self.model,
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                schema=schema.__name__
            )
            
            return validated
            
        except json.JSONDecodeError as e:
            self.logger.error("llm_invalid_json", error=str(e), content=content)
            raise LLMResponseError(f"LLM returned invalid JSON: {e}")
        except ValidationError as e:
            self.logger.error("llm_schema_validation_failed", error=str(e), content=parsed)
            raise LLMResponseError(f"LLM output failed schema validation: {e}")
        except httpx.HTTPError as e:
            self.logger.error("llm_http_error", error=str(e))
            raise LLMResponseError(f"LLM API request failed: {e}")
        except Exception as e:
            self.logger.error("llm_unexpected_error", error=str(e))
            raise LLMResponseError(f"Unexpected LLM error: {e}")
    
    async def close(self):
        await self.client.aclose()


# Singleton pattern for dependency injection
_llm_client: Optional[LLMClient] = None

async def get_llm_client() -> LLMClient:
    """Get or create LLM client."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client