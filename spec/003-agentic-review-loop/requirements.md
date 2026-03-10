# Requirements: Agentic Review Loop (003)

**Scope:** Backend
**Abhaengigkeiten:** Sprint 3 (llm_client.py), Sprint 3.5 (automatable, numerische confidence)

---

## Problemstellung

Die Pipeline ist linear: Draft → Self-Check → fertig. Der Self-Check erkennt
Schwaechen, aber der Draft wird nicht verbessert. Zusaetzlich: Self-Enhancement
Bias (Zheng NeurIPS 2023) — das Tool bewertet eigenen Output systematisch besser.

## Funktionale Anforderungen

### FA-1: Kompakt-Review (`review_for_revision()`)
- Erstellt einen kompakten Review nur mit CRITICAL + HIGH Issues
- Jedes Issue enthaelt: Sektion-Referenz, Problem, konkreter Verbesserungsvorschlag
- Nur automatable Dimensionen (nutzt `automatable`-Flag aus Sprint 3.5)
- Kein Full-Report, nur actionable Feedback fuer die Revision

### FA-2: Selektive Revision (`revise_draft()`)
- Input: Draft-Markdown + kompakte Issues aus FA-1
- LLM ueberarbeitet NUR betroffene Sektionen (kein kompletter Rewrite)
- Output: revidierter Draft + Changelog (was geaendert, warum)
- Immutability: neues DraftResult-Objekt, altes bleibt als Artifact
- Nutzt `llm_complete()` aus Sprint 3

### FA-3: Revise-Loop Orchestrierung
- Flow: Draft → Review → Score pruefen → ggf. Revise → Re-Review → Done
- Konvergenz-Kriterien (hart):
  - Max 2 Revisionen
  - Score sinkt → sofortiger Abbruch
  - Keine CRITICAL/HIGH Issues mehr → Stop
- Score-Schwelle: >= 35/50 (= kein CRITICAL, max 2 HIGH)
- Nutzt `compute_delta()` (bereits vorhanden in reviewer.py) fuer Delta-Tracking

### FA-4: Self-Consistency Probe
- Review 3x mit Temperature 0.3/0.7/1.0 ausfuehren
- Agreement pro Dimension messen (% Uebereinstimmung der Ratings)
- Bei Agreement < 60% fuer eine Dimension: als `requires_human` flaggen
- Nur triggered bei Borderline-Scores (30-40/50)

### FA-5: Handlungsorientierte Sub-Fragen (Rubrik-Upgrade)
- Statt vager Dimension-Bewertungen: konkrete Ja/Nein-Fragen
- Beispiel Evidence: "Jeder Claim hat min. 1 Zitat: ja/nein"
- Config-basiert in `config/dimensions/sub_questions.json`
- Hoeheres Inter-Rater-Agreement

### FA-6: State Machine Sub-States
- SYNTHESIS Phase bekommt Sub-Phasen: DRAFTING, REVIEWING, REVISING
- Jede Revision als Artifact im State (diff nachvollziehbar)
- Provenance-Logging fuer jeden Revise-Schritt

### FA-7: CLI Integration
```bash
research-toolkit draft TOPIC --venue acm --revise
research-toolkit draft TOPIC --revise --max-revisions 1
```
- `--revise` aktiviert den Review-Loop nach Draft
- `--max-revisions N` (default: 2) begrenzt Iterationen
- Ohne `--revise`: identisches Verhalten wie bisher (Regression)

## Nicht-funktionale Anforderungen

### NFA-1: Backward Compatibility
- Ohne `--revise`: identisches Verhalten, keine Regression
- Bestehende ReviewResult/DimensionResult-Schemas bleiben kompatibel
- Bestehende State Machine Phasen bleiben unveraendert

### NFA-2: Observability
- Jede Revision im Provenance-Log (`provenance.jsonl`)
- Delta zwischen Review-Runden in ReviewResult gespeichert
- Self-Consistency Ergebnisse in ReviewResult.metadata

### NFA-3: Goodhart-Schutz
- Max 2 Revisionen (hart, nicht konfigurierbar ueber 3)
- Score-Verschlechterung = sofortiger Abbruch
- Self-Consistency Probe bei Borderline entschaerft Bias

## Bestehende Infrastruktur (Dependency Check)

| Komponente | Status | Datei |
|-----------|--------|-------|
| `compute_delta()` | Vorhanden | `reviewer.py:133` |
| `ReviewDelta` | Vorhanden | `reviewer.py:98` |
| `ReviewResult.verdict` | Vorhanden (computed) | `reviewer.py:122` |
| `DimensionResult.automatable` | Vorhanden (Sprint 3.5) | `reviewer.py:69` |
| `llm_complete()` | Vorhanden (Sprint 3) | `llm_client.py` |
| `ProvenanceLogger` | Vorhanden | `provenance.py:29` |
| State Machine Sub-States | NICHT vorhanden | `state.py` — zu erweitern |
| `--revise` CLI Flag | NICHT vorhanden | `cli.py` — zu erweitern |
| Sub-Fragen Config | NICHT vorhanden | Neu: `config/dimensions/sub_questions.json` |

## Scope Guard

**Nicht in diesem Sprint:**
- Externe Reviewer (nur Self-Review)
- Multi-Agent Review (mehrere LLMs bewerten)
- Automatisches Rubric-Tuning
- Feedback-Loop zurueck zur Search-Phase

## Akzeptanzkriterien

- [ ] Score steigt nach Revision (>= +3 Punkte Schnitt)
- [ ] Max 2 Revisions, Verschlechterung → sofortiger Abbruch
- [ ] Self-Consistency Probe bei Borderline-Scores
- [ ] Handlungsorientierte Sub-Fragen statt vager Dimensionen
- [ ] Jede Revision im Provenance-Log nachvollziehbar
- [ ] Ohne `--revise`: identisches Verhalten (Regression)
- [ ] Tests: >= 90% Coverage fuer neue Funktionen
- [ ] `pytest tests/ -v` — alle 330+ bestehenden Tests passing

## Test-Baseline
```bash
pytest tests/ -v  # 330 Tests, alle passing
```
