"""Provenance Logger — Herkunftskette fuer alle Claims und Aktionen.

Jeder Agent loggt hierhin. Der Citation Verifier prueft dagegen.
Format: JSON Lines (append-only).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


class ProvenanceEntry(BaseModel):
    """Ein einzelner Eintrag in der Herkunftskette."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    phase: str
    agent: str
    action: str
    source: str | None = None
    claim: str | None = None
    evidence_card_id: str | None = None
    metadata: dict | None = None


class ProvenanceLogger:
    """Append-only Logger fuer provenance.jsonl."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or PROVENANCE_FILE
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, entry: ProvenanceEntry) -> None:
        """Schreibt einen Eintrag ans Ende der JSONL-Datei."""
        with self._path.open("a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")

    def log_action(
        self,
        phase: str,
        agent: str,
        action: str,
        *,
        source: str | None = None,
        claim: str | None = None,
        evidence_card_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Convenience-Methode fuer schnelles Logging."""
        entry = ProvenanceEntry(
            phase=phase,
            agent=agent,
            action=action,
            source=source,
            claim=claim,
            evidence_card_id=evidence_card_id,
            metadata=metadata,
        )
        self.log(entry)

    def read_all(self) -> list[ProvenanceEntry]:
        """Liest alle Eintraege. Fuer Citation Verifier und Audit."""
        if not self._path.exists():
            return []
        entries = []
        for line in self._path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                entries = [*entries, ProvenanceEntry.model_validate_json(line)]
        return entries

    def filter_by_phase(self, phase: str) -> list[ProvenanceEntry]:
        """Filtert Eintraege nach Phase."""
        return [e for e in self.read_all() if e.phase == phase]

    def filter_by_agent(self, agent: str) -> list[ProvenanceEntry]:
        """Filtert Eintraege nach Agent."""
        return [e for e in self.read_all() if e.agent == agent]


PROVENANCE_FILE = Path("provenance.jsonl")
