"""Tests fuer Claim Verification."""

from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock, patch

from src.agents.claim_verifier import (
    AtomicClaim,
    ClaimVerification,
    VerificationLabel,
    VerificationReport,
    _build_extraction_prompt,
    _parse_extraction_response,
    _split_draft_sections,
    extract_claims,
    verify_claims,
    format_verification_report,
    run_verification,
)
from src.utils.llm_client import LLMConfig


def _llm_config() -> LLMConfig:
    return LLMConfig(api_key="test-key", model="test-model")


class TestAtomicClaim:
    def test_fields(self):
        claim = AtomicClaim(
            claim="X steigert Performance um 15%",
            cited_paper_id="10.1234/test",
            source_sentence="Smith (2024) zeigt, dass X die Performance um 15% steigert.",
        )
        assert claim.claim == "X steigert Performance um 15%"
        assert claim.cited_paper_id == "10.1234/test"

    def test_minimal(self):
        claim = AtomicClaim(claim="Test", cited_paper_id="p1", source_sentence="Test.")
        assert claim.claim == "Test"


class TestVerificationLabel:
    def test_all_labels(self):
        assert VerificationLabel.SUPPORTS == "SUPPORTS"
        assert VerificationLabel.REFUTES == "REFUTES"
        assert VerificationLabel.NOT_ENOUGH_INFO == "NOT_ENOUGH_INFO"
        assert VerificationLabel.NO_ABSTRACT == "NO_ABSTRACT"


class TestClaimVerification:
    def test_fields(self):
        cv = ClaimVerification(
            claim=AtomicClaim(claim="X", cited_paper_id="p1", source_sentence="S"),
            label=VerificationLabel.SUPPORTS,
            confidence=0.85,
            reasoning="Abstract bestaetigt den Claim",
            abstract_used="Ein Abstract...",
        )
        assert cv.label == VerificationLabel.SUPPORTS
        assert cv.confidence == 0.85

    def test_no_abstract(self):
        cv = ClaimVerification(
            claim=AtomicClaim(claim="X", cited_paper_id="p1", source_sentence="S"),
            label=VerificationLabel.NO_ABSTRACT,
            confidence=0.0,
            reasoning="Kein Abstract verfuegbar",
        )
        assert cv.abstract_used is None


class TestVerificationReport:
    def test_computed_stats(self):
        claims = [
            ClaimVerification(
                claim=AtomicClaim(claim="A", cited_paper_id="p1", source_sentence="S"),
                label=VerificationLabel.SUPPORTS, confidence=0.9, reasoning="",
            ),
            ClaimVerification(
                claim=AtomicClaim(claim="B", cited_paper_id="p2", source_sentence="S"),
                label=VerificationLabel.REFUTES, confidence=0.8, reasoning="",
            ),
            ClaimVerification(
                claim=AtomicClaim(claim="C", cited_paper_id="p3", source_sentence="S"),
                label=VerificationLabel.NOT_ENOUGH_INFO, confidence=0.5, reasoning="",
            ),
            ClaimVerification(
                claim=AtomicClaim(claim="D", cited_paper_id="p4", source_sentence="S"),
                label=VerificationLabel.NO_ABSTRACT, confidence=0.0, reasoning="",
            ),
        ]
        report = VerificationReport(document="test.md", claims=claims)
        assert report.supports_count == 1
        assert report.refutes_count == 1
        assert report.nei_count == 1
        assert report.no_abstract_count == 1
        assert report.total_claims == 4


# --- Task 2: Extraction ---


class TestBuildExtractionPrompt:
    def test_contains_draft(self):
        prompt = _build_extraction_prompt("Ein Draft mit Claims.", {"p1": "Paper A"})
        assert "Ein Draft mit Claims." in prompt

    def test_contains_paper_ids(self):
        prompt = _build_extraction_prompt("Draft.", {"p1": "Paper A", "p2": "Paper B"})
        assert "p1" in prompt
        assert "Paper A" in prompt


