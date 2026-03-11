# Requirements: Feedback Infrastructure

**Scope:** Backend (Python-Module) | **Erstellt:** 2026-03-10

## Zweck

Grundlagen fuer Qualitaetsmessung in der Pipeline. Ohne diese Infrastruktur
koennen spaetere Sprints (Review Loop, Ranking Feedback) ihre Wirkung nicht
messen. 4 unabhaengige Aenderungen, die einzeln Wert liefern:

1. **Numerische Confidence** — messbar statt kategorisch
2. **Frontier-Split** — ehrlich kennzeichnen was automatisierbar ist
3. **Feedback-Schema** — ab sofort Experten-Feedback sammeln
4. **Implizites Tracking** — kostenloses Signal (welche Papers zitiert werden)

## Aenderung 1: Numerische Confidence in Evidence Cards

### Betroffenes Modul: `src/utils/evidence_card.py`

**Ist (Zeile 37):**
```python
confidence: str = "medium"  # low, medium, high
```

**Soll:**
```python
confidence: float = 0.5  # 0.0 bis 1.0
```

**Anforderungen:**
- Pydantic v2 Validator fuer Backward-Kompatibilitaet:
  `"low" -> 0.3`, `"medium" -> 0.5`, `"high" -> 0.8`
- Alte JSON-Files mit `confidence: "medium"` laden weiterhin korrekt
- Neue Evidence Cards speichern `confidence: 0.72` (Float)
- Prompt-Aenderung in relevanten Skills: "Rate confidence 0.0-1.0"

### Nicht in Scope
- Kein automatisches Confidence-Kalibrierung (das waere F10)
- Keine UI-Aenderung (CLI zeigt weiterhin Wert an, jetzt als Float)

## Aenderung 2: Dimension-Confidence Split (automatable-Flag)

### Betroffenes Modul: `src/agents/reviewer.py`

**Ist (Zeilen 62-68):**
```python
class DimensionResult(BaseModel):
    name: str
    rating: Rating
    comment: str
    confidence: Confidence = Confidence.AUTO
```

**Soll:**
```python
class DimensionResult(BaseModel):
    name: str
    rating: Rating
    comment: str
    confidence: Confidence = Confidence.AUTO
    automatable: bool = True  # NEU
```

**Mapping:**
| Dimension | automatable | Begruendung |
|-----------|------------|-------------|
| Structure | True | Regelbasiert pruefbar |
| Clarity | True | Sprachliche Analyse |
| Format | True | Template-Matching |
| Evidence | True (teilweise) | Zitat-Zaehlung, nicht Korrektheit |
| Logic | False | Argumentationslogik braucht Domaenwissen |
| Context | False | Einordnung braucht Feld-Expertise |
| Significance | False | Intrinsisch subjektiv |

**Anforderungen:**
- Default `True` (bestehende Dimensionen aendern sich nicht)
- Non-automatable Dimensionen: Sprint 4 nutzt dieses Flag fuer
  Self-Consistency Probe (nur bei `automatable=False`)
- Mapping wird in `config/rubrics/` hinterlegt (nicht hardcoded)

## Aenderung 3: Feedback Schema

### Neues File: `config/feedback_schema.json`

**Format:**
```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["topic", "timestamp", "ranking_method", "top_k_shown"],
  "properties": {
    "topic": { "type": "string" },
    "timestamp": { "type": "string", "format": "date-time" },
    "ranking_method": { "type": "string" },
    "top_k_shown": { "type": "integer" },
    "expert_relevant": { "type": "array", "items": { "type": "string" } },
    "expert_irrelevant": { "type": "array", "items": { "type": "string" } },
    "notes": { "type": "string" }
  }
}
```

### Neues Modul: `src/utils/feedback_logger.py`

**Anforderungen:**
- Append-only JSONL (gleiches Pattern wie `provenance.py`)
- Default-Pfad: `output/feedback.jsonl`
- `log_feedback(entry: FeedbackEntry)` — validiert gegen Schema, appended
- `read_feedback(topic?: str) -> list[FeedbackEntry]` — liest + optional filtert
- Pydantic-Modell `FeedbackEntry` mit den Schema-Feldern

### Nicht in Scope
- Keine CLI-Integration (manuell oder per Script befuellt)
- Kein automatisches Feedback-Sammeln (das waere Sprint 4+)

## Aenderung 4: Implizites Citation-Tracking

### Betroffenes Modul: `src/pipeline/provenance.py`

**Neuer Event-Typ:** `CITATION_USED`

**Anforderungen:**
- Nach Draft-Generierung: Abgleich welche `paper_id`s aus Evidence Cards
  im Draft-Markdown tatsaechlich zitiert werden
- Neuer Event in provenance.jsonl:
  ```json
  {
    "phase": "synthesis",
    "agent": "citation-tracker",
    "action": "CITATION_USED",
    "evidence_card_id": "paper_123",
    "metadata": {"cited_in_sections": ["introduction", "related_work"]}
  }
  ```
- Tracking-Funktion: `track_citations(draft_md: str, cards: list[EvidenceCard]) -> list[str]`
  gibt Liste der zitierten paper_ids zurueck
- Laeuft automatisch nach Draft, kein User-Input noetig

### Nicht in Scope
- Kein Full-Text-Matching (nur Title/Author/Year-Matching im Markdown)
- Keine Bewertung ob richtig zitiert (das waere F9)

## Error Cases

| Bedingung | Verhalten |
|-----------|-----------|
| Alte Evidence Card mit `confidence: "high"` | Validator konvertiert zu `0.8` |
| Unbekannter Confidence-String | `ValueError` mit klarer Meldung |
| `feedback.jsonl` existiert nicht | Wird beim ersten `log_feedback()` erstellt |
| Draft ohne Zitate | `CITATION_USED` Events: leere Liste, Warning loggen |
| Provenance-File locked | Retry-Pattern wie bestehend in `provenance.py` |

## Erfolgskriterien

- [ ] Alte Evidence Cards (confidence: str) laden fehlerfrei
- [ ] Neue Evidence Cards: `confidence: float` (0.0-1.0)
- [ ] `DimensionResult.automatable: bool` vorhanden, Default True
- [ ] Automatable-Mapping in `config/rubrics/` konfigurierbar
- [ ] `config/feedback_schema.json` valides JSON Schema
- [ ] `feedback.jsonl` wird korrekt geschrieben + gelesen
- [ ] `CITATION_USED` Events in provenance.jsonl nach Draft
- [ ] Alle 248+ bestehenden Tests passing (Regression)
- [ ] >= 90% Coverage fuer neue Module
- [ ] Zero neue Dependencies

## Nicht in diesem Sprint (Scope Guard)

- [x] Keine CLI-Aenderungen
- [x] Kein automatisches Feedback-Sammeln
- [x] Keine Confidence-Kalibrierung gegen Ground Truth
- [x] Kein Review Loop (das ist Sprint 4)
- [x] Keine Aenderung am Ranking oder Screening
- [x] Kein neues Package

## Dependency Check Ergebnisse

| Check | Ergebnis |
|-------|----------|
| `evidence_card.confidence` | Zeile 37: `str = "medium"` — muss zu `float` migriert werden |
| `DimensionResult` | Zeilen 62-68: kein `automatable`-Feld — muss hinzugefuegt werden |
| `Confidence` Enum | Zeilen 47-51: `AUTO`, `REQUIRES_HUMAN` — bleibt unveraendert |
| `provenance.py` | Flexible Strings (phase/agent/action) — neuer Event-Typ trivial |
| `config/feedback*` | Existiert nicht — muss neu erstellt werden |
| Bestehende Tests | 37 Tests in evidence_card, reviewer, provenance — muessen erweitert werden |
| Libraries | Nur Pydantic v2 + Standard-Lib — keine neue Dependency |
| Breaking Changes | Nur `confidence: str -> float` — Backward-Compat via Validator |
