"""Tests fuer die State Machine."""

import json
from pathlib import Path

import pytest

from pipeline.state import (
    HitlGate,
    Phase,
    PhaseStatus,
    ResearchState,
    load_state,
    save_state,
)


@pytest.fixture
def state() -> ResearchState:
    return ResearchState(project_id="test-001", title="Test-Forschungsprojekt")


@pytest.fixture
def tmp_state_file(tmp_path: Path) -> Path:
    return tmp_path / "research_state.json"


class TestResearchState:
    def test_initial_state_has_all_phases(self, state: ResearchState) -> None:
        assert len(state.phases) == 6
        for phase in Phase:
            if phase != Phase.COMPLETED:
                assert phase.value in state.phases

    def test_initial_phase_is_ideation(self, state: ResearchState) -> None:
        assert state.current_phase == Phase.IDEATION

    def test_all_phases_start_not_started(self, state: ResearchState) -> None:
        for record in state.phases.values():
            assert record.status == PhaseStatus.NOT_STARTED

    def test_start_phase(self, state: ResearchState) -> None:
        state.start_phase(Phase.IDEATION)
        record = state.phases["ideation"]
        assert record.status == PhaseStatus.IN_PROGRESS
        assert record.started_at is not None
        assert state.current_phase == Phase.IDEATION

    def test_complete_phase_with_artifacts(self, state: ResearchState) -> None:
        state.start_phase(Phase.IDEATION)
        state.complete_phase(Phase.IDEATION, artifacts=["novelty_report.md"])
        record = state.phases["ideation"]
        assert record.status == PhaseStatus.COMPLETED
        assert record.completed_at is not None
        assert "novelty_report.md" in record.artifacts

    def test_complete_phase_without_artifacts(self, state: ResearchState) -> None:
        state.start_phase(Phase.IDEATION)
        state.complete_phase(Phase.IDEATION)
        record = state.phases["ideation"]
        assert record.status == PhaseStatus.COMPLETED
        assert record.artifacts == []

    def test_halt_for_human(self, state: ResearchState) -> None:
        gate = HitlGate(
            gate_id="pivot-decision",
            question="Soll die Hypothese pivotiert werden?",
        )
        state.start_phase(Phase.IDEATION)
        state.halt_for_human(Phase.IDEATION, gate)
        record = state.phases["ideation"]
        assert record.status == PhaseStatus.HALTED_FOR_HUMAN
        assert record.hitl_gate is not None
        assert record.hitl_gate.decision is None

    def test_resolve_hitl(self, state: ResearchState) -> None:
        gate = HitlGate(
            gate_id="pivot-decision",
            question="Soll die Hypothese pivotiert werden?",
        )
        state.start_phase(Phase.IDEATION)
        state.halt_for_human(Phase.IDEATION, gate)
        state.resolve_hitl(Phase.IDEATION, "Ja, pivotieren auf Sub-Topic X")
        record = state.phases["ideation"]
        assert record.status == PhaseStatus.IN_PROGRESS
        assert record.hitl_gate.decision == "Ja, pivotieren auf Sub-Topic X"
        assert record.hitl_gate.decided_at is not None

    def test_resolve_hitl_without_gate_raises(self, state: ResearchState) -> None:
        state.start_phase(Phase.IDEATION)
        with pytest.raises(ValueError, match="kein offenes HITL-Gate"):
            state.resolve_hitl(Phase.IDEATION, "decision")

    def test_fail_phase(self, state: ResearchState) -> None:
        state.start_phase(Phase.INGESTION)
        state.fail_phase(Phase.INGESTION, "PDF Parsing fehlgeschlagen")
        record = state.phases["ingestion"]
        assert record.status == PhaseStatus.FAILED
        assert record.error == "PDF Parsing fehlgeschlagen"


class TestStatePersistence:
    def test_save_and_load(self, state: ResearchState, tmp_state_file: Path) -> None:
        state.start_phase(Phase.IDEATION)
        state.complete_phase(Phase.IDEATION, artifacts=["report.md"])
        save_state(state, tmp_state_file)

        loaded = load_state(tmp_state_file)
        assert loaded is not None
        assert loaded.project_id == "test-001"
        assert loaded.phases["ideation"].status == PhaseStatus.COMPLETED
        assert "report.md" in loaded.phases["ideation"].artifacts

    def test_load_nonexistent_returns_none(self, tmp_path: Path) -> None:
        result = load_state(tmp_path / "nonexistent.json")
        assert result is None

    def test_save_is_atomic(self, state: ResearchState, tmp_state_file: Path) -> None:
        save_state(state, tmp_state_file)
        # .tmp Datei darf nach save nicht mehr existieren
        assert not tmp_state_file.with_suffix(".tmp").exists()
        assert tmp_state_file.exists()

    def test_roundtrip_preserves_hitl_gate(
        self, state: ResearchState, tmp_state_file: Path
    ) -> None:
        gate = HitlGate(gate_id="test-gate", question="Test?")
        state.start_phase(Phase.EXPERIMENT)
        state.halt_for_human(Phase.EXPERIMENT, gate)
        save_state(state, tmp_state_file)

        loaded = load_state(tmp_state_file)
        assert loaded is not None
        assert loaded.phases["experiment"].hitl_gate.gate_id == "test-gate"
