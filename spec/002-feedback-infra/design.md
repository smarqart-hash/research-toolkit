# Design: Feedback Infrastructure

## Architektur

### Datenfluss

```
Evidence Card (confidence: float)
  → Reviewer (DimensionResult + automatable)
    → Draft
      → Citation Tracker (CITATION_USED Events)
        → provenance.jsonl

Experte (manuell)
  → feedback.jsonl (FeedbackEntry)
    → Spaeter: Ranking-Evaluation (Sprint 4+)
```

### Betroffene Dateien

| Datei | Aenderung |
|-------|-----------|
| `src/utils/evidence_card.py` | `confidence: str -> float` + Backward-Compat Validator |
| `src/agents/reviewer.py` | `DimensionResult.automatable: bool` hinzufuegen |
| `src/utils/feedback_logger.py` | **NEU** — Feedback JSONL Logger |
| `src/pipeline/provenance.py` | `track_citations()` Funktion + CITATION_USED Event |
| `config/feedback_schema.json` | **NEU** — JSON Schema fuer Feedback |
| `config/rubrics/automatable.json` | **NEU** — Dimension-Automatable Mapping |

## Datenmodell

### Evidence Card — Confidence Migration

```python
# src/utils/evidence_card.py

from pydantic import field_validator

_CONFIDENCE_MAP: dict[str, float] = {
    "low": 0.3,
    "medium": 0.5,
    "high": 0.8,
}

class EvidenceCard(BaseModel):
    # ... bestehende Felder ...
    confidence: float = 0.5  # 0.0 bis 1.0

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, v: str | float | int) -> float:
        """Backward-Compat: 'low'/'medium'/'high' -> Float."""
        if isinstance(v, str):
            if v in _CONFIDENCE_MAP:
                return _CONFIDENCE_MAP[v]
            raise ValueError(f"Unbekannter Confidence-Wert: {v!r}")
        return float(v)
```

**Serialisierung:** Neue Cards speichern `0.72`, alte Cards mit `"medium"` werden beim Laden zu `0.5`.

### DimensionResult — automatable Flag

```python
# src/agents/reviewer.py

class DimensionResult(BaseModel):
    name: str
    rating: Rating
    comment: str
    confidence: Confidence = Confidence.AUTO
    automatable: bool = True  # NEU — Default True fuer Backward-Compat
```

**Kein Enum** fuer automatable — einfaches Bool reicht. Die Zuordnung
Dimension -> automatable kommt aus Config, nicht aus Code.

### Automatable Config

```json
// config/rubrics/automatable.json
{
  "structure": true,
  "clarity": true,
  "format": true,
  "evidence": true,
  "logic": false,
  "context": false,
  "significance": false
}
```

Reviewer laedt dieses Mapping und setzt `automatable` beim Erstellen
der `DimensionResult`-Instanzen. Unbekannte Dimensionen: Default `true`.

### FeedbackEntry + Logger

```python
# src/utils/feedback_logger.py

from __future__ import annotations
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
import json

class FeedbackEntry(BaseModel):
    """Experten-Feedback zu einem Ranking-Ergebnis."""
    topic: str
    timestamp: datetime = Field(default_factory=datetime.now)
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
        """Liest alle Eintraege, optional gefiltert nach Topic."""
        if not self._path.exists():
            return []
        entries: list[FeedbackEntry] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = FeedbackEntry.model_validate_json(line)
            if topic is None or entry.topic == topic:
                entries = [*entries, entry]
        return entries
```

**Pattern:** Identisch zu `ProvenanceLogger` — append-only JSONL, Pydantic-Validierung,
immutable list-building.

### Citation Tracker

