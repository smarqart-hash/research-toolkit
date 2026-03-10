# Sprint 6: Search Quality Fix — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the three search quality issues discovered in Meta-Loop v3: source-biased ranking (F18+F12), missing query accumulation (F13), and score serialization gap (F14).

**Architecture:** Source-aware ranking normalizes citation scores per-source (percentile within each source pool). Accumulation merges new results into existing session pool via `--append` flag. OpenAlex relevance pre-filter drops papers below API relevance threshold before entering the ranking pipeline.

**Tech Stack:** Python 3.11+, Pydantic v2, httpx, pytest, Typer CLI

**Findings addressed:** F12 (OpenAlex Relevanz), F13 (Akkumuliertes Suchen), F14 (Score-Serialisierung), F18 (Source-Bias im Ranking)

**Quality Gates:** TDD (Red-Green-Refactor), Adversarial Review nach Task 3 + Task 6

---

## Task 1: Source-Aware Relevance Score (F18 + F12)

**Files:**
- Modify: `src/agents/paper_ranker.py:57-88` (relevance_score)
- Test: `tests/test_paper_ranker.py`

### Step 1: Write failing tests

```python
# tests/test_paper_ranker.py — neue Test-Klasse

class TestSourceAwareRelevanceScore:
    """Testet source-normalisierte Scores."""

    def test_openalex_citation_cap(self):
        """OpenAlex Citation-Beitrag ist auf 0.15 gedeckelt (statt 0.4)."""
        paper = UnifiedPaper(
            paper_id="oa1", title="Highly Cited OA",
            citation_count=5000, source="openalex", year=2024,
            abstract="Test abstract",
        )
        # OA mit 5000 Cites soll NICHT hoeher ranken als
        # thematisch relevantes SS-Paper mit 50 Cites
        assert paper.relevance_score <= 0.75

    def test_ss_citation_weight_unchanged(self):
        """SS Citation-Gewicht bleibt bei max 0.4."""
        paper = UnifiedPaper(
            paper_id="ss1", title="SS Paper",
            citation_count=100, source="semantic_scholar", year=2024,
            abstract="Test", is_open_access=True,
        )
        assert paper.relevance_score > 0.5

    def test_openalex_high_cite_lower_than_ss_moderate_cite(self):
        """OA-Paper mit 3000 Cites rankt niedriger als SS mit 50 + OA + Abstract."""
        oa_paper = UnifiedPaper(
            paper_id="oa", title="Off-topic OA",
            citation_count=3000, source="openalex", year=2023,
        )
        ss_paper = UnifiedPaper(
            paper_id="ss", title="On-topic SS",
            citation_count=50, source="semantic_scholar", year=2024,
            abstract="Relevant abstract", is_open_access=True,
        )
        assert ss_paper.relevance_score > oa_paper.relevance_score

    def test_exa_no_citations_still_ranks(self):
        """Exa-Paper ohne Citations bekommt Score aus anderen Signalen."""
        paper = UnifiedPaper(
            paper_id="exa1", title="Exa Paper",
            source="exa", year=2025, abstract="Abstract vorhanden",
        )
        assert paper.relevance_score > 0.0
```

### Step 2: Run tests to verify they fail

Run: `pytest tests/test_paper_ranker.py::TestSourceAwareRelevanceScore -v`
Expected: At least 2 FAIL (openalex_citation_cap, high_cite_lower)

### Step 3: Implement source-aware scoring

Modify `relevance_score` in `paper_ranker.py:57-88`:

```python
@computed_field
@property
def relevance_score(self) -> float:
    """Heuristischer Relevanz-Score (0-1) fuer Ranking.

    Source-aware: OpenAlex Citation-Cap bei 0.15 (statt 0.4),
    weil breite Queries hochzitierte aber irrelevante Papers liefern.
    """
    import math
    score = 0.0

    # Source-spezifische Citation-Caps
    _citation_caps = {
        "semantic_scholar": 0.4,
        "openalex": 0.15,
        "exa": 0.05,
    }
    cite_cap = _citation_caps.get(self.source, 0.2)

    # Zitationen (log-skaliert, source-capped)
    if self.citation_count and self.citation_count > 0:
        score += min(cite_cap, math.log10(self.citation_count + 1) / 10)

    # Aktualitaet (max 0.3)
    if self.year:
        recency = max(0, self.year - 2018) / 8
        score += min(0.3, recency * 0.3)

    # Open Access Bonus (0.1)
    if self.is_open_access:
        score += 0.1

    # Abstract vorhanden (0.15 — aufgewertet, staerkstes Qualitaetssignal)
    if self.abstract:
        score += 0.15

    # Strukturierte Metadaten: SS bevorzugt (0.1), OA neutral (0.05)
    if self.source == "semantic_scholar":
        score += 0.1
    elif self.source == "openalex":
        score += 0.05

    return round(min(1.0, score), 3)
```

