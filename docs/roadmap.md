# Research Toolkit — Roadmap

> Aktive Planung. Erledigtes in `docs/roadmap-archive.md` auslagern.
> Konsolidiert am 10. Maerz 2026: Roadmap + Optionenlandkarte (Paper-2-Feedback).

## Abgeschlossen

| Sprint | Thema | Commit |
|--------|-------|--------|
| Sprint 1 | Search Quality (Screening + SPECTER2 + Pipeline-Docs) | `7533eb4`..`b472949` |
| Sprint 2 | Reflexivitaet (--reflexive Flag + Calibration Transparency) | `8427206` |

---

## Sprint 3: Smart Query Generation

> Ziel: `generate_search_queries` von Heuristik auf LLM-gestuetzte Query-Optimierung upgraden.

### Problem

`forschungsstand.py:191` — aktuelle Implementierung:
- Strippt Fragewoerter, konkateniert Topic + Fragment
- Keine Synonyme, keine Boolean-Operatoren, keine Scope-Eingrenzung
- Exa und Semantic Scholar brauchen unterschiedliche Query-Formate

### Loesung: 3-Stufen Query-Pipeline

```
Stufe 1: Topic Refinement (bei vagem Input)
  → Research Question (PICO/SPIDER Format)
Stufe 2: Query Expansion
  → 5-8 Queries (SS-Boolean + Exa-Natural-Language)
Stufe 3: Query Validation
  → Dry-Run: Top-3 Relevanz-Check, bei < 0.5 adjustieren
```

### Dateien

| Datei | Aenderung |
|-------|-----------|
| `src/agents/query_generator.py` | **NEU** — LLM-gestuetzte Query-Generierung |
| `src/agents/forschungsstand.py` | `generate_search_queries()` delegiert an neues Modul |
| `skills/search.md` | Doku fuer `--refine` Mode |
| `config/query_templates/` | **NEU** — Few-Shot-Beispiele pro Disziplin |
| `tests/test_query_generator.py` | **NEU** |

### Akzeptanzkriterien

- [ ] `--refine` generiert mind. 5 Queries (3 SS + 2 Exa)
- [ ] Queries enthalten Synonyme die in der Heuristik fehlten
- [ ] Dry-Run Validation erkennt irrelevante Queries
- [ ] Ohne `--refine`: identisches Verhalten (Regression)
- [ ] Tests: >= 90% Coverage fuer `query_generator.py`

---

## Sprint 3.5: Feedback Infrastructure

> Ziel: Minimale Infrastruktur fuer externes Feedback + Frontier-Transparency.
> Quelle: Optionenlandkarte S1+S2+S5+S6. Aufwand: ~1 Tag.

### Motivation (Paper 2 / Ceiling-Detektor-These)

Ohne Feedback-Infrastruktur koennen spaetere Sprints (Review Loop, Claim
Verification) ihre Qualitaet nicht messen. Dieses Sprint legt die Grundlage.

### Tasks

1. **Numerische Confidence (S1)** — `confidence: float` (0.0-1.0) statt `str`
   auf EvidenceCard. Verbalized Confidence im Prompt. Pydantic Validator fuer
   Backward-Kompatibilitaet (alte "low/medium/high" → 0.3/0.5/0.8).
2. **Dimension-Confidence Split (S2)** — `automatable: bool` pro DimensionResult.
   Clarity/Structure = True, Significance/Novelty = False. Macht die Frontier
   zwischen "Machine kann bewerten" und "Mensch muss bewerten" explizit.
3. **Feedback Schema (S5)** — `feedback.jsonl` Format: Topic, Expert-Top-5,
   Timestamp, Ranking-Method. Prerequisite fuer Ranking-Feedback.
4. **Implizites Feedback (S6)** — Welche Papers landen im Draft? Evidence Card →
   Draft → Citation-Match automatisch in `provenance.jsonl` loggen.

### Dateien

| Datei | Aenderung |
|-------|-----------|
| `src/utils/evidence_card.py` | `confidence: float`, Validator |
| `src/agents/reviewer.py` | `automatable: bool` auf DimensionResult |
| `src/pipeline/provenance.py` | Feedback-Events + Citation-Match |
| `config/feedback_schema.json` | **NEU** — JSON Schema |
| `tests/test_evidence_card.py` | Backward-Compat Tests |
| `tests/test_reviewer.py` | automatable-Flag Tests |

