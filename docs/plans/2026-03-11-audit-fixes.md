# Audit-Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Alle CRITICAL und HIGH Findings aus dem Audit (2026-03-11) fixen. MEDIUM als Backlog dokumentiert.

**Architecture:** 5 Tasks in logischer Reihenfolge: Import-Fixes → Connection Pooling → Robustheit → Performance → Code-Qualitaet. Jeder Task ist ein eigener Commit.

**Tech Stack:** Python 3.11+, Pydantic v2, httpx, pytest

**Audit-Quelle:** `docs/audit/2026-03-11-audit-summary.md`

---

## Task 1: Import-Fehler fixen (5 CRITICAL)

**Files:**
- Modify: `cli.py:261,272,296-301`
- Modify: `src/utils/citation_tracker.py:12`
- Modify: `src/agents/drafting.py:603`
- Test: `tests/test_cli.py` (bestehende Tests)

**Step 1: Fix cli.py — check-Command Import**

```python
# cli.py:296 — VORHER:
from src.agents.reference_extractor import extract_references
# NACHHER:
from src.agents.reference_extractor import extract_all_references
```

Auch den Aufruf in Zeile ~301 anpassen: `extract_references(text)` → `extract_all_references(text)`

**Step 2: Fix cli.py — review-Command Imports**

```python
# cli.py:261 — VORHER:
from src.agents.reviewer import ReviewConfig
# ENTFERNEN (ReviewConfig existiert nicht, wird nicht gebraucht)

# cli.py:263-264 — VORHER:
from src.utils.rubric_loader import find_rubric_for_venue, load_all_rubrics
# NACHHER:
from src.utils.rubric_loader import find_rubric_for_venue

# cli.py:272 — VORHER:
rubrics = load_all_rubrics()
matched = find_rubric_for_venue(venue, rubrics=rubrics)
# NACHHER:
matched = None
try:
    matched = find_rubric_for_venue(venue)
except FileNotFoundError:
    matched = None
```

**Step 3: Fix citation_tracker.py — Import-Pfad**

```python
# src/utils/citation_tracker.py:12 — VORHER:
from utils.evidence_card import EvidenceCard
# NACHHER:
from src.utils.evidence_card import EvidenceCard
```

**Step 4: Fix drafting.py — Import-Pfad**

```python
# src/agents/drafting.py:603 — VORHER:
from utils.citation_tracker import track_citations
# NACHHER:
from src.utils.citation_tracker import track_citations
```

**Step 5: Tests ausfuehren**

Run: `pytest tests/test_cli.py -v`
Expected: PASS (keine ImportErrors mehr)

Run: `python -c "from src.utils.citation_tracker import track_citations; print('OK')"`
Expected: `OK`

Run: `python -c "from src.agents.reference_extractor import extract_all_references; print('OK')"`
Expected: `OK`

**Step 6: Commit**

```bash
git add cli.py src/utils/citation_tracker.py src/agents/drafting.py
git commit -m "fix: resolve broken imports in check/review commands + citation_tracker"
```

---

## Task 2: Connection Pooling (3 CRITICAL + 1 HIGH)

**Files:**
- Modify: `src/agents/semantic_scholar.py`
- Modify: `src/agents/exa_client.py`
- Modify: `src/agents/openalex_client.py`
- Modify: `src/utils/llm_client.py`
- Test: `tests/test_forschungsstand.py`, `tests/test_exa_client.py`, `tests/test_openalex_client.py`, `tests/test_llm_client.py`

**Step 1: Refactor SemanticScholarClient — Client als Instanzvariable**

```python
# semantic_scholar.py — Client einmal erstellen, nicht pro Request

class SemanticScholarClient:
    MAX_RETRIES = 1
    RETRY_DELAY_S = 2.0

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("S2_API_KEY")
        self._headers: dict[str, str] = {}
        if self._api_key:
            self._headers["x-api-key"] = self._api_key
        else:
            logger.warning("S2_API_KEY nicht gesetzt — Rate Limits sind strenger")
        self._client = httpx.AsyncClient(timeout=30, headers=self._headers)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def _request(self, method, url, *, params=None) -> httpx.Response:
        for attempt in range(self.MAX_RETRIES + 1):
            response = await self._client.request(method, url, params=params)
            if response.status_code == 429 and attempt < self.MAX_RETRIES:
                logger.warning(...)
                await asyncio.sleep(self.RETRY_DELAY_S)
                continue
            response.raise_for_status()
            return response
        raise httpx.HTTPStatusError(...)
```

**Step 2: Gleiches Pattern fuer ExaClient**

