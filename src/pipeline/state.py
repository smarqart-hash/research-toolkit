"""State Machine fuer die 6-Phasen Research Pipeline.

Checkpointet nach jeder Phase. Resume nach Absturz.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class Phase(str, Enum):
    """Die 6 Phasen der Forschungspipeline."""

    IDEATION = "ideation"
    INGESTION = "ingestion"
    EXPERIMENT = "experiment"
    SYNTHESIS = "synthesis"
    REVIEW = "review"
    TYPESETTING = "typesetting"
    COMPLETED = "completed"


class PhaseStatus(str, Enum):
    """Status einer einzelnen Phase."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    HALTED_FOR_HUMAN = "halted_for_human"
    COMPLETED = "completed"
    FAILED = "failed"


class SynthesisSubPhase(str, Enum):
    """Sub-Phasen innerhalb der SYNTHESIS-Phase fuer den Review-Loop."""

    DRAFTING = "drafting"
    REVIEWING = "reviewing"
    REVISING = "revising"
    CONSISTENCY_CHECK = "consistency_check"
    COMPLETED = "completed"


class HitlGate(BaseModel):
    """Human-in-the-Loop Entscheidungspunkt."""

    gate_id: str
    question: str
    decision: str | None = None
    decided_at: str | None = None


class PhaseRecord(BaseModel):
    """Zustand einer einzelnen Phase."""

    status: PhaseStatus = PhaseStatus.NOT_STARTED
    started_at: str | None = None
    completed_at: str | None = None
    artifacts: list[str] = Field(default_factory=list)
    hitl_gate: HitlGate | None = None
    error: str | None = None
    sub_phase: str | None = None


class ResearchState(BaseModel):
    """Gesamtzustand der Forschungspipeline."""

    project_id: str
    title: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    current_phase: Phase = Phase.IDEATION
    venue_profile: str | None = None
    phases: dict[str, PhaseRecord] = Field(default_factory=lambda: {
        phase.value: PhaseRecord() for phase in Phase if phase != Phase.COMPLETED
    })

    def start_phase(self, phase: Phase) -> None:
        """Markiert eine Phase als gestartet.

        Raises:
            ValueError: Wenn Phase bereits IN_PROGRESS ist.
        """
        record = self.phases[phase.value]
        if record.status == PhaseStatus.IN_PROGRESS:
            raise ValueError(
                f"Phase {phase.value} ist bereits IN_PROGRESS — "
                f"zuerst complete_phase() oder fail_phase() aufrufen"
            )
        record.status = PhaseStatus.IN_PROGRESS
        record.started_at = datetime.now(timezone.utc).isoformat()
        self.current_phase = phase

    def complete_phase(self, phase: Phase, artifacts: list[str] | None = None) -> None:
        """Markiert eine Phase als abgeschlossen.

        Raises:
            ValueError: Wenn Phase nicht IN_PROGRESS ist.
        """
        record = self.phases[phase.value]
        if record.status != PhaseStatus.IN_PROGRESS:
            raise ValueError(
                f"Phase {phase.value} kann nicht abgeschlossen werden — "
                f"Status ist {record.status.value}, erwartet: in_progress"
            )
        record.status = PhaseStatus.COMPLETED
        record.completed_at = datetime.now(timezone.utc).isoformat()
        if artifacts:
            record.artifacts = [*record.artifacts, *artifacts]

    def halt_for_human(self, phase: Phase, gate: HitlGate) -> None:
        """Haelt Pipeline fuer menschliche Entscheidung an."""
        record = self.phases[phase.value]
        record.status = PhaseStatus.HALTED_FOR_HUMAN
        record.hitl_gate = gate

    def resolve_hitl(self, phase: Phase, decision: str) -> None:
        """Loest einen HITL-Gate auf."""
        record = self.phases[phase.value]
        if record.hitl_gate is None:
            raise ValueError(f"Phase {phase.value} hat kein offenes HITL-Gate")
        record.hitl_gate.decision = decision
        record.hitl_gate.decided_at = datetime.now(timezone.utc).isoformat()
        record.status = PhaseStatus.IN_PROGRESS

    def fail_phase(self, phase: Phase, error: str) -> None:
        """Markiert eine Phase als fehlgeschlagen.

        Raises:
            ValueError: Wenn Phase nicht IN_PROGRESS ist.
        """
        record = self.phases[phase.value]
        if record.status != PhaseStatus.IN_PROGRESS:
            raise ValueError(
                f"Phase {phase.value} kann nicht als fehlgeschlagen markiert werden — "
                f"Status ist {record.status.value}, erwartet: in_progress"
            )
        record.status = PhaseStatus.FAILED
        record.error = error


def save_state(state: ResearchState, path: Path) -> None:
    """Speichert State atomar auf Festplatte.

    Fallback auf os.replace() bei PermissionError (Windows-Kompatibilitaet).
    """
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    try:
        tmp_path.replace(path)
    except PermissionError:
        os.replace(str(tmp_path), str(path))


def load_state(path: Path) -> ResearchState | None:
    """Laedt State von Festplatte. None wenn nicht vorhanden."""
    if not path.exists():
        return None
    return ResearchState.model_validate_json(path.read_text(encoding="utf-8"))


STATE_FILE = Path("research_state.json")