### Akzeptanzkriterien

- [ ] Alte Evidence Cards (confidence: str) laden weiterhin
- [ ] Neue Evidence Cards haben `confidence: float`
- [ ] DimensionResult hat `automatable: bool`
- [ ] `feedback.jsonl` Schema dokumentiert
- [ ] Citation-Match in Provenance geloggt

---

## Sprint 4: Agentic Review Loop

> Ziel: Draft → Critic → Revise Schleife mit Bias-Awareness.

### Problem

Pipeline ist linear: Draft → Self-Check → fertig. Kein Revise-Loop.
Zusaetzlich: Self-Enhancement Bias (Zheng NeurIPS 2023) — das Tool
bewertet eigenen Output systematisch besser.

### Loesung: Revise-Loop + Quality Gates aus Optionenlandkarte

```
SYNTHESIS.DRAFT → SYNTHESIS.REVIEW → Score >= 35/50? → COMPLETED
                                   → Score < 35/50?  → SYNTHESIS.REVISE
                                                        → SYNTHESIS.REVIEW (max 2x)
```

**Aus Optionenlandkarte integriert:**
- S3: Self-Consistency Probe (Review 3x, Agreement messen) als Quality Gate
- S4: Handlungsorientierte Sub-Fragen statt vager Dimensionen

### Dateien

| Datei | Aenderung |
|-------|-----------|
| `src/agents/drafting.py` | `revise_draft()` NEU |
| `src/agents/reviewer.py` | `review_for_revision()` NEU, Sub-Fragen |
| `src/pipeline/state.py` | Sub-States fuer SYNTHESIS Phase |
| `tests/test_revise_loop.py` | **NEU** |

### Akzeptanzkriterien

- [ ] Score steigt nach Revision (>= +3 Punkte Schnitt)
- [ ] Max 2 Revisions, Verschlechterung → sofortiger Abbruch
- [ ] Self-Consistency Probe bei Borderline-Scores (30-40/50)
- [ ] Jede Revision im Provenance-Log nachvollziehbar
- [ ] Ohne `--revise`: identisches Verhalten

---

## Sprint 5: Claim Verification (Finding F9)

> Ziel: Evidence Card Claims gegen Abstracts verifizieren.
> Quelle: Optionenlandkarte M6+M1+A2. Schliesst das groesste Loch.

### Problem

Check-Skill verifiziert ob Quellen *existieren*, nicht ob *Claims stimmen*.
Ein Evidence Card koennte sagen "18% Trust-Reduktion" obwohl das Paper
das Gegenteil zeigt.

### Loesung: Abstract-Level NLI + Atomic Claims

1. **Atomic Claim Extraction (M6)** — FactScore-Pattern: Draft in atomare
   Claims zerlegen. Jeder Claim einzeln verifizierbar.
2. **Abstract-Level NLI (M1)** — Claim gegen Abstract pruefen via LLM-Prompt.
   Labels: SUPPORTS / REFUTES / NOT_ENOUGH_INFO. `verification_status` auf
   EvidenceCard speichern.
3. **SciFact Benchmark (A2)** — Check-Skill auf SciFact evaluieren.
   Baseline-Zahlen dokumentieren (SOTA: F1 0.72-0.88).

### Dateien

| Datei | Aenderung |
|-------|-----------|
| `src/agents/claim_verifier.py` | **NEU** — NLI + Atomic Claims |
| `src/utils/evidence_card.py` | `verification_status: str` Feld |
| `src/agents/quellen_checker.py` | Integration mit claim_verifier |
| `tests/test_claim_verifier.py` | **NEU** |
| `benchmarks/scifact/` | **NEU** — Evaluation-Skripte |

### Akzeptanzkriterien

- [ ] Atomic Claims extrahierbar aus Draft-Markdown
- [ ] NLI-Labels (SUPPORTS/REFUTES/NEI) auf Evidence Cards
- [ ] SciFact Baseline F1 dokumentiert
- [ ] False Positives: mind. 1 absichtlich falsche Claim erkannt

---

## Sprint 6: Evidence Card Relations

