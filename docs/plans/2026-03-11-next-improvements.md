# Next Improvements — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 4 offene Verbesserungen nach Search Quality Sprint: OA-spezifische Queries, Exa DACH-Domains, SPECTER2-Setup, F20-Dokumentation.

**Architecture:** Jeder Task ist unabhängig — keine Abhängigkeiten untereinander. OA-Queries erweitern `QuerySet` + `query_generator.py`. Exa-Domains sind ein 3-Zeilen-Edit. SPECTER2 ist reines Setup. F20 ist Docs.

**Tech Stack:** Python 3.11+, httpx, sentence-transformers (optional), pytest

**Priorität:** Task 1 (OA-Queries) hat den grössten Impact auf Suchqualität. Task 2 (Exa DACH) ist ein Quickwin. Task 3 (SPECTER2) ist Setup. Task 4 (F20 Docs) ist reine Dokumentation.

---

## Task 1: OA-spezifische Queries (eigener Typ statt SS-Queries wiederverwenden)

**Problem:** `forschungsstand.py` übergibt `ss_queries` (Boolean-Format wie `"topic AND aspect"`) an OpenAlex. OpenAlex interpretiert das als Freitext — Boolean-Operatoren werden ignoriert oder verschlechtern Ergebnisse.

**Lösung:** `QuerySet` um `oa_queries` erweitern. `query_generator.py` generiert OA-optimierte Queries (Freitext, keine Boolean-Ops). `forschungsstand.py` nutzt `oa_queries` für OpenAlex.

**Files:**
- Modify: `src/agents/query_generator.py` — `QuerySet` Model + `_expand_local()` + `_expand_llm()`
- Modify: `src/agents/forschungsstand.py` — `_search_openalex()` nutzt `oa_queries`
- Modify: `config/query_templates/expand_prompt.txt` — OA-Queries im LLM-Prompt
- Test: `tests/test_query_generator.py`
- Test: `tests/test_forschungsstand.py`

### Step 1: Write failing test for QuerySet.oa_queries

```python
# tests/test_query_generator.py — neue Test-Klasse

class TestOaQueries:
    def test_queryset_has_oa_queries(self):
        """QuerySet muss oa_queries Feld haben."""
        qs = QuerySet(
            research_question="Test",
            ss_queries=["q1"],
            exa_queries=["q2"],
            oa_queries=["q3"],
            source="local",
        )
        assert qs.oa_queries == ["q3"]

    def test_local_expansion_generates_oa_queries(self):
        """Lokale Expansion erzeugt OA-Queries ohne Boolean-Operatoren."""
        qs = _expand_local("machine learning fairness")
        assert len(qs.oa_queries) >= 2
        for q in qs.oa_queries:
            assert " AND " not in q
            assert " OR " not in q
```

Run: `pytest tests/test_query_generator.py::TestOaQueries -v`
Expected: FAIL — `oa_queries` Feld existiert nicht in QuerySet

### Step 2: Extend QuerySet model

In `src/agents/query_generator.py`, `QuerySet` Pydantic Model erweitern:

```python
class QuerySet(BaseModel):
    research_question: str
    ss_queries: list[str]
    exa_queries: list[str]
    oa_queries: list[str] = []       # NEU — Freitext-Queries fuer OpenAlex
    source: Literal["local", "llm"]
```

### Step 3: Generate OA queries in _expand_local()

In `_expand_local()` (ca. Line 99-143) nach den Exa-Queries:

```python
# OA-Queries: Freitext ohne Boolean-Operatoren, concept-fokussiert
oa_queries = [
    topic,                                          # Basis-Query
    f"{topic} survey",                              # Survey-Fokus
    *[f"{topic} {syn}" for syn in synonyms[:2]],    # Synonym-Varianten
]
```

OA-Queries sind bewusst kürzer und ohne Boolean — OpenAlex nutzt eigene Relevanz-Engine.

### Step 4: Run tests to verify they pass

Run: `pytest tests/test_query_generator.py::TestOaQueries -v`
Expected: PASS

### Step 5: Write failing test for LLM expansion

```python
# tests/test_query_generator.py

def test_llm_expansion_includes_oa_queries(self, mock_llm):
    """LLM-Expansion muss oa_queries im Response parsen."""
    mock_llm.return_value = json.dumps({
        "research_question": "test",
        "ss_queries": ["q1 AND q2"],
        "exa_queries": ["what is q1"],
        "oa_queries": ["q1 q2 survey"],
    })
    qs = asyncio.run(_expand_llm("test topic", ["test"]))
    assert len(qs.oa_queries) >= 1
```

