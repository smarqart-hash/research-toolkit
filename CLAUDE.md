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
| `src/utils/evidence_card.py` | Strukturierte Paper-Extrakte |
| `src/utils/rubric_loader.py` | Venue-Rubrics + Policy Context |
| `src/utils/document_splitter.py` | Dokument-Splitting |
| `skills/` | LLM Instruction Files (search, draft, review, check) |
| `config/` | Venue/Voice Profiles (JSON), Rubrics, Policy Context |
| `cli.py` | Typer Entry Point (5 Commands) |

### Kern-Dateien fuer Features

| Feature | Dateien |
|---------|---------|
| Search + Ranking | `forschungsstand.py`, `paper_ranker.py`, `semantic_scholar.py`, `exa_client.py`, `openalex_client.py` |
| Draft | `drafting.py` + `config/venue_profiles/` + `config/voice_profiles/` |
| Review | `reviewer.py` + `rubric_loader.py` |
| Check | `quellen_checker.py` + `reference_extractor.py` |

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

- **Framework**: pytest (420 Tests, alle passing)
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
research-toolkit search TOPIC        # --max, --sources ss,openalex,exa, --years, --append
research-toolkit draft TOPIC --venue X  # --voice, --input, --mode
research-toolkit review DOCUMENT     # --venue
research-toolkit check DOCUMENT
research-toolkit venues              # Liste Venue-Profile
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

**SPECTER2 ist NICHT aktiv** — nur als optionale Dependency `[nlp]` installierbar.
Deduplication via DOI oder Title-Hash (SHA256).

## Environment Variables

| Variable | Zweck | Required |
|----------|-------|----------|
| `S2_API_KEY` | Semantic Scholar API | Nein (funktioniert ohne, aber Rate Limits) |
| `EXA_API_KEY` | Exa Search API | Nein (Exa wird uebersprungen) |
| `OPENALEX_MAILTO` | OpenAlex Polite Pool (hoehere Rate Limits) | Nein (funktioniert ohne) |
| `OUTPUT_DIR` | Output-Verzeichnis | Nein (default: ./output) |

## Meta-Loop (Aktive Entwicklung)

Reflexiver Feedback-Loop: Das Toolkit hat ein Paper ueber sich selbst generiert
(`examples/ai_automated_research/draft.md`). Daraus wurden 6 Findings abgeleitet.

### Sprint 1: Search Quality (`feature/search-quality`)
- Screening-Schritt (PRISMA-Flow)
- Ranking verbessern (SPECTER2 aktivieren)
- Pipeline-Dokumentation (`skills/pipeline.md`)

### Sprint 2: Reflexivitaet (`feature/reflexive-loop`)
- `--reflexive` Flag im Draft-Skill
- Rubric-Kalibrierung dokumentieren

Spec: `docs/meta-loop/iteration-X-spec.md` VOR Implementation schreiben.