### Step 4: Run tests to verify they pass

Run: `pytest tests/test_paper_ranker.py -v`
Expected: ALL PASS (neue + bestehende)

### Step 5: Commit

```bash
git add src/agents/paper_ranker.py tests/test_paper_ranker.py
git commit -m "feat: source-aware relevance scoring (F18+F12)"
```

---

## Task 2: OpenAlex Relevance Pre-Filter (F12)

**Files:**
- Modify: `src/agents/openalex_client.py` (OpenAlexWork + Client)
- Modify: `src/agents/paper_ranker.py:124-146` (from_openalex)
- Modify: `src/agents/forschungsstand.py:118-151` (_search_openalex)
- Test: `tests/test_openalex_client.py`, `tests/test_paper_ranker.py`

### Step 1: Write failing tests

```python
# tests/test_openalex_client.py — neue Tests

class TestOpenAlexRelevanceFilter:
    """Testet Relevanz-Vorfilterung."""

    def test_work_has_relevance_score(self):
        """OpenAlexWork hat relevance_score Feld."""
        work = OpenAlexWork(
            id="W1", display_name="Test",
            relevance_score=0.85,
        )
        assert work.relevance_score == 0.85

    def test_work_default_relevance_zero(self):
        """Ohne Score: Default 0.0."""
        work = OpenAlexWork(id="W2", display_name="Test")
        assert work.relevance_score == 0.0


# tests/test_forschungsstand.py — neue Tests

class TestOpenAlexPreFilter:
    """Testet dass OpenAlex-Ergebnisse unter Relevanz-Schwelle gefiltert werden."""

    @pytest.mark.asyncio
    async def test_low_relevance_filtered(self):
        """Papers mit OA relevance_score < 0.3 werden vor Ranking entfernt."""
        # Mock OpenAlex response mit Mix aus relevant und irrelevant
        # Nur Papers mit relevance_score >= 0.3 sollten durchkommen
        pass  # Wird in Step 3 konkretisiert
```

### Step 2: Run to verify fail

Run: `pytest tests/test_openalex_client.py::TestOpenAlexRelevanceFilter -v`
Expected: FAIL (relevance_score not a field)

### Step 3: Add relevance_score to OpenAlexWork

Modify `openalex_client.py` — `OpenAlexWork` Klasse:

```python
class OpenAlexWork(BaseModel):
    # ... bestehende Felder ...
    relevance_score: float = 0.0  # Von OpenAlex API geliefert
```

Modify `_search_openalex` in `forschungsstand.py` — nach `batch = [from_openalex(w) ...]`:

```python
# Pre-Filter: OpenAlex-Papers unter Relevanz-Schwelle entfernen
MIN_OA_RELEVANCE = 0.3
batch = [from_openalex(w) for w in response.results if w.relevance_score >= MIN_OA_RELEVANCE]
```

### Step 4: Run all tests

Run: `pytest tests/ -v`
Expected: ALL PASS

### Step 5: Commit

```bash
git add src/agents/openalex_client.py src/agents/forschungsstand.py src/agents/paper_ranker.py tests/
git commit -m "feat: OpenAlex relevance pre-filter at 0.3 threshold (F12)"
```

---

## Task 3: Score-Serialisierung Fix (F14)

**Files:**
- Modify: `src/agents/paper_ranker.py` (UnifiedPaper)
- Test: `tests/test_paper_ranker.py`

### Step 1: Write failing test

