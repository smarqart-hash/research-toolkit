"""Tests fuer Topic Decomposer."""

from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock, patch

from src.agents.topic_decomposer import (
    Facet,
    TopicDecomposition,
    _extract_json,
    _validate_facet_count,
    decompose_topic,
)
from src.utils.llm_client import LLMConfig


def _llm_config() -> LLMConfig:
    return LLMConfig(api_key="test-key", model="test-model")


def _valid_decomposition_dict(num_facets: int = 3) -> dict:
    """Erstellt ein valides Decomposition-Dict fuer Tests."""
    facets = [
        {
            "name": f"Facette {i + 1}",
            "description": f"Beschreibung fuer Facette {i + 1}",
            "search_query": f"search query facet {i + 1}",
        }
        for i in range(num_facets)
    ]
    return {
        "topic": "Kuenstliche Intelligenz in der Medizin",
        "research_question": "How does AI improve diagnostic accuracy in clinical settings?",
        "scope": "Covers machine learning models for medical imaging and diagnosis.",
        "core_terms": ["medical AI", "diagnostic accuracy", "clinical decision support"],
        "exclusions": ["administrative AI", "drug discovery"],
        "facets": facets,
        "suggested_leitfragen": [
            "Welche ML-Modelle werden in der Bildgebung eingesetzt?",
            "Wie wird Bias in medizinischen Datensaetzen gemessen?",
        ],
    }


class TestFacet:
    def test_fields(self):
        facet = Facet(
            name="Readability Research",
            description="Empirische Studien zu Lesbarkeitsmetriken",
            search_query="readability metrics text comprehension",
        )
        assert facet.name == "Readability Research"
        assert facet.search_query == "readability metrics text comprehension"

    def test_all_required_fields(self):
        with pytest.raises(Exception):
            Facet(name="Test")  # fehlende Pflichtfelder


class TestTopicDecomposition:
    def test_full_model(self):
        data = _valid_decomposition_dict(4)
        decomp = TopicDecomposition.model_validate(data)
        assert decomp.topic == "Kuenstliche Intelligenz in der Medizin"
        assert len(decomp.facets) == 4
        assert decomp.facets[0].name == "Facette 1"
        assert len(decomp.core_terms) == 3
        assert len(decomp.suggested_leitfragen) == 2

    def test_optional_fields_default_empty(self):
        decomp = TopicDecomposition(
            topic="Test",
            research_question="RQ?",
            scope="Scope.",
        )
        assert decomp.core_terms == []
        assert decomp.exclusions == []
        assert decomp.facets == []
        assert decomp.suggested_leitfragen == []

    def test_missing_required_field(self):
        with pytest.raises(Exception):
            TopicDecomposition.model_validate({"topic": "Test"})


class TestExtractJson:
    def test_plain_json(self):
        data = {"key": "value"}
        result = _extract_json(json.dumps(data))
        assert json.loads(result) == data

    def test_markdown_code_block(self):
        data = {"key": "value"}
        wrapped = f"```json\n{json.dumps(data)}\n```"
        result = _extract_json(wrapped)
        assert json.loads(result) == data

    def test_markdown_block_without_lang(self):
        data = {"key": "value"}
        wrapped = f"```\n{json.dumps(data)}\n```"
        result = _extract_json(wrapped)
        assert json.loads(result) == data

    def test_json_embedded_in_text(self):
        data = {"key": "value"}
        wrapped = f"Hier ist das Ergebnis: {json.dumps(data)} Ende."
        result = _extract_json(wrapped)
        assert json.loads(result) == data

    def test_plain_text_returned_as_is(self):
        result = _extract_json("no json here")
        assert result == "no json here"


class TestValidateFacetCount:
    def test_valid_count_min(self):
        data = _valid_decomposition_dict(2)
        decomp = TopicDecomposition.model_validate(data)
        _validate_facet_count(decomp)  # kein Fehler

    def test_valid_count_max(self):
        data = _valid_decomposition_dict(8)
        decomp = TopicDecomposition.model_validate(data)
        _validate_facet_count(decomp)  # kein Fehler

    def test_too_few_facets(self):
        data = _valid_decomposition_dict(1)
        decomp = TopicDecomposition.model_validate(data)
        with pytest.raises(ValueError, match="Zu wenige Facetten"):
            _validate_facet_count(decomp)

    def test_too_many_facets(self):
        data = _valid_decomposition_dict(9)
        decomp = TopicDecomposition.model_validate(data)
        with pytest.raises(ValueError, match="Zu viele Facetten"):
            _validate_facet_count(decomp)

    def test_zero_facets(self):
        decomp = TopicDecomposition(
            topic="Test",
            research_question="RQ?",
            scope="Scope.",
        )
        with pytest.raises(ValueError, match="Zu wenige Facetten"):
            _validate_facet_count(decomp)


