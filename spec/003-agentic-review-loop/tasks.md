# Tasks: Agentic Review Loop (003)

**Geschaetzt:** 10 Tasks, 4 Phasen

## Abhaengigkeitsgraph

```
T1 (Models) ──┐
T2 (Config)  ──┼── T4 (Review-Fn) → T5 (Revise-Fn) → T6 (Loop) → T9 (CLI)
T3 (State)  ──┘                                         │
                   T7 (Consistency) ─────────────────────┘
                   T8 (Provenance) ──────────────────────┘
                                                            T10 (Regression)
```

## Phase 1: Foundation (T1-T3, parallel)

- [ ] **T1: Pydantic-Modelle** — `src/agents/review_loop.py`
  - SubQuestion, SubQuestionResult, CompactIssue, CompactReview
  - RevisionChangelog, ConsistencyResult, ReviseLoopResult
  - Tests: Modell-Konstruktion, computed_field has_blockers, Score-Berechnung
  - ~80 Zeilen Code, ~40 Zeilen Tests

- [ ] **T2: Sub-Fragen Config** — `config/dimensions/sub_questions.json`
  - 9 Sub-Fragen mit Gewichten (Evidence, Structure, Clarity, Logic, Context, Format)
  - `load_sub_questions()` Funktion in review_loop.py
  - Tests: Laden, Fallback bei fehlender Datei, Validierung
  - ~30 Zeilen Code, ~25 Zeilen Tests

- [ ] **T3: State Machine Sub-States** — `src/pipeline/state.py`
  - `SynthesisSubPhase` Enum (DRAFTING, REVIEWING, REVISING, CONSISTENCY_CHECK, COMPLETED)
  - `sub_phase: str | None = None` Feld in PhaseRecord
  - Tests: Sub-Phase setzen/lesen, Backward-Compat (None default)
  - ~15 Zeilen Code, ~20 Zeilen Tests

## Phase 2: Core Functions (T4-T5, sequenziell)

- [ ] **T4: review_for_revision()** — `src/agents/review_loop.py`
  - LLM-Prompt: Sub-Fragen beantworten + CRITICAL/HIGH Issues extrahieren
  - JSON-Parsing der LLM-Antwort mit Fallback
  - Score-Berechnung aus gewichteten Sub-Fragen
  - Nur automatable Dimensionen (Filter via Config)
  - Tests: Mock LLM, JSON-Parse, Score-Berechnung, leere Antwort
  - ~60 Zeilen Code, ~50 Zeilen Tests

- [ ] **T5: revise_draft()** — `src/agents/review_loop.py`
  - LLM-Prompt: Selektive Revision mit Issues als Kontext
  - Changelog-Extraktion aus LLM-Antwort
  - Immutability: neuer String, kein in-place Edit
  - Tests: Mock LLM, Changelog-Parsing, leere Issues → unveraenderter Draft
  - ~50 Zeilen Code, ~40 Zeilen Tests

## Phase 3: Orchestrierung (T6-T8, T7+T8 parallel)

- [ ] **T6: run_revise_loop()** — `src/agents/review_loop.py`
  - Loop-Logik: Review → Score-Check → Revise → Re-Review
  - Konvergenz: max_revisions, Score-Abbruch, keine Issues
  - max_revisions Cap auf 2 (hart)
  - Tests: 0 Issues → sofort fertig, Score sinkt → Abort, 2 Runden → Stop
  - ~50 Zeilen Code, ~60 Zeilen Tests

- [ ] **T7: self_consistency_probe()** — `src/agents/review_loop.py`
  - 3x Review mit T=0.3/0.7/1.0
  - Agreement-Berechnung pro Dimension
  - Flagging bei < 60% Agreement
  - Tests: Mock 3 Reviews, Agreement-Math, Flagging-Logik
  - ~40 Zeilen Code, ~35 Zeilen Tests

- [ ] **T8: Provenance-Integration** — in `run_revise_loop()`
  - Log-Eintraege: REVIEW_COMPLETED, REVISION_APPLIED, CONSISTENCY_CHECK, LOOP_ABORTED
  - Metadata: iteration, score, delta, issues_count
  - Tests: Mock ProvenanceLogger, Eintraege pruefen
  - ~20 Zeilen Code, ~25 Zeilen Tests

## Phase 4: Integration (T9-T10, sequenziell)

- [ ] **T9: CLI Integration** — `cli.py`
  - `--revise` Flag im draft Command
  - `--max-revisions N` (default 2, max 2)
  - Rich-Output: Score pro Runde, Changelog, Consistency-Warnings
  - Tests: CLI-Parameter-Parsing (kein E2E noetig)
  - ~25 Zeilen Code, ~15 Zeilen Tests

- [ ] **T10: Regression + Spec Verify**
  - `pytest tests/ -v` — alle 330+ bestehenden Tests passing
  - Neue Tests: >= 40 Tests fuer review_loop.py
  - Spec Verify: Jede FA gecheckt, CLI-Flags vorhanden, State Sub-Phases funktional
  - Ruff + Black clean