class TestParseExtractionResponse:
    def test_valid_json(self):
        response = json.dumps({
            "claims": [
                {
                    "claim": "X steigert Y um 15%",
                    "cited_paper_id": "p1",
                    "source_sentence": "Smith (2024) zeigt dass X Y um 15% steigert.",
                },
            ]
        })
        result = _parse_extraction_response(response, {"p1"})
        assert len(result) == 1
        assert result[0].claim == "X steigert Y um 15%"

    def test_markdown_wrapper(self):
        inner = json.dumps({"claims": [
            {"claim": "A", "cited_paper_id": "p1", "source_sentence": "S"}
        ]})
        response = f"```json\n{inner}\n```"
        result = _parse_extraction_response(response, {"p1"})
        assert len(result) == 1

    def test_invalid_json_returns_empty(self):
        result = _parse_extraction_response("kein json", {"p1"})
        assert result == []

    def test_unknown_paper_id_skipped(self):
        response = json.dumps({
            "claims": [
                {"claim": "A", "cited_paper_id": "unknown", "source_sentence": "S"},
            ]
        })
        result = _parse_extraction_response(response, {"p1"})
        assert result == []


class TestSplitDraftSections:
    def test_splits_on_headings(self):
        draft = "## Intro\nText A.\n## Methods\nText B."
        # Kurzer Draft — wird nicht gesplittet
        # Brauchen langen Draft fuer Split
        long_a = "## Intro\n" + "A " * 4000
        long_b = "## Methods\n" + "B " * 4000
        draft = f"{long_a}\n{long_b}"
        sections = _split_draft_sections(draft)
        assert len(sections) == 2
        assert "A " in sections[0]
        assert "B " in sections[1]

    def test_no_headings_returns_whole(self):
        sections = _split_draft_sections("Just text.")
        assert len(sections) == 1

    def test_short_draft_single_section(self):
        sections = _split_draft_sections("## A\nShort.")
        assert len(sections) == 1


class TestExtractClaims:
    @pytest.mark.asyncio
    async def test_basic_flow(self):
        llm_response = json.dumps({
            "claims": [
                {"claim": "X ist besser", "cited_paper_id": "p1", "source_sentence": "Laut S."},
            ]
        })
        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            mock.return_value = llm_response
            result = await extract_claims("Draft text.", {"p1": "Paper A"}, config=config)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_long_draft_batched_by_sections(self):
        """Langer Draft wird in Sektionen aufgeteilt (je ein LLM-Call)."""
        section_a = "## Intro\n" + "A " * 4000
        section_b = "## Methods\n" + "B " * 4000
        draft = f"{section_a}\n{section_b}"
        response_a = json.dumps({"claims": [
            {"claim": "Claim A", "cited_paper_id": "p1", "source_sentence": "S"},
        ]})
        response_b = json.dumps({"claims": [
            {"claim": "Claim B", "cited_paper_id": "p1", "source_sentence": "S"},
        ]})
        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            mock.side_effect = [response_a, response_b]
            result = await extract_claims(draft, {"p1": "Paper A"}, config=config)
        assert len(result) == 2
        assert mock.call_count == 2

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty(self):
        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            mock.side_effect = RuntimeError("API down")
            result = await extract_claims("Draft.", {"p1": "A"}, config=config)
        assert result == []

    @pytest.mark.asyncio
    async def test_uses_higher_max_tokens(self):
        """extract_claims nutzt 2048 max_tokens statt Default 1024."""
        llm_response = json.dumps({"claims": []})
        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            mock.return_value = llm_response
            await extract_claims("Draft.", {"p1": "A"}, config=config)
            used_config = mock.call_args.kwargs.get("config")
            assert used_config.max_tokens == 2048

    @pytest.mark.asyncio
    async def test_empty_paper_map_returns_empty(self):
        config = _llm_config()
        result = await extract_claims("Draft.", {}, config=config)
        assert result == []


# --- Task 3: NLI Verification ---


