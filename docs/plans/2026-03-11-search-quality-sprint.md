# Search Quality Sprint — F19 + Quickwins

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Source-Quota fuer Exa (F19), hoehere Limits, Language-Feld durchreichen, LLM-Key-Mapping fixen, duplizierte Funktion bereinigen.

**Architecture:** Aenderungen in 4 Modulen: paper_ranker.py (Quota + language), forschungsstand.py (per_page + Duplikat-Fix), openalex_client.py (API Key), llm_client.py (Key-Mapping). Prompt-Optimierung in config/.

**Tech Stack:** Python 3.11+, Pydantic v2, httpx, pytest

---

### Task 1: Duplikat _check_low_recall entfernen

**Files:**
- Modify: `src/agents/forschungsstand.py:84-113` (erste Kopie entfernen)

**Step 1: Entferne die erste _check_low_recall Definition (Zeile 84-113)**

Die Funktion existiert doppelt (Zeile 84-113 UND 146-175). Entferne die erste Kopie.
Behalte die zweite (Zeile 146+) weil sie naeher an _check_source_balance steht.

```python
# ENTFERNE Zeile 84-113 komplett (erste _check_low_recall)
# Die zweite Definition ab Zeile 146 bleibt
```

**Step 2: Tests ausfuehren**

Run: `pytest tests/test_forschungsstand.py -v`
Expected: Alle Tests PASS (keine Aenderung am Verhalten)

**Step 3: Commit**

```bash
git add src/agents/forschungsstand.py
git commit -m "fix: remove duplicate _check_low_recall function (rebase artifact)"
```

---

### Task 2: F19 — Source-Quota im Ranking

**Files:**
- Modify: `src/agents/paper_ranker.py` (rank_papers erweitern)
- Test: `tests/test_paper_ranker.py`

**Step 1: Schreibe failing Tests**

```python
class TestSourceQuota:
    """Source-Quota: Mindestens N Papers pro aktiver Quelle."""

    def test_exa_papers_preserved_with_quota(self):
        """Exa-Papers ueberleben Ranking dank Source-Quota."""
        # 20 SS-Papers mit hohem Score + 5 Exa-Papers mit niedrigem Score
        ss_papers = [
            UnifiedPaper(
                paper_id=f"ss-{i}",
                title=f"SS Paper {i}",
                abstract="Abstract",
                year=2024,
                citation_count=100,
                source="semantic_scholar",
                is_open_access=True,
            )
            for i in range(20)
        ]
        exa_papers = [
            UnifiedPaper(
                paper_id=f"exa-{i}",
                title=f"Exa Paper {i}",
                abstract="Abstract",
                year=2024,
                citation_count=None,
                source="exa",
            )
            for i in range(5)
        ]
        all_papers = [*ss_papers, *exa_papers]
        ranked = rank_papers(all_papers, top_k=15)
        exa_count = sum(1 for p in ranked if p.source == "exa")
        assert exa_count >= 3, f"Source-Quota: erwartet >= 3 Exa, aber nur {exa_count}"

    def test_quota_does_not_exceed_available(self):
        """Quota nimmt nicht mehr als verfuegbar."""
        ss_papers = [
            UnifiedPaper(
                paper_id=f"ss-{i}",
                title=f"SS Paper {i}",
                source="semantic_scholar",
                year=2024,
            )
            for i in range(20)
        ]
        exa_papers = [
            UnifiedPaper(
                paper_id="exa-0",
                title="Exa Paper 0",
                source="exa",
                year=2024,
            )
        ]
        ranked = rank_papers([*ss_papers, *exa_papers], top_k=15)
        exa_count = sum(1 for p in ranked if p.source == "exa")
        # Nur 1 Exa verfuegbar, Quota kann nicht mehr als 1 liefern
        assert exa_count == 1

    def test_quota_respects_top_k(self):
        """Ergebnis ueberschreitet top_k nicht durch Quota."""
        papers = [
            UnifiedPaper(
                paper_id=f"s-{i}",
                title=f"Paper {i}",
                source=src,
                year=2024,
            )
            for i, src in enumerate(
                ["semantic_scholar"] * 10 + ["openalex"] * 10 + ["exa"] * 10
            )
        ]
        ranked = rank_papers(papers, top_k=10)
        assert len(ranked) == 10

    def test_no_quota_without_top_k(self):
        """Ohne top_k wird keine Quota angewendet (alle Papers zurueck)."""
        papers = [
            UnifiedPaper(
                paper_id=f"s-{i}",
                title=f"Paper {i}",
                source="semantic_scholar",
                year=2024,
            )
            for i in range(5)
        ]
        ranked = rank_papers(papers)
        assert len(ranked) == 5
```

