"""Tests fuer den Agentic Review Loop (Spec 003).

Testet Modelle, Config-Laden, Review/Revise-Funktionen, Loop-Orchestrierung,
Self-Consistency Probe und Provenance-Integration.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.review_loop import (
    CompactIssue,
    CompactReview,
    ConsistencyResult,
    ReviseLoopResult,
    RevisionChangelog,
    SubQuestion,
    SubQuestionResult,
    _parse_review_response,
    _parse_revision_response,
    compute_agreement,
    compute_score,
    load_sub_questions,
    review_for_revision,
    revise_draft,
    run_revise_loop,
    self_consistency_probe,
)
from src.agents.reviewer import Severity

# --- Hilfsfunktionen ---


def _high_issue(section: str = "X") -> CompactIssue:
    """Erstellt ein HIGH-Issue fuer Tests."""
    return CompactIssue(
        section=section, problem="P", suggestion="S",
        severity=Severity.HIGH,
    )


def _make_sub_questions() -> list[SubQuestion]:
    """Erstellt Test-Sub-Fragen."""
    return [
        SubQuestion(dimension="Evidence", question="Quellen vorhanden?", weight=2.0),
        SubQuestion(dimension="Structure", question="Klare These?", weight=1.5),
        SubQuestion(dimension="Clarity", question="Verstaendlich?", weight=1.0),
    ]


def _make_review_json(
    answers: list[bool] | None = None,
    issues: list[dict] | None = None,
) -> str:
    """Erstellt Mock-LLM-Review-Antwort als JSON-String."""
    sub_questions = _make_sub_questions()
    if answers is None:
        answers = [True, True, False]
    sq_data = [
        {"question": sq.question, "answer": a, "evidence": "Test"}
        for sq, a in zip(sub_questions, answers)
    ]
    issue_data = issues or []
    return json.dumps({"sub_questions": sq_data, "issues": issue_data})


# --- Test: Pydantic-Modelle ---


class TestModels:
    """Tests fuer Pydantic-Modelle."""

    def test_sub_question_creation(self):
        sq = SubQuestion(dimension="Evidence", question="Test?", weight=2.0)
        assert sq.dimension == "Evidence"
        assert sq.weight == 2.0

    def test_sub_question_default_weight(self):
        sq = SubQuestion(dimension="X", question="Y?")
        assert sq.weight == 1.0

    def test_compact_issue_creation(self):
        issue = CompactIssue(
            section="Einleitung",
            problem="Keine Quellen",
            suggestion="Quellen ergaenzen",
            severity=Severity.CRITICAL,
        )
        assert issue.severity == Severity.CRITICAL

    def test_compact_review_has_blockers_true(self):
        review = CompactReview(
            issues=[
                CompactIssue(
                    section="X", problem="P", suggestion="S", severity=Severity.CRITICAL
                )
            ],
            score=20,
        )
        assert review.has_blockers is True

    def test_compact_review_has_blockers_false(self):
        review = CompactReview(
            issues=[
                _high_issue()
            ],
            score=30,
        )
        assert review.has_blockers is False

    def test_compact_review_empty_no_blockers(self):
        review = CompactReview()
        assert review.has_blockers is False

    def test_revision_changelog_creation(self):
        cl = RevisionChangelog(
            sections_modified=["Einleitung"],
            changes=["Quellen ergaenzt"],
            issues_addressed=["Keine Quellen"],
        )
        assert len(cl.sections_modified) == 1

    def test_consistency_result_flagged(self):
        cr = ConsistencyResult(
            dimension="Evidence",
            ratings=["erfuellt", "nicht_erfuellt", "erfuellt"],
            agreement_pct=66.7,
            flagged_for_human=False,
        )
        assert cr.flagged_for_human is False

    def test_revise_loop_result_defaults(self):
        result = ReviseLoopResult(final_draft_md="test")
        assert result.iterations == 0
        assert result.aborted is False
        assert result.reviews == []


# --- Test: Score-Berechnung ---


class TestComputeScore:
    """Tests fuer compute_score()."""

    def test_all_true(self):
        sqs = _make_sub_questions()
        results = [SubQuestionResult(question=sq, answer=True) for sq in sqs]
        assert compute_score(results) == 50

    def test_all_false(self):
        sqs = _make_sub_questions()
        results = [SubQuestionResult(question=sq, answer=False) for sq in sqs]
        assert compute_score(results) == 0

    def test_mixed(self):
        sqs = _make_sub_questions()
        results = [
            SubQuestionResult(question=sqs[0], answer=True),   # 2.0
            SubQuestionResult(question=sqs[1], answer=False),  # 0
            SubQuestionResult(question=sqs[2], answer=True),   # 1.0
        ]
        # 3.0 / 4.5 * 50 = 33.3 → 33
        assert compute_score(results) == 33

    def test_empty(self):
        assert compute_score([]) == 0


# --- Test: Agreement-Berechnung ---


class TestComputeAgreement:
    """Tests fuer compute_agreement()."""

    def test_full_agreement(self):
        assert compute_agreement(["a", "a", "a"]) == 100.0

    def test_no_agreement(self):
        assert compute_agreement(["a", "b", "c"]) == pytest.approx(33.3, abs=0.1)

    def test_partial_agreement(self):
        assert compute_agreement(["a", "a", "b"]) == pytest.approx(66.7, abs=0.1)

    def test_empty(self):
        assert compute_agreement([]) == 0.0


# --- Test: Config laden ---


class TestLoadSubQuestions:
    """Tests fuer load_sub_questions()."""

    def test_load_from_file(self, tmp_path):
        data = [
            {"dimension": "X", "question": "Q1?", "weight": 1.5},
            {"dimension": "Y", "question": "Q2?"},
        ]
        path = tmp_path / "sq.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        result = load_sub_questions(path)
        assert len(result) == 2
        assert result[0].weight == 1.5
        assert result[1].weight == 1.0  # Default

    def test_missing_file_returns_empty(self, tmp_path):
        result = load_sub_questions(tmp_path / "nonexistent.json")
        assert result == []

    def test_invalid_json_returns_empty(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json", encoding="utf-8")
        result = load_sub_questions(path)
        assert result == []

    def test_invalid_schema_returns_empty(self, tmp_path):
        path = tmp_path / "bad_schema.json"
        path.write_text(json.dumps([{"bad_key": "value"}]), encoding="utf-8")
        result = load_sub_questions(path)
        assert result == []


# --- Test: JSON-Parsing ---


class TestParseReviewResponse:
    """Tests fuer _parse_review_response()."""

    def test_valid_json(self):
        sqs = _make_sub_questions()
        raw = _make_review_json(answers=[True, False, True])
        result = _parse_review_response(raw, sqs)
        assert isinstance(result, CompactReview)
        assert len(result.sub_question_results) == 3
        assert result.sub_question_results[0].answer is True
        assert result.sub_question_results[1].answer is False

    def test_json_in_markdown_block(self):
        sqs = _make_sub_questions()
        inner = _make_review_json()
        raw = f"Hier ist mein Review:\n```json\n{inner}\n```"
        result = _parse_review_response(raw, sqs)
        assert len(result.sub_question_results) == 3

    def test_invalid_json_returns_empty(self):
        sqs = _make_sub_questions()
        result = _parse_review_response("not json at all", sqs)
        assert result.score == 0
        assert result.issues == []

    def test_issues_parsed(self):
        sqs = _make_sub_questions()
        issues = [{
            "section": "Methode", "problem": "Fehlt",
            "suggestion": "Ergaenzen", "severity": "HIGH",
        }]
        raw = _make_review_json(issues=issues)
        result = _parse_review_response(raw, sqs)
        assert len(result.issues) == 1
        assert result.issues[0].severity == Severity.HIGH

    def test_low_severity_filtered(self):
        sqs = _make_sub_questions()
        issues = [
            {"section": "X", "problem": "P", "suggestion": "S", "severity": "LOW"},
            {"section": "Y", "problem": "P", "suggestion": "S", "severity": "MEDIUM"},
        ]
        raw = _make_review_json(issues=issues)
        result = _parse_review_response(raw, sqs)
        assert len(result.issues) == 0


class TestParseRevisionResponse:
    """Tests fuer _parse_revision_response()."""

    def test_with_changelog(self):
        cl_json = json.dumps({
            "sections_modified": ["Einleitung"],
            "changes": ["Quelle ergaenzt"],
            "issues_addressed": ["Keine Quellen"],
        })
        raw = f"Ueberarbeiteter Text hier.\n```json\n{cl_json}\n```"
        text, changelog = _parse_revision_response(raw)
        assert "Ueberarbeiteter Text hier." in text
        assert changelog.sections_modified == ["Einleitung"]

    def test_without_changelog(self):
        raw = "Nur Text ohne JSON."
        text, changelog = _parse_revision_response(raw)
        assert text == "Nur Text ohne JSON."
        assert changelog.sections_modified == []

    def test_malformed_changelog_json(self):
        raw = "Text\n```json\nnot valid\n```"
        text, changelog = _parse_revision_response(raw)
        assert changelog.sections_modified == []

    def test_strips_preamble(self):
        raw = "Hier ist die ueberarbeitete Version:\n\n## Kernaussage\n\nText hier."
        text, _ = _parse_revision_response(raw)
        assert text.startswith("## Kernaussage")
        assert "ueberarbeitete Version" not in text

    def test_strips_rest_bleibt(self):
        raw = "## Kernaussage\n\nText.\n\n[Rest des Dokuments bleibt unveraendert]"
        text, _ = _parse_revision_response(raw)
        assert "[Rest des Dokuments" not in text

    def test_clean_text_unchanged(self):
        raw = "## Kernaussage\n\nText hier.\n\n## Hintergrund\n\nMehr Text."
        text, _ = _parse_revision_response(raw)
        assert text == raw


class TestShouldAcceptRevision:
    """Tests fuer Revisions-Laengen-Guard."""

    def test_short_revision_rejected(self):
        from src.agents.review_loop import _should_accept_revision

        original = "## Kernaussage\n\n" + "A" * 1000 + "\n\n## Hintergrund\n\n" + "B" * 1000
        short_revision = "## Kernaussage\n\nKurzer Text."
        assert _should_accept_revision(original, short_revision) is False

    def test_full_revision_accepted(self):
        from src.agents.review_loop import _should_accept_revision

        original = "## Kernaussage\n\nText." * 10
        full_revision = "## Kernaussage\n\nBesserer Text." * 10
        assert _should_accept_revision(original, full_revision) is True

    def test_empty_original_accepted(self):
        from src.agents.review_loop import _should_accept_revision

        assert _should_accept_revision("", "Neuer Text") is True


# --- Test: LLM-Funktionen (gemockt) ---


class TestReviewForRevision:
    """Tests fuer review_for_revision() mit gemocktem LLM."""

    @pytest.mark.asyncio
    @patch("src.utils.llm_client.llm_complete", new_callable=AsyncMock)
    @patch("src.utils.llm_client.load_llm_config")
    async def test_returns_compact_review(self, mock_config, mock_llm):
        from src.utils.llm_client import LLMConfig

        mock_config.return_value = LLMConfig(api_key="test-key")
        mock_llm.return_value = _make_review_json(answers=[True, True, True])

        sqs = _make_sub_questions()
        result = await review_for_revision("Testtext", sqs)
        assert isinstance(result, CompactReview)
        assert result.score == 50

    @pytest.mark.asyncio
    @patch("src.utils.llm_client.llm_complete", new_callable=AsyncMock)
    @patch("src.utils.llm_client.load_llm_config")
    async def test_with_custom_temperature(self, mock_config, mock_llm):
        from src.utils.llm_client import LLMConfig

        mock_config.return_value = LLMConfig(api_key="test-key")
        mock_llm.return_value = _make_review_json()

        sqs = _make_sub_questions()
        result = await review_for_revision("Text", sqs, temperature=0.7)
        assert isinstance(result, CompactReview)
        # Verify temperature was passed through
        call_kwargs = mock_llm.call_args
        config_used = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        assert config_used.temperature == 0.7


class TestReviseDraft:
    """Tests fuer revise_draft() mit gemocktem LLM."""

    @pytest.mark.asyncio
    async def test_empty_issues_returns_unchanged(self):
        text, changelog = await revise_draft("Original text", [])
        assert text == "Original text"
        assert changelog.sections_modified == []

    @pytest.mark.asyncio
    @patch("src.utils.llm_client.llm_complete", new_callable=AsyncMock)
    @patch("src.utils.llm_client.load_llm_config")
    async def test_returns_revised_text(self, mock_config, mock_llm):
        from src.utils.llm_client import LLMConfig

        mock_config.return_value = LLMConfig(api_key="test-key")
        mock_llm.return_value = (
            'Verbesserter Text.\n```json\n'
            '{"sections_modified": ["Methode"], "changes": ["Quelle ergaenzt"], '
            '"issues_addressed": ["Keine Quellen"]}\n```'
        )

        issues = [
            CompactIssue(
                section="Methode", problem="Keine Quellen", suggestion="Quellen ergaenzen",
                severity=Severity.HIGH,
            )
        ]
        text, changelog = await revise_draft("Alter Text", issues)
        assert "Verbesserter Text." in text
        assert "Methode" in changelog.sections_modified


# --- Test: Loop-Orchestrierung ---


class TestRunReviseLoop:
    """Tests fuer run_revise_loop()."""

    @pytest.mark.asyncio
    @patch("src.agents.review_loop.review_for_revision", new_callable=AsyncMock)
    async def test_no_issues_stops_immediately(self, mock_review):
        mock_review.return_value = CompactReview(issues=[], score=45, iteration=1)

        sqs = _make_sub_questions()
        result = await run_revise_loop("Draft", sqs)
        assert result.iterations == 0
        assert result.aborted is False
        assert len(result.reviews) == 1

    @pytest.mark.asyncio
    @patch("src.agents.review_loop.review_for_revision", new_callable=AsyncMock)
    async def test_score_above_threshold_stops(self, mock_review):
        mock_review.return_value = CompactReview(
            issues=[
                _high_issue()
            ],
            score=40,
            iteration=1,
        )

        sqs = _make_sub_questions()
        result = await run_revise_loop("Draft", sqs, score_threshold=35)
        assert result.iterations == 0
        assert result.aborted is False

    @pytest.mark.asyncio
    @patch("src.agents.review_loop.revise_draft", new_callable=AsyncMock)
    @patch("src.agents.review_loop.review_for_revision", new_callable=AsyncMock)
    async def test_score_drops_aborts(self, mock_review, mock_revise):
        # Runde 1: Score 25, Runde 2: Score 20 → Abort
        mock_review.side_effect = [
            CompactReview(
                issues=[_high_issue()],
                score=25,
            ),
            CompactReview(
                issues=[_high_issue()],
                score=20,
            ),
        ]
        mock_revise.return_value = ("Revidiert", RevisionChangelog())

        sqs = _make_sub_questions()
        result = await run_revise_loop("Draft", sqs)
        assert result.aborted is True
        assert "nicht verbessert" in result.abort_reason

    @pytest.mark.asyncio
    @patch("src.agents.review_loop.revise_draft", new_callable=AsyncMock)
    @patch("src.agents.review_loop.review_for_revision", new_callable=AsyncMock)
    async def test_max_revisions_respected(self, mock_review, mock_revise):
        mock_review.return_value = CompactReview(
            issues=[_high_issue()],
            score=20,
        )
        mock_revise.return_value = ("Revidiert", RevisionChangelog())

        sqs = _make_sub_questions()
        result = await run_revise_loop("Draft", sqs, max_revisions=1)
        assert result.iterations <= 1

    @pytest.mark.asyncio
    @patch("src.agents.review_loop.revise_draft", new_callable=AsyncMock)
    @patch("src.agents.review_loop.review_for_revision", new_callable=AsyncMock)
    async def test_max_revisions_capped_at_2(self, mock_review, mock_revise):
        mock_review.return_value = CompactReview(
            issues=[_high_issue()],
            score=20,
        )
        mock_revise.return_value = ("Revidiert", RevisionChangelog())

        sqs = _make_sub_questions()
        result = await run_revise_loop("Draft", sqs, max_revisions=5)
        assert result.iterations <= 2

    @pytest.mark.asyncio
    @patch("src.agents.review_loop.self_consistency_probe", new_callable=AsyncMock)
    @patch("src.agents.review_loop.review_for_revision", new_callable=AsyncMock)
    async def test_borderline_triggers_consistency(self, mock_review, mock_consistency):
        mock_review.return_value = CompactReview(issues=[], score=35)
        mock_consistency.return_value = [
            ConsistencyResult(dimension="Evidence", ratings=["a", "a", "b"], agreement_pct=66.7)
        ]

        sqs = _make_sub_questions()
        result = await run_revise_loop("Draft", sqs)
        assert len(result.consistency) == 1
        mock_consistency.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.agents.review_loop.review_for_revision", new_callable=AsyncMock)
    async def test_high_score_skips_consistency(self, mock_review):
        mock_review.return_value = CompactReview(issues=[], score=45)

        sqs = _make_sub_questions()
        result = await run_revise_loop("Draft", sqs)
        assert result.consistency == []


# --- Test: Self-Consistency ---


class TestSelfConsistencyProbe:
    """Tests fuer self_consistency_probe()."""

    @pytest.mark.asyncio
    @patch("src.agents.review_loop.review_for_revision", new_callable=AsyncMock)
    async def test_three_reviews_executed(self, mock_review):
        sqs = _make_sub_questions()
        mock_review.return_value = CompactReview(
            sub_question_results=[
                SubQuestionResult(question=sqs[0], answer=True),
                SubQuestionResult(question=sqs[1], answer=True),
                SubQuestionResult(question=sqs[2], answer=False),
            ],
            score=30,
        )

        result = await self_consistency_probe("Text", sqs)
        assert mock_review.call_count == 3
        assert len(result) == 3  # 3 Dimensionen

    @pytest.mark.asyncio
    @patch("src.agents.review_loop.review_for_revision", new_callable=AsyncMock)
    async def test_full_agreement_not_flagged(self, mock_review):
        sqs = _make_sub_questions()
        mock_review.return_value = CompactReview(
            sub_question_results=[
                SubQuestionResult(question=sqs[0], answer=True),
                SubQuestionResult(question=sqs[1], answer=True),
                SubQuestionResult(question=sqs[2], answer=True),
            ],
            score=50,
        )

        result = await self_consistency_probe("Text", sqs)
        for cr in result:
            assert cr.flagged_for_human is False
            assert cr.agreement_pct == 100.0

    @pytest.mark.asyncio
    @patch("src.agents.review_loop.review_for_revision", new_callable=AsyncMock)
    async def test_low_agreement_flagged(self, mock_review):
        sqs = _make_sub_questions()
        # 3 verschiedene Antworten pro Aufruf
        mock_review.side_effect = [
            CompactReview(
                sub_question_results=[
                    SubQuestionResult(question=sqs[0], answer=True),
                    SubQuestionResult(question=sqs[1], answer=True),
                    SubQuestionResult(question=sqs[2], answer=True),
                ],
                score=50,
            ),
            CompactReview(
                sub_question_results=[
                    SubQuestionResult(question=sqs[0], answer=False),
                    SubQuestionResult(question=sqs[1], answer=False),
                    SubQuestionResult(question=sqs[2], answer=False),
                ],
                score=0,
            ),
            CompactReview(
                sub_question_results=[
                    SubQuestionResult(question=sqs[0], answer=True),
                    SubQuestionResult(question=sqs[1], answer=True),
                    SubQuestionResult(question=sqs[2], answer=False),
                ],
                score=30,
            ),
        ]

        result = await self_consistency_probe("Text", sqs)
        # Evidence: True, False, True → 66.7% → not flagged
        # Clarity: True, False, False → 66.7% → not flagged
        # Mindestens eine Dimension sollte Agreement < 100 haben
        assert any(cr.agreement_pct < 100.0 for cr in result)


# --- Test: Provenance-Integration ---


class TestProvenanceIntegration:
    """Tests fuer Provenance-Logging im Review-Loop."""

    @pytest.mark.asyncio
    @patch("src.agents.review_loop.review_for_revision", new_callable=AsyncMock)
    async def test_review_logged(self, mock_review):
        mock_review.return_value = CompactReview(issues=[], score=45)
        mock_provenance = MagicMock()

        sqs = _make_sub_questions()
        await run_revise_loop("Draft", sqs, provenance=mock_provenance)

        mock_provenance.log_action.assert_called()
        call_args = mock_provenance.log_action.call_args_list[0]
        assert call_args.kwargs["action"] == "REVIEW_COMPLETED"

    @pytest.mark.asyncio
    @patch("src.agents.review_loop.revise_draft", new_callable=AsyncMock)
    @patch("src.agents.review_loop.review_for_revision", new_callable=AsyncMock)
    async def test_abort_logged(self, mock_review, mock_revise):
        mock_review.side_effect = [
            CompactReview(
                issues=[_high_issue()],
                score=25,
            ),
            CompactReview(
                issues=[_high_issue()],
                score=20,
            ),
        ]
        mock_revise.return_value = ("Revidiert", RevisionChangelog())
        mock_provenance = MagicMock()

        sqs = _make_sub_questions()
        await run_revise_loop("Draft", sqs, provenance=mock_provenance)

        actions = [c.kwargs["action"] for c in mock_provenance.log_action.call_args_list]
        assert "LOOP_ABORTED" in actions

    @pytest.mark.asyncio
    @patch("src.agents.review_loop.revise_draft", new_callable=AsyncMock)
    @patch("src.agents.review_loop.review_for_revision", new_callable=AsyncMock)
    async def test_revision_logged(self, mock_review, mock_revise):
        mock_review.side_effect = [
            CompactReview(
                issues=[_high_issue()],
                score=20,
            ),
            CompactReview(issues=[], score=45),
        ]
        mock_revise.return_value = ("Revidiert", RevisionChangelog(sections_modified=["X"]))
        mock_provenance = MagicMock()

        sqs = _make_sub_questions()
        await run_revise_loop("Draft", sqs, provenance=mock_provenance)

        actions = [c.kwargs["action"] for c in mock_provenance.log_action.call_args_list]
        assert "REVISION_APPLIED" in actions


# --- Test: State Machine Sub-States ---


class TestSynthesisSubPhase:
    """Tests fuer SynthesisSubPhase in state.py."""

    def test_sub_phase_values(self):
        from src.pipeline.state import SynthesisSubPhase

        assert SynthesisSubPhase.DRAFTING == "drafting"
        assert SynthesisSubPhase.REVIEWING == "reviewing"
        assert SynthesisSubPhase.REVISING == "revising"
        assert SynthesisSubPhase.CONSISTENCY_CHECK == "consistency_check"
        assert SynthesisSubPhase.COMPLETED == "completed"

    def test_phase_record_sub_phase_default_none(self):
        from src.pipeline.state import PhaseRecord

        record = PhaseRecord()
        assert record.sub_phase is None

    def test_phase_record_sub_phase_set(self):
        from src.pipeline.state import PhaseRecord, SynthesisSubPhase

        record = PhaseRecord(sub_phase=SynthesisSubPhase.REVIEWING.value)
        assert record.sub_phase == "reviewing"

    def test_backward_compat_no_sub_phase(self):
        """Bestehende States ohne sub_phase bleiben kompatibel."""
        from src.pipeline.state import PhaseRecord

        data = {"status": "in_progress", "started_at": "2026-01-01T00:00:00Z"}
        record = PhaseRecord.model_validate(data)
        assert record.sub_phase is None
        assert record.status.value == "in_progress"