```python
# exa_client.py — Client in __init__ erstellen
def __init__(self, api_key=None):
    self._api_key = api_key if api_key is not None else os.environ.get("EXA_API_KEY")
    self._client = httpx.AsyncClient(
        timeout=30,
        headers={"x-api-key": self._api_key or "", "Content-Type": "application/json"},
    )

async def close(self):
    await self._client.aclose()

async def __aenter__(self):
    return self

async def __aexit__(self, *args):
    await self.close()
```

**Step 3: Gleiches Pattern fuer OpenAlexClient**

```python
# openalex_client.py — Client in __init__ erstellen
def __init__(self, mailto=None, api_key=None):
    self._mailto = mailto or os.environ.get("OPENALEX_MAILTO")
    self._api_key = api_key or os.environ.get("OPENALEX_API_KEY")
    self._client = httpx.AsyncClient(timeout=30)

async def close(self):
    await self._client.aclose()

async def __aenter__(self):
    return self

async def __aexit__(self, *args):
    await self.close()
```

**Step 4: Refactor llm_client.py — Shared Client**

```python
# llm_client.py — Client ausserhalb der Funktion, Lazy Init
_llm_client: httpx.AsyncClient | None = None

def _get_llm_client(timeout: float) -> httpx.AsyncClient:
    global _llm_client
    if _llm_client is None or _llm_client.is_closed:
        _llm_client = httpx.AsyncClient(timeout=timeout)
    return _llm_client

async def llm_complete(system_prompt, user_message, *, config=None) -> str:
    ...
    client = _get_llm_client(config.timeout_s)
    response = await client.post(...)
    ...
```

**Step 5: Caller in forschungsstand.py anpassen**

Die `_search_ss`, `_search_openalex`, `_search_exa` Funktionen erstellen aktuell Clients inline.
Anpassen: Clients in `search_papers()` erstellen und als Parameter durchreichen.
Clients nach `asyncio.gather` schliessen.

```python
async def search_papers(topic, *, ...):
    ...
    ss_client = SemanticScholarClient()
    oa_client = OpenAlexClient()
    exa_client = ExaClient()
    try:
        # ... search_tasks mit clients ...
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
    finally:
        await ss_client.close()
        await oa_client.close()
        await exa_client.close()
```

**Step 6: Tests anpassen und ausfuehren**

Bestehende Tests die `httpx.AsyncClient` mocken muessen angepasst werden.
Mock-Target aendert sich von `httpx.AsyncClient` zu `client._client.request` o.ae.

Run: `pytest tests/test_forschungsstand.py tests/test_exa_client.py tests/test_openalex_client.py tests/test_llm_client.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/agents/semantic_scholar.py src/agents/exa_client.py src/agents/openalex_client.py src/utils/llm_client.py src/agents/forschungsstand.py tests/
git commit -m "perf: add connection pooling to all API clients"
```

---

## Task 3: Robustheit-Fixes (12 HIGH)

**Files:**
- Modify: `src/pipeline/provenance.py`
- Modify: `src/utils/feedback_logger.py`
- Modify: `src/utils/llm_client.py`
- Modify: `cli.py`
- Modify: `src/agents/forschungsstand.py`
- Modify: `src/agents/paper_ranker.py`
- Modify: `src/pipeline/state.py`
- Modify: `src/agents/doctor.py`
- Modify: `src/agents/openalex_client.py`
- Test: Bestehende + neue Tests

**Step 1: JSONL-Parsing robust machen (provenance.py + feedback_logger.py)**

```python
# provenance.py:read_all() — try/except pro Zeile
def read_all(self) -> list[ProvenanceEntry]:
    if not self._path.exists():
        return []
    entries: list[ProvenanceEntry] = []
    for i, line in enumerate(self._path.read_text(encoding="utf-8").strip().split("\n"), 1):
        if not line:
            continue
        try:
            entries.append(ProvenanceEntry.model_validate_json(line))
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Korrupte JSONL-Zeile %d in %s: %s", i, self._path, e)
    return entries
```

Gleiches Pattern fuer `feedback_logger.py:read_feedback()`.

**Step 2: LLM Response Bounds-Check**

```python
# llm_client.py:101-106 — sicherer Zugriff
data = response.json()
choices = data.get("choices", [])
if not choices:
    raise RuntimeError("LLM-Antwort enthaelt keine choices")
message = choices[0].get("message", {})
content = message.get("content")
if content is None:
    raise RuntimeError("LLM-Antwort enthaelt keinen content")
return content
```

**Step 3: CLI Input-Validierung**

```python
# cli.py — sources validieren
VALID_SOURCES = {"ss", "openalex", "exa"}
source_list = [s.strip() for s in sources.split(",") if s.strip()]
invalid = set(source_list) - VALID_SOURCES
if invalid:
    console.print(f"[red]Ungueltige Quellen:[/red] {', '.join(invalid)}")
    console.print(f"Erlaubt: {', '.join(sorted(VALID_SOURCES))}")
    raise typer.Exit(1)

# cli.py — max_results mit min=1
max_results: int = typer.Option(30, "--max", "-m", min=1, help="Max papers after ranking"),
```