```python
class TestScoreSerialization:
    """Testet dass relevance_score im JSON-Output erscheint."""

    def test_relevance_score_in_json(self):
        """computed_field relevance_score ist im model_dump enthalten."""
        paper = UnifiedPaper(
            paper_id="test", title="Test Paper",
            citation_count=100, source="semantic_scholar",
            year=2024, abstract="Abstract",
        )
        dumped = paper.model_dump()
        assert "relevance_score" in dumped
        assert dumped["relevance_score"] > 0.0

    def test_relevance_score_in_json_string(self):
        """relevance_score erscheint in model_dump_json."""
        paper = UnifiedPaper(
            paper_id="test", title="Test",
            citation_count=50, source="openalex", year=2024,
        )
        json_str = paper.model_dump_json()
        assert '"relevance_score"' in json_str
```

### Step 2: Run to verify

Run: `pytest tests/test_paper_ranker.py::TestScoreSerialization -v`
Expected: Wahrscheinlich PASS (Pydantic v2 computed_field wird serialisiert).
Falls PASS: dokumentieren und weiter. Falls FAIL: fixen.

### Step 3: Verify and commit

```bash
git add tests/test_paper_ranker.py
git commit -m "test: verify relevance_score serialization (F14)"
```

---

## Quality Gate 1: Adversarial Review (nach Task 1-3)

**Profil:** `code`

Pruefe:
1. **Korrektheit:** Source-Caps beeinflussen bestehende Tests nicht negativ
2. **Immutabilitaet:** Keine Mutationen eingefuehrt
3. **Regression:** `pytest tests/ -v --tb=short` — alle 420+ Tests passing
4. **Edge Cases:** Paper mit source="unknown" — wie verhalt sich relevance_score?

Run: `pytest tests/ -v --tb=short`
Expected: 420+ Tests, ALL PASS

Bei FAIL: Fix vor Weiterarbeit. Bei PASS: weiter zu Task 4.

---

## Task 4: Akkumuliertes Suchen — Session Pool (F13)

**Files:**
- Modify: `src/agents/forschungsstand.py:346-363` (save/load)
- Modify: `cli.py:74-181` (search command)
- Test: `tests/test_forschungsstand.py`

### Step 1: Write failing tests

```python
# tests/test_forschungsstand.py — neue Tests

class TestAccumulatedSearch:
    """Testet akkumuliertes Speichern von Suchergebnissen."""

    def test_save_and_load_roundtrip(self, tmp_path):
        """Normaler Save/Load funktioniert weiterhin."""
        result = ForschungsstandResult(topic="Test", papers=[], total_found=0)
        path = save_forschungsstand(result, tmp_path)
        loaded = load_forschungsstand(path)
        assert loaded.topic == "Test"

    def test_merge_results_deduplicates(self):
        """merge_results entfernt Duplikate aus zwei Result-Sets."""
        paper_a = UnifiedPaper(
            paper_id="doi:10.1", title="Paper A",
            source="semantic_scholar", doi="10.1",
        )
        paper_b = UnifiedPaper(
            paper_id="doi:10.2", title="Paper B",
            source="openalex", doi="10.2",
        )
        paper_a_dup = UnifiedPaper(
            paper_id="doi:10.1", title="Paper A",
            source="openalex", doi="10.1",
        )
        existing = ForschungsstandResult(
            topic="Test", papers=[paper_a], total_found=1,
        )
        new = ForschungsstandResult(
            topic="Test", papers=[paper_b, paper_a_dup], total_found=2,
        )
        merged = merge_results(existing, new)
        assert len(merged.papers) == 2
        # SS-Version von Paper A bleibt (bessere Metadaten)
        paper_a_result = [p for p in merged.papers if p.doi == "10.1"][0]
        assert paper_a_result.source == "semantic_scholar"

    def test_merge_accumulates_total_found(self):
        """merge_results addiert total_found."""
        existing = ForschungsstandResult(topic="T", papers=[], total_found=50)
        new = ForschungsstandResult(topic="T", papers=[], total_found=30)
        merged = merge_results(existing, new)
        assert merged.total_found == 80
```

### Step 2: Run to verify fail

Run: `pytest tests/test_forschungsstand.py::TestAccumulatedSearch -v`
Expected: FAIL (merge_results not defined)

### Step 3: Implement merge_results

Add to `forschungsstand.py`:

