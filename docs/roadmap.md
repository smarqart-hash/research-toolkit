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
| Post-v4 | Code Audit | 8 CRITICAL + 27 HIGH + 28 MEDIUM gefixt |
| Post-v4 | Claim Verification | FactScore-Pattern, `--verify` Flag, 28 Tests |
| Quickwin | M2+M3 | LLM-as-Ranking-Judge + Self-Enhancement Bias Test, 36 Tests |
| Post-v5 | Search Quality Tuning | OA-PreFilter 0.5, Prompt Precision, `--min-citations`, `--fields-of-study`, `--judge` |

Findings: F1-F21 alle geloest. F22-F25 aus v5 adressiert. Details: `docs/meta-loop/findings*.md`.

---

## Naechste Sprints

### Evidence Card Relations ← NAECHSTER

> Armer-Mann's-Knowledge-Graph: Relationen zwischen Claims.

- `supports`, `contradicts`, `extends` Felder auf EvidenceCard
- Conflict Map als Markdown generierbar
- Abhaengigkeit: Claim Verification ✅

### Sprint N+1: Prompt-Versioning (Roadmap-Sprint 7)

> Pipeline-Prompts extrahieren nach `config/prompts/v1/`.

- 5 Prompts (Clustering, Extraction, Draft, Self-Check, Review)
- Test-Harness: Golden Dataset pro Prompt
- Optional: Langfuse-Integration

---

## Backlog

| Idee | Aufwand | Quelle | Abhaengigkeit |
|------|---------|--------|---------------|
| ~~LLM-as-Ranking-Judge (M2)~~ | ✅ | Optionenlandkarte | Erledigt |
| ~~Self-Enhancement Bias Test (M3)~~ | ✅ | Optionenlandkarte | Erledigt |
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
| A/B Prompt-Tests (Query Expansion) | 1 Woche | Session 11.03. | Prompt-Versioning |
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
