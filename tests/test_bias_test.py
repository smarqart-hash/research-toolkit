"""Tests fuer Self-Enhancement Bias Test (M3)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.bias_test import (
    BiasTestResult,
    TextScoring,
    _build_scoring_prompt,
    _parse_scoring_response,
    run_bias_test,
)
from src.utils.llm_client import LLMConfig


# --- Fixtures ---


def _llm_config() -> LLMConfig:
    return LLMConfig(api_key="test-key", model="test-model")


_OWN_DRAFT = "Dies ist ein AI-generierter Forschungsstand ueber Machine Learning."
_CONTROL_A = "Manuell geschriebener Text ueber Deep Learning Anwendungen."
_CONTROL_B = "Ein weiterer externer Text ueber Neuronale Netze."


# --- Modelle ---


class TestTextScoring:
    def test_fields(self):
        ts = TextScoring(
            text_id="own", label="own_draft", score=7.5, reasoning="Gut strukturiert"
        )
        assert ts.text_id == "own"
        assert ts.score == 7.5
        assert ts.label == "own_draft"

    def test_score_bounds(self):
        with pytest.raises(ValueError):
            TextScoring(text_id="x", label="x", score=11.0, reasoning="")
        with pytest.raises(ValueError):
            TextScoring(text_id="x", label="x", score=-1.0, reasoning="")


class TestBiasTestResult:
    def test_bias_detected_when_own_higher(self):
        """Bias erkannt wenn eigener Draft signifikant hoeher bewertet."""
        result = BiasTestResult(
            own_draft_score=8.5,
            control_mean_score=5.0,
            scorings=[],
            bias_detected=True,
            bias_magnitude=3.5,
        )
        assert result.bias_detected is True
        assert result.bias_magnitude == 3.5

    def test_no_bias_when_scores_similar(self):
        """Kein Bias wenn Scores aehnlich."""
        result = BiasTestResult(
            own_draft_score=6.0,
            control_mean_score=5.5,
            scorings=[],
            bias_detected=False,
            bias_magnitude=0.5,
        )
        assert result.bias_detected is False

    def test_negative_magnitude_no_self_enhancement(self):
        """Negative Magnitude = eigener Draft schlechter → kein Self-Enhancement."""
        result = BiasTestResult(
            own_draft_score=3.0,
            control_mean_score=7.0,
            scorings=[],
            bias_detected=False,
            bias_magnitude=-4.0,
        )
        assert result.bias_magnitude == -4.0
        assert result.bias_detected is False


# --- Prompt-Building ---


class TestBuildScoringPrompt:
    def test_contains_all_texts(self):
        prompt = _build_scoring_prompt(
            topic="ML fairness",
            texts=[("t1", _OWN_DRAFT), ("t2", _CONTROL_A)],
        )
        assert "ML fairness" in prompt
        assert _OWN_DRAFT in prompt
        assert _CONTROL_A in prompt

    def test_text_ids_in_prompt(self):
        prompt = _build_scoring_prompt(
            topic="test",
            texts=[("text_A", "Inhalt A"), ("text_B", "Inhalt B")],
        )
        assert "text_A" in prompt
        assert "text_B" in prompt

    def test_texts_shuffled_order(self):
        """Texte sollten in der gegebenen Reihenfolge erscheinen (Caller shuffled)."""
        prompt = _build_scoring_prompt(
            topic="test",
            texts=[("first", "Erster Text"), ("second", "Zweiter Text")],
        )
        # Beide muessen enthalten sein
        assert "Erster Text" in prompt
        assert "Zweiter Text" in prompt


# --- Response Parsing ---


class TestParseScoringResponse:
    def test_valid_json(self):
        response = json.dumps({
            "scorings": [
                {"text_id": "t1", "score": 7, "reasoning": "Gut"},
                {"text_id": "t2", "score": 5, "reasoning": "Ok"},
            ]
        })
        result = _parse_scoring_response(response, ["t1", "t2"])
        assert len(result) == 2
        assert result[0].score == 7.0
        assert result[1].score == 5.0

    def test_markdown_wrapper(self):
        inner = json.dumps({
            "scorings": [{"text_id": "t1", "score": 6, "reasoning": ""}]
        })
        response = f"```json\n{inner}\n```"
        result = _parse_scoring_response(response, ["t1"])
        assert len(result) == 1

    def test_invalid_json_returns_empty(self):
        result = _parse_scoring_response("Kein JSON", ["t1"])
        assert result == []

    def test_unknown_text_id_skipped(self):
        response = json.dumps({
            "scorings": [{"text_id": "unknown", "score": 5, "reasoning": ""}]
        })
        result = _parse_scoring_response(response, ["t1"])
        assert result == []

    def test_score_clamped(self):
        response = json.dumps({
            "scorings": [
                {"text_id": "t1", "score": 15, "reasoning": ""},
                {"text_id": "t2", "score": -3, "reasoning": ""},
            ]
        })
        result = _parse_scoring_response(response, ["t1", "t2"])
        assert result[0].score == 10.0
        assert result[1].score == 0.0


# --- Integration ---


class TestSelfEnhancement:
    def _make_dynamic_response(self, mock_llm, own_score: float, control_score: float):
        """Erzeugt LLM-Response die IDs aus dem Prompt extrahiert."""

        async def _dynamic_response(system_prompt, user_msg, *, config=None):
            # IDs aus dem Prompt extrahieren (Format: "--- Text tN ---")
            import re

            ids = re.findall(r"--- Text (t\d+) ---", user_msg)
            # Erster Text im Prompt bekommt own_score, Rest control_score
            # Aber wir wissen nicht welcher own ist — geben allen control_score,
            # ausser dem mit dem own_draft-Inhalt
            scorings = []
            for tid in ids:
                # Pruefe ob der eigene Draft-Text in diesem Abschnitt steht
                pattern = f"--- Text {tid} ---\n(.*?)(?:--- Text|$)"
                match = re.search(pattern, user_msg, re.DOTALL)
                text_content = match.group(1).strip() if match else ""
                if _OWN_DRAFT[:30] in text_content:
                    scorings.append({"text_id": tid, "score": own_score, "reasoning": "Own"})
                else:
                    scorings.append({"text_id": tid, "score": control_score, "reasoning": "Ctrl"})
            return json.dumps({"scorings": scorings})

        mock_llm.side_effect = _dynamic_response

    @pytest.mark.asyncio
    async def test_basic_flow(self):
        """Grundlegender Flow: eigener Draft + Kontrolle → BiasTestResult."""
        config = _llm_config()

        with patch("src.agents.bias_test.llm_complete", new_callable=AsyncMock) as mock_llm:
            self._make_dynamic_response(mock_llm, own_score=8.0, control_score=4.5)
            result = await run_bias_test(
                topic="ML",
                own_draft=_OWN_DRAFT,
                control_texts=[_CONTROL_A, _CONTROL_B],
                config=config,
            )

        assert isinstance(result, BiasTestResult)
        assert result.own_draft_score == 8.0
        assert result.control_mean_score == 4.5
        assert result.bias_magnitude == 3.5
        assert result.bias_detected is True

    @pytest.mark.asyncio
    async def test_no_bias(self):
        """Kein Bias wenn Scores aehnlich."""
        config = _llm_config()

        with patch("src.agents.bias_test.llm_complete", new_callable=AsyncMock) as mock_llm:
            self._make_dynamic_response(mock_llm, own_score=6.0, control_score=6.0)
            result = await run_bias_test(
                topic="ML",
                own_draft=_OWN_DRAFT,
                control_texts=[_CONTROL_A],
                config=config,
            )

        assert result.bias_detected is False
        assert result.bias_magnitude == 0.0

    @pytest.mark.asyncio
    async def test_llm_error_graceful(self):
        """LLM-Fehler fuehrt zu Ergebnis mit Scores 0."""
        config = _llm_config()

        with patch("src.agents.bias_test.llm_complete", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = RuntimeError("API down")
            result = await run_bias_test(
                topic="ML",
                own_draft=_OWN_DRAFT,
                control_texts=[_CONTROL_A],
                config=config,
            )

        assert result.own_draft_score == 0.0
        assert result.control_mean_score == 0.0
        assert result.bias_detected is False

    @pytest.mark.asyncio
    async def test_empty_controls(self):
        """Ohne Kontrolltexte kein sinnvoller Bias-Test."""
        config = _llm_config()
        result = await run_bias_test(
            topic="ML",
            own_draft=_OWN_DRAFT,
            control_texts=[],
            config=config,
        )
        assert result.control_mean_score == 0.0
        assert result.bias_detected is False

    @pytest.mark.asyncio
    async def test_blinded_text_ids(self):
        """LLM sieht nur neutrale IDs (t1, t2, ...), nicht 'own_draft'."""
        config = _llm_config()

        with patch("src.agents.bias_test.llm_complete", new_callable=AsyncMock) as mock_llm:
            self._make_dynamic_response(mock_llm, own_score=5.0, control_score=5.0)
            await run_bias_test(
                topic="ML",
                own_draft=_OWN_DRAFT,
                control_texts=[_CONTROL_A],
                config=config,
            )

            # Pruefe dass "own_draft" nicht im Prompt vorkommt
            call_args = mock_llm.call_args
            user_msg = call_args[0][1]  # 2. Positional-Arg = user_message
            assert "own_draft" not in user_msg
            assert "eigener" not in user_msg.lower()