```python
def merge_results(
    existing: ForschungsstandResult,
    new: ForschungsstandResult,
) -> ForschungsstandResult:
    """Mergt neue Suchergebnisse in bestehenden Pool.

    Dedupliziert ueber dedup_key. Bei Konflikten: SS > OA > Exa.
    Akkumuliert total_found und vereinigt sources_used.
    """
    all_papers = [*existing.papers, *new.papers]
    merged_papers = deduplicate(all_papers)

    merged_sources = list(dict.fromkeys([*existing.sources_used, *new.sources_used]))

    return ForschungsstandResult(
        topic=existing.topic,
        papers=merged_papers,
        total_found=existing.total_found + new.total_found,
        total_after_dedup=len(merged_papers),
        sources_used=merged_sources,
        leitfragen=[*existing.leitfragen, *[
            f for f in new.leitfragen if f not in existing.leitfragen
        ]],
    )
```

### Step 4: Run tests

Run: `pytest tests/test_forschungsstand.py -v`
Expected: ALL PASS

### Step 5: Commit

```bash
git add src/agents/forschungsstand.py tests/test_forschungsstand.py
git commit -m "feat: merge_results for accumulated search (F13)"
```

---

## Task 5: CLI --append Flag (F13)

**Files:**
- Modify: `cli.py:74-181` (search command)
- Test: Manual CLI test

### Step 1: Add --append flag

Modify `cli.py` search command:

```python
@app.command()
def search(
    # ... bestehende Parameter ...
    append: bool = typer.Option(
        False, "--append", "-a", help="Merge into existing results (akkumuliert)"
    ),
) -> None:
```

After `result = ForschungsstandResult(...)`, add:

```python
    # Akkumuliertes Suchen: bestehende Ergebnisse laden und mergen
    if append:
        existing_path = output_dir / "search_results.json" / slugify(topic) / "forschungsstand.json"
        if existing_path.exists():
            existing = load_forschungsstand(existing_path)
            result = merge_results(existing, result)
            console.print(
                f"[cyan]Merged:[/cyan] {len(result.papers)} papers "
                f"(+{len(papers)} new, {result.total_found} total found)"
            )
```

### Step 2: Import merge_results + slugify in cli.py

Add to the import block inside search():

```python
from src.agents.forschungsstand import merge_results, slugify
```

### Step 3: Run full test suite

Run: `pytest tests/ -v`
Expected: ALL PASS (CLI aendert keine getestete Logik)

### Step 4: Commit

```bash
git add cli.py
git commit -m "feat: --append flag for accumulated search (F13)"
```

---

## Task 6: Deprecation Cleanup (--exa/--no-exa entfernen)

**Files:**
- Modify: `cli.py:84-126` (search command — exa param + compat logic)
- Test: `tests/test_cli.py` (falls vorhanden)

### Step 1: Remove deprecated --exa/--no-exa

Remove `use_exa` parameter and backward-compat block from search().
Simplify to only use `--sources`.

### Step 2: Run tests

Run: `pytest tests/ -v`
Expected: ALL PASS

### Step 3: Commit

```bash
git add cli.py
git commit -m "chore: remove deprecated --exa/--no-exa flag"
```

---

## Quality Gate 2: Adversarial Review (nach Task 4-6)

**Profil:** `code` + `architecture`

Pruefe:
1. **Korrektheit:** merge_results Dedup stimmt, SS > OA Prioritaet
2. **Immutabilitaet:** merge_results erzeugt neue Objekte
3. **Edge Cases:** --append bei nicht-existierender Datei, leerer Pool
4. **Regression:** Alle 420+ Tests passing
5. **Architecture:** Ist merge_results am richtigen Ort (forschungsstand.py)?

Run: `pytest tests/ -v --tb=short && python cli.py search "test" --max 5 --sources openalex`
Expected: Tests PASS, CLI funktioniert

---

## Task 7: Source-Balance Warning (F15)

**Files:**
- Modify: `src/agents/forschungsstand.py:267-306` (search_papers)
- Test: `tests/test_forschungsstand.py`

### Step 1: Write failing test

