"""Duenner LLM-Client — OpenAI-kompatibles Chat-Completions-Format.

Funktioniert mit OpenRouter, OpenAI, Ollama, LM Studio, vLLM etc.
Keine neue Dependency: nur httpx (bereits installiert).
"""

from __future__ import annotations

import logging
import os

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Defaults fuer OpenRouter Free-Tier
_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_MODEL = "google/gemini-2.0-flash-exp:free"


class LLMConfig(BaseModel):
    """Konfiguration fuer den LLM-Client."""

    base_url: str = _DEFAULT_BASE_URL
    api_key: str = ""
    model: str = _DEFAULT_MODEL
    timeout_s: float = 30.0
    max_tokens: int = 1024
    temperature: float = 0.3

    @property
    def is_available(self) -> bool:
        """Prueft ob ein API-Key konfiguriert ist."""
        return bool(self.api_key)


def load_llm_config() -> LLMConfig:
    """Laedt LLM-Config aus Environment-Variablen."""
    return LLMConfig(
        base_url=os.environ.get("LLM_BASE_URL", _DEFAULT_BASE_URL),
        api_key=os.environ.get("LLM_API_KEY", ""),
        model=os.environ.get("LLM_MODEL", _DEFAULT_MODEL),
    )


async def llm_complete(
    system_prompt: str,
    user_message: str,
    *,
    config: LLMConfig | None = None,
) -> str:
    """Sendet einen Chat-Completions-Request an ein OpenAI-kompatibles API.

    Args:
        system_prompt: System-Nachricht.
        user_message: User-Nachricht.
        config: LLM-Konfiguration (Default: aus Env-Vars).

    Returns:
        Antwort-Text des Modells.

    Raises:
        httpx.HTTPStatusError: Bei API-Fehlern.
        httpx.TimeoutException: Bei Timeout.
        RuntimeError: Wenn kein API-Key konfiguriert.
    """
    if config is None:
        config = load_llm_config()

    if not config.is_available:
        raise RuntimeError(
            "Kein LLM_API_KEY gesetzt. Setze LLM_API_KEY fuer OpenRouter/OpenAI/Ollama."
        )

    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }

    payload: dict = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
    }
    # response_format nicht setzen — nicht alle Provider unterstuetzen es
    # (z.B. Gemini Flash via OpenRouter). Stattdessen im Prompt erzwingen.

    async with httpx.AsyncClient(timeout=config.timeout_s) as client:
        response = await client.post(
            f"{config.base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
    response.raise_for_status()

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("LLM-Antwort enthaelt keine choices")

    return choices[0]["message"]["content"]
