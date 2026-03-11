# ~~Sprint 3 Handover: Smart Query Generation~~

> Status: ERLEDIGT (merged 2026-03-10, Spec `001-smart-query-gen`)
> Branch: `feature/001-smart-query-gen` → master
> Vorgaenger: Sprint 1+2 (abgeschlossen), kein offener PR

---

## Ziel

`generate_search_queries()` in `forschungsstand.py:191` von Heuristik
auf LLM-gestuetzte Query-Optimierung upgraden. Bessere Recall-Rate,
weniger manuelle Nachsteuerung.

## Ist-Zustand (Code verifiziert)

### `forschungsstand.py:191-205` — Aktuelle Heuristik
```python
def generate_search_queries(topic: str, leitfragen: list[str]) -> list[str]:
    queries = [topic]
    for frage in leitfragen:
        cleaned = frage.strip().rstrip("?")
        for prefix in ["Wie ", "Was ", "Welche ", "Warum ", "Inwieweit "]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break
        queries = [*queries, f"{topic} {cleaned}"]
    return queries
```

**Probleme:**
- Nur Fragewoerter entfernen + Topic konkatenieren
- Keine Synonyme, Boolean-Operatoren, Scope-Eingrenzung
- SS und Exa bekommen identische Queries (brauchen verschiedene Formate)
- Keine Validierung ob Queries relevante Ergebnisse liefern

### Aufruf in `search_papers()` (Zeile 79-188)
- `search_papers(topic, queries=None)` → generiert Queries automatisch
- `search_papers(topic, queries=[...])` → nimmt uebergebene Queries
- Ergebnis geht an SS-Client + optional Exa-Client
- Danach: Deduplizierung → Ranking (SPECTER2) → Screening → Return

### Relevante Dateien
- `src/agents/forschungsstand.py` — Hauptmodul, zu aendern
- `src/agents/semantic_scholar.py` — SS-Client, akzeptiert `query: str`
- `src/agents/exa_client.py` — Exa-Client, akzeptiert `query: str`
- `src/agents/paper_ranker.py` — Ranking, unveraendert
- `cli.py` — Typer CLI, `search` Command

### Test-Baseline
```bash
pytest tests/ -v  # 248 Tests, alle passing
```

---

## Soll-Zustand

### Neues Modul: `src/agents/query_generator.py`

```python
class SearchScope(BaseModel):
    year_range: tuple[int, int] | None = None
    languages: list[str] = ["en"]
    venues: list[str] = []

class QuerySet(BaseModel):
    research_question: str
    ss_queries: list[str]    # Boolean-Format fuer Semantic Scholar
    exa_queries: list[str]   # Natural Language fuer Exa
    scope: SearchScope

async def refine_topic(topic: str) -> str:
    """Vages Topic → praezise Research Question (PICO/SPIDER)."""

async def expand_queries(research_question: str, scope: SearchScope) -> QuerySet:
    """Research Question → QuerySet mit Synonymen + Akronymen."""

async def validate_queries(query_set: QuerySet, ss_client, exa_client) -> QuerySet:
    """Dry-Run: Top-3 pruefen, bei < 0.5 Relevanz adjustieren."""
```

### Integration
- `forschungsstand.py`: `generate_search_queries()` delegiert an `query_generator`
  wenn `--refine` Flag gesetzt. Ohne Flag: alte Heuristik (kein Breaking Change).
- `cli.py`: `--refine` und `--brief-only` Flags hinzufuegen.

---

## Implementation Tasks (Reihenfolge)

1. **QuerySet + SearchScope Modelle** — Pydantic, in `query_generator.py`
2. **`refine_topic()`** — LLM-Call mit 3 Few-Shot-Beispielen
3. **`expand_queries()`** — LLM-Call, getrennte SS/Exa-Formate
4. **`validate_queries()`** — Dry-Run gegen APIs, Relevanz-Check
5. **Integration** — `--refine` Flag in `forschungsstand.py` + `cli.py`
6. **Config** — `config/query_templates/default.json` mit Few-Shot-Beispielen
7. **Tests** — Unit + Integration + Regression

## Akzeptanzkriterien

- [ ] `--refine` generiert mind. 5 Queries (3 SS + 2 Exa)
- [ ] Queries enthalten Synonyme die in der Heuristik fehlten
- [ ] Dry-Run Validation erkennt irrelevante Queries (>= 1 Test-Case)
- [ ] Ohne `--refine`: identisches Verhalten wie vorher (Regression)
- [ ] Kein neuer API-Key noetig (LLM via bestehenden Provider)
- [ ] Tests: >= 90% Coverage fuer `query_generator.py`
- [ ] `pytest tests/ -v` — alle bestehenden Tests passing

## Abhaengigkeiten

- LLM-Provider muss konfiguriert sein (aktuell: Claude/GPT via User-Wahl)
- Semantic Scholar API fuer Dry-Run Validation
- Kein neues Package noetig

## Risiken

- LLM-Latenz bei `refine_topic()` — ~2-3s extra pro Run
- API Rate Limits bei `validate_queries()` Dry-Run
- Exa-Queries koennen stark von SS-Queries abweichen → getrennt testen

## Konventionen (aus CLAUDE.md)

- `from __future__ import annotations` in jeder Datei
- Immutability: `queries = [*queries, new]` statt `.append()`
- Async: `httpx.AsyncClient` fuer externe APIs
- Pydantic v2: `BaseModel`, `computed_field`
- Black (line-length=100) + Ruff
- Deutsch: Docstrings + Kommentare. Englisch: Variablen + Funktionen