Run: `pytest tests/test_query_generator.py::test_llm_expansion_includes_oa_queries -v`
Expected: FAIL — LLM-Parser kennt `oa_queries` nicht

### Step 6: Update _expand_llm() to parse oa_queries

In `_expand_llm()` (ca. Line 158-208), JSON-Parsing erweitern:

```python
oa_queries = data.get("oa_queries", [])
if not oa_queries:
    # Fallback: SS-Queries ohne Boolean-Operatoren
    oa_queries = [re.sub(r"\s+(AND|OR|NOT)\s+", " ", q) for q in ss_queries]
```

### Step 7: Update expand_prompt.txt

In `config/query_templates/expand_prompt.txt` das JSON-Schema erweitern:

```
Antwort-Format (JSON):
{
  "research_question": "...",
  "ss_queries": ["Boolean-Query 1", ...],
  "exa_queries": ["Natural Language Query 1", ...],
  "oa_queries": ["Freitext-Query 1 (KEINE Boolean-Operatoren)", ...]
}

oa_queries: Kurze Freitext-Queries fuer OpenAlex. Kein AND/OR/NOT.
Fokus auf Konzepte und Synonyme. 3-5 Queries.
```

### Step 8: Run all query generator tests

Run: `pytest tests/test_query_generator.py -v`
Expected: ALL PASS

### Step 9: Write failing test for forschungsstand OA query usage

```python
# tests/test_forschungsstand.py — in bestehender Testklasse

async def test_search_openalex_uses_oa_queries(self, ...):
    """OpenAlex-Suche nutzt oa_queries statt ss_queries."""
    # Mock expand_queries um QuerySet mit oa_queries zurueckzugeben
    # Assert: openalex_client.search_works wird mit oa_queries aufgerufen
```

### Step 10: Update forschungsstand.py to use oa_queries

In `_search_openalex()` bzw. der OpenAlex-Schleife in `search_papers()`:

```python
# Vorher: for query in ss_queries:
# Nachher:
oa_queries = query_set.oa_queries if query_set and query_set.oa_queries else ss_queries
for query in oa_queries:
    results = await oa_client.search_works(query, ...)
```

Fallback auf `ss_queries` wenn `oa_queries` leer (Backward Compatibility ohne --refine).

### Step 11: Run full test suite

Run: `pytest tests/ -v`
Expected: ALL PASS (476+ Tests)

### Step 12: Commit

```bash
git add src/agents/query_generator.py src/agents/forschungsstand.py \
        config/query_templates/expand_prompt.txt \
        tests/test_query_generator.py tests/test_forschungsstand.py
git commit -m "feat: add OA-specific queries to QuerySet (no Boolean ops)"
```

---

## Task 2: Exa Domain-Liste für DACH erweitern (GESIS, DNB, ZBW)

**Problem:** Exa `include_domains` enthält nur englischsprachige Quellen. DACH-Repositorien fehlen.

**Files:**
- Modify: `src/agents/exa_client.py:82-94` — Domain-Liste erweitern
- Test: `tests/test_exa_client.py`

### Step 1: Write failing test

```python
# tests/test_exa_client.py

def test_include_domains_contain_dach_sources():
    """Exa Domain-Liste muss DACH-Repositorien enthalten."""
    from src.agents.exa_client import ExaClient
    # Payload bauen und pruefen
    client = ExaClient(api_key="test")
    # Domains aus dem Payload extrahieren (je nach Implementierung)
    expected_dach = ["gesis.org", "dnb.de", "zbw.eu"]
    # Assert alle DACH-Domains sind enthalten
```

Run: `pytest tests/test_exa_client.py::test_include_domains_contain_dach_sources -v`
Expected: FAIL

### Step 2: Add DACH domains to exa_client.py

In `src/agents/exa_client.py`, Line 82-94, drei Domains ergänzen:

```python
"include_domains": [
    "arxiv.org",
    "doi.org",
    "nature.com",
    "ieee.org",
    "sciencedirect.com",
    "springer.com",
    "mdpi.com",
    "wiley.com",
    "acm.org",
    "nih.gov",
    "nasa.gov",
    # DACH-Repositorien
    "gesis.org",
    "dnb.de",
    "zbw.eu",
],
```

### Step 3: Run test

