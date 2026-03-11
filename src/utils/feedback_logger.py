"""Feedback Logger — Experten-Feedback zu Ranking-Ergebnissen.

Append-only JSONL, gleiches Pattern wie provenance.py.
Sammelt menschliches Feedback fuer spaetere Ranking-Evaluation.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FeedbackEntry(BaseModel):
    """Experten-Feedback zu einem Ranking-Ergebnis."""

    topic: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    ranking_method: str
    top_k_shown: int
    expert_relevant: list[str] = Field(default_factory=list)
    expert_irrelevant: list[str] = Field(default_factory=list)
    notes: str = ""


class FeedbackLogger:
    """Append-only JSONL Logger fuer Experten-Feedback."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path("output/feedback.jsonl")

    def log_feedback(self, entry: FeedbackEntry) -> None:
        """Validiert und appended einen Feedback-Eintrag."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")

    def read_feedback(self, topic: str | None = None) -> list[FeedbackEntry]:
        """Liest alle Eintraege, optional gefiltert nach Topic.

        Korrupte Zeilen werden uebersprungen und geloggt.
        """
        if not self._path.exists():
            return []
        entries: list[FeedbackEntry] = []
        for line_no, line in enumerate(self._path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                entry = FeedbackEntry.model_validate_json(line)
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning("Korrupte Zeile %d in %s: %s", line_no, self._path, exc)
                continue
            if topic is None or entry.topic == topic:
                entries.append(entry)
        return entries
