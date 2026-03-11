# Roadmap Archive — Sprint-Details

> Detaillierte Sprint-Spezifikationen fuer abgeschlossene Sprints.
> Aktive Planung: `docs/roadmap.md`

## Sprint 3: Smart Query Generation

- 2-Tier Query-Expansion: lokal (Synonym-Map + Boolean) + LLM (OpenRouter)
- `query_generator.py`, `llm_client.py`, `config/query_templates/`
- CLI: `--refine` / `-r` + `--no-validate`
- 45 Tests, SDD-Workflow mit Spec `spec/001-smart-query-gen/`

## Sprint 3.5: Feedback Infrastructure

- Numerische Confidence (float 0.0-1.0), Dimension-Confidence Split
- Feedback Schema (`feedback.jsonl`), Citation-Match in Provenance

## Sprint 4: Agentic Review Loop

- Draft→Review→Revise Loop (max 2 Revisionen, Score-Drop-Abbruch)
- Self-Consistency Probe (3x Review mit T=0.3/0.7/1.0)
- Sub-Fragen statt vager Dimensionen (9 Ja/Nein, Score 0-50)
- 50 Tests, Spec `spec/003-agentic-review-loop/`

## Sprint 5: Multi-Source Search

- OpenAlex API Client, `SearchConfig.sources`, `asyncio.gather`
- CLI: `--sources ss,openalex,exa`, Language-Default `["en", "de"]`
- 127 Tests, 90% Coverage

## Sprint 6: Search Quality Fixes (F12-F15, F18)

- Source-aware Citation-Caps, OpenAlex Pre-Filter, `--append`
- Source-Balance Warning, Abstract-Weight auf 0.15
- 2 Adversarial Reviews bestanden

## Sprint 7: Paper Import + Low-Recall (F17)

- BibTeX-Import (`bibtex_parser.py`), `--papers` CLI-Flag
- Low-Recall-Warnung bei <15 Papers

## Quickwin: Doctor + SPECTER2

- `doctor.py`: Feature-Availability Check (6 Dependencies)
- Source-aware Enhanced Scoring (SS: 0.25, OA: 0.10, Exa: 0.03)

## Post-v4: Search Quality Sprint + OA-Queries

- F19 Source-Quota, per_page Limits, LLM Key Mapping
- `QuerySet.oa_queries` (Freitext), Exa DACH-Domains
- F20 Multi-Query-Workflow Docs

## Roadmap-Sprint 5: Claim Verification (geplant)

- Atomic Claim Extraction (FactScore), Abstract-Level NLI
- SciFact Benchmark, `claim_verifier.py`

## Roadmap-Sprint 6: Evidence Card Relations (geplant)

- supports/contradicts/extends Felder, Conflict Map

## Roadmap-Sprint 7: Prompt-Versioning (geplant)

- Prompts nach `config/prompts/v1/`, Test-Harness