Run: `pytest tests/test_exa_client.py -v`
Expected: ALL PASS

### Step 4: Commit

```bash
git add src/agents/exa_client.py tests/test_exa_client.py
git commit -m "feat: add DACH domains (GESIS, DNB, ZBW) to Exa search"
```

---

## Task 3: SPECTER2 installieren + verifizieren

**Problem:** SPECTER2 (sentence-transformers) ist als `[nlp]` Optional Dependency definiert aber nicht installiert. Enhanced Scoring fällt still auf Heuristik zurück.

**Files:**
- Keine Code-Änderungen — reines Setup
- Verify: `paper_ranker.py` Enhanced Scoring funktioniert

### Step 1: Install nlp extra

```bash
pip install -e ".[nlp]"
```

Expected: `sentence-transformers>=3.0` + `numpy>=1.26` werden installiert.

### Step 2: Verify SPECTER2 loads

```bash
python -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('allenai/specter2_base'); print('OK:', m)"
```

Expected: Model wird heruntergeladen (~440MB) und geladen.

### Step 3: Run doctor command

```bash
python cli.py doctor
```

Expected: SPECTER2 zeigt ✓ statt ✗.

### Step 4: Run ranking tests

```bash
pytest tests/test_paper_ranker.py -v
```

Expected: ALL PASS — Enhanced Scoring Tests laufen jetzt mit echtem Model.

### Step 5: Commit (nur falls pyproject.toml geändert)

Kein Commit nötig — reine lokale Installation.

---

## Task 4: F20 Multi-Query-Workflow dokumentieren

**Problem:** `--refine` mit OpenRouter ist undokumentiert. User wissen nicht wie sie den 2-Tier-Query-Workflow nutzen.

**Files:**
- Create: `docs/guides/multi-query-workflow.md`
- Modify: `CLAUDE.md` — F20 als gelöst markieren

### Step 1: Dokumentation schreiben

```markdown
# Multi-Query-Workflow (--refine)

## Übersicht

`--refine` aktiviert 2-stufige Query-Expansion:
1. **Lokal** (immer): Synonym-Map + Boolean-Queries + Exa Natural Language
2. **LLM** (optional): OpenRouter generiert diverse, DACH-aware Queries

## Voraussetzungen

- `OPENROUTER_API_KEY` oder `LLM_API_KEY` in `.env` (nur für Stufe 2)
- Ohne Key: Fallback auf lokale Expansion (funktioniert immer)

## Nutzung

research-toolkit search "machine learning fairness" --refine
research-toolkit search "KI in der Verwaltung" --refine --sources ss,openalex,exa

## Query-Typen

| Typ | Format | Ziel |
|-----|--------|------|
| SS-Queries | Boolean (`topic AND aspect`) | Semantic Scholar |
| OA-Queries | Freitext (keine Boolean-Ops) | OpenAlex |
| Exa-Queries | Natural Language (explorativ) | Exa Search |

## Validierung

`--no-validate` überspringt Dry-Run (schneller, aber keine Qualitätsprüfung).
Default: Jede Query wird mit limit=1 getestet, leere Queries entfernt.

## Troubleshooting

- "LLM expansion failed" → Key prüfen, Fallback auf lokal ist OK
- Wenige Ergebnisse → `--refine` + `--sources ss,openalex,exa` + `--append`
```

### Step 2: Update CLAUDE.md — F20 als dokumentiert markieren

Im `CLAUDE.md` Abschnitt "Noch offen": F20 Eintrag aktualisieren.

### Step 3: Update Memory — F20 als gelöst markieren

### Step 4: Commit

```bash
git add docs/guides/multi-query-workflow.md CLAUDE.md
git commit -m "docs: add multi-query workflow guide (F20)"
```

---

## Zusammenfassung

| Task | Typ | Aufwand | Impact |
|------|-----|---------|--------|
| 1. OA-Queries | Feature | Medium | HIGH — bessere OpenAlex-Ergebnisse |
| 2. Exa DACH | Quickwin | Klein | MEDIUM — DACH-Abdeckung |
| 3. SPECTER2 | Setup | Klein | MEDIUM — Enhanced Scoring aktiv |
| 4. F20 Docs | Docs | Klein | LOW — Nutzbarkeit |

**Empfohlene Reihenfolge:** Task 2 → Task 3 → Task 1 → Task 4
(Quickwins zuerst, dann das grösste Feature, Docs am Ende)