**Step 4: dedup_key Fallback fuer leere Titel**

```python
# paper_ranker.py:49-56 — Fallback auf paper_id
@computed_field
@property
def dedup_key(self) -> str:
    if self.doi:
        return f"doi:{self.doi.lower()}"
    if not self.title or not self.title.strip():
        return f"id:{self.paper_id}"
    normalized = "".join(c for c in self.title.lower() if c.isalnum() or c == " ")
    normalized = " ".join(normalized.split())
    return f"title:{hashlib.sha256(normalized.encode()).hexdigest()[:16]}"
```

**Step 5: --append Pfad-Bug fixen**

```python
# cli.py:164 — output_dir statt output_path
if append:
    existing_path = output_dir / slugify(topic) / "forschungsstand.json"
    # ... (war: output_path / slugify(topic) / ...)
```

**Step 6: State Machine Transitions-Validierung**

```python
# state.py — Guards in start_phase/complete_phase
def start_phase(self, phase: Phase) -> None:
    record = self.phases[phase.value]
    if record.status == PhaseStatus.IN_PROGRESS:
        raise ValueError(f"Phase {phase.value} ist bereits IN_PROGRESS")
    record.status = PhaseStatus.IN_PROGRESS
    record.started_at = datetime.now(timezone.utc).isoformat()
    self.current_phase = phase

def complete_phase(self, phase: Phase, artifacts: list[str] | None = None) -> None:
    record = self.phases[phase.value]
    if record.status != PhaseStatus.IN_PROGRESS:
        raise ValueError(f"Phase {phase.value} ist nicht IN_PROGRESS (aktuell: {record.status})")
    record.status = PhaseStatus.COMPLETED
    record.completed_at = datetime.now(timezone.utc).isoformat()
    if artifacts:
        record.artifacts = [*record.artifacts, *artifacts]
```

**Step 7: doctor.py — LLM_API_KEY pruefen**

```python
# doctor.py:85 — VORHER:
llm_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
# NACHHER:
llm_key = (
    os.environ.get("LLM_API_KEY")
    or os.environ.get("OPENROUTER_API_KEY")
    or os.environ.get("OPENAI_API_KEY")
)
```

**Step 8: OpenAlex relevance_score Filter-Bug**

```python
# forschungsstand.py:202-203 — Score-Check nur wenn > 0
relevant = [
    w for w in response.results
    if w.relevance_score <= 0 or w.relevance_score >= min_oa_relevance
]
```

**Step 9: save_state Windows-Safety**

```python
# state.py:118-122 — Windows-safe atomic write
import os as _os

def save_state(state: ResearchState, path: Path) -> None:
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    try:
        tmp_path.replace(path)
    except PermissionError:
        # Windows: Zieldatei evtl. noch gesperrt
        _os.replace(str(tmp_path), str(path))
```

**Step 10: Tests schreiben und ausfuehren**

Neue Tests fuer:
- JSONL mit korrupter Zeile → Warning statt Crash
- `--sources foo` → Exit 1
- `--max 0` → Exit 1
- Leerer Titel → eindeutiger dedup_key
- State Machine: complete ohne start → ValueError

Run: `pytest tests/ -v`
Expected: Alle PASS

**Step 11: Commit**

```bash
git add src/ cli.py tests/
git commit -m "fix: robustness improvements (JSONL parsing, input validation, edge cases)"
```

---

## Task 4: Performance-Fixes (5 HIGH)

**Files:**
- Modify: `src/agents/paper_ranker.py`
- Modify: `src/agents/forschungsstand.py`
- Modify: `src/pipeline/provenance.py`
- Test: Bestehende Tests

**Step 1: `import math` an Dateianfang verschieben**

```python
# paper_ranker.py — Zeile 1-17: math zu den Imports hinzufuegen
import math
# ... und aus relevance_score + _compute_enhanced_score entfernen
```

**Step 2: _citation_caps als Modul-Konstanten**

```python
# paper_ranker.py — nach Imports
HEURISTIC_CITATION_CAPS = {"semantic_scholar": 0.4, "openalex": 0.15, "exa": 0.05}
ENHANCED_CITATION_CAPS = {"semantic_scholar": 0.25, "openalex": 0.10, "exa": 0.03}
```

Und in `relevance_score` / `_compute_enhanced_score` referenzieren.

**Step 3: O(n²) → List Comprehension in rank_papers()**

```python
# paper_ranker.py:375-381 — VORHER:
updated = []
for paper in papers:
    s2_score = specter2_scores.get(paper.paper_id)
    updated = [*updated, paper.model_copy(update={"specter2_score": s2_score})]
# NACHHER:
updated = [
    paper.model_copy(update={"specter2_score": specter2_scores.get(paper.paper_id)})
    for paper in papers
]
```

