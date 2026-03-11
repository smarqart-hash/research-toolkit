# Spec 003: Multi-Source Search — Design

> Scope: Backend (API-Integration + CLI)

## Architektur-Ueberblick

```
CLI (--sources ss,openalex,exa)
  → forschungsstand.py: search_papers()
    → asyncio.gather(
        _search_semantic_scholar(queries, config),
        _search_openalex(queries, config),        # NEU
        _search_exa(queries, config),             # bestehend, refactored
      )
    → [*ss_papers, *oa_papers, *exa_papers]
    → deduplicate() → rank_papers() → screen_papers()  (unveraendert)
```

### Design-Entscheidung: BASE entfaellt

BASE (Bielefeld Academic Search Engine) erfordert **IP-Whitelisting** vor API-Nutzung.
Das ist fuer ein Open-Source-CLI-Tool nicht praktikabel.

**Ersatz:** OpenAlex hat einen `language`-Filter (`filter=language:de`) und indexiert
viele deutsche Repositories (OPUS, DepositOnce, etc.). Damit deckt OpenAlex den
DACH-Bedarf hinreichend ab.

BASE kann spaeter als optionaler Client ergaenzt werden (mit Setup-Anleitung fuer
IP-Whitelisting). Nicht in Sprint 5.

---

## Neue Dateien

### `src/agents/openalex_client.py` (~120 Zeilen)

```python
"""OpenAlex API Client — Breite akademische Suche.

Kostenlos, kein API Key noetig. Polite Pool mit mailto-Header
fuer hoehere Rate Limits. 200M+ Works indexiert.

API Docs: https://developers.openalex.org/
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openalex.org"


class OpenAlexAuthor(BaseModel):
    """Autor aus Authorship."""
    display_name: str
    orcid: str | None = None


class OpenAlexAuthorship(BaseModel):
    """Authorship-Eintrag."""
    author: OpenAlexAuthor


class OpenAlexOpenAccess(BaseModel):
    """Open Access Info."""
    is_oa: bool = False
    oa_url: str | None = None


class OpenAlexWork(BaseModel):
    """Ein Work aus der OpenAlex API."""
    id: str
    doi: str | None = None
    display_name: str  # = Titel
    publication_year: int | None = None
    authorships: list[OpenAlexAuthorship] = Field(default_factory=list)
    cited_by_count: int = 0
    abstract_inverted_index: dict[str, list[int]] | None = None
    open_access: OpenAlexOpenAccess = Field(default_factory=OpenAlexOpenAccess)
    language: str | None = None
    type: str | None = None

    @property
    def abstract(self) -> str | None:
        """Rekonstruiert Abstract aus Inverted Index."""
        if not self.abstract_inverted_index:
            return None
        # Inverted Index: {"word": [pos1, pos2]} → sortiert nach Position
        positions: list[tuple[int, str]] = []
        for word, idxs in self.abstract_inverted_index.items():
            for idx in idxs:
                positions.append((idx, word))
        positions.sort(key=lambda x: x[0])
        return " ".join(w for _, w in positions)

    @property
    def first_author(self) -> str:
        if self.authorships:
            return self.authorships[0].author.display_name
        return "Unbekannt"


class OpenAlexSearchResponse(BaseModel):
    """Antwort der Works-Suche."""
    meta: dict = Field(default_factory=dict)  # count, per_page, next_cursor
    results: list[OpenAlexWork] = Field(default_factory=list)


class OpenAlexClient:
    """Client fuer die OpenAlex Works API.

    Immer verfuegbar (kein API Key noetig).
    Polite Pool: mailto-Parameter fuer hoehere Rate Limits.
    """

    MAX_RETRIES = 1
    RETRY_DELAY_S = 2.0

    def __init__(self, mailto: str | None = None) -> None:
        self._mailto = mailto or os.environ.get("OPENALEX_MAILTO")

    async def search_works(
        self,
        query: str,
        *,
        per_page: int = 50,
        year_range: str | None = None,
        languages: list[str] | None = None,
    ) -> OpenAlexSearchResponse:
        """Sucht Works nach Freitext-Query.

        Args:
            query: Suchbegriff.
            per_page: Max Ergebnisse (1-200).
            year_range: z.B. "2020-2026" → filter=publication_year:2020-2026
            languages: z.B. ["en", "de"] → filter=language:en|de
        """
        params: dict[str, str | int] = {
            "search": query,
            "per_page": min(per_page, 200),
        }
        if self._mailto:
            params["mailto"] = self._mailto

        # Filter zusammenbauen
        filters: list[str] = []
        if year_range:
            filters.append(f"publication_year:{year_range}")
        if languages:
            lang_filter = "|".join(languages)
            filters.append(f"language:{lang_filter}")
        if filters:
            params["filter"] = ",".join(filters)

        for attempt in range(self.MAX_RETRIES + 1):
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{BASE_URL}/works",
                    params=params,
                )
            if response.status_code == 429 and attempt < self.MAX_RETRIES:
                logger.warning(
                    "OpenAlex Rate Limit (429), warte %.1fs (Versuch %d/%d)",
                    self.RETRY_DELAY_S,
                    attempt + 1,
                    self.MAX_RETRIES + 1,
                )
                await asyncio.sleep(self.RETRY_DELAY_S)
                continue
            response.raise_for_status()
            return OpenAlexSearchResponse.model_validate(response.json())

        raise httpx.HTTPStatusError(
            "OpenAlex Rate Limit nach Retries",
            request=response.request,
            response=response,
        )
```

