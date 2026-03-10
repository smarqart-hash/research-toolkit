# Sprint 4 Skizze: Agentic Review Loop

> Status: SKIZZE (Handover wird vor Implementation geschrieben)
> Aufwand: ~1 Woche
> Abhaengigkeit: Sprint 3.5 (Feedback Infra — automatable-Flag, numerische Confidence)
> Quelle: Roadmap Sprint 4 + Optionenlandkarte S3/S4

---

## Motivation

Pipeline ist linear: Draft → Self-Check → fertig. Der Self-Check erkennt
Schwaechen, aber der Draft wird nicht verbessert. Zusaetzlich:
Self-Enhancement Bias (Zheng NeurIPS 2023) — das Tool bewertet eigenen
Output systematisch besser.

Sprint 4 schliesst beides: Revise-Loop + Bias-Awareness.

---

## Architektur

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

**Konvergenz-Kriterien:**
- Max 2 Revisions (hart)
- Score sinkt → sofortiger Abbruch
- Keine CRITICAL/HIGH Issues mehr → Stop

---

## 5 Tasks

### T1: `review_for_revision()` — Kompakt-Review

**Wo:** `src/agents/reviewer.py` (NEU)
- Nur Issues mit Severity CRITICAL + HIGH
- Jedes Issue mit Sektion-Referenz + konkretem Verbesserungsvorschlag
- Kein Full-Report, nur actionable Feedback
- Nutzt `automatable`-Flag (aus Sprint 3.5): nur automatable Dimensionen

### T2: `revise_draft()` — Selektive Revision

**Wo:** `src/agents/drafting.py` (NEU)
- Input: Draft-Markdown + kompakte Issues
- LLM ueberarbeitet NUR betroffene Sektionen (nicht kompletter Rewrite)
- Output: revidierter Draft + Changelog (was geaendert, warum)
- Immutability: neues Draft-Objekt, altes bleibt als Artifact

### T3: Self-Consistency Probe (S3) — Quality Gate

**Wo:** `src/agents/reviewer.py` (NEU)
- Review 3x mit Temperature 0.3/0.7/1.0 laufen lassen
- Agreement pro Dimension messen (Cohen's Kappa oder simpler: % Uebereinstimmung)
- Bei Kappa < 0.4 fuer eine Dimension: als `requires_human` flaggen
- Triggered bei Borderline-Scores (30-40/50)

### T4: Handlungsorientierte Sub-Fragen (S4) — Rubrik-Upgrade

**Wo:** `src/agents/reviewer.py` — DimensionResult-Prompts
- Statt: "Evidence: stark/angemessen/ausbaufaehig/kritisch"
- Neu: "Jeder Claim hat min. 1 Zitat: ja/nein" + "Methodenbeschreibung
  reproduzierbar: ja/nein" + "Statistische Ergebnisse mit Konfidenzintervall: ja/nein"
- Hoeheres Inter-Rater-Agreement (Rogers & Augenstein 2020)

### T5: State Machine Sub-States

**Wo:** `src/pipeline/state.py`
- SYNTHESIS Phase bekommt Sub-Phasen: DRAFTING, REVIEWING, REVISING
- Jede Revision als Artifact im State (diff nachvollziehbar)
- Delta-Tracking via `compute_delta()` zwischen Review-Runden

---

## CLI-Aenderung

```bash
# Bisherig (unveraendert)
research-toolkit draft "AI traffic control" --venue acm

# Neu: mit Revise-Loop
research-toolkit draft "AI traffic control" --venue acm --revise

# Optional: max Revisions begrenzen
research-toolkit draft "AI traffic control" --revise --max-revisions 1
```

## Akzeptanzkriterien

- [ ] Score steigt nach Revision (>= +3 Punkte Schnitt)
- [ ] Max 2 Revisions, Verschlechterung → sofortiger Abbruch
- [ ] Self-Consistency Probe bei Borderline-Scores
- [ ] Handlungsorientierte Sub-Fragen statt vager Dimensionen
- [ ] Jede Revision im Provenance-Log nachvollziehbar
- [ ] Ohne `--revise`: identisches Verhalten (Regression)

## Risiken

- Goodhart's Law: System optimiert auf Reviewer-Zufriedenheit, nicht Qualitaet
  → Mitigation: Max 2 Revisions + Score-Verschlechterung = Stop
- Self-Enhancement Bias: Reviewer bewertet eigenen revidierten Output besser
  → Mitigation: Self-Consistency Probe + automatable-Flag
- LLM-Kosten: 3x Review (Self-Consistency) + 2x Revision = 5x API-Calls
  → Mitigation: Self-Consistency nur bei Borderline, Kompakt-Review statt Full

## Research-Referenz
- [Recursive Self-Improvement Limits](../research/20260305-recursive-self-improvement-limits.md) — Huang ICLR 2024
- [Meta-Review Rubrics](../research/20260305-meta-review-rubrics.md) — Zheng NeurIPS 2023, Rogers 2020