```python
# In src/pipeline/provenance.py (oder eigenes Modul)

import re
import logging

logger = logging.getLogger(__name__)

def track_citations(
    draft_md: str,
    cards: list[EvidenceCard],
) -> list[str]:
    """Findet welche Evidence-Card-Papers im Draft zitiert werden.

    Matching-Strategie:
    - Titel-Substring im Markdown (case-insensitive)
    - Autor-Nachname + Jahr Pattern (z.B. "Smith 2024", "Smith et al. 2024")

    Gibt Liste der zitierten paper_ids zurueck.
    """
    cited_ids: list[str] = []
    draft_lower = draft_md.lower()

    for card in cards:
        title_match = card.paper_title.lower() in draft_lower if card.paper_title else False

        # Autor-Jahr Pattern: "Nachname (2024)" oder "Nachname et al. (2024)"
        author_year_match = False
        if card.authors and card.year:
            first_author = card.authors[0].split()[-1]  # Nachname
            pattern = rf"{re.escape(first_author)}.*{card.year}"
            author_year_match = bool(re.search(pattern, draft_md, re.IGNORECASE))

        if title_match or author_year_match:
            cited_ids = [*cited_ids, card.paper_id]

    if not cited_ids:
        logger.warning("Keine Zitationen im Draft gefunden — 0 CITATION_USED Events")

    return cited_ids
```

**Provenance-Integration:**
```python
# Nach Draft-Generierung aufrufen:
cited_ids = track_citations(draft_markdown, evidence_cards)
for paper_id in cited_ids:
    provenance.log_action(
        phase="synthesis",
        agent="citation-tracker",
        action="CITATION_USED",
        evidence_card_id=paper_id,
        metadata={"cited_in_draft": True},
    )
```

## Integration in bestehende Module

### `reviewer.py` — automatable setzen

```python
# In der Review-Logik, wo DimensionResults erstellt werden:

_AUTOMATABLE_CONFIG = _load_automatable_config()  # config/rubrics/automatable.json

def _create_dimension_result(name: str, rating: Rating, comment: str) -> DimensionResult:
    return DimensionResult(
        name=name,
        rating=rating,
        comment=comment,
        automatable=_AUTOMATABLE_CONFIG.get(name.lower(), True),
    )
```

### `drafting.py` — Citation Tracking nach Draft

```python
# Am Ende von generate_draft() oder im Pipeline-Orchestrator:

if evidence_cards:
    cited_ids = track_citations(draft_markdown, evidence_cards)
    # Provenance Events loggen (siehe oben)
```

## Error Handling

| Szenario | Verhalten | Code |
|----------|-----------|------|
| Alte Card `confidence: "high"` | Validator -> `0.8` | `_normalize_confidence` |
| `confidence: "invalid"` | `ValueError` raised | Pydantic Validation |
| `confidence: 1.5` (out of range) | Akzeptiert (kein Clamp) | Bewusst: LLM kann >1.0 liefern |
| `automatable.json` fehlt | Default: alle `True` | Graceful Degradation |
| `feedback.jsonl` nicht vorhanden | Wird bei erstem Write erstellt | `mkdir(parents=True)` |
| Draft ohne Zitate | Warning + leere cited_ids | `logger.warning()` |
| Evidence Card ohne paper_title/authors | Kein Match moeglich, uebersprungen | Silent Skip |

## Adversarial Check

1. **Brauchen wir numerische Confidence jetzt?**
   Ja — Sprint 4 nutzt Confidence-Schwellen fuer Borderline-Detection.
   Kategorisch ("medium") erlaubt keine Schwellwerte.

2. **Ist automatable zu simpel als Bool?**
   Fuer Sprint 4 reicht Bool. Falls spaeter Abstufungen noetig:
   Migration `bool -> float` analog zu Confidence moeglich.

3. **Citation Tracking via Titel-Matching — zu fragil?**
   Ja, Titel koennen gekuerzt oder umformuliert sein. Aber: kostenloses
   Signal (keine API-Calls, keine Latenz). False Negatives sind akzeptabel,
   False Positives sind selten (Titel sind spezifisch genug).

4. **Feedback-Schema als eigene JSONL statt in Provenance?**
   Ja, bewusste Trennung: Provenance = Pipeline-interne Events,
   Feedback = externe Experten-Bewertungen. Verschiedene Konsumenten.
