from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx

from app.collectors.logging import CollectorLoggerProtocol


class LLMError(Exception):
    pass


class LLMProviderError(LLMError):
    def __init__(self, message: str, provider: str, status_code: Optional[int] = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


class RateLimitError(LLMProviderError):
    def __init__(self, provider: str, retry_after: float = 60.0):
        self.retry_after = retry_after
        super().__init__("Rate limit exceeded", provider, 429)


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        ...

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[type] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> dict[str, Any]:
        ...


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str, **kwargs: Any) -> None:
        self._api_key = api_key
        self._model = model
        self._max_tokens = kwargs.get("max_tokens", 8192)
        self._temperature = kwargs.get("temperature", 0.7)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self._api_key)

            config = types.GenerateContentConfig(
                max_output_tokens=max_tokens or self._max_tokens,
                temperature=temperature or self._temperature,
            )
            if system_prompt:
                config.system_instruction = system_prompt

            response = client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=config,
            )
            return response.text
        except Exception as e:
            raise LLMProviderError(str(e), "gemini") from e

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[type] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> dict[str, Any]:
        if response_model is not None:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=self._api_key)

                config = types.GenerateContentConfig(
                    max_output_tokens=max_tokens or self._max_tokens,
                    temperature=temperature or self._temperature,
                    response_mime_type="application/json",
                    response_schema=response_model,
                )
                if system_prompt:
                    config.system_instruction = system_prompt

                response = client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=config,
                )

                if hasattr(response, "parsed") and response.parsed is not None:
                    data = response.parsed
                    if isinstance(data, dict):
                        return data
                    if hasattr(data, "model_dump"):
                        return data.model_dump()
                    return json.loads(json.dumps(data, default=str))

                return json.loads(response.text)
            except Exception as e:
                raise LLMProviderError(str(e), "gemini") from e

        text = await self.generate(prompt, system_prompt, max_tokens, temperature)
        return self._parse_json(text)

    def _parse_json(self, text: str) -> dict[str, Any]:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            cleaned = "\n".join(
                line for line in lines
                if not line.startswith("```")
            )
            text = cleaned.strip()
        return json.loads(text)


class GroqProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str, **kwargs: Any) -> None:
        self._api_key = api_key
        self._model = model
        self._max_tokens = kwargs.get("max_tokens", 8192)
        self._temperature = kwargs.get("temperature", 0.7)
        self._base_url = "https://api.groq.com/openai/v1"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": messages,
                    "max_tokens": max_tokens or self._max_tokens,
                    "temperature": temperature or self._temperature,
                },
            )

            if resp.status_code == 429:
                raise RateLimitError("groq")
            if resp.status_code != 200:
                raise LLMProviderError(
                    f"HTTP {resp.status_code}: {resp.text}",
                    "groq",
                    resp.status_code,
                )

            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise LLMProviderError("Empty response from Groq", "groq")
            return choices[0]["message"]["content"]

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[type] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> dict[str, Any]:
        sys_prompt = system_prompt or ""
        if response_model is not None:
            sys_prompt += (
                "\n\nYou MUST respond with valid JSON matching this schema:\n"
                f"{json.dumps(response_model.model_json_schema(), indent=2)}"
            )

        text = await self.generate(prompt, sys_prompt, max_tokens, temperature)
        return self._parse_json(text)

    def _parse_json(self, text: str) -> dict[str, Any]:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            cleaned = "\n".join(
                line for line in lines
                if not line.startswith("```")
            )
            text = cleaned.strip()
        return json.loads(text)


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str, model: str, **kwargs: Any) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._max_tokens = kwargs.get("max_tokens", 4096)
        self._temperature = kwargs.get("temperature", 0.7)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "options": {
                "num_predict": max_tokens or self._max_tokens,
                "temperature": temperature or self._temperature,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base_url}/api/generate",
                json=payload,
            )

            if resp.status_code != 200:
                raise LLMProviderError(
                    f"HTTP {resp.status_code}: {resp.text}",
                    "ollama",
                    resp.status_code,
                )

            lines = resp.text.strip().splitlines()
            full_text = ""
            for line in lines:
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                    full_text += chunk.get("response", "")
                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue

            return full_text

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[type] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> dict[str, Any]:
        sys_prompt = system_prompt or ""
        if response_model is not None:
            sys_prompt += (
                "\n\nYou MUST respond with valid JSON matching this schema:\n"
                f"{json.dumps(response_model.model_json_schema(), indent=2)}"
            )

        text = await self.generate(prompt, sys_prompt, max_tokens, temperature)
        return self._parse_json(text)

    def _parse_json(self, text: str) -> dict[str, Any]:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            cleaned = "\n".join(
                line for line in lines
                if not line.startswith("```")
            )
            text = cleaned.strip()
        return json.loads(text)