### `tests/test_openalex_client.py` (~150 Zeilen)

Analog zu `test_semantic_scholar.py` / `test_exa_client.py`:
- Factory: `_openalex_work(**overrides)` → `OpenAlexWork`
- TestFromOpenAlex: Konverter-Tests
- TestOpenAlexClient: Mocked HTTP (search, retry, error handling)
- TestAbstractReconstruction: Inverted Index → Klartext

---

## Geaenderte Dateien

### `src/agents/paper_ranker.py`

Neuer Konverter + Import:

```python
from src.agents.openalex_client import OpenAlexWork

def from_openalex(work: OpenAlexWork) -> UnifiedPaper:
    """Konvertiert ein OpenAlex Work in UnifiedPaper."""
    return UnifiedPaper(
        paper_id=work.doi or work.id,
        title=work.display_name,
        abstract=work.abstract,  # via @property aus inverted_index
        year=work.publication_year,
        authors=[a.author.display_name for a in work.authorships],
        citation_count=work.cited_by_count,
        source="openalex",
        doi=work.doi,
        url=work.id,  # OpenAlex URL
        is_open_access=work.open_access.is_oa,
    )
```

`relevance_score`: Kein SS-Bonus mehr fuer `source == "semantic_scholar"`.
Stattdessen: +0.1 fuer Quellen mit strukturierten Metadaten (SS + OpenAlex).

### `src/agents/forschungsstand.py`

**SearchConfig** erweitert:

```python
@dataclass
class SearchConfig:
    max_results_per_query: int = 50
    year_filter: str | None = None
    fields_of_study: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=lambda: ["ss", "openalex"])
    top_k: int = 30
    languages: list[str] = field(default_factory=lambda: ["en", "de"])
```

`use_exa: bool` entfaellt → `"exa" in config.sources` ersetzt.

**search_papers()** refactored:

```python
async def search_papers(...) -> tuple[...]:
    # ...
    # Parallele Suche ueber alle konfigurierten Quellen
    search_tasks = []
    if "ss" in config.sources:
        search_tasks.append(_search_ss(ss_queries, config, stats))
    if "openalex" in config.sources:
        search_tasks.append(_search_openalex(ss_queries, config, stats))
    if "exa" in config.sources:
        search_tasks.append(_search_exa(exa_queries, config, stats))

    results = await asyncio.gather(*search_tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logger.warning("Quelle fehlgeschlagen: %s", result)
            continue
        all_papers = [*all_papers, *result]
    # ... deduplicate, rank, screen wie bisher
```

Extrahierte Hilfsfunktionen:
- `_search_ss(queries, config, stats) -> list[UnifiedPaper]`
- `_search_openalex(queries, config, stats) -> list[UnifiedPaper]`
- `_search_exa(queries, config, stats) -> list[UnifiedPaper]`

### `cli.py`

```python
@app.command()
def search(
    topic: str = typer.Argument(...),
    max_results: int = typer.Option(30, "--max", "-m"),
    sources: str = typer.Option("ss,openalex", "--sources", "-s",
                                help="Komma-separiert: ss,openalex,base,exa"),
    # --exa/--no-exa entfaellt (backward-compat via Deprecation-Warning)
    year_filter: str = typer.Option(None, "--years", "-y"),
    refine: bool = typer.Option(False, "--refine", "-r"),
    ...
):
    source_list = [s.strip() for s in sources.split(",")]
    config = SearchConfig(
        top_k=max_results,
        sources=source_list,
        year_filter=year_filter,
    )
```

### `src/agents/query_generator.py`

`SearchScope.languages` Default: `["en", "de"]`

---

## Adversarial Check

### 1. Unsicherste Annahme
**OpenAlex `abstract_inverted_index` ist zuverlaessig vorhanden.**
→ Verifizierbar: Stichprobe zeigt ~70% der Works haben Abstract.
→ Mitigation: `abstract` Property gibt `None` zurueck wenn fehlend — wie bei SS.

### 2. Einfachere Loesung?
Nur OpenAlex ohne Refactoring von `search_papers()` — aber das sequentielle
Pattern (erst SS, dann Exa) skaliert nicht auf 3+ Quellen. `asyncio.gather`
ist die richtige Abstraktion und vereinfacht auch den bestehenden Code.

### 3. Integrations-Risiko
`use_exa: bool` → `sources: list[str]` ist ein Breaking Change in `SearchConfig`.
→ Mitigation: Alle internen Aufrufe anpassen. CLI `--exa/--no-exa` als
Deprecation-Warning beibehalten (1 Sprint), dann entfernen.

---

## Environment Variables

| Variable | Zweck | Required |
|----------|-------|----------|
| `OPENALEX_MAILTO` | Polite Pool Email (hoehere Rate Limits) | Nein (funktioniert ohne) |
| `S2_API_KEY` | Semantic Scholar API | Nein (bestehend) |
| `EXA_API_KEY` | Exa Search API | Nein (bestehend) |
