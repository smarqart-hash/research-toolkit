"""Tests fuer Evidence Cards."""

from pathlib import Path

import pytest

from utils.evidence_card import (
    EvidenceCard,
    Metrics,
    load_evidence_cards,
    save_evidence_cards,
)


@pytest.fixture
def sample_card() -> EvidenceCard:
    return EvidenceCard(
        card_id="ec-001",
        paper_id="doi:10.1234/example",
        paper_title="LLM Reasoning in Medical Diagnostics",
        authors=["Doe, J.", "Smith, A."],
        year=2025,
        claim="GPT-4 erreicht 87% Accuracy bei seltenen Diagnosen",
        method="Retrospective study, N=1200",
        metrics=Metrics(
            p_value=0.003,
            effect_size=0.42,
            sample_size=1200,
        ),
        limitations=["Single-center", "Retrospective design"],
        confidence="high",
        source_section="Results 3.2",
        tags=["llm", "medical", "diagnostics"],
        funding_source="NIH Grant R01-123456",
    )


@pytest.fixture
def cards_dir(tmp_path: Path) -> Path:
    return tmp_path / "evidence_cards"


class TestEvidenceCard:
    def test_card_creation(self, sample_card: EvidenceCard) -> None:
        assert sample_card.card_id == "ec-001"
        assert sample_card.claim.startswith("GPT-4")
        assert sample_card.metrics.p_value == 0.003

    def test_card_with_minimal_fields(self) -> None:
        card = EvidenceCard(
            card_id="ec-min",
            paper_id="arxiv:2401.00001",
            paper_title="Minimal Paper",
            claim="Minimal claim",
            method="Survey",
        )
        assert card.confidence == 0.5
        assert card.limitations == []
        assert card.funding_source is None

    def test_confidence_backward_compat_high(self, sample_card: EvidenceCard) -> None:
        """Alte String-Confidence wird zu Float konvertiert."""
        assert sample_card.confidence == 0.8

    def test_confidence_backward_compat_low(self) -> None:
        card = EvidenceCard(
            card_id="ec-low",
            paper_id="test",
            paper_title="Test",
            claim="C",
            method="M",
            confidence="low",
        )
        assert card.confidence == 0.3

    def test_confidence_backward_compat_medium(self) -> None:
        card = EvidenceCard(
            card_id="ec-med",
            paper_id="test",
            paper_title="Test",
            claim="C",
            method="M",
            confidence="medium",
        )
        assert card.confidence == 0.5

    def test_confidence_float_passthrough(self) -> None:
        card = EvidenceCard(
            card_id="ec-f",
            paper_id="test",
            paper_title="Test",
            claim="C",
            method="M",
            confidence=0.72,
        )
        assert card.confidence == 0.72

    def test_confidence_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Unbekannter Confidence-Wert"):
            EvidenceCard(
                card_id="ec-bad",
                paper_id="test",
                paper_title="Test",
                claim="C",
                method="M",
                confidence="invalid",
            )

    def test_metrics_custom_fields(self) -> None:
        metrics = Metrics(custom={"f1_score": 0.91, "auc": 0.95})
        assert metrics.custom["f1_score"] == 0.91
        assert metrics.p_value is None


class TestEvidenceCardPersistence:
    def test_save_creates_files(
        self, sample_card: EvidenceCard, cards_dir: Path
    ) -> None:
        paths = save_evidence_cards([sample_card], cards_dir)
        assert len(paths) == 1
        assert paths[0].exists()
        assert paths[0].name == "ec-001.json"

    def test_save_creates_directory(
        self, sample_card: EvidenceCard, cards_dir: Path
    ) -> None:
        assert not cards_dir.exists()
        save_evidence_cards([sample_card], cards_dir)
        assert cards_dir.exists()

    def test_load_roundtrip(
        self, sample_card: EvidenceCard, cards_dir: Path
    ) -> None:
        save_evidence_cards([sample_card], cards_dir)
        loaded = load_evidence_cards(cards_dir)
        assert len(loaded) == 1
        assert loaded[0].card_id == sample_card.card_id
        assert loaded[0].claim == sample_card.claim
        assert loaded[0].metrics.p_value == sample_card.metrics.p_value

    def test_load_empty_directory(self, cards_dir: Path) -> None:
        cards_dir.mkdir(parents=True)
        assert load_evidence_cards(cards_dir) == []

    def test_load_nonexistent_directory(self, tmp_path: Path) -> None:
        assert load_evidence_cards(tmp_path / "nonexistent") == []

    def test_save_multiple_cards(self, cards_dir: Path) -> None:
        cards = [
            EvidenceCard(
                card_id=f"ec-{i:03d}",
                paper_id=f"doi:10.1234/paper-{i}",
                paper_title=f"Paper {i}",
                claim=f"Claim {i}",
                method="Method",
            )
            for i in range(5)
        ]
        paths = save_evidence_cards(cards, cards_dir)
        assert len(paths) == 5
        loaded = load_evidence_cards(cards_dir)
        assert len(loaded) == 5