Run: `pytest tests/test_paper_ranker.py::TestSourceQuota -v`
Expected: FAIL (Source-Quota nicht implementiert)

**Step 2: Implementiere Source-Quota in rank_papers**

In `paper_ranker.py`, aendere `rank_papers()` — nach dem Sortieren, vor dem top_k-Cut:

```python
def _apply_source_quota(
    ranked: list[UnifiedPaper],
    top_k: int,
    *,
    min_per_source: int = 3,
) -> list[UnifiedPaper]:
    """Garantiert Mindestanzahl Papers pro aktiver Quelle im Top-K.

    Algorithmus:
    1. Sammle aktive Quellen (die Papers im Pool haben)
    2. Reserviere min_per_source Plaetze pro Quelle (Top-N der jeweiligen Quelle)
    3. Fuelle restliche Plaetze nach globalem Score auf
    """
    sources = list(dict.fromkeys(p.source for p in ranked))
    if len(sources) <= 1:
        return ranked[:top_k]

    # Phase 1: Quota-Papers pro Quelle
    reserved: list[UnifiedPaper] = []
    reserved_ids: set[str] = set()
    for source in sources:
        source_papers = [p for p in ranked if p.source == source]
        quota = min(min_per_source, len(source_papers))
        for paper in source_papers[:quota]:
            if paper.paper_id not in reserved_ids:
                reserved = [*reserved, paper]
                reserved_ids.add(paper.paper_id)

    # Phase 2: Restliche Plaetze nach Score
    remaining_slots = max(0, top_k - len(reserved))
    fill = [p for p in ranked if p.paper_id not in reserved_ids][:remaining_slots]

    # Zusammenfuehren und nach Score neu sortieren
    result = [*reserved, *fill]
    result.sort(key=lambda p: p.relevance_score, reverse=True)
    return result[:top_k]
```

In `rank_papers()`, ersetze die beiden `if top_k:` Bloecke:

```python
    # Alte Zeilen:
    # if top_k:
    #     return ranked[:top_k]

    # Neue Zeilen:
    if top_k:
        return _apply_source_quota(ranked, top_k)
```

**Step 3: Tests ausfuehren**

Run: `pytest tests/test_paper_ranker.py -v`
Expected: Alle Tests PASS (alte + neue)

**Step 4: Commit**

```bash
git add src/agents/paper_ranker.py tests/test_paper_ranker.py
git commit -m "feat: source quota in ranking — min 3 papers per source (F19)"
```

---

### Task 3: Language-Feld in UnifiedPaper durchreichen

**Files:**
- Modify: `src/agents/paper_ranker.py` (UnifiedPaper + from_openalex)
- Test: `tests/test_paper_ranker.py`

**Step 1: Schreibe failing Test**

```python
class TestLanguageField:
    def test_unified_paper_has_language(self):
        paper = UnifiedPaper(
            paper_id="test", title="Test", source="openalex", language="de"
        )
        assert paper.language == "de"

    def test_unified_paper_language_default_none(self):
        paper = UnifiedPaper(paper_id="test", title="Test", source="openalex")
        assert paper.language is None

    def test_from_openalex_passes_language(self):
        from src.agents.openalex_client import OpenAlexWork
        work = OpenAlexWork(
            id="W1", display_name="Test", language="de", relevance_score=0.5,
        )
        paper = from_openalex(work)
        assert paper.language == "de"
```

Run: `pytest tests/test_paper_ranker.py::TestLanguageField -v`
Expected: FAIL (language Feld fehlt)

**Step 2: Implementiere**

In `UnifiedPaper` (paper_ranker.py), neues Feld:
```python
    language: str | None = None  # ISO 639-1, z.B. "en", "de"
```

In `from_openalex()`, ergaenze:
```python
    return UnifiedPaper(
        ...
        is_open_access=work.open_access.is_oa,
        language=work.language,  # NEU
    )
```

**Step 3: Tests ausfuehren**

Run: `pytest tests/test_paper_ranker.py -v`
Expected: Alle PASS

**Step 4: Commit**

