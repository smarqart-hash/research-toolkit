# Tasks: Smart Query Generation (001)

**Geschaetzte Dauer:** ~3-4h Implementation + Tests
**Branch:** `feature/001-smart-query-gen`

---

## Phase 1: Datenmodelle + Config (keine Abhaengigkeiten)

- [x] **T1: Pydantic-Modelle erstellen**
  `src/agents/query_generator.py` — `SearchScope`, `QuerySet` Klassen.
  Nur Modelle, keine Logik. Tests: Serialisierung, Defaults, Validierung.

- [x] **T2: Synonym-Map + Prompt-Config erstellen**
  `config/query_templates/synonyms.json` — ~50 akademische Terme.
  `config/query_templates/expand_prompt.txt` — System-Prompt fuer LLM.

- [x] **T3: LLM-Client erstellen**
  `src/utils/llm_client.py` — `LLMConfig`, `llm_complete()` Funktion.
  OpenAI-kompatibles Chat-Completions-Format via httpx.
  Tests: Mock-Response, Timeout-Handling, fehlender API-Key.

## Phase 2: Kern-Logik (abhaengig von Phase 1)

- [x] **T4: Lokale Expansion implementieren**
  `_expand_local(topic, leitfragen) -> QuerySet` in `query_generator.py`.
  Synonym-Map laden, Boolean-Queries bauen, Exa-Queries formulieren.
  Tests: Min. 3 SS + 2 Exa Queries, Synonym-Matching, Edge Cases.

- [x] **T5: LLM-Enhanced Expansion implementieren**
  `_expand_llm(topic, leitfragen, config) -> QuerySet` in `query_generator.py`.
  Prompt laden, LLM-Call, JSON-Response parsen, Fallback bei Fehler.
  Tests: Mock-LLM-Response, JSON-Parse-Fehler, Timeout-Fallback.

- [x] **T6: Public API + Fallback-Kette**
  `expand_queries()` und `refine_topic()` als oeffentliche Funktionen.
  Fallback: LLM → lokal → Topic-only. `source`-Feld im QuerySet setzen.
  Tests: Fallback-Kette, source-Tracking.

## Phase 3: Integration (abhaengig von Phase 2)

- [x] **T7: `search_papers()` erweitern**
  `forschungsstand.py` — `refine` + `no_validate` Parameter.
  SS-Queries an SS-Client, Exa-Queries an Exa-Client (getrennt).
  Tests: Regression (ohne refine identisch), mit refine korrekte Trennung.

- [x] **T8: `validate_queries()` implementieren**
  Dry-Run: Top-1 Ergebnis pro Query, 0-Ergebnis-Queries entfernen.
  Garantie: min. 1 Query bleibt (Fallback auf Topic).
  Tests: Mock-API, Query-Entfernung, Fallback-Garantie.

- [x] **T9: CLI-Flags hinzufuegen**
  `cli.py` — `--refine` / `-r` und `--no-validate` Flags.
  Flags an `search_papers()` durchreichen. Rich-Output fuer QuerySet.
  Tests: CLI-Smoke-Test (Typer testing).

## Phase 4: Qualitaetssicherung

- [x] **T10: Coverage + Ruff + Regression**
  `pytest tests/ -v` — alle 248+ Tests passing.
  `ruff check src/agents/query_generator.py src/utils/llm_client.py`
  Coverage >= 90% fuer neue Module.

---

## Abhaengigkeits-Graph

```
T1 ──┐
T2 ──┼── T4 ──┐
T3 ──┘   T5 ──┼── T6 ── T7 ── T9 ── T10
              │   T8 ──────────┘
              └────────────────┘
```

Phase 1 (T1-T3) kann parallel. Phase 2 (T4-T6) sequenziell.
Phase 3 (T7-T9) sequenziell. T10 am Ende.