# Tasks: Feedback Infrastructure (002)

**Geschaetzte Dauer:** ~1 Tag (6-8h Implementation + Tests)
**Branch:** `feature/002-feedback-infra`

---

## Phase 1: Datenmodell-Aenderungen (keine Abhaengigkeiten untereinander)

- [ ] **T1: Evidence Card Confidence Migration** (~1.5h)
  `src/utils/evidence_card.py` — `confidence: str` -> `confidence: float`
  Pydantic `@field_validator` fuer Backward-Compat: `"low"->0.3`, `"medium"->0.5`, `"high"->0.8`.
  Tests: alte JSON-Files laden, neue Cards mit Float, ungueltige Strings -> ValueError.

- [ ] **T2: DimensionResult automatable Flag** (~1h)
  `src/agents/reviewer.py` — `automatable: bool = True` zu `DimensionResult` hinzufuegen.
  `config/rubrics/automatable.json` erstellen mit Dimension-Mapping.
  Reviewer setzt Flag beim Erstellen der DimensionResults.
  Tests: Default True, Config-Mapping, unbekannte Dimension -> True.

## Phase 2: Neue Module (abhaengig von Phase 1 nur fuer T4)

- [ ] **T3: Feedback Logger** (~1.5h)
  `src/utils/feedback_logger.py` — `FeedbackEntry` Modell + `FeedbackLogger` Klasse.
  `config/feedback_schema.json` — JSON Schema.
  Append-only JSONL, gleicher Pattern wie `provenance.py`.
  Tests: Write + Read Round-Trip, Topic-Filter, leere Datei, Verzeichnis-Erstellung.

- [ ] **T4: Citation Tracker** (~2h)
  `src/pipeline/provenance.py` — `track_citations()` Funktion.
  Titel-Matching + Autor-Jahr-Pattern im Draft-Markdown.
  `CITATION_USED` Events in provenance.jsonl loggen.
  Tests: Titel-Match, Autor-Jahr-Match, kein Match -> Warning,
  Edge Cases (fehlender Titel, fehlende Autoren, leerer Draft).

## Phase 3: Integration (abhaengig von Phase 1+2)

- [ ] **T5: Reviewer-Integration** (~0.5h)
  `src/agents/reviewer.py` — `automatable.json` laden, Flag bei DimensionResult-Erstellung setzen.
  Graceful Degradation: Config fehlt -> alle True.
  Tests: Review mit Config, Review ohne Config.

- [ ] **T6: Draft-Integration Citation Tracking** (~1h)
  `src/agents/drafting.py` oder Pipeline-Orchestrator — `track_citations()` nach Draft aufrufen.
  Provenance Events loggen.
  Tests: Mock-Draft mit Zitaten, Mock-Draft ohne Zitaten.

## Phase 4: Qualitaetssicherung

- [ ] **T7: Coverage + Ruff + Regression** (~0.5h)
  `pytest tests/ -v` — alle 248+ Tests passing.
  `ruff check src/utils/feedback_logger.py src/utils/evidence_card.py`
  Coverage >= 90% fuer geaenderte/neue Module.
  Backward-Compat: alte Evidence Card JSONs laden korrekt.

---

## Abhaengigkeits-Graph

```
T1 ──────── T5 ──┐
T2 ──────── T5   │
T3 ────────────── T7
T4 ──── T6 ────── T7
```

Phase 1 (T1, T2) kann parallel.
Phase 2 (T3, T4) kann parallel.
Phase 3 (T5, T6) kann parallel (verschiedene Dateien).
T7 am Ende.

## Parallelisierungs-Hinweis

Maximale Parallelitaet:
- **Runde 1:** T1 + T2 (parallel, verschiedene Dateien)
- **Runde 2:** T3 + T4 (parallel, verschiedene Dateien)
- **Runde 3:** T5 + T6 (parallel, verschiedene Dateien)
- **Runde 4:** T7 (sequenziell, Gesamtpruefung)
