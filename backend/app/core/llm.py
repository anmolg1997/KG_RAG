"""
LLM client wrapper using LiteLLM for model-agnostic inference.
Supports OpenAI, Anthropic, Ollama, and other providers.
"""

import json
import logging
import re
from typing import Any, Optional, Type, TypeVar

import litellm
from litellm import acompletion
from pydantic import BaseModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import settings

logger = logging.getLogger(__name__)


class APIKeyMaskingFilter(logging.Filter):
    """
    Logging filter that masks API keys and other sensitive data.
    
    Patterns masked:
    - OpenAI keys: sk-proj-..., sk-...
    - Anthropic keys: sk-ant-...
    - Bearer tokens
    - Generic API keys
    """
    
    # Patterns for various API key formats
    PATTERNS = [
        # OpenAI API keys (sk-proj-..., sk-...)
        (r'(sk-proj-[a-zA-Z0-9]{20})[a-zA-Z0-9_-]+', r'\1***MASKED***'),
        (r'(sk-[a-zA-Z0-9]{20})[a-zA-Z0-9_-]+', r'\1***MASKED***'),
        # Anthropic API keys
        (r'(sk-ant-[a-zA-Z0-9]{10})[a-zA-Z0-9_-]+', r'\1***MASKED***'),
        # Bearer tokens in headers
        (r"'Authorization': 'Bearer ([^']{10})[^']*'", r"'Authorization': 'Bearer \1***MASKED***'"),
        # Generic API key patterns
        (r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{20})[a-zA-Z0-9_-]+', r'\1\2***MASKED***'),
    ]
    
    def __init__(self):
        super().__init__()
        # Compile patterns for efficiency
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), replacement)
            for pattern, replacement in self.PATTERNS
        ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Apply masking to the log message."""
        if record.msg:
            record.msg = self._mask_sensitive_data(str(record.msg))
        if record.args:
            record.args = tuple(
                self._mask_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True
    
    def _mask_sensitive_data(self, text: str) -> str:
        """Replace sensitive patterns in text with masked versions."""
        for pattern, replacement in self.compiled_patterns:
            text = pattern.sub(replacement, text)
        return text


def setup_secure_logging():
    """Apply API key masking filter to all relevant loggers."""
    masking_filter = APIKeyMaskingFilter()
    
    # Apply to root logger
    logging.getLogger().addFilter(masking_filter)
    
    # Apply to LiteLLM loggers specifically
    for logger_name in ['LiteLLM', 'litellm', 'openai', 'anthropic']:
        log = logging.getLogger(logger_name)
        log.addFilter(masking_filter)
    
    # Also apply masking filter to all existing handlers
    for handler in logging.getLogger().handlers:
        handler.addFilter(masking_filter)


class SecurePrintRedirector:
    """
    Redirects stdout/stderr through API key masking.
    Used to catch LiteLLM's direct print() statements.
    """
    
    def __init__(self, original_stream, masking_filter: APIKeyMaskingFilter):
        self.original_stream = original_stream
        self.masking_filter = masking_filter
    
    def write(self, text: str):
        masked_text = self.masking_filter._mask_sensitive_data(text)
        self.original_stream.write(masked_text)
    
    def flush(self):
        self.original_stream.flush()
    
    def __getattr__(self, name):
        return getattr(self.original_stream, name)


def setup_secure_print():
    """Redirect print statements through API key masking."""
    import sys
    masking_filter = APIKeyMaskingFilter()
    sys.stdout = SecurePrintRedirector(sys.__stdout__, masking_filter)
    sys.stderr = SecurePrintRedirector(sys.__stderr__, masking_filter)


# Apply secure logging on module import
setup_secure_logging()
setup_secure_print()

# Type variable for generic structured output
T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """
    Model-agnostic LLM client using LiteLLM.
    
    Supports:
        - OpenAI (gpt-4o, gpt-4o-mini, etc.)
        - Anthropic (claude-3-5-sonnet, etc.)
        - Ollama (llama3.2, mistral, etc.)
        - And many more via LiteLLM
    
    Usage:
        client = LLMClient()
        
        # Simple completion
        response = await client.complete("What is 2+2?")
        
        # Structured output with Pydantic
        class Answer(BaseModel):
            value: int
            explanation: str
        
        result = await client.complete_structured(
            "What is 2+2?",
            response_model=Answer
        )
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        self.model = model or settings.default_llm_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Configure LiteLLM
        self._configure_api_keys()
        
        # Enable verbose logging in debug mode
        if settings.debug:
            litellm.set_verbose = True

    def _configure_api_keys(self) -> None:
        """Configure API keys for different providers."""
        import os
        
        if settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = settings.openai_api_key
        
        if settings.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
        
        # Ollama doesn't need API key, just base URL
        if self.model.startswith("ollama/"):
            litellm.api_base = settings.ollama_base_url

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    )
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a completion for the given prompt.
        
        Args:
            prompt: User prompt/message
            system_prompt: Optional system prompt for context
            model: Override default model
            temperature: Override default temperature
            max_tokens: Override default max tokens
            
        Returns:
            Generated text response
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await acompletion(
                model=model or self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )
            
            content = response.choices[0].message.content
            logger.debug(f"LLM response: {content[:200]}...")
            return content
            
        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    )
    async def complete_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> T:
        """
        Generate a structured completion that conforms to a Pydantic model.
        
        Uses JSON mode or function calling depending on model support.
        
        Args:
            prompt: User prompt/message
            response_model: Pydantic model class for response structure
            system_prompt: Optional system prompt for context
            model: Override default model
            temperature: Override default temperature
            max_tokens: Override default max tokens
            
        Returns:
            Parsed response as Pydantic model instance
        """
        # Build JSON schema instruction
        schema = response_model.model_json_schema()
        schema_str = json.dumps(schema, indent=2)
        
        json_instruction = f"""
You must respond with valid JSON that conforms to this schema:
{schema_str}

Important:
- Output ONLY the JSON object, no additional text
- Ensure all required fields are present
- Use null for optional fields if not applicable
"""
        
        # Combine system prompts
        full_system = system_prompt or ""
        full_system += "\n\n" + json_instruction
        
        messages = [
            {"role": "system", "content": full_system.strip()},
            {"role": "user", "content": prompt},
        ]
        
        try:
            response = await acompletion(
                model=model or self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                response_format={"type": "json_object"},
            )
            
            content = response.choices[0].message.content
            logger.debug(f"LLM structured response: {content[:200]}...")
            
            # Parse and validate with Pydantic
            data = json.loads(content)
            return response_model.model_validate(data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"LLM response was not valid JSON: {e}")
        except Exception as e:
            logger.error(f"Structured completion failed: {e}")
            raise

    async def complete_with_tools(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Generate a completion with tool/function calling capability.
        
        Args:
            prompt: User prompt/message
            tools: List of tool definitions in OpenAI format
            system_prompt: Optional system prompt
            model: Override default model
            
        Returns:
            Response including any tool calls
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await acompletion(
                model=model or self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            
            message = response.choices[0].message
            
            result = {
                "content": message.content,
                "tool_calls": None,
            }
            
            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": json.loads(tc.function.arguments),
                        },
                    }
                    for tc in message.tool_calls
                ]
            
            return result
            
        except Exception as e:
            logger.error(f"Tool completion failed: {e}")
            raise


# Singleton instances for different use cases
_default_client: Optional[LLMClient] = None
_extraction_client: Optional[LLMClient] = None
_rag_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the default LLM client."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


def get_extraction_client() -> LLMClient:
    """Get the LLM client optimized for extraction tasks."""
    global _extraction_client
    if _extraction_client is None:
        _extraction_client = LLMClient(
            model=settings.extraction_model,
            temperature=settings.extraction_temperature,
            max_tokens=settings.extraction_max_tokens,
        )
    return _extraction_client


def get_rag_client() -> LLMClient:
    """Get the LLM client optimized for RAG response generation."""
    global _rag_client
    if _rag_client is None:
        _rag_client = LLMClient(
            model=settings.rag_model,
            temperature=settings.rag_temperature,
            max_tokens=settings.rag_max_tokens,
        )
    return _rag_client