class LLMClient:
    def __init__(
        self,
        provider: Optional[BaseLLMProvider] = None,
        logger: Optional[CollectorLoggerProtocol] = None,
        max_retries: int = 3,
    ) -> None:
        self._provider = provider
        self._logger = logger
        self._max_retries = max_retries

    @classmethod
    def from_settings(
        cls,
        settings: Any,
        logger: Optional[CollectorLoggerProtocol] = None,
    ) -> LLMClient:
        gemini_settings = settings.gemini
        provider_name = gemini_settings.provider
        provider: BaseLLMProvider

        if provider_name == "gemini" and gemini_settings.gemini_api_key:
            provider = GeminiProvider(
                api_key=gemini_settings.gemini_api_key,
                model=gemini_settings.gemini_model,
                max_tokens=gemini_settings.gemini_max_tokens,
                temperature=gemini_settings.gemini_temperature,
            )
        elif provider_name == "groq" and gemini_settings.groq_api_key:
            provider = GroqProvider(
                api_key=gemini_settings.groq_api_key,
                model=gemini_settings.groq_model,
                max_tokens=gemini_settings.groq_max_tokens,
                temperature=gemini_settings.groq_temperature,
            )
        else:
            provider = OllamaProvider(
                base_url=gemini_settings.ollama_base_url,
                model=gemini_settings.ollama_model,
                max_tokens=gemini_settings.ollama_max_tokens,
                temperature=gemini_settings.ollama_temperature,
            )

        return cls(provider=provider, logger=logger)

    @property
    def provider(self) -> Optional[BaseLLMProvider]:
        return self._provider

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        if self._provider is None:
            raise LLMError("No LLM provider configured")

        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries):
            try:
                return await self._provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except RateLimitError as e:
                last_error = e
                wait = e.retry_after * (2 ** attempt)
                if self._logger:
                    self._logger.warning(
                        f"Rate limited (attempt {attempt + 1}), "
                        f"retrying in {wait:.1f}s"
                    )
                time.sleep(wait)
            except LLMProviderError as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    wait = 2 ** attempt
                    if self._logger:
                        self._logger.warning(
                            f"Provider error: {e} (attempt {attempt + 1}), "
                            f"retrying in {wait}s"
                        )
                    time.sleep(wait)
                else:
                    raise
            except Exception as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    wait = 2 ** attempt
                    if self._logger:
                        self._logger.warning(
                            f"Unexpected error: {e} (attempt {attempt + 1}), "
                            f"retrying in {wait}s"
                        )
                    time.sleep(wait)
                else:
                    raise LLMError(f"LLM generation failed after {self._max_retries} retries") from e

        raise LLMError(f"LLM generation failed after {self._max_retries} retries") from last_error

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_model: Optional[type] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> dict[str, Any]:
        if self._provider is None:
            raise LLMError("No LLM provider configured")

        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries):
            try:
                return await self._provider.generate_structured(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    response_model=response_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except RateLimitError as e:
                last_error = e
                wait = e.retry_after * (2 ** attempt)
                if self._logger:
                    self._logger.warning(
                        f"Rate limited (attempt {attempt + 1}), "
                        f"retrying in {wait:.1f}s"
                    )
                time.sleep(wait)
            except (LLMProviderError, json.JSONDecodeError) as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    wait = 2 ** attempt
                    if self._logger:
                        self._logger.warning(
                            f"Error: {e} (attempt {attempt + 1}), "
                            f"retrying in {wait}s"
                        )
                    time.sleep(wait)
                else:
                    raise
            except Exception as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    wait = 2 ** attempt
                    if self._logger:
                        self._logger.warning(
                            f"Unexpected error: {e} (attempt {attempt + 1}), "
                            f"retrying in {wait}s"
                        )
                    time.sleep(wait)
                else:
                    raise LLMError(
                        f"Structured generation failed after {self._max_retries} retries"
                    ) from e

        raise LLMError(
            f"Structured generation failed after {self._max_retries} retries"
        ) from last_error