**Step 4: O(n²) → extend/append in forschungsstand.py**

```python
# _search_ss, _search_openalex, _search_exa — VORHER:
papers = [*papers, *batch]
# NACHHER (lokale Variable, Mutation OK):
papers.extend(batch)
```

Gleiches fuer `all_papers = [*all_papers, *result]` in `search_papers()`.

**Step 5: provenance.py read_all() — O(n²) Fix + Caching**

```python
# provenance.py — .append statt [*list, item], filter direkt
def read_all(self) -> list[ProvenanceEntry]:
    if not self._path.exists():
        return []
    entries: list[ProvenanceEntry] = []
    for line in self._path.read_text(encoding="utf-8").strip().split("\n"):
        if line:
            entries.append(ProvenanceEntry.model_validate_json(line))
    return entries

def filter_by_phase(self, phase: str) -> list[ProvenanceEntry]:
    return [e for e in self.read_all() if e.phase == phase]
```

**Step 6: Tests ausfuehren**

Run: `pytest tests/ -v`
Expected: Alle PASS (kein Verhalten aendert sich, nur Performance)

**Step 7: Commit**

```bash
git add src/agents/paper_ranker.py src/agents/forschungsstand.py src/pipeline/provenance.py
git commit -m "perf: eliminate O(n²) list copies + module-level imports"
```

---

## Task 5: Code-Qualitaet (4 HIGH)

**Files:**
- Modify: `src/agents/paper_ranker.py`
- Modify: `src/agents/openalex_client.py`
- Test: Bestehende Tests

**Step 1: SPECTER2 Cache — functools.lru_cache statt global**

```python
# paper_ranker.py — VORHER:
_specter2_model = None

def _load_specter2_model():
    global _specter2_model
    if _specter2_model is not None:
        return _specter2_model
    from sentence_transformers import SentenceTransformer
    _specter2_model = SentenceTransformer("allenai/specter2_base")
    return _specter2_model

# NACHHER:
@functools.lru_cache(maxsize=1)
def _load_specter2_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("allenai/specter2_base")
```

**Step 2: OpenAlex Abstract Caching**

```python
# openalex_client.py — functools.cached_property statt @property
from functools import cached_property

class OpenAlexWork(BaseModel):
    ...
    model_config = {"frozen": False}  # Noetig fuer cached_property

    @cached_property
    def abstract(self) -> str | None:
        if not self.abstract_inverted_index:
            return None
        positions = sorted(
            ((idx, word) for word, idxs in self.abstract_inverted_index.items() for idx in idxs),
            key=lambda x: x[0],
        )
        return " ".join(w for _, w in positions)
```

Hinweis: `cached_property` und Pydantic `BaseModel` sind nicht direkt kompatibel. Alternative: `model_post_init` + normales Feld, oder Abstract in `from_openalex()` einmal berechnen.

Pragmatischere Loesung — Abstract einmal in `from_openalex()` berechnen:

```python
# paper_ranker.py:from_openalex() — Abstract direkt uebergeben
def from_openalex(work: OpenAlexWork) -> UnifiedPaper:
    abstract = work.abstract  # 1x berechnen
    return UnifiedPaper(
        ...
        abstract=abstract,
        ...
    )
```

Das reicht, da `from_openalex` der einzige Consumer ist.

**Step 3: Tests ausfuehren**

Run: `pytest tests/ -v`
Expected: Alle PASS

**Step 4: Commit**

```bash
git add src/agents/paper_ranker.py src/agents/openalex_client.py
git commit -m "refactor: lru_cache for SPECTER2, eliminate duplicate citation_caps"
```

---

## MEDIUM Backlog (nicht in diesem Plan)

Dokumentiert in `docs/audit/2026-03-11-audit-summary.md`:
- 3 Dateien >400 Zeilen aufsplitten
- SearchConfig dataclass → BaseModel
- DRY: generische `_search_source()` Funktion
- Magic Numbers als Konstanten
- Intra-Source Query-Parallelisierung
- Diverse Edge Cases (year_filter, BibTeX encoding, confidence range)

---

## Zusammenfassung

| Task | Findings | Typ | Geschaetzte Dauer |
|------|----------|-----|-------------------|
| 1: Import-Fixes | 5 CRITICAL | fix | ~20min |
| 2: Connection Pooling | 3 CRITICAL + 1 HIGH | perf | ~1.5h |
| 3: Robustheit | 12 HIGH | fix | ~1.5h |
| 4: Performance | 5 HIGH | perf | ~30min |
| 5: Code-Qualitaet | 4 HIGH | refactor | ~30min |
| **Gesamt** | **8 CRIT + 22 HIGH** | | **~4h** |
