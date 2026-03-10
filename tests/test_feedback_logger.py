"""Tests fuer den Feedback Logger."""

from pathlib import Path

import pytest

from utils.feedback_logger import FeedbackEntry, FeedbackLogger


@pytest.fixture
def logger(tmp_path: Path) -> FeedbackLogger:
    return FeedbackLogger(path=tmp_path / "feedback.jsonl")


@pytest.fixture
def sample_entry() -> FeedbackEntry:
    return FeedbackEntry(
        topic="AI traffic control",
        ranking_method="specter2_enhanced",
        top_k_shown=20,
        expert_relevant=["paper_1", "paper_3", "paper_7"],
        expert_irrelevant=["paper_12"],
        notes="Gute Abdeckung, aber Paper 5 fehlt",
    )


class TestFeedbackEntry:
    def test_creation_with_defaults(self) -> None:
        entry = FeedbackEntry(
            topic="test",
            ranking_method="heuristic",
            top_k_shown=10,
        )
        assert entry.topic == "test"
        assert entry.expert_relevant == []
        assert entry.expert_irrelevant == []
        assert entry.notes == ""
        assert entry.timestamp  # Auto-generiert

    def test_creation_with_all_fields(self, sample_entry: FeedbackEntry) -> None:
        assert sample_entry.topic == "AI traffic control"
        assert len(sample_entry.expert_relevant) == 3
        assert "paper_12" in sample_entry.expert_irrelevant


class TestFeedbackLogger:
    def test_log_creates_file(
        self, logger: FeedbackLogger, sample_entry: FeedbackEntry
    ) -> None:
        logger.log_feedback(sample_entry)
        assert logger._path.exists()

    def test_log_creates_parent_directory(self, tmp_path: Path) -> None:
        nested_logger = FeedbackLogger(path=tmp_path / "deep" / "nested" / "feedback.jsonl")
        entry = FeedbackEntry(topic="test", ranking_method="heuristic", top_k_shown=5)
        nested_logger.log_feedback(entry)
        assert nested_logger._path.exists()

    def test_log_appends_entries(
        self, logger: FeedbackLogger, sample_entry: FeedbackEntry
    ) -> None:
        logger.log_feedback(sample_entry)
        logger.log_feedback(sample_entry)
        lines = logger._path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    def test_read_all(
        self, logger: FeedbackLogger, sample_entry: FeedbackEntry
    ) -> None:
        logger.log_feedback(sample_entry)
        entries = logger.read_feedback()
        assert len(entries) == 1
        assert entries[0].topic == "AI traffic control"
        assert entries[0].ranking_method == "specter2_enhanced"

    def test_read_empty_file(self, tmp_path: Path) -> None:
        logger = FeedbackLogger(path=tmp_path / "empty.jsonl")
        assert logger.read_feedback() == []

    def test_read_nonexistent_file(self, tmp_path: Path) -> None:
        logger = FeedbackLogger(path=tmp_path / "nonexistent.jsonl")
        assert logger.read_feedback() == []

    def test_filter_by_topic(self, logger: FeedbackLogger) -> None:
        logger.log_feedback(
            FeedbackEntry(topic="topic_a", ranking_method="heuristic", top_k_shown=10)
        )
        logger.log_feedback(
            FeedbackEntry(topic="topic_b", ranking_method="specter2", top_k_shown=20)
        )
        logger.log_feedback(
            FeedbackEntry(topic="topic_a", ranking_method="specter2", top_k_shown=15)
        )

        topic_a = logger.read_feedback(topic="topic_a")
        assert len(topic_a) == 2
        assert all(e.topic == "topic_a" for e in topic_a)

        topic_b = logger.read_feedback(topic="topic_b")
        assert len(topic_b) == 1

    def test_roundtrip_preserves_data(
        self, logger: FeedbackLogger, sample_entry: FeedbackEntry
    ) -> None:
        logger.log_feedback(sample_entry)
        loaded = logger.read_feedback()
        assert loaded[0].topic == sample_entry.topic
        assert loaded[0].expert_relevant == sample_entry.expert_relevant
        assert loaded[0].notes == sample_entry.notes
