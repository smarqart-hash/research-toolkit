"""Tests fuer LLM-as-Ranking-Judge (M2)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.paper_ranker import UnifiedPaper
from src.agents.ranking_judge import (
    JudgedPaper,
    JudgementResult,
    _build_judge_prompt,
    _parse_judge_response,
    judge_relevance,
)
from src.utils.llm_client import LLMConfig


# --- Fixtures ---


def _paper(
    paper_id: str = "p1",
    title: str = "Test Paper",
    abstract: str | None = "Ein Abstract ueber ML.",
    year: int = 2024,
    citation_count: int = 10,
    source: str = "semantic_scholar",
) -> UnifiedPaper:
    return UnifiedPaper(
        paper_id=paper_id,
        title=title,
        abstract=abstract,
        year=year,
        citation_count=citation_count,
        source=source,
        is_open_access=True,
    )


def _llm_config() -> LLMConfig:
    return LLMConfig(api_key="test-key", model="test-model")


# --- Modelle ---


class TestJudgedPaper:
    def test_fields(self):
        jp = JudgedPaper(paper_id="p1", title="Test", llm_score=7.5, reasoning="Gut relevant")
        assert jp.paper_id == "p1"
        assert jp.llm_score == 7.5
        assert jp.reasoning == "Gut relevant"

    def test_score_clamped_0_10(self):
        """LLM-Score muss zwischen 0 und 10 liegen."""
        jp = JudgedPaper(paper_id="p1", title="T", llm_score=10.0, reasoning="")
        assert jp.llm_score == 10.0

        with pytest.raises(ValueError, match="less than or equal to 10"):
            JudgedPaper(paper_id="p1", title="T", llm_score=11.0, reasoning="")

        with pytest.raises(ValueError, match="greater than or equal to 0"):
            JudgedPaper(paper_id="p1", title="T", llm_score=-1.0, reasoning="")


class TestJudgementResult:
    def test_correlation_perfect(self):
        """Perfekte Uebereinstimmung ergibt Korrelation nahe 1."""
        result = JudgementResult(
            query="test",
            judged_papers=[
                JudgedPaper(paper_id="p1", title="A", llm_score=8.0, reasoning=""),
                JudgedPaper(paper_id="p2", title="B", llm_score=4.0, reasoning=""),
                JudgedPaper(paper_id="p3", title="C", llm_score=2.0, reasoning=""),
            ],
            heuristic_scores={"p1": 0.8, "p2": 0.4, "p3": 0.2},
        )
        # Rank-Korrelation sollte hoch sein bei gleicher Reihenfolge
        assert result.rank_correlation is not None
        assert result.rank_correlation > 0.9

    def test_correlation_inverted(self):
        """Invertierte Reihenfolge ergibt negative Korrelation."""
        result = JudgementResult(
            query="test",
            judged_papers=[
                JudgedPaper(paper_id="p1", title="A", llm_score=2.0, reasoning=""),
                JudgedPaper(paper_id="p2", title="B", llm_score=5.0, reasoning=""),
                JudgedPaper(paper_id="p3", title="C", llm_score=8.0, reasoning=""),
            ],
            heuristic_scores={"p1": 0.8, "p2": 0.5, "p3": 0.2},
        )
        assert result.rank_correlation is not None
        assert result.rank_correlation < -0.9

    def test_correlation_too_few_papers(self):
        """Weniger als 3 Papers → keine Korrelation berechenbar."""
        result = JudgementResult(
            query="test",
            judged_papers=[
                JudgedPaper(paper_id="p1", title="A", llm_score=5.0, reasoning=""),
            ],
            heuristic_scores={"p1": 0.5},
        )
        assert result.rank_correlation is None

    def test_mean_score_delta(self):
        """Mittlere Differenz zwischen LLM und Heuristik (normalisiert auf 0-1)."""
        result = JudgementResult(
            query="test",
            judged_papers=[
                JudgedPaper(paper_id="p1", title="A", llm_score=8.0, reasoning=""),
                JudgedPaper(paper_id="p2", title="B", llm_score=6.0, reasoning=""),
            ],
            heuristic_scores={"p1": 0.8, "p2": 0.6},
        )
        # LLM: 0.8, 0.6 (normalisiert /10) == Heuristik: 0.8, 0.6 → delta = 0.0
        assert result.mean_score_delta == 0.0


# --- Prompt-Building ---


class TestBuildJudgePrompt:
    def test_contains_query(self):
        prompt = _build_judge_prompt("machine learning fairness", [_paper()])
        assert "machine learning fairness" in prompt

    def test_contains_paper_info(self):
        paper = _paper(title="Fairness in AI", abstract="Studie ueber Bias")
        prompt = _build_judge_prompt("ML fairness", [paper])
        assert "Fairness in AI" in prompt
        assert "Studie ueber Bias" in prompt

    def test_papers_without_abstract(self):
        """Papers ohne Abstract werden mit Hinweis versehen."""
        paper = _paper(abstract=None)
        prompt = _build_judge_prompt("test", [paper])
        assert "kein abstract" in prompt.lower()


# --- Response Parsing ---


class TestParseJudgeResponse:
    def test_valid_json(self):
        response = json.dumps({
            "judgements": [
                {"paper_id": "p1", "score": 8, "reasoning": "Sehr relevant"},
                {"paper_id": "p2", "score": 3, "reasoning": "Kaum relevant"},
            ]
        })
        papers = [_paper(paper_id="p1"), _paper(paper_id="p2", title="Paper 2")]
        result = _parse_judge_response(response, papers)
        assert len(result) == 2
        assert result[0].llm_score == 8.0
        assert result[1].llm_score == 3.0

    def test_json_in_markdown_wrapper(self):
        """LLM gibt manchmal ```json ... ``` zurueck."""
        inner = json.dumps({
            "judgements": [{"paper_id": "p1", "score": 7, "reasoning": "Ok"}]
        })
        response = f"```json\n{inner}\n```"
        papers = [_paper(paper_id="p1")]
        result = _parse_judge_response(response, papers)
        assert len(result) == 1
        assert result[0].llm_score == 7.0

    def test_invalid_json_returns_empty(self):
        result = _parse_judge_response("Das ist kein JSON", [_paper()])
        assert result == []

    def test_score_clamped(self):
        """Scores ausserhalb 0-10 werden auf 0-10 geclampt."""
        response = json.dumps({
            "judgements": [
                {"paper_id": "p1", "score": 15, "reasoning": ""},
                {"paper_id": "p2", "score": -5, "reasoning": ""},
            ]
        })
        papers = [_paper(paper_id="p1"), _paper(paper_id="p2")]
        result = _parse_judge_response(response, papers)
        assert result[0].llm_score == 10.0
        assert result[1].llm_score == 0.0

    def test_unknown_paper_id_skipped(self):
        """Paper-IDs die nicht im Input sind werden uebersprungen."""
        response = json.dumps({
            "judgements": [
                {"paper_id": "unknown", "score": 5, "reasoning": ""},
            ]
        })
        papers = [_paper(paper_id="p1")]
        result = _parse_judge_response(response, papers)
        assert result == []


# --- Integration ---


class TestJudgeRelevance:
    @pytest.mark.asyncio
    async def test_basic_flow(self):
        """Grundlegender Flow: Papers rein, JudgementResult raus."""
        llm_response = json.dumps({
            "judgements": [
                {"paper_id": "p1", "score": 8, "reasoning": "Sehr relevant"},
                {"paper_id": "p2", "score": 3, "reasoning": "Wenig relevant"},
            ]
        })
        papers = [_paper(paper_id="p1"), _paper(paper_id="p2", title="Paper 2")]
        config = _llm_config()

        with patch("src.agents.ranking_judge.llm_complete", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_response
            result = await judge_relevance("ML fairness", papers, config=config)

        assert isinstance(result, JudgementResult)
        assert len(result.judged_papers) == 2
        assert result.query == "ML fairness"
        # Heuristic Scores aus relevance_score
        assert "p1" in result.heuristic_scores
        assert "p2" in result.heuristic_scores

    @pytest.mark.asyncio
    async def test_empty_papers(self):
        """Leere Paper-Liste ergibt leeres Ergebnis."""
        config = _llm_config()
        result = await judge_relevance("test", [], config=config)
        assert result.judged_papers == []
        assert result.heuristic_scores == {}

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_judgements(self):
        """LLM-Fehler fuehrt zu leerem Ergebnis, kein Crash."""
        papers = [_paper()]
        config = _llm_config()

        with patch("src.agents.ranking_judge.llm_complete", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = RuntimeError("API down")
            result = await judge_relevance("test", papers, config=config)

        assert result.judged_papers == []
        assert "p1" in result.heuristic_scores  # Heuristic trotzdem berechnet

    @pytest.mark.asyncio
    async def test_batching_large_list(self):
        """Bei >10 Papers wird in Batches aufgeteilt."""
        papers = [_paper(paper_id=f"p{i}") for i in range(15)]
        config = _llm_config()

        batch_response = json.dumps({
            "judgements": [
                {"paper_id": f"p{i}", "score": 5, "reasoning": "Ok"} for i in range(10)
            ]
        })
        batch2_response = json.dumps({
            "judgements": [
                {"paper_id": f"p{i}", "score": 5, "reasoning": "Ok"} for i in range(10, 15)
            ]
        })

        with patch("src.agents.ranking_judge.llm_complete", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = [batch_response, batch2_response]
            result = await judge_relevance("test", papers, config=config)

        assert mock_llm.call_count == 2
        assert len(result.judged_papers) == 15
