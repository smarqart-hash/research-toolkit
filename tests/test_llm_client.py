"""Tests fuer den LLM-Client."""

from __future__ import annotations

import pytest

from src.utils.llm_client import load_llm_config


class TestLlmConfig:
    """Tests fuer API-Key-Mapping in load_llm_config."""

    def test_openrouter_key_fallback(self, monkeypatch: pytest.MonkeyPatch):
        """OPENROUTER_API_KEY wird als Fallback genutzt wenn LLM_API_KEY leer."""
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "or-test-key")

        config = load_llm_config()

        assert config.api_key == "or-test-key"

    def test_llm_key_has_priority(self, monkeypatch: pytest.MonkeyPatch):
        """LLM_API_KEY hat Vorrang vor OPENROUTER_API_KEY."""
        monkeypatch.setenv("LLM_API_KEY", "llm-primary-key")
        monkeypatch.setenv("OPENROUTER_API_KEY", "or-fallback-key")

        config = load_llm_config()

        assert config.api_key == "llm-primary-key"
