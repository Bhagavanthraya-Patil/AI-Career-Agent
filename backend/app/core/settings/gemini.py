from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field, model_validator

from . import BaseConfig


class GeminiSettings(BaseConfig):
    provider: Literal["gemini", "groq", "ollama"] = Field(
        default="gemini",
        description="Default LLM provider to use",
    )

    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key",
    )
    gemini_model: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model identifier",
    )
    gemini_max_tokens: int = Field(
        default=8192,
        description="Maximum output tokens for Gemini",
    )
    gemini_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for Gemini (0.0-2.0)",
    )

    groq_api_key: str = Field(
        default="",
        description="Groq API key",
    )
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model identifier",
    )
    groq_max_tokens: int = Field(
        default=8192,
        description="Maximum output tokens for Groq",
    )
    groq_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for Groq (0.0-2.0)",
    )

    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server base URL",
    )
    ollama_model: str = Field(
        default="llama3.1:8b",
        description="Ollama model identifier",
    )
    ollama_max_tokens: int = Field(
        default=4096,
        description="Maximum output tokens for Ollama",
    )
    ollama_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for Ollama (0.0-2.0)",
    )

    cache_ttl_seconds: int = Field(
        default=3600,
        description="LLM response cache TTL (0 to disable)",
    )

    @model_validator(mode="after")
    def validate_provider_key(self):
        if self.provider == "gemini" and not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is required when provider is 'gemini'"
            )
        if self.provider == "groq" and not self.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is required when provider is 'groq'"
            )
        return self
