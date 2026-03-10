# Sprint 5 Handover: Multi-Source Search (OpenAlex)

> Status: ERLEDIGT (Spec `003-multi-source-search`)
> Branch: `feature/003-multi-source-search`
> Vorgaenger: Sprint 4 (Agentic Review Loop)

---

## Ziel

Search-Pipeline von 2 auf 3 Quellen erweitert: **OpenAlex** ergaenzt
Semantic Scholar + Exa. Flag-basierte Steuerung via `--sources`.
DACH-Support durch Language-Default `["en", "de"]`.

## Ergebnis

### Neue Dateien
- `src/agents/openalex_client.py` — Async OpenAlex Works API Client
- `tests/test_openalex_client.py` — 25 Tests (Modelle, HTTP, Abstract-Rekonstruktion)

### Geaenderte Dateien
- `src/agents/paper_ranker.py` — `from_openalex()` Konverter, Relevance Score Update
- `src/agents/forschungsstand.py` — `SearchConfig.sources`, `asyncio.gather` Parallelisierung
- `cli.py` — `--sources` Flag, `--exa/--no-exa` Deprecation
- `src/agents/query_generator.py` — Language-Default `["en", "de"]`
- `CLAUDE.md` — Aktualisiert

### Kennzahlen
- 420 Tests, alle passing
- 90% Gesamt-Coverage
- OpenAlex Client: 96% Coverage

## Design-Entscheidungen

- **BASE entfaellt** — IP-Whitelisting nicht praktikabel fuer Open-Source-CLI
- **OpenAlex deckt DACH ab** — via `filter=language:de`
- **`asyncio.gather`** statt sequentiell — alle Quellen parallel
- **`--sources` ersetzt `--exa/--no-exa`** — Deprecation-Warning fuer 1 Sprint

## Abhaengigkeiten fuer naechsten Sprint

- `SearchConfig.sources` ist erweiterbar (z.B. `"pubmed"`, `"core"`)
- `from_X()` Konverter-Pattern in `paper_ranker.py` skaliert
- BASE koennte spaeter als opt-in ergaenzt werden (mit Setup-Guide)
