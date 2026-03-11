"""Evidence Card Schema — Komprimierte Paper-Extrakte.

Statt Volltext-PDFs an den Drafting-Agent zu geben,
extrahieren wir strukturierte Evidence Cards (Token-effizient).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class Metrics(BaseModel):
    """Quantitative Metriken aus einem Paper."""

    p_value: float | None = None
    effect_size: float | None = None
    confidence_interval: tuple[float, float] | None = None
    sample_size: int | None = None
    custom: dict[str, float] = Field(default_factory=dict)


_CONFIDENCE_MAP: dict[str, float] = {
    "low": 0.3,
    "medium": 0.5,
    "high": 0.8,
}


class EvidenceCard(BaseModel):
    """Strukturierte Zusammenfassung einer Kernaussage aus einem Paper."""

    card_id: str
    paper_id: str  # DOI, arXiv ID, oder interner Identifier
    paper_title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    claim: str
    method: str
    metrics: Metrics = Field(default_factory=Metrics)
    limitations: list[str] = Field(default_factory=list)
    confidence: float = 0.5  # 0.0 bis 1.0
    source_section: str | None = None
    tags: list[str] = Field(default_factory=list)
    funding_source: str | None = None  # Bias-Scoring (aus Adversarial Critique)

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, v: str | float | int) -> float:
        """Backward-Compat: 'low'/'medium'/'high' -> Float."""
        if isinstance(v, str):
            if v in _CONFIDENCE_MAP:
                return _CONFIDENCE_MAP[v]
            raise ValueError(
                f"Unbekannter Confidence-Wert: {v!r}. "
                f"Erlaubt: {list(_CONFIDENCE_MAP.keys())} oder Float 0.0-1.0"
            )
        val = float(v)
        if not 0.0 <= val <= 1.0:
            raise ValueError(
                f"Confidence muss zwischen 0.0 und 1.0 liegen, war: {val}"
            )
        return val


def save_evidence_cards(cards: list[EvidenceCard], directory: Path) -> list[Path]:
    """Speichert Evidence Cards als einzelne JSON-Dateien."""
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for card in cards:
        path = directory / f"{card.card_id}.json"
        path.write_text(card.model_dump_json(indent=2), encoding="utf-8")
        paths = [*paths, path]
    return paths


def load_evidence_cards(directory: Path) -> list[EvidenceCard]:
    """Laedt alle Evidence Cards aus einem Verzeichnis."""
    if not directory.exists():
        return []
    cards = []
    for path in sorted(directory.glob("*.json")):
        card = EvidenceCard.model_validate_json(path.read_text(encoding="utf-8"))
        cards = [*cards, card]
    return cards
