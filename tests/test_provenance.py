"""Tests fuer den Provenance Logger."""

from pathlib import Path

import pytest

from pipeline.provenance import ProvenanceEntry, ProvenanceLogger


@pytest.fixture
def logger(tmp_path: Path) -> ProvenanceLogger:
    return ProvenanceLogger(path=tmp_path / "provenance.jsonl")


class TestProvenanceLogger:
    def test_log_creates_file(self, logger: ProvenanceLogger) -> None:
        logger.log_action(
            phase="ideation",
            agent="novelty-scout",
            action="search_papers",
            source="exa:query-123",
        )
        assert logger._path.exists()

    def test_log_appends_entries(self, logger: ProvenanceLogger) -> None:
        logger.log_action(phase="ideation", agent="scout", action="search")
        logger.log_action(phase="ideation", agent="scout", action="score")
        lines = logger._path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    def test_read_all_returns_entries(self, logger: ProvenanceLogger) -> None:
        logger.log_action(
            phase="ingestion",
            agent="parser",
            action="parse_pdf",
            source="doi:10.1234/test",
            claim="Methode X verbessert Y",
            evidence_card_id="ec-001",
        )
        entries = logger.read_all()
        assert len(entries) == 1
        assert entries[0].phase == "ingestion"
        assert entries[0].agent == "parser"
        assert entries[0].evidence_card_id == "ec-001"

    def test_read_all_empty_file(self, tmp_path: Path) -> None:
        logger = ProvenanceLogger(path=tmp_path / "empty.jsonl")
        assert logger.read_all() == []

    def test_filter_by_phase(self, logger: ProvenanceLogger) -> None:
        logger.log_action(phase="ideation", agent="scout", action="search")
        logger.log_action(phase="ingestion", agent="parser", action="parse")
        logger.log_action(phase="ideation", agent="scout", action="score")
        ideation_entries = logger.filter_by_phase("ideation")
        assert len(ideation_entries) == 2

    def test_filter_by_agent(self, logger: ProvenanceLogger) -> None:
        logger.log_action(phase="review", agent="citation-verifier", action="verify")
        logger.log_action(phase="review", agent="method-critic", action="critique")
        logger.log_action(phase="review", agent="citation-verifier", action="flag")
        verifier_entries = logger.filter_by_agent("citation-verifier")
        assert len(verifier_entries) == 2

    def test_entry_has_timestamp(self, logger: ProvenanceLogger) -> None:
        logger.log_action(phase="test", agent="test", action="test")
        entries = logger.read_all()
        assert entries[0].timestamp is not None

    def test_log_with_metadata(self, logger: ProvenanceLogger) -> None:
        logger.log_action(
            phase="experiment",
            agent="data-scientist",
            action="run_experiment",
            metadata={"seed": 42, "model": "linear_regression"},
        )
        entries = logger.read_all()
        assert entries[0].metadata["seed"] == 42