```bash
git add src/agents/paper_ranker.py tests/test_paper_ranker.py
git commit -m "feat: pass language field through UnifiedPaper from OpenAlex"
```

---

### Task 4: per_page/limit hochsetzen

**Files:**
- Modify: `src/agents/forschungsstand.py` (SearchConfig default + Exa num_results)
- Test: `tests/test_forschungsstand.py`

**Step 1: Schreibe failing Test**

```python
class TestHigherLimits:
    def test_default_max_results_per_query_100(self):
        config = SearchConfig()
        assert config.max_results_per_query == 100

    def test_exa_num_results_matches_config(self):
        """Exa nutzt config.max_results_per_query (statt hardcoded 20)."""
        # Pruefe dass _search_exa den config-Wert nutzt
        from unittest.mock import MagicMock
        from src.agents.forschungsstand import _search_exa
        from src.agents.exa_client import ExaSearchResponse

        config = SearchConfig(sources=["exa"], max_results_per_query=50)
        stats = {"exa_total": 0, "exa_errors": 0}

        call_args = {}

        async def mock_search(query, *, num_results=20, **kwargs):
            call_args["num_results"] = num_results
            return ExaSearchResponse(results=[])

        async def run():
            with patch(
                "src.agents.forschungsstand.ExaClient"
            ) as mock_cls:
                instance = mock_cls.return_value
                instance.is_available = True
                instance.search_papers = mock_search
                await _search_exa(["test"], config, stats)

        asyncio.run(run())
        assert call_args.get("num_results") == 50
```

Run: `pytest tests/test_forschungsstand.py::TestHigherLimits -v`
Expected: FAIL

**Step 2: Implementiere**

In `SearchConfig`:
```python
    max_results_per_query: int = 100  # war 50
```

In `_search_exa()`, aendere den hardcoded Wert:
```python
    # Alt:
    exa_response = await exa_client.search_papers(query, num_results=20)

    # Neu:
    exa_response = await exa_client.search_papers(
        query, num_results=config.max_results_per_query,
    )
```

**Step 3: Bestehende Tests anpassen**

`test_defaults` in TestSearchConfig aendern:
```python
    def test_defaults(self):
        config = SearchConfig()
        assert config.max_results_per_query == 100  # war 50
```

**Step 4: Tests ausfuehren**

Run: `pytest tests/test_forschungsstand.py -v`
Expected: Alle PASS

**Step 5: Commit**

```bash
git add src/agents/forschungsstand.py tests/test_forschungsstand.py
git commit -m "feat: raise per_page limits — SS 100, OA 200, Exa dynamic"
```

---

### Task 5: LLM_API_KEY Mapping fuer OpenRouter

**Files:**
- Modify: `src/utils/llm_client.py`
- Test: `tests/test_query_generator.py` (oder neuer test)

**Step 1: Schreibe failing Test**

```python
# In tests/test_llm_client.py (NEU)
import os
from unittest.mock import patch
from src.utils.llm_client import load_llm_config

class TestLlmConfig:
    def test_openrouter_key_fallback(self):
        """OPENROUTER_API_KEY wird als Fallback fuer LLM_API_KEY genutzt."""
        env = {"OPENROUTER_API_KEY": "sk-or-test", "LLM_API_KEY": ""}
        with patch.dict(os.environ, env, clear=False):
            # LLM_API_KEY leer -> Fallback auf OPENROUTER_API_KEY
            os.environ.pop("LLM_API_KEY", None)
            config = load_llm_config()
            assert config.is_available is True
            assert config.api_key == "sk-or-test"

    def test_llm_key_has_priority(self):
        """LLM_API_KEY hat Vorrang vor OPENROUTER_API_KEY."""
        env = {"LLM_API_KEY": "sk-llm", "OPENROUTER_API_KEY": "sk-or"}
        with patch.dict(os.environ, env, clear=False):
            config = load_llm_config()
            assert config.api_key == "sk-llm"
```

Run: `pytest tests/test_llm_client.py -v`
Expected: FAIL

**Step 2: Implementiere**