class TestDecomposeTopic:
    @pytest.mark.asyncio
    async def test_valid_response(self):
        """Erfolgreicher LLM-Call mit valider JSON-Antwort."""
        data = _valid_decomposition_dict(3)
        mock_response = json.dumps(data)

        with patch("src.agents.topic_decomposer.llm_complete", new=AsyncMock(return_value=mock_response)):
            result = await decompose_topic("Kuenstliche Intelligenz in der Medizin", config=_llm_config())

        assert isinstance(result, TopicDecomposition)
        assert result.topic == "Kuenstliche Intelligenz in der Medizin"
        assert len(result.facets) == 3
        assert result.research_question != ""
        assert result.scope != ""

    @pytest.mark.asyncio
    async def test_valid_response_english_language(self):
        """Erfolgreicher LLM-Call mit language='en'."""
        data = _valid_decomposition_dict(4)
        mock_response = json.dumps(data)

        with patch("src.agents.topic_decomposer.llm_complete", new=AsyncMock(return_value=mock_response)) as mock:
            result = await decompose_topic("AI in Medicine", language="en", config=_llm_config())

        assert isinstance(result, TopicDecomposition)
        assert len(result.facets) == 4
        # Prueft dass der User-Prompt aufgerufen wurde (language hat Einfluss auf Prompt)
        call_kwargs = mock.call_args
        assert call_kwargs is not None

    @pytest.mark.asyncio
    async def test_garbage_response_raises_value_error(self):
        """Garbage-Response fuehrt zu ValueError."""
        with patch(
            "src.agents.topic_decomposer.llm_complete",
            new=AsyncMock(return_value="Das ist kein JSON und auch kein JSON-Fragment"),
        ):
            with pytest.raises(ValueError):
                await decompose_topic("Test-Thema", config=_llm_config())

    @pytest.mark.asyncio
    async def test_invalid_json_raises_value_error(self):
        """Invalides JSON fuehrt zu ValueError."""
        with patch(
            "src.agents.topic_decomposer.llm_complete",
            new=AsyncMock(return_value="{invalid: json}"),
        ):
            with pytest.raises(ValueError, match="kein valides JSON"):
                await decompose_topic("Test-Thema", config=_llm_config())

    @pytest.mark.asyncio
    async def test_too_few_facets_raises_value_error(self):
        """Zu wenige Facetten fuehren zu ValueError."""
        data = _valid_decomposition_dict(1)
        mock_response = json.dumps(data)

        with patch("src.agents.topic_decomposer.llm_complete", new=AsyncMock(return_value=mock_response)):
            with pytest.raises(ValueError, match="Zu wenige Facetten"):
                await decompose_topic("Test-Thema", config=_llm_config())

    @pytest.mark.asyncio
    async def test_too_many_facets_raises_value_error(self):
        """Zu viele Facetten fuehren zu ValueError."""
        data = _valid_decomposition_dict(9)
        mock_response = json.dumps(data)

        with patch("src.agents.topic_decomposer.llm_complete", new=AsyncMock(return_value=mock_response)):
            with pytest.raises(ValueError, match="Zu viele Facetten"):
                await decompose_topic("Test-Thema", config=_llm_config())

    @pytest.mark.asyncio
    async def test_missing_required_fields_raises_value_error(self):
        """Fehlende Pflichtfelder im JSON fuehren zu ValueError."""
        incomplete_data = {
            "topic": "Test",
            "facets": [{"name": "F1", "description": "D1", "search_query": "q1"}] * 3,
            # research_question und scope fehlen
        }
        mock_response = json.dumps(incomplete_data)

        with patch("src.agents.topic_decomposer.llm_complete", new=AsyncMock(return_value=mock_response)):
            with pytest.raises(ValueError, match="JSON-Schema-Validierung fehlgeschlagen"):
                await decompose_topic("Test-Thema", config=_llm_config())

    @pytest.mark.asyncio
    async def test_markdown_wrapped_json_works(self):
        """JSON in Markdown-Codeblock wird korrekt extrahiert."""
        data = _valid_decomposition_dict(3)
        wrapped = f"```json\n{json.dumps(data)}\n```"

        with patch("src.agents.topic_decomposer.llm_complete", new=AsyncMock(return_value=wrapped)):
            result = await decompose_topic("Test-Thema", config=_llm_config())

        assert isinstance(result, TopicDecomposition)
        assert len(result.facets) == 3

    @pytest.mark.asyncio
    async def test_min_valid_facets(self):
        """Genau 2 Facetten (Minimum) werden akzeptiert."""
        data = _valid_decomposition_dict(2)
        mock_response = json.dumps(data)

        with patch("src.agents.topic_decomposer.llm_complete", new=AsyncMock(return_value=mock_response)):
            result = await decompose_topic("Enges Thema", config=_llm_config())

        assert len(result.facets) == 2

    @pytest.mark.asyncio
    async def test_max_valid_facets(self):
        """Genau 8 Facetten (Maximum) werden akzeptiert."""
        data = _valid_decomposition_dict(8)
        mock_response = json.dumps(data)

        with patch("src.agents.topic_decomposer.llm_complete", new=AsyncMock(return_value=mock_response)):
            result = await decompose_topic("Breites Thema", config=_llm_config())

        assert len(result.facets) == 8
