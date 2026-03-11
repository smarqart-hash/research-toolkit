# Research Toolkit — Roadmap

> Aktive Planung. Sprint-Details in `docs/roadmap-archive.md`.
> Stand: 11. Maerz 2026.

## Abgeschlossen

| Sprint | Thema | Highlights |
|--------|-------|------------|
| Sprint 1 | Search Quality | Screening + SPECTER2 + Pipeline-Docs |
| Sprint 2 | Reflexivitaet | `--reflexive` Flag + Calibration Transparency |
| Sprint 3 | Smart Query Generation | 2-Tier Expansion (lokal + LLM), `--refine` |
| Sprint 3.5 | Feedback Infrastructure | Numerische Confidence, Feedback Schema |
| Sprint 4 | Agentic Review Loop | Draft→Review→Revise, Self-Consistency Probe |
| Sprint 5 | Multi-Source Search | OpenAlex Client, `--sources`, Language-Filter |
| Sprint 6 | Search Quality Fixes | Source-aware Citation-Caps, `--append`, Pre-Filter |
| Sprint 7 | Paper Import | BibTeX-Import (`--papers`), Low-Recall-Warnung |
| Quickwin | Doctor + SPECTER2 | `doctor` Command, Source-aware Enhanced Scoring |
| Post-v4 | Search Quality Sprint | F19 Source-Quota, per_page Limits, Prompt-Opt |
| Post-v4 | OA-Queries + DACH | `oa_queries` (Freitext), Exa DACH-Domains, F20 Docs |

Findings: F1-F21 alle geloest. Details: `docs/meta-loop/findings*.md`.

---

## Naechste Sprints

### Sprint N: Claim Verification (Roadmap-Sprint 5)

> Schliesst das groesste Loch: Check verifiziert Quellen-Existenz, nicht Claim-Wahrheit.

- Atomic Claim Extraction (FactScore-Pattern)
- Abstract-Level NLI via LLM (SUPPORTS / REFUTES / NOT_ENOUGH_INFO)
- Optional: SciFact Benchmark (SOTA F1: 0.72-0.88)
- Dateien: `claim_verifier.py` NEU, `evidence_card.py` erweitern
- Abhaengigkeit: Keine

### Sprint N+1: Evidence Card Relations (Roadmap-Sprint 6)

> Armer-Mann's-Knowledge-Graph: Relationen zwischen Claims.

- `supports`, `contradicts`, `extends` Felder auf EvidenceCard
- Conflict Map als Markdown generierbar
- Abhaengigkeit: Claim Verification

### Sprint N+2: Prompt-Versioning (Roadmap-Sprint 7)

> Pipeline-Prompts extrahieren nach `config/prompts/v1/`.

- 5 Prompts (Clustering, Extraction, Draft, Self-Check, Review)
- Test-Harness: Golden Dataset pro Prompt
- Optional: Langfuse-Integration

---

## Backlog

| Idee | Aufwand | Quelle | Abhaengigkeit |
|------|---------|--------|---------------|
| LLM-as-Ranking-Judge (M2) | 3 Tage | Optionenlandkarte | Sprint 3.5 ✅ |
| Self-Enhancement Bias Test (M3) | 3 Tage | Optionenlandkarte | Sprint 4 ✅ |
| ECE-Tracking (M4) | 1 Woche | Optionenlandkarte | Sprint 3.5 ✅ |
| CORE/Unpaywall Full-Text (M5) | 1 Woche | Optionenlandkarte | Claim Verification |
| Gewichtungs-Optimierung (A1) | 2 Wochen | Optionenlandkarte | M2 |
| Inter-Rater mit zweitem LLM (A3) | 1 Woche | Optionenlandkarte | Sprint 4 ✅ |
| Conformal Prediction Sets (A4) | 2 Wochen | Optionenlandkarte | M4 |
| Fine-tuned NLI DeBERTa (A5) | 2 Wochen | Optionenlandkarte | Claim Verification |
| Venue-spezifische Rubrics (A6) | 2 Wochen | Optionenlandkarte | Sprint 4 ✅ |
| Local Vector Index (chromadb) | M-L | Roadmap (alt) | — |
| Full Knowledge Graph | L-XL | Roadmap (alt) | Evidence Relations |
| Prompt-Versioning mit Langfuse | L | Roadmap (alt) | Prompt-Versioning |
| DSPy-Integration | L | Roadmap (alt) | Prompt-Versioning |
| Learned Ranking Model (V1) | Monate | Optionenlandkarte | A1 |
| Emergente Dimensionen (V2) | Monate | Optionenlandkarte | A3 |
| Active Learning Pipeline (V3) | Monate | Optionenlandkarte | V1 |
| Cross-Encoder Full-Text (V4) | Monate | Optionenlandkarte | M5+A5 |
| Provenance Chain (V5) | Monate | Optionenlandkarte | Claim Verif. + Relations |

---

## Research-Referenzen

- [Calibrated Confidence](docs/research/20260305-calibrated-confidence.md)
- [Ranking Feedback Loops](docs/research/20260305-ranking-feedback-loops.md)
- [Meta-Review Rubrics](docs/research/20260305-meta-review-rubrics.md)
- [Recursive Self-Improvement Limits](docs/research/20260305-recursive-self-improvement-limits.md)
- [Claim Verification](docs/research/20260305-claim-verification.md)
- [Synthese / Optionenlandkarte](docs/research/20260305-synthese-optionenlandkarte.md)