In `llm_client.py`, aendere `load_llm_config()`:
```python
def load_llm_config() -> LLMConfig:
    """Laedt LLM-Config aus Environment-Variablen.

    Fallback: OPENROUTER_API_KEY wenn LLM_API_KEY nicht gesetzt.
    """
    api_key = os.environ.get("LLM_API_KEY", "") or os.environ.get("OPENROUTER_API_KEY", "")
    return LLMConfig(
        base_url=os.environ.get("LLM_BASE_URL", _DEFAULT_BASE_URL),
        api_key=api_key,
        model=os.environ.get("LLM_MODEL", _DEFAULT_MODEL),
    )
```

**Step 3: Tests ausfuehren**

Run: `pytest tests/test_llm_client.py -v`
Expected: Alle PASS

**Step 4: Commit**

```bash
git add src/utils/llm_client.py tests/test_llm_client.py
git commit -m "feat: OPENROUTER_API_KEY fallback for LLM_API_KEY"
```

---

### Task 6: OpenAlex API Key + CLAUDE.md committen

**Files:**
- Stage: `src/agents/openalex_client.py` (bereits geaendert, unstaged)
- Stage: `CLAUDE.md` (bereits geaendert, unstaged)
- Stage: `docs/meta-loop/findings-v4.md` (untracked)

**Step 1: Tests ausfuehren**

Run: `pytest tests/test_openalex_client.py -v`
Expected: Alle PASS

**Step 2: Commit**

```bash
git add src/agents/openalex_client.py CLAUDE.md docs/meta-loop/findings-v4.md
git commit -m "docs: commit findings-v4 + OpenAlex API key support + CLAUDE.md update"
```

---

### Task 7: Prompt-Optimierung fuer expand_prompt.txt

**Files:**
- Modify: `config/query_templates/expand_prompt.txt`

**Step 1: Invoke prompt-engineer Skill**

Nutze den `prompt-engineer` Skill auf `expand_prompt.txt` mit Fokus auf:
- Bessere Query-Diversitaet (F20: verschiedene Aspekte des Themas abdecken)
- Explizite Anweisung: "Queries MUESSEN unterschiedliche Aspekte abdecken"
- OpenAlex-spezifische Queries (OA nutzt die SS-Queries — eigene waeren besser)
- Deutsche Synonyme in SS-Queries einbauen fuer DACH-Relevanz

**Step 2: Aktualisierter Prompt**

Ersetze expand_prompt.txt mit optimierter Version. Kernverbesserungen:
- Diversitaets-Constraint: "Jede Query muss einen ANDEREN Aspekt abdecken"
- OA-Queries: Neues Feld `oa_queries` fuer breitere akademische Suche
- Deutsche Terms: "Ergaenze deutsche Synonyme in Klammern wo sinnvoll"
- Mindest-Aspekte: "Decke mindestens 3 verschiedene Sub-Topics ab"

**Step 3: Tests ausfuehren**

Run: `pytest tests/test_query_generator.py -v`
Expected: Alle PASS (Prompt aendert nur LLM-Verhalten, nicht lokale Expansion)

**Step 4: Commit**

```bash
git add config/query_templates/expand_prompt.txt
git commit -m "feat: optimize expand_prompt for query diversity + DACH coverage"
```

---

### Task 8: MEMORY.md + Finaler Test-Run

**Files:**
- Modify: `~/.claude/projects/.../memory/MEMORY.md`

**Step 1: Vollstaendiger Test-Run**

Run: `pytest tests/ -v`
Expected: 475+ Tests PASS

**Step 2: MEMORY.md updaten**

- Test-Count aktualisieren
- Sprint-Eintrag: "Search Quality Sprint"
- Offene Findings aktualisieren (F19 geloest, F21 Status)
- Technische Details: Source-Quota, per_page, language field

**Step 3: Finaler Commit**

```bash
git add CLAUDE.md  # falls weitere Aenderungen
git commit -m "docs: update CLAUDE.md with search quality sprint changes"
```

---

## Fuer Spaeter (NICHT in diesem Sprint)

- **F20 vollstaendig**: Multi-Query-Workflow als CLI-Subcommand (`search --strategy multi-query`)
- **Exa Domain-Liste erweitern**: Deutsche Repos (GESIS, DNB, ZBW)
- **SPECTER2 installieren**: `pip install sentence-transformers` fuer Enhanced Ranking
- **S2 API Key**: Bereits in .env — muss getestet werden ob Rate Limits besser
- **OpenAlex Pagination**: Cursor-basiert fuer > 200 Papers
- **OA-spezifische Queries**: Eigener Query-Typ in QuerySet (nicht SS-Queries wiederverwenden)
