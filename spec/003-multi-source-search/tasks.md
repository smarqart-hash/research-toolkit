# Spec 003: Multi-Source Search — Tasks

> Geschaetzte Gesamtdauer: ~8h
> Branch: `feature/003-multi-source-search`

## Phase 1: OpenAlex Client (TDD)

### T1: Pydantic-Modelle (~30min)
- [x] `src/agents/openalex_client.py` erstellen
- [x] `OpenAlexAuthor`, `OpenAlexAuthorship`, `OpenAlexOpenAccess` Modelle
- [x] `OpenAlexWork` mit `abstract` Property (Inverted Index → Klartext)
- [x] `OpenAlexSearchResponse` Modell
- [x] Tests: `tests/test_openalex_client.py` — Factory `_openalex_work()`, Abstract-Rekonstruktion, Edge Cases (leerer Index, None)

### T2: OpenAlexClient HTTP (~1h)
- [x] `OpenAlexClient.__init__(mailto=None)` mit `OPENALEX_MAILTO` Env-Fallback
- [x] `search_works(query, per_page, year_range, languages)` implementieren
- [x] Filter-Bau: `publication_year:2020-2026`, `language:en|de`
- [x] Retry bei 429 (analog SS/Exa Pattern)
- [x] Tests: Mocked HTTP (success, 429 retry, timeout, error), Filter-Kombination

## Phase 2: Integration in Ranking

### T3: `from_openalex()` Konverter (~30min)
- [x] `from_openalex(work: OpenAlexWork) -> UnifiedPaper` in `paper_ranker.py`
- [x] DOI-Extraktion (OpenAlex liefert `doi` als URL: `https://doi.org/10.xxx` → normalisieren)
- [x] `source="openalex"`, Authors aus Authorships
- [x] `relevance_score`: SS-Bonus anpassen → +0.1 fuer SS + OpenAlex (strukturierte Metadaten)
- [x] Tests: `test_paper_ranker.py` erweitern — `TestFromOpenAlex` Klasse

## Phase 3: Orchestrierung

### T4: `SearchConfig` refactoren (~30min)
- [x] `use_exa: bool` → `sources: list[str]` (Default: `["ss", "openalex"]`)
- [x] `languages: list[str]` hinzufuegen (Default: `["en", "de"]`)
- [x] Alle internen Aufrufe anpassen (Tests!)
- [x] Tests: bestehende `test_forschungsstand.py` anpassen (use_exa → sources)

### T5: `search_papers()` parallelisieren (~1.5h)
- [x] Hilfsfunktionen extrahieren: `_search_ss()`, `_search_openalex()`, `_search_exa()`
- [x] `asyncio.gather(*tasks, return_exceptions=True)` fuer parallele Suche
- [x] Stats-Dict erweitern: `openalex_total`, `openalex_errors`
- [x] Graceful Degradation: Exception → Warning, mit restlichen Quellen fortfahren
- [x] `ForschungsstandResult.sources_used` korrekt befuellen
- [x] Tests: Mock alle 3 Quellen, teste Partial Failure, teste sources-Filter

## Phase 4: CLI

### T6: `--sources` Flag (~30min)
- [x] `--sources` Option (Default: `"ss,openalex"`)
- [x] Komma-Split → `config.sources`
- [x] `--exa/--no-exa` Deprecation-Warning (1 Sprint, dann entfernen)
- [x] Rich-Panel zeigt aktive Quellen an
- [x] Tests: CLI-Args parsen (Typer Testing)

### T7: Language-Default anpassen (~15min)
- [x] `SearchScope.languages` Default in `query_generator.py`: `["en"]` → `["en", "de"]`
- [x] Tests: bestehende `test_query_generator.py` anpassen

## Phase 5: Abschluss

### T8: Integration-Test + Regression (~1h)
- [x] `pytest tests/ -v` — alle bestehenden Tests passing
- [x] Coverage pruefen: `pytest --cov=src --cov-report=term-missing`
- [x] Neuer Integrations-Test: `search_papers(sources=["ss", "openalex"])` mit Mocks
- [x] Regressions-Test: `search_papers()` ohne `sources` → Default-Verhalten

### T9: Docs + Env (~30min)
- [x] `CLAUDE.md` aktualisieren: OpenAlex in Modulstruktur + Environment Variables
- [x] `.env.example` erweitern: `OPENALEX_MAILTO=`
- [x] Sprint-5-Handover-Doc: `docs/plans/sprint-5-handover.md`

## Abhaengigkeiten

```
T1 → T2 → T3 → T5
              T4 → T5 → T6
                   T7
         T5 → T8 → T9
```

T1-T3 (Client + Konverter) sind unabhaengig von T4 (SearchConfig Refactoring).
T5 braucht beides. T6-T9 koennen nach T5 parallel.
