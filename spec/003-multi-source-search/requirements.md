# Spec 003: Multi-Source Search — Requirements

> Scope: Backend (API-Integration + CLI)
> Sprint: 5
> Finding: F8 (Multi-Source Search)

## Ziel

Search-Pipeline von 2 auf 4 Quellen erweitern: **OpenAlex** (international, kostenlos)
und **BASE** (Bielefeld Academic Search Engine, stark deutsch/europaeisch).
Flag-basierte Steuerung via `--sources`. Bestehende Dedup + Ranking + Screening
Pipeline bleibt unveraendert — nur der Input-Pool wird breiter.

## Funktionale Anforderungen

### FR-1: OpenAlex Client
- Async HTTP Client (`httpx.AsyncClient`) analog zu `SemanticScholarClient`
- Endpoint: `https://api.openalex.org/works`
- Kein API Key noetig (Polite Pool mit `mailto`-Header)
- Felder: title, abstract, year, authors, cited_by_count, doi, open_access, type
- Paginierung: `cursor`-basiert (OpenAlex Standard)
- Rate Limit Handling: Retry bei 429, max 1 Retry
- Year-Filter und Language-Filter unterstuetzen

### FR-2: BASE Client
- Async HTTP Client analog
- Endpoint: `https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi`
- Format: JSON (`format=json`)
- Kein API Key noetig
- Felder: dctitle, dcdescription, dcyear, dcauthor, dcdoi, dcidentifier, dcoa
- Year-Filter unterstuetzen
- Language-Filter: `dclang:ger OR dclang:eng`

### FR-3: UnifiedPaper Konverter
- `from_openalex(work) -> UnifiedPaper` in `paper_ranker.py`
- `from_base(result) -> UnifiedPaper` in `paper_ranker.py`
- `source`-Feld: `"openalex"` bzw. `"base"`
- DOI-Extraktion fuer Dedup (OpenAlex hat DOI nativ, BASE via `dcdoi`)

### FR-4: CLI `--sources` Flag
- Neuer Parameter: `--sources` (Komma-separiert)
- Default: `ss,openalex` (Semantic Scholar + OpenAlex)
- Optionen: `ss`, `openalex`, `base`, `exa`
- Ersetzt bestehenden `--exa/--no-exa` Flag (Backward-Compat: `--exa` = `--sources ss,openalex,exa`)
- Beispiele:
  ```bash
  research-toolkit search "topic"                    # ss,openalex (default)
  research-toolkit search "topic" --sources ss,base  # nur SS + BASE
  research-toolkit search "topic" --sources ss,openalex,base,exa  # alle
  ```

### FR-5: Orchestrierung in `search_papers()`
- `SearchConfig` erhaelt `sources: list[str]` statt `use_exa: bool`
- Alle aktiven Quellen werden parallel abgefragt (`asyncio.gather`)
- Stats-Dict erhaelt Keys pro Quelle: `openalex_total`, `base_total`, etc.
- `ForschungsstandResult.sources_used` reflektiert tatsaechlich genutzte Quellen

### FR-6: Language-Support
- `SearchScope.languages` Default aendern: `["en"]` → `["en", "de"]`
- BASE-Queries werden automatisch auf `dclang` gefiltert
- OpenAlex: `filter=language:en|de`

## Nicht-Funktionale Anforderungen

### NFR-1: Keine neuen Dependencies
- Nur `httpx` (bereits vorhanden) fuer HTTP
- Keine neuen Packages

### NFR-2: Graceful Degradation
- Wenn eine Quelle nicht erreichbar: Warning loggen, mit restlichen Quellen fortfahren
- Wenn alle Quellen fehlschlagen: bestehende Warning-Logik (Zeile 190-196)

### NFR-3: Performance
- Parallele API-Calls via `asyncio.gather` (nicht sequentiell)
- Timeout: 30s pro Quelle (wie bestehend)

### NFR-4: Testbarkeit
- Alle HTTP-Calls mockbar via `@patch`
- Pydantic-Modelle fuer API-Responses (validiert)
- Test-Factories: `_openalex_work()`, `_base_result()`

## Dependency Check (verifiziert)

| Check | Status |
|-------|--------|
| Feature existiert? | Nein (kein OpenAlex/BASE Code) |
| Bestehende Clients als Pattern? | Ja: `semantic_scholar.py`, `exa_client.py` |
| Konverter-Pattern? | Ja: `from_semantic_scholar()`, `from_exa()` in `paper_ranker.py` |
| httpx installiert? | Ja (pyproject.toml) |
| Test-Pattern? | Ja: `test_semantic_scholar.py`, `test_exa_client.py` |
| Branch? | master (Worktree noetig fuer Implementation) |
| Tests baseline? | 293 Tests passing |

## Abgrenzung (Out of Scope)

- PubMed, DBLP, CORE, DNB (spaetere Sprints)
- Full-Text Download (F9 Evidence Card Verification)
- Query-Optimierung pro Quelle (bestehende Queries werden fuer alle genutzt)
- OpenAlex Concepts/Topics API (nur Works-Suche)
