"""Pydantic-Schemas fuer den Review-Agent.

Definiert den Output-Kontrakt: Dimensionen, Issues, Verdict.
Alle Schemas sind immutable (frozen) und serialisierbar.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, computed_field


class Rating(str, Enum):
    """Ordinale Bewertungslabels statt numerischer Scores."""

    STARK = "stark"
    ANGEMESSEN = "angemessen"
    AUSBAUFAEHIG = "ausbaufaehig"
    KRITISCH = "kritisch"


class Severity(str, Enum):
    """Issue-Schweregrade mit klaren Abgrenzungen."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IssueCategory(str, Enum):
    """Kategorien fuer gefundene Issues."""

    STRUCTURE = "Structure"
    EVIDENCE = "Evidence"
    LOGIC = "Logic"
    CONTEXT = "Context"
    CLARITY = "Clarity"
    FORMAT = "Format"


class Confidence(str, Enum):
    """Vertrauensniveau der Bewertung."""

    AUTO = "auto"
    REQUIRES_HUMAN = "requires_human"


class Verdict(str, Enum):
    """Gesamturteil nach Review."""

    READY = "READY"
    REVISION_NEEDED = "REVISION_NEEDED"
    MAJOR_REWORK = "MAJOR_REWORK"


class DimensionResult(BaseModel):
    """Bewertung einer einzelnen Dimension."""

    name: str
    rating: Rating
    comment: str
    confidence: Confidence = Confidence.AUTO


class HumanFlag(BaseModel):
    """Beobachtung die menschliche Beurteilung erfordert."""

    dimension: str
    confidence: Confidence = Confidence.REQUIRES_HUMAN
    observation: str
    location: str


class ReviewIssue(BaseModel):
    """Ein konkretes Issue im Dokument."""

    severity: Severity
    category: IssueCategory
    location: str
    problem: str
    suggestion: str
    dimension: str

    @computed_field
    @property
    def issue_id(self) -> str:
        """Hash-basierte ID fuer stabilen Delta-Vergleich."""
        content = f"{self.location}|{self.problem[:50]}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]


class ReviewDelta(BaseModel):
    """Delta-Vergleich zwischen zwei Review-Iterationen."""

    resolved_ids: list[str] = Field(default_factory=list)
    new_ids: list[str] = Field(default_factory=list)
    open_ids: list[str] = Field(default_factory=list)
    summary: str = ""


class ReviewResult(BaseModel):
    """Gesamtergebnis eines Reviews."""

    document: str
    venue: str
    rubric: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    iteration: int = 1
    dimensions: list[DimensionResult] = Field(default_factory=list)
    human_flags: list[HumanFlag] = Field(default_factory=list)
    issues: list[ReviewIssue] = Field(default_factory=list)
    delta: ReviewDelta | None = None

    @computed_field
    @property
    def verdict(self) -> Verdict:
        """Berechnet Verdict aus Issues."""
        critical_count = sum(1 for i in self.issues if i.severity == Severity.CRITICAL)
        high_count = sum(1 for i in self.issues if i.severity == Severity.HIGH)
        if critical_count >= 3:
            return Verdict.MAJOR_REWORK
        if critical_count >= 1 or high_count >= 3:
            return Verdict.REVISION_NEEDED
        return Verdict.READY


def compute_delta(current: ReviewResult, previous: ReviewResult) -> ReviewDelta:
    """Berechnet Delta zwischen zwei Reviews auf Issue-Ebene."""
    current_ids = {i.issue_id for i in current.issues}
    previous_ids = {i.issue_id for i in previous.issues}

    resolved = sorted(previous_ids - current_ids)
    new = sorted(current_ids - previous_ids)
    still_open = sorted(current_ids & previous_ids)

    summary = (
        f"{len(resolved)} von {len(previous_ids)} Issues geloest, "
        f"{len(new)} neue, {len(still_open)} offen"
    )

    return ReviewDelta(
        resolved_ids=resolved,
        new_ids=new,
        open_ids=still_open,
        summary=summary,
    )


def save_review(result: ReviewResult, directory: Path) -> Path:
    """Speichert Review-Ergebnis als JSON."""
    directory.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    doc_stem = Path(result.document).stem
    filename = f"review-{date_str}-{doc_stem}.json"
    path = directory / filename
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_latest_review(document: str, directory: Path) -> ReviewResult | None:
    """Laedt den neuesten Review fuer ein Dokument."""
    if not directory.exists():
        return None
    doc_stem = Path(document).stem
    reviews = sorted(directory.glob(f"review-*-{doc_stem}.json"), reverse=True)
    if not reviews:
        return None
    return ReviewResult.model_validate_json(reviews[0].read_text(encoding="utf-8"))