> Ziel: Armer-Mann's-Knowledge-Graph. Relationen zwischen Claims.

### Loesung: Relations-Felder auf EvidenceCard

```python
class EvidenceCard(BaseModel):
    ...
    supports: list[str] = []      # card_ids die stuetzen
    contradicts: list[str] = []   # card_ids die widersprechen
    extends: list[str] = []       # card_ids auf denen aufgebaut wird
    relation_confidence: float = 0.0  # numerisch (nicht str, konsistent mit S1)
```

### Akzeptanzkriterien

- [ ] Bestehende Evidence Cards laden weiterhin (backward-compat)
- [ ] Mind. 1 Widerspruch in Test-Corpus erkannt
- [ ] Conflict Map als Markdown generierbar
- [ ] `relation_confidence: float` (konsistent mit Sprint 3.5)

---

## Sprint 7: Prompt-Versioning

> Pipeline-Prompts von Inline-Strings nach `config/prompts/` extrahieren.

### Kandidaten

| Prompt | Wo |
|--------|-----|
| Clustering | `forschungsstand.py` |
| Evidence Extraction | `forschungsstand.py` |
| Draft Kapitel-Generierung | `drafting.py` |
| Self-Check | `drafting.py` |
| Review 7-Dimensionen | `reviewer.py` |

### Ansatz

1. Prompts extrahieren in `config/prompts/v1/` (versioniert)
2. Jeder Prompt: XML-Tags, Few-Shot, Scoring-Rubrik
3. Test-Harness: Golden Dataset pro Prompt (5 Input/Output-Paare)

---

## Backlog

| Idee | Aufwand | Quelle | Abhaengigkeit |
|------|---------|--------|---------------|
| LLM-as-Ranking-Judge (M2) | 3 Tage | Optionenlandkarte | Sprint 3.5 |
| Self-Enhancement Bias Test (M3) | 3 Tage | Optionenlandkarte | Sprint 4 |
| ECE-Tracking (M4) | 1 Woche | Optionenlandkarte | Sprint 3.5 |
| CORE/Unpaywall Full-Text (M5) | 1 Woche | Optionenlandkarte | Sprint 5 |
| OpenAlex als 3. Suchquelle | M | Roadmap (alt) | — |
| Gewichtungs-Optimierung (A1) | 2 Wochen | Optionenlandkarte | M2 |
| Inter-Rater mit zweitem LLM (A3) | 1 Woche | Optionenlandkarte | Sprint 4 |
| Conformal Prediction Sets (A4) | 2 Wochen | Optionenlandkarte | M4 |
| Fine-tuned NLI DeBERTa (A5) | 2 Wochen | Optionenlandkarte | Sprint 5 |
| Venue-spezifische Rubrics (A6) | 2 Wochen | Optionenlandkarte | Sprint 4 |
| Local Vector Index (chromadb) | M-L | Roadmap (alt) | — |
| Full Knowledge Graph | L-XL | Roadmap (alt) | Sprint 6 |
| Prompt-Versioning mit Langfuse | L | Roadmap (alt) | Sprint 7 |
| DSPy-Integration | L | Roadmap (alt) | Sprint 7 |
| Learned Ranking Model (V1) | Monate | Optionenlandkarte | A1 |
| Emergente Dimensionen (V2) | Monate | Optionenlandkarte | A3 |
| Active Learning Pipeline (V3) | Monate | Optionenlandkarte | V1 |
| Cross-Encoder Full-Text (V4) | Monate | Optionenlandkarte | M5+A5 |
| Provenance Chain (V5) | Monate | Optionenlandkarte | Sprint 5+6 |

---

## Research-Referenzen

Detaillierte Forschungsgrundlage fuer Sprint 3.5-5 + Backlog:
- [Calibrated Confidence](docs/research/20260305-calibrated-confidence.md)
- [Ranking Feedback Loops](docs/research/20260305-ranking-feedback-loops.md)
- [Meta-Review Rubrics](docs/research/20260305-meta-review-rubrics.md)
- [Recursive Self-Improvement Limits](docs/research/20260305-recursive-self-improvement-limits.md)
- [Claim Verification](docs/research/20260305-claim-verification.md)
- [Synthese / Optionenlandkarte](docs/research/20260305-synthese-optionenlandkarte.md)
