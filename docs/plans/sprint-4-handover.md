# Sprint 4 Handover: Agentic Review Loop

> Status: BEREIT ZUR IMPLEMENTATION
> Branch: `feature/002-agentic-review` (Worktree anlegen)
> Vorgaenger: Sprint 3 (erledigt), Sprint 3.5 (parallel, Abhaengigkeit fuer T1+T3)
> Skizze: `docs/plans/sprint-4-skizze.md`

---

## Ziel

Draft → Review → Revise Loop: Der Self-Check erkennt Schwaechen,
aber aktuell wird nichts verbessert. Sprint 4 schliesst den Loop.
Max 2 Revisionen mit Goodhart-Schutz (Score sinkt → Abbruch).

## Ist-Zustand (Code verifiziert)

### `src/agents/drafting.py` — Draft-Pipeline
- `generate_draft()` → erstellt Markdown-Draft mit Sektionen
- `DraftingConfig` mit `venue`, `voice`, `reflexive` Flags
- `generate_reflexive_section()` fuer Self-Check (Sprint 2)
- Kein Revise-Mechanismus vorhanden

### `src/agents/reviewer.py` — Review-Pipeline
- `review_draft()` → Full Review mit DimensionResult pro Dimension
- `DimensionResult`: score (1-10), confidence, narrative
- 7 Dimensionen: Structure, Clarity, Format, Evidence, Logic, Context, Significance
- Kein Kompakt-Review, kein actionable Feedback-Format

### `src/pipeline/state.py` — State Machine
- SYNTHESIS Phase: monolithisch, keine Sub-Phasen
- Kein Delta-Tracking zwischen Review-Runden

### Relevante Dateien
- `src/agents/drafting.py` — Draft + Revise (zu erweitern)
- `src/agents/reviewer.py` — Review + Kompakt-Review (zu erweitern)
- `src/pipeline/state.py` — Sub-Phasen (zu erweitern)
- `src/pipeline/provenance.py` — Audit Trail (zu erweitern)
- `cli.py` — `--revise` Flag (zu erweitern)

### Test-Baseline
```bash
pytest tests/ -v  # 293 Tests, alle passing
```

---

## Soll-Zustand

### Revise-Loop Architektur
```
SYNTHESIS.DRAFT
  → SYNTHESIS.REVIEW (voller Review)
    → Score >= 35/50? → COMPLETED
    → Score < 35/50?  → SYNTHESIS.REVISE
                        → SYNTHESIS.REVIEW (nur CRITICAL+HIGH)
                        → Score >= 35? → COMPLETED
                        → Score < 35?  → COMPLETED (mit Warning)
                                         (max 2 Revisions, Goodhart-Schutz)
```

### Konvergenz-Kriterien
- Max 2 Revisions (hart)
- Score sinkt → sofortiger Abbruch
- Keine CRITICAL/HIGH Issues mehr → Stop

---

## Implementation Tasks (Reihenfolge)

### T1: `review_for_revision()` — Kompakt-Review (~3h)
**Wo:** `src/agents/reviewer.py`
- Nur Issues mit Severity CRITICAL + HIGH
- Jedes Issue: Sektion-Referenz + konkreter Verbesserungsvorschlag
- Kein Full-Report, nur actionable Feedback
- **Abhaengigkeit Sprint 3.5:** Nutzt `automatable`-Flag (nur automatable Dimensionen)

### T2: `revise_draft()` — Selektive Revision (~4h)
**Wo:** `src/agents/drafting.py`
- Input: Draft-Markdown + kompakte Issues
- LLM ueberarbeitet NUR betroffene Sektionen
- Output: revidierter Draft + Changelog (was geaendert, warum)
- Immutability: neues Draft-Objekt, altes bleibt als Artifact

### T3: Self-Consistency Probe — Quality Gate (~3h)
**Wo:** `src/agents/reviewer.py`
- Review 3x mit Temperature 0.3/0.7/1.0
- Agreement pro Dimension (% Uebereinstimmung)
- Bei Agreement < 60%: als `requires_human` flaggen
- Triggered nur bei Borderline-Scores (30-40/50)
- **Abhaengigkeit Sprint 3.5:** Nutzt numerische Confidence

### T4: Handlungsorientierte Sub-Fragen — Rubrik-Upgrade (~2h)
**Wo:** `src/agents/reviewer.py` — DimensionResult Prompts
- Statt: "Evidence: stark/angemessen/ausbaufaehig/kritisch"
- Neu: Konkrete Ja/Nein-Fragen ("Jeder Claim hat min. 1 Zitat?")
- Hoeheres Inter-Rater-Agreement

### T5: State Machine Sub-States (~2h)
**Wo:** `src/pipeline/state.py`
- SYNTHESIS Phase: Sub-Phasen DRAFTING, REVIEWING, REVISING
- Jede Revision als Artifact im State
- Delta-Tracking via `compute_delta()` zwischen Review-Runden

### T6: CLI Integration + Tests (~2h)
**Wo:** `cli.py`
```bash
research-toolkit draft TOPIC --venue acm --revise
research-toolkit draft TOPIC --revise --max-revisions 1
```

---

## Akzeptanzkriterien

- [ ] Score steigt nach Revision (>= +3 Punkte Schnitt)
- [ ] Max 2 Revisions, Verschlechterung → sofortiger Abbruch
- [ ] Self-Consistency Probe bei Borderline-Scores
- [ ] Handlungsorientierte Sub-Fragen statt vager Dimensionen
- [ ] Jede Revision im Provenance-Log nachvollziehbar
- [ ] Ohne `--revise`: identisches Verhalten (Regression)
- [ ] Tests: >= 90% Coverage fuer neue Funktionen
- [ ] `pytest tests/ -v` — alle bestehenden Tests passing

## Abhaengigkeiten

- Sprint 3.5 (Feedback Infra): `automatable`-Flag + numerische Confidence
  → T1 + T3 brauchen Sprint 3.5. T2/T4/T5 koennen parallel beginnen.
- LLM-Provider: Nutzt `llm_client.py` aus Sprint 3 (bereits vorhanden)
- Kein neues Package noetig

## Risiken

- **Goodhart's Law:** System optimiert auf Reviewer-Zufriedenheit
  → Mitigation: Max 2 Revisions + Score-Verschlechterung = Stop
- **Self-Enhancement Bias:** Reviewer bewertet eigenen Output besser
  → Mitigation: Self-Consistency Probe + automatable-Flag
- **LLM-Kosten:** 3x Review (Probe) + 2x Revision = 5x API-Calls
  → Mitigation: Probe nur bei Borderline, Kompakt-Review statt Full

## Konventionen (aus CLAUDE.md)

- `from __future__ import annotations` in jeder Datei
- Immutability: `items = [*items, new]` statt `.append()`
- Async: `httpx.AsyncClient` fuer externe APIs
- Pydantic v2: `BaseModel`, `computed_field`
- Black (line-length=100) + Ruff
- Deutsch: Docstrings + Kommentare. Englisch: Variablen + Funktionen