```python
class TestSourceBalanceWarning:
    """Warnung wenn eine Quelle <10% des Pools liefert."""

    def test_imbalanced_sources_logged(self, caplog):
        """Warnung bei SS=2, OA=40 Papers."""
        # Verwendet stats dict
        stats = {"ss_total": 2, "openalex_total": 40, "exa_total": 0}
        warnings = _check_source_balance(stats)
        assert len(warnings) >= 1
        assert "ss" in warnings[0].lower() or "semantic" in warnings[0].lower()

    def test_balanced_sources_no_warning(self):
        """Keine Warnung bei SS=20, OA=25."""
        stats = {"ss_total": 20, "openalex_total": 25, "exa_total": 0}
        warnings = _check_source_balance(stats)
        assert len(warnings) == 0
```

### Step 2: Implement _check_source_balance

Add to `forschungsstand.py`:

```python
def _check_source_balance(stats: dict[str, int]) -> list[str]:
    """Prueft ob Quellen-Verteilung stark asymmetrisch ist.

    Warnt wenn eine aktive Quelle <10% des Gesamtpools liefert.
    """
    source_counts = {
        "Semantic Scholar": stats.get("ss_total", 0),
        "OpenAlex": stats.get("openalex_total", 0),
        "Exa": stats.get("exa_total", 0),
    }
    active = {k: v for k, v in source_counts.items() if v > 0}
    total = sum(active.values())
    if total == 0 or len(active) < 2:
        return []

    warnings: list[str] = []
    for source, count in active.items():
        ratio = count / total
        if ratio < 0.1:
            warnings = [
                *warnings,
                f"{source} lieferte nur {count}/{total} Papers ({ratio:.0%}). "
                f"Ergebnisse koennten asymmetrisch sein.",
            ]
    return warnings
```

Call in `search_papers()` after gathering results, log warnings.

### Step 3: Run tests, commit

Run: `pytest tests/ -v`

```bash
git add src/agents/forschungsstand.py tests/test_forschungsstand.py
git commit -m "feat: source balance warning for asymmetric results (F15)"
```

---

## Task 8: Final Integration Test + Handover

### Step 1: Run full suite

```bash
pytest tests/ -v --tb=short
```
Expected: 430+ Tests, ALL PASS

### Step 2: Manual smoke test

```bash
python cli.py search "AI automated research" --sources openalex --max 10
python cli.py search "LLM literature review" --sources openalex --max 10 --append
```
Expected: Second search merges into first, shows merged count.

### Step 3: Final commit + Handover doc

```bash
git add -A
git commit -m "docs: sprint 6 handover — search quality fixes (F12-F15, F18)"
```

### Step 4: Update CLAUDE.md

Add Sprint 6 to Ranking section:
- Source-aware scoring (OA citation cap 0.15, SS cap 0.4)
- OpenAlex relevance pre-filter (threshold 0.3)
- `--append` flag for accumulated search
- Source balance warnings

---

## Quality Gate 3: Final Adversarial Review

**Profil:** `research` (Meta-Bewertung des Sprints)

| Prinzip | Kriterium |
|---------|-----------|
| Quellenqualitaet | Wurden F12/F18 tatsaechlich geloest? Test mit gleicher Query wie Meta-Loop v3? |
| Vollstaendigkeit | Alle 4 Findings adressiert? |
| Bias-Check | Fuehren die Caps zu neuen Biases (z.B. OA-Papers systematisch unterbewertet)? |
| Actionability | Kann naechster Sprint auf diesen Fixes aufbauen? |
| Reproduzierbarkeit | Gleiche Query liefert bessere Ergebnisse als v3? |

---

## Sprint-Zusammenfassung

| Task | Finding | Aufwand | Dateien |
|------|---------|---------|---------|
| T1 | F18+F12: Source-aware Scoring | ~30min | paper_ranker.py |
| T2 | F12: OA Relevance Pre-Filter | ~20min | openalex_client.py, forschungsstand.py |
| T3 | F14: Score Serialization | ~10min | paper_ranker.py (Test only) |
| T4 | F13: merge_results | ~30min | forschungsstand.py |
| T5 | F13: CLI --append | ~15min | cli.py |
| T6 | Cleanup: --exa/--no-exa | ~10min | cli.py |
| T7 | F15: Source Balance Warning | ~15min | forschungsstand.py |
| T8 | Integration + Handover | ~15min | docs, CLAUDE.md |

**Total:** ~2.5h | **Tests:** ~15 neue | **Quality Gates:** 3 (nach T3, T6, T8)
