"""Tests fuer Robustheit-Fixes (Audit Task 3).

Deckt ab: JSONL-Parsing, Input-Validierung, Edge Cases, State-Transitions.
"""

from __future__ import annotations

import json

import pytest

from src.agents.paper_ranker import UnifiedPaper
from src.pipeline.provenance import ProvenanceEntry, ProvenanceLogger
from src.pipeline.state import Phase, PhaseStatus, ResearchState
from src.utils.feedback_logger import FeedbackEntry, FeedbackLogger


# --- Fix 1: JSONL-Parsing robust ---


class TestProvenanceCorruptLines:
    """Korrupte Zeilen in provenance.jsonl duerfen nicht crashen."""

    def test_read_all_skips_corrupt_line(self, tmp_path):
        """Korrupte Zeile wird uebersprungen, valide bleiben erhalten."""
        jsonl = tmp_path / "provenance.jsonl"
        valid = ProvenanceEntry(phase="test", agent="test", action="test")
        jsonl.write_text(
            valid.model_dump_json() + "\n"
            + "THIS IS NOT JSON\n"
            + valid.model_dump_json() + "\n",
            encoding="utf-8",
        )
        logger = ProvenanceLogger(path=jsonl)
        entries = logger.read_all()
        assert len(entries) == 2

    def test_read_all_empty_file(self, tmp_path):
        """Leere Datei gibt leere Liste zurueck."""
        jsonl = tmp_path / "provenance.jsonl"
        jsonl.write_text("", encoding="utf-8")
        logger = ProvenanceLogger(path=jsonl)
        assert logger.read_all() == []

    def test_read_all_only_corrupt(self, tmp_path):
        """Nur korrupte Zeilen gibt leere Liste zurueck."""
        jsonl = tmp_path / "provenance.jsonl"
        jsonl.write_text("bad line 1\nbad line 2\n", encoding="utf-8")
        logger = ProvenanceLogger(path=jsonl)
        assert logger.read_all() == []


class TestFeedbackCorruptLines:
    """Korrupte Zeilen in feedback.jsonl duerfen nicht crashen."""

    def test_read_feedback_skips_corrupt(self, tmp_path):
        """Korrupte Zeile wird uebersprungen."""
        jsonl = tmp_path / "feedback.jsonl"
        valid = FeedbackEntry(topic="test", ranking_method="heuristic", top_k_shown=10)
        jsonl.write_text(
            valid.model_dump_json() + "\n"
            + "{invalid json\n"
            + valid.model_dump_json() + "\n",
            encoding="utf-8",
        )
        logger = FeedbackLogger(path=jsonl)
        entries = logger.read_feedback()
        assert len(entries) == 2

    def test_read_feedback_only_corrupt(self, tmp_path):
        """Nur korrupte Zeilen gibt leere Liste zurueck."""
        jsonl = tmp_path / "feedback.jsonl"
        jsonl.write_text("not json\n", encoding="utf-8")
        logger = FeedbackLogger(path=jsonl)
        assert logger.read_feedback() == []


# --- Fix 4: dedup_key Fallback fuer leere Titel ---


class TestDedupKeyEmptyTitle:
    """dedup_key muss auch bei leerem Titel funktionieren."""

    def test_empty_title_uses_paper_id(self):
        """Leerer Titel faellt auf paper_id zurueck."""
        paper = UnifiedPaper(paper_id="abc123", title="", source="semantic_scholar")
        assert paper.dedup_key == "id:abc123"

    def test_whitespace_title_uses_paper_id(self):
        """Nur-Whitespace-Titel faellt auf paper_id zurueck."""
        paper = UnifiedPaper(paper_id="xyz", title="   ", source="exa")
        assert paper.dedup_key == "id:xyz"

    def test_normal_title_uses_hash(self):
        """Normaler Titel verwendet Title-Hash."""
        paper = UnifiedPaper(paper_id="abc", title="Deep Learning", source="semantic_scholar")
        assert paper.dedup_key.startswith("title:")

    def test_doi_preferred_over_title(self):
        """DOI hat Vorrang vor Titel."""
        paper = UnifiedPaper(
            paper_id="abc", title="Test", doi="10.1234/test", source="semantic_scholar"
        )
        assert paper.dedup_key == "doi:10.1234/test"


# --- Fix 6: State Machine Transitions ---


class TestStateTransitionValidation:
    """State Machine muss ungueltige Transitions ablehnen."""

    def _make_state(self) -> ResearchState:
        return ResearchState(project_id="test", title="Test")

    def test_start_phase_rejects_already_in_progress(self):
        """Doppeltes start_phase wirft ValueError."""
        state = self._make_state()
        state.start_phase(Phase.IDEATION)
        with pytest.raises(ValueError, match="bereits IN_PROGRESS"):
            state.start_phase(Phase.IDEATION)

    def test_complete_phase_rejects_not_in_progress(self):
        """complete_phase auf NOT_STARTED wirft ValueError."""
        state = self._make_state()
        with pytest.raises(ValueError, match="nicht.*abgeschlossen"):
            state.complete_phase(Phase.IDEATION)

    def test_fail_phase_rejects_not_in_progress(self):
        """fail_phase auf NOT_STARTED wirft ValueError."""
        state = self._make_state()
        with pytest.raises(ValueError, match="nicht.*fehlgeschlagen"):
            state.fail_phase(Phase.IDEATION, "error")

    def test_valid_transition_start_complete(self):
        """Gueltige Transition: start → complete."""
        state = self._make_state()
        state.start_phase(Phase.IDEATION)
        state.complete_phase(Phase.IDEATION)
        record = state.phases[Phase.IDEATION.value]
        assert record.status == PhaseStatus.COMPLETED

    def test_valid_transition_start_fail(self):
        """Gueltige Transition: start → fail."""
        state = self._make_state()
        state.start_phase(Phase.IDEATION)
        state.fail_phase(Phase.IDEATION, "something broke")
        record = state.phases[Phase.IDEATION.value]
        assert record.status == PhaseStatus.FAILED

    def test_complete_after_fail_rejects(self):
        """complete_phase nach fail wirft ValueError."""
        state = self._make_state()
        state.start_phase(Phase.IDEATION)
        state.fail_phase(Phase.IDEATION, "err")
        with pytest.raises(ValueError, match="nicht.*abgeschlossen"):
            state.complete_phase(Phase.IDEATION)
