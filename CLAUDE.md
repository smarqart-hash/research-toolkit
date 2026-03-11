# Research Toolkit — Projekt-Konventionen

## Architektur

Modulares Python-CLI-Toolkit fuer AI-gestuetzte akademische Forschung.
4 Skills (Search, Draft, Review, Check) kommunizieren ueber Evidence Cards.

```
CLI (Typer) → Agents (Domain-Logik) → Pipeline (State + Provenance)
                                    → Utils (Evidence Cards, Rubrics)
```

### Modulstruktur

| Modul | Zweck |
|-------|-------|
| `src/agents/` | Domain-Logik: Search, Draft, Review, Check, Ranking |
| `src/pipeline/state.py` | State Machine (6 Phasen + HITL Gates) |
| `src/pipeline/provenance.py` | Append-only JSONL Audit Trail |
| `src/utils/__init__.py` | PROJECT_ROOT, CONFIG_DIR Konstanten |
| `src/utils/evidence_card.py` | Strukturierte Paper-Extrakte |
| `src/utils/rubric_loader.py` | Venue-Rubrics + Policy Context |
| `src/utils/document_splitter.py` | Dokument-Splitting |
| `src/utils/bibtex_parser.py` | BibTeX-Import zu UnifiedPaper |
| `skills/` | LLM Instruction Files (search, draft, review, check) |
| `config/` | Venue/Voice Profiles (JSON), Rubrics, Policy Context |
| `src/agents/claim_verifier.py` | LLM-basierte Claim-Verifikation (FactScore) |
| `src/agents/doctor.py` | Feature-Availability Check (doctor Command) |
| `cli.py` | Typer Entry Point (6 Commands) |

### Kern-Dateien fuer Features

| Feature | Dateien |
|---------|---------|
| Search + Ranking | `forschungsstand.py`, `paper_ranker.py`, `semantic_scholar.py`, `exa_client.py`, `openalex_client.py` |
| Draft | `drafting.py` + `config/venue_profiles/` + `config/voice_profiles/` |
| Review | `reviewer.py` + `rubric_loader.py` |
| Check | `quellen_checker.py` + `reference_extractor.py` |
| Verify | `claim_verifier.py` (FactScore-Pattern: Claim-Extraktion + NLI) |
| Import | `bibtex_parser.py` |

## Coding Conventions

### Sprache
- **Code**: Englisch (Funktionen, Variablen, Klassen)
- **Docstrings + Kommentare**: Deutsch
- **Enum-Werte**: Deutsch (z.B. `STARK`, `AUSBAUFAEHIG`)

### Stack
- Python 3.11+, Hatch Build System
- Pydantic v2 (BaseModel, computed_field) — bevorzugtes Datenmodell
- httpx (async HTTP), Typer (CLI), Rich (UI)
- `from __future__ import annotations` in jeder Datei

### Patterns
- **Immutability**: `papers = [*papers, new_paper]` statt `.append()`
- **Error Handling**: try/except mit `logger.warning()`, Fehler zaehlen in Stats-Dict
- **Async I/O**: `httpx.AsyncClient` fuer externe APIs
- **Computed Fields**: `@computed_field` fuer abgeleitete Werte
- **Privat**: `_`-Prefix fuer interne Funktionen

### Formatierung
- Black (line-length=100) + Ruff (E, F, W, I, N, UP)
- Target: Python 3.11

## Tests

- **Framework**: pytest (564 Tests, alle passing)
- **Pfad**: `tests/` — pythonpath: `["src", "."]`
- **Factories**: `_ss_paper()`, `_exa_result()`, `_openalex_work()` als lokale Helfer (kein Factory-Framework)
- **Fixtures**: `@pytest.fixture` fuer State, tmp_path
- **Mocking**: `@patch("module.Class.method")` fuer externe APIs
- **Assertions**: Simple `assert X == Y`, `pytest.raises(ValueError, match="...")`
- **Organisation**: Test-Klassen nach Funktion (TestFromSemanticScholar, TestDedupKey, etc.)

```bash
# Tests ausfuehren
pytest tests/ -v
pytest tests/ --cov=src --cov-report=term-missing
```

## CLI Commands

```bash
research-toolkit search TOPIC        # --max, --sources ss,openalex,exa, --years, --append, --papers
research-toolkit draft TOPIC --venue X  # --voice, --input, --mode
research-toolkit review DOCUMENT     # --venue
research-toolkit check DOCUMENT      # --verify (LLM Claim-Verifikation)
research-toolkit venues              # Liste Venue-Profile
research-toolkit doctor              # Feature-Availability Check
```

## Ranking (Aktueller Stand — Sprint 6)

Source-aware Composite Score (0-1):
- Citations (log-skaliert, **source-capped**: SS max 0.4, OA max 0.15, Exa max 0.05)
- 30% Recency (2018-2026)
- 15% Abstract vorhanden (aufgewertet als Qualitaetssignal)
- 10% Open Access Bonus
- Metadaten-Bonus: SS 0.1, OA 0.05, Exa 0.0

**OpenAlex Pre-Filter:** Papers unter relevance_score 0.3 werden vor Ranking entfernt.
**Source-Balance Warning:** Warnung wenn eine Quelle <10% des Pools liefert.
**Akkumuliertes Suchen:** `--append` Flag merged neue Ergebnisse in bestehenden Pool.
**Paper-Import:** `--papers refs.bib` importiert externe Papers (source="import") in den Pool.
**Low-Recall-Warnung:** Warnung wenn < 15 Papers nach Ranking + Empfehlungen (Exa, Import).

**OA-spezifische Queries:** `QuerySet.oa_queries` — Freitext ohne Boolean-Operatoren fuer OpenAlex.
**Exa DACH-Domains:** gesis.org, dnb.de, zbw.eu in `include_domains`.
**SPECTER2** optional (`[nlp]`). Enhanced Score ebenfalls source-aware (SS: 0.25, OA: 0.10, Exa: 0.03).
Deduplication via DOI oder Title-Hash (SHA256).

## Environment Variables

| Variable | Zweck | Required |
|----------|-------|----------|
| `S2_API_KEY` | Semantic Scholar API | Nein (funktioniert ohne, aber Rate Limits) |
| `EXA_API_KEY` | Exa Search API | Nein (Exa wird uebersprungen) |
| `OPENALEX_API_KEY` | OpenAlex Premium API Key | Nein (hoehere Rate Limits) |
| `OPENALEX_MAILTO` | OpenAlex Polite Pool (Alternative zu API Key) | Nein (funktioniert ohne) |
| `OUTPUT_DIR` | Output-Verzeichnis | Nein (default: ./output) |

## Meta-Loop

Reflexiver Feedback-Loop: Toolkit generiert Paper ueber sich selbst, leitet Findings ab.
Abgeschlossen: Sprint 1-7 + Quickwin + Code Audit + Claim Verification (Details: `docs/plans/`).
Code Audit 2026-03-11: CRITICAL(8)+HIGH(27)+MEDIUM(28) gefixt, LOW(15) als Backlog.
Claim Verification: FactScore-Pattern (Extraktion + NLI), 28 Tests, `--verify` Flag im check-Command.
Offen: Keine aktiven Findings. F19-F21 geloest (Details: Memory).