class TestVerifyClaims:
    @pytest.mark.asyncio
    async def test_supports(self):
        claims = [AtomicClaim(claim="X ist effektiv", cited_paper_id="p1", source_sentence="S")]
        abstracts = {"p1": "Unsere Studie zeigt dass X effektiv ist."}
        llm_response = json.dumps({
            "verifications": [
                {"claim_index": 0, "label": "SUPPORTS", "confidence": 0.9, "reasoning": "Bestaetigt"}
            ]
        })
        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            mock.return_value = llm_response
            result = await verify_claims(claims, abstracts, config=config)
        assert len(result) == 1
        assert result[0].label == VerificationLabel.SUPPORTS
        assert result[0].abstract_used == "Unsere Studie zeigt dass X effektiv ist."

    @pytest.mark.asyncio
    async def test_no_abstract(self):
        """Paper ohne Abstract → NO_ABSTRACT Label, kein LLM-Call."""
        claims = [AtomicClaim(claim="X", cited_paper_id="p1", source_sentence="S")]
        abstracts = {}  # Kein Abstract fuer p1
        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            result = await verify_claims(claims, abstracts, config=config)
        assert len(result) == 1
        assert result[0].label == VerificationLabel.NO_ABSTRACT
        mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_batching(self):
        """Claims werden in Batches von 5 verarbeitet."""
        claims = [
            AtomicClaim(claim=f"Claim {i}", cited_paper_id="p1", source_sentence="S")
            for i in range(8)
        ]
        abstracts = {"p1": "Abstract."}
        batch1 = json.dumps({"verifications": [
            {"claim_index": i, "label": "SUPPORTS", "confidence": 0.8, "reasoning": ""}
            for i in range(5)
        ]})
        batch2 = json.dumps({"verifications": [
            {"claim_index": i, "label": "SUPPORTS", "confidence": 0.8, "reasoning": ""}
            for i in range(3)
        ]})
        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            mock.side_effect = [batch1, batch2]
            result = await verify_claims(claims, abstracts, config=config)
        assert mock.call_count == 2
        assert len(result) == 8

    @pytest.mark.asyncio
    async def test_llm_error_graceful(self):
        claims = [AtomicClaim(claim="X", cited_paper_id="p1", source_sentence="S")]
        abstracts = {"p1": "Abstract."}
        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            mock.side_effect = RuntimeError("API")
            result = await verify_claims(claims, abstracts, config=config)
        assert len(result) == 1
        assert result[0].label == VerificationLabel.NOT_ENOUGH_INFO


# --- Task 4: Report Formatting ---


class TestFormatVerificationReport:
    def test_basic_markdown(self):
        report = VerificationReport(
            document="test.md",
            claims=[
                ClaimVerification(
                    claim=AtomicClaim(claim="X ist gut", cited_paper_id="p1", source_sentence="S"),
                    label=VerificationLabel.SUPPORTS, confidence=0.9, reasoning="Bestaetigt",
                ),
                ClaimVerification(
                    claim=AtomicClaim(claim="Y ist schlecht", cited_paper_id="p2", source_sentence="S"),
                    label=VerificationLabel.REFUTES, confidence=0.8, reasoning="Widerlegt",
                ),
            ],
        )
        md = format_verification_report(report)
        assert "test.md" in md
        assert "Y ist schlecht" in md  # REFUTES erscheint unter "Widerlegte Claims"
        assert "X ist gut" in md  # SUPPORTS erscheint unter "Bestaetigte Claims"
        assert "2" in md  # total claims

    def test_empty_report(self):
        report = VerificationReport(document="test.md")
        md = format_verification_report(report)
        assert "0" in md


# --- Task 5: Orchestration ---


class TestRunVerification:
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """End-to-End: Draft → Extract Claims → Verify → Report."""
        draft = "Smith (2024) zeigt dass X die Performance um 15% steigert."
        abstracts = {"p1": "Wir zeigen dass X Performance um 15% verbessert."}
        paper_map = {"p1": "Smith et al. 2024"}

        extract_response = json.dumps({"claims": [
            {"claim": "X steigert Performance um 15%", "cited_paper_id": "p1",
             "source_sentence": "Smith (2024) zeigt dass X die Performance um 15% steigert."}
        ]})
        verify_response = json.dumps({"verifications": [
            {"claim_index": 0, "label": "SUPPORTS", "confidence": 0.9, "reasoning": "Bestaetigt"}
        ]})

        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            mock.side_effect = [extract_response, verify_response]
            report = await run_verification(
                draft_md=draft,
                paper_map=paper_map,
                abstracts=abstracts,
                document_name="test.md",
                config=config,
            )

        assert report.total_claims == 1
        assert report.supports_count == 1

    @pytest.mark.asyncio
    async def test_no_claims_extracted(self):
        """Keine Claims → leerer Report."""
        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            mock.return_value = json.dumps({"claims": []})
            report = await run_verification(
                draft_md="Kein Claim hier.",
                paper_map={"p1": "Paper"},
                abstracts={"p1": "Abstract"},
                document_name="test.md",
                config=config,
            )
        assert report.total_claims == 0
