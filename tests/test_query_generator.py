"""Tests fuer Smart Query Generator (query_generator.py + llm_client.py)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.query_generator import (
    QuerySet,
    SearchScope,
    _build_boolean_query,
    _expand_llm,
    _expand_local,
    _extract_leitfragen_keywords,
    _find_synonyms,
    _load_expand_prompt,
    _load_synonyms,
    expand_queries,
    refine_topic,
    validate_queries,
)
from src.utils.llm_client import LLMConfig, llm_complete, load_llm_config

# --- Datenmodelle ---


class TestSearchScope:
    def test_defaults(self) -> None:
        scope = SearchScope()
        assert scope.year_range is None
        assert scope.languages == ["en", "de"]
        assert scope.fields_of_study == []

    def test_custom_values(self) -> None:
        scope = SearchScope(year_range=(2020, 2026), languages=["en", "de"])
        assert scope.year_range == (2020, 2026)
        assert scope.languages == ["en", "de"]

    def test_serialization_roundtrip(self) -> None:
        scope = SearchScope(year_range=(2020, 2026), fields_of_study=["CS"])
        data = scope.model_dump()
        restored = SearchScope.model_validate(data)
        assert restored == scope


class TestQuerySet:
    def test_defaults(self) -> None:
        qs = QuerySet(research_question="test topic")
        assert qs.ss_queries == []
        assert qs.exa_queries == []
        assert qs.oa_queries == []
        assert qs.source == "local"

    def test_with_queries(self) -> None:
        qs = QuerySet(
            research_question="How does RL optimize traffic?",
            ss_queries=["RL AND traffic"],
            exa_queries=["Recent advances in RL traffic"],
            oa_queries=["RL traffic optimization"],
            source="llm",
        )
        assert len(qs.ss_queries) == 1
        assert len(qs.oa_queries) == 1
        assert qs.source == "llm"

    def test_serialization_roundtrip(self) -> None:
        qs = QuerySet(
            research_question="test",
            ss_queries=["q1", "q2"],
            exa_queries=["e1"],
            oa_queries=["oa1"],
            scope=SearchScope(year_range=(2020, 2026)),
        )
        data = qs.model_dump()
        restored = QuerySet.model_validate(data)
        assert restored == qs


# --- Hilfsfunktionen ---


class TestFindSynonyms:
    def test_finds_matching_term(self) -> None:
        synonym_map = {"machine learning": ["ML", "deep learning"]}
        matches = _find_synonyms("advances in machine learning", synonym_map)
        assert len(matches) == 1
        assert matches[0][0] == "machine learning"
        assert "ML" in matches[0][1]

    def test_case_insensitive(self) -> None:
        synonym_map = {"machine learning": ["ML"]}
        matches = _find_synonyms("Machine Learning methods", synonym_map)
        assert len(matches) == 1

    def test_no_match(self) -> None:
        synonym_map = {"machine learning": ["ML"]}
        matches = _find_synonyms("quantum computing", synonym_map)
        assert matches == []

    def test_multiple_matches(self) -> None:
        synonym_map = {
            "machine learning": ["ML"],
            "deep learning": ["DL"],
        }
        matches = _find_synonyms("deep learning in machine learning", synonym_map)
        assert len(matches) == 2


class TestExtractLeitfragenKeywords:
    def test_removes_german_question_words(self) -> None:
        keywords = _extract_leitfragen_keywords(["Wie verbessert RL die Ampelsteuerung?"])
        assert keywords == ["verbessert RL die Ampelsteuerung"]

    def test_removes_english_question_words(self) -> None:
        keywords = _extract_leitfragen_keywords(["How does RL improve traffic?"])
        assert keywords == ["does RL improve traffic"]

    def test_strips_whitespace_and_question_mark(self) -> None:
        keywords = _extract_leitfragen_keywords(["  Was ist der Stand?  "])
        assert keywords == ["ist der Stand"]

    def test_no_question_word(self) -> None:
        keywords = _extract_leitfragen_keywords(["RL fuer Verkehrssteuerung"])
        assert keywords == ["RL fuer Verkehrssteuerung"]

    def test_empty_list(self) -> None:
        assert _extract_leitfragen_keywords([]) == []


class TestBuildBooleanQuery:
    def test_with_extra_terms(self) -> None:
        result = _build_boolean_query("traffic", ["RL", "DRL"])
        assert result == 'traffic AND ("RL" OR "DRL")'

    def test_without_extra_terms(self) -> None:
        result = _build_boolean_query("traffic", [])
        assert result == "traffic"


# --- Config-Fallbacks ---


class TestLoadSynonyms:
    def test_returns_dict_from_file(self) -> None:
        result = _load_synonyms()
        assert isinstance(result, dict)
        assert len(result) > 0

    @patch("src.agents.query_generator._QUERY_TEMPLATES_DIR", Path("/nonexistent"))
    def test_returns_empty_on_missing_file(self) -> None:
        result = _load_synonyms()
        assert result == {}


class TestLoadExpandPrompt:
    def test_returns_prompt_from_file(self) -> None:
        result = _load_expand_prompt()
        assert "JSON" in result
        assert len(result) > 50

    @patch("src.agents.query_generator._QUERY_TEMPLATES_DIR", Path("/nonexistent"))
    def test_returns_fallback_on_missing_file(self) -> None:
        result = _load_expand_prompt()
        assert "JSON" in result
        assert len(result) < 100


# --- Stufe 1: Lokale Expansion ---


class TestExpandLocal:
    def test_minimum_queries(self) -> None:
        qs = _expand_local("quantum computing")
        assert len(qs.ss_queries) >= 3
        assert len(qs.exa_queries) >= 2
        assert qs.source == "local"

    def test_includes_topic_as_first_query(self) -> None:
        qs = _expand_local("machine learning")
        assert qs.ss_queries[0] == "machine learning"

    def test_exa_queries_are_topic_focused(self) -> None:
        qs = _expand_local("deep learning")
        assert any("deep learning" in q for q in qs.exa_queries)
        assert len(qs.exa_queries) >= 2

    def test_with_leitfragen(self) -> None:
        qs = _expand_local(
            "reinforcement learning",
            leitfragen=["Wie funktioniert Q-learning?", "Was sind die Grenzen?"],
        )
        assert len(qs.ss_queries) >= 3
        assert any("Q-learning" in q or "funktioniert" in q for q in qs.ss_queries)

    def test_with_scope(self) -> None:
        scope = SearchScope(year_range=(2020, 2026))
        qs = _expand_local("NLP", scope=scope)
        assert qs.scope.year_range == (2020, 2026)

    def test_research_question_is_topic(self) -> None:
        qs = _expand_local("test topic")
        assert qs.research_question == "test topic"

    @patch("src.agents.query_generator._load_synonyms")
    def test_synonym_expansion(self, mock_load: MagicMock) -> None:
        mock_load.return_value = {"machine learning": ["ML", "deep learning", "neural network"]}
        qs = _expand_local("machine learning applications")
        assert any("ML" in q or "deep learning" in q for q in qs.ss_queries)

    def test_generates_oa_queries(self) -> None:
        """Lokale Expansion erzeugt OA-Queries ohne Boolean-Operatoren."""
        qs = _expand_local("machine learning fairness")
        assert len(qs.oa_queries) >= 2
        for q in qs.oa_queries:
            assert " AND " not in q
            assert " OR " not in q

    def test_oa_queries_contain_topic(self) -> None:
        """OA-Queries enthalten das Topic."""
        qs = _expand_local("reinforcement learning")
        assert any("reinforcement learning" in q for q in qs.oa_queries)


# --- Stufe 2: LLM-Enhanced ---


class TestExpandLLM:
    @pytest.mark.asyncio
    @patch("src.utils.llm_client.llm_complete")
    async def test_successful_llm_expansion(self, mock_llm: AsyncMock) -> None:
        mock_llm.return_value = json.dumps({
            "research_question": "How does RL optimize traffic signals?",
            "ss_queries": ["RL AND traffic signal", "DRL AND intersection", "Q-learning AND urban"],
            "exa_queries": ["Recent RL traffic advances", "Deep RL for smart cities"],
        })
        qs = await _expand_llm("RL Verkehrssteuerung")
        assert qs.source == "llm"
        assert len(qs.ss_queries) == 3
        assert len(qs.exa_queries) == 2

    @pytest.mark.asyncio
    @patch("src.utils.llm_client.llm_complete")
    async def test_invalid_json_raises_with_preview(self, mock_llm: AsyncMock) -> None:
        mock_llm.return_value = "not valid json"
        with pytest.raises(ValueError, match="(?s)kein valides JSON.*Preview.*not valid"):
            await _expand_llm("test")

    @pytest.mark.asyncio
    @patch("src.utils.llm_client.llm_complete")
    async def test_llm_expansion_includes_oa_queries(self, mock_llm: AsyncMock) -> None:
        mock_llm.return_value = json.dumps({
            "research_question": "How does RL optimize traffic?",
            "ss_queries": ["RL AND traffic signal"],
            "exa_queries": ["Recent RL traffic advances"],
            "oa_queries": ["reinforcement learning traffic optimization"],
        })
        qs = await _expand_llm("RL Verkehrssteuerung")
        assert len(qs.oa_queries) == 1
        assert "reinforcement learning" in qs.oa_queries[0]

    @pytest.mark.asyncio
    @patch("src.utils.llm_client.llm_complete")
    async def test_llm_fallback_strips_boolean_and_parens(self, mock_llm: AsyncMock) -> None:
        """Wenn LLM keine oa_queries liefert, Boolean + Klammern entfernen."""
        mock_llm.return_value = json.dumps({
            "research_question": "test",
            "ss_queries": [
                "(traffic control OR Verkehrssteuerung) AND survey",
                "foo OR bar",
            ],
            "exa_queries": ["what is topic"],
        })
        qs = await _expand_llm("test")
        assert len(qs.oa_queries) == 2
        for q in qs.oa_queries:
            assert " AND " not in q
            assert " OR " not in q
            assert "(" not in q
            assert ")" not in q
            assert "  " not in q  # Kein doppeltes Leerzeichen

    @pytest.mark.asyncio
    @patch("src.utils.llm_client.llm_complete")
    async def test_empty_ss_queries_raises(self, mock_llm: AsyncMock) -> None:
        mock_llm.return_value = json.dumps({
            "research_question": "test",
            "ss_queries": [],
            "exa_queries": ["q1"],
        })
        with pytest.raises(ValueError, match="SS-Queries"):
            await _expand_llm("test")


# --- Public API ---


class TestExpandQueries:
    @pytest.mark.asyncio
    @patch("src.utils.llm_client.load_llm_config")
    async def test_falls_back_to_local_without_key(self, mock_config: MagicMock) -> None:
        mock_config.return_value = LLMConfig(api_key="")
        qs = await expand_queries("machine learning")
        assert qs.source == "local"
        assert len(qs.ss_queries) >= 3

    @pytest.mark.asyncio
    @patch("src.utils.llm_client.load_llm_config")
    @patch("src.agents.query_generator._expand_llm", new_callable=AsyncMock)
    async def test_uses_llm_when_available(
        self, mock_llm: AsyncMock, mock_config: MagicMock
    ) -> None:
        mock_config.return_value = LLMConfig(api_key="test-key")
        mock_llm.return_value = QuerySet(
            research_question="test", ss_queries=["q1"], exa_queries=["e1"], source="llm"
        )
        qs = await expand_queries("test")
        assert qs.source == "llm"

    @pytest.mark.asyncio
    @patch("src.utils.llm_client.load_llm_config")
    @patch("src.agents.query_generator._expand_llm", new_callable=AsyncMock)
    async def test_fallback_on_llm_error(
        self, mock_llm: AsyncMock, mock_config: MagicMock
    ) -> None:
        mock_config.return_value = LLMConfig(api_key="test-key")
        mock_llm.side_effect = RuntimeError("API down")
        qs = await expand_queries("machine learning")
        assert qs.source == "local"


class TestRefineTopic:
    @pytest.mark.asyncio
    @patch("src.utils.llm_client.load_llm_config")
    async def test_returns_topic_without_key(self, mock_config: MagicMock) -> None:
        mock_config.return_value = LLMConfig(api_key="")
        result = await refine_topic("vages thema")
        assert result == "vages thema"

    @pytest.mark.asyncio
    @patch("src.utils.llm_client.load_llm_config")
    @patch("src.agents.query_generator._expand_llm", new_callable=AsyncMock)
    async def test_returns_refined_question(
        self, mock_llm: AsyncMock, mock_config: MagicMock
    ) -> None:
        mock_config.return_value = LLMConfig(api_key="test-key")
        mock_llm.return_value = QuerySet(
            research_question="Refined question?",
            ss_queries=["q1"],
            exa_queries=["e1"],
        )
        result = await refine_topic("vages thema")
        assert result == "Refined question?"


# --- Validate Queries ---


class TestValidateQueries:
    def _mock_ss_client(self, results_per_query: dict[str, int]) -> MagicMock:
        """Erstellt Mock-SS-Client mit konfigurierbaren Ergebniszahlen."""
        client = MagicMock()

        async def mock_search(query: str, limit: int = 1) -> MagicMock:
            response = MagicMock()
            response.total = results_per_query.get(query, 0)
            return response

        client.search_papers = mock_search
        return client

    @pytest.mark.asyncio
    async def test_removes_zero_result_queries(self) -> None:
        qs = QuerySet(
            research_question="test",
            ss_queries=["good query", "bad query"],
            exa_queries=["exa1"],
        )
        ss_client = self._mock_ss_client({"good query": 5, "bad query": 0})
        result = await validate_queries(qs, ss_client)
        assert "good query" in result.ss_queries
        assert "bad query" not in result.ss_queries

    @pytest.mark.asyncio
    async def test_keeps_fallback_on_all_empty(self) -> None:
        qs = QuerySet(
            research_question="fallback topic",
            ss_queries=["empty1", "empty2"],
            exa_queries=["exa1"],
        )
        ss_client = self._mock_ss_client({})
        result = await validate_queries(qs, ss_client)
        assert len(result.ss_queries) >= 1
        assert result.ss_queries[0] == "fallback topic"

    @pytest.mark.asyncio
    async def test_preserves_exa_without_client(self) -> None:
        qs = QuerySet(
            research_question="test",
            ss_queries=["q1"],
            exa_queries=["exa1", "exa2"],
        )
        ss_client = self._mock_ss_client({"q1": 5})
        result = await validate_queries(qs, ss_client, exa_client=None)
        assert result.exa_queries == ["exa1", "exa2"]

    @pytest.mark.asyncio
    async def test_preserves_oa_queries(self) -> None:
        """validate_queries reicht oa_queries unveraendert durch."""
        qs = QuerySet(
            research_question="test",
            ss_queries=["q1"],
            exa_queries=["exa1"],
            oa_queries=["oa1", "oa2"],
        )
        ss_client = self._mock_ss_client({"q1": 5})
        result = await validate_queries(qs, ss_client)
        assert result.oa_queries == ["oa1", "oa2"]


# --- LLM Client ---


class TestLLMConfig:
    def test_not_available_without_key(self) -> None:
        config = LLMConfig()
        assert not config.is_available

    def test_available_with_key(self) -> None:
        config = LLMConfig(api_key="test-key")
        assert config.is_available

    def test_defaults(self) -> None:
        config = LLMConfig()
        assert "openrouter" in config.base_url
        assert config.timeout_s == 30.0


class TestLoadLLMConfig:
    @patch.dict("os.environ", {"LLM_API_KEY": "my-key", "LLM_MODEL": "gpt-4"}, clear=False)
    def test_loads_from_env(self) -> None:
        config = load_llm_config()
        assert config.api_key == "my-key"
        assert config.model == "gpt-4"

    @patch.dict("os.environ", {}, clear=False)
    def test_defaults_without_env(self) -> None:
        # Entferne alle LLM-Keys falls gesetzt
        import os
        os.environ.pop("LLM_API_KEY", None)
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ.pop("LLM_MODEL", None)
        os.environ.pop("LLM_BASE_URL", None)
        config = load_llm_config()
        assert config.api_key == ""
        assert config.is_available is False


class TestLLMComplete:
    @pytest.mark.asyncio
    async def test_raises_without_key(self) -> None:
        config = LLMConfig(api_key="")
        with pytest.raises(RuntimeError, match="LLM_API_KEY"):
            await llm_complete("system", "user", config=config)
