# Design: Smart Query Generation

## Architektur

### Datenfluss

```
CLI (--refine)
  → query_generator.expand_queries(topic, leitfragen)
    → Stufe 1: lokale Expansion (immer)
    → Stufe 2: LLM-enhanced (wenn LLM_API_KEY gesetzt)
    → QuerySet {ss_queries, exa_queries}
  → forschungsstand.search_papers() nutzt QuerySet statt Heuristik
    → SS-Client bekommt ss_queries
    → Exa-Client bekommt exa_queries
  → Optional: validate_queries() Dry-Run
```

### Betroffene Dateien

| Datei | Aenderung |
|-------|-----------|
| `src/agents/query_generator.py` | **NEU** — Kern-Modul |
| `src/utils/llm_client.py` | **NEU** — Duenner OpenAI-kompatibler Client |
| `src/agents/forschungsstand.py` | Integration: `--refine` delegiert an query_generator |
| `cli.py` | `--refine` + `--no-validate` Flags |
| `config/query_templates/` | **NEU** — Synonym-Maps + Few-Shot-Prompts |

## Datenmodell

### `src/agents/query_generator.py`

```python
from __future__ import annotations
from pydantic import BaseModel, Field

class SearchScope(BaseModel):
    """Suchbereich-Eingrenzung."""
    year_range: tuple[int, int] | None = None
    languages: list[str] = Field(default_factory=lambda: ["en"])
    fields_of_study: list[str] = Field(default_factory=list)

class QuerySet(BaseModel):
    """Generierte Suchqueries, getrennt nach API-Format."""
    research_question: str
    ss_queries: list[str]    # Boolean-Format: "topic AND (synonym1 OR synonym2)"
    exa_queries: list[str]   # Natural Language: "What are recent advances in..."
    scope: SearchScope = Field(default_factory=SearchScope)
    source: str = "local"    # "local" | "llm" — Tracking woher die Queries kommen
```

### `src/utils/llm_client.py`

```python
from __future__ import annotations
from pydantic import BaseModel

class LLMConfig(BaseModel):
    """Konfiguration fuer den LLM-Client."""
    base_url: str = "https://openrouter.ai/api/v1"
    api_key: str = ""
    model: str = "google/gemini-2.0-flash-exp:free"
    timeout_s: float = 30.0
    max_tokens: int = 1024

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)
```

## Kern-Design: 2-Stufen-Expansion

### Stufe 1: Lokale Expansion (immer, kein API-Call)

```python
def _expand_local(topic: str, leitfragen: list[str]) -> QuerySet:
    """Regelbasierte Query-Expansion."""
    # 1. Topic in Kern-Terme splitten
    # 2. Synonym-Map laden (config/query_templates/synonyms.json)
    # 3. SS-Queries: Boolean-Kombinationen bauen
    # 4. Exa-Queries: Natural-Language-Varianten
```

**Synonym-Map** (`config/query_templates/synonyms.json`):
```json
{
  "machine learning": ["ML", "deep learning", "neural network"],
  "reinforcement learning": ["RL", "policy gradient", "Q-learning"],
  "natural language processing": ["NLP", "text mining", "computational linguistics"],
  "computer vision": ["CV", "image recognition", "object detection"],
  "autonomous driving": ["self-driving", "automated vehicles", "ADAS"]
}
```

**Lokale SS-Query-Logik:**
1. Topic als Basis-Query
2. Fuer jedes Leitfragen-Keyword: `topic AND keyword`
3. Fuer gefundene Synonyme: `topic AND (term OR synonym1 OR synonym2)`
4. Min. 3 SS-Queries garantiert

**Lokale Exa-Query-Logik:**
1. Topic als Natural-Language-Frage: `"What are recent advances in {topic}?"`
2. Pro Leitfrage: Frage direkt als Query
3. Min. 2 Exa-Queries garantiert

### Stufe 2: LLM-Enhanced (optional, wenn API-Key vorhanden)

```python
async def _expand_llm(topic: str, leitfragen: list[str], config: LLMConfig) -> QuerySet:
    """LLM-gestuetzte Query-Expansion via OpenAI-kompatibles API."""
```

**System-Prompt** (`config/query_templates/expand_prompt.txt`):
```
Du bist ein akademischer Recherche-Assistent. Generiere Suchqueries
fuer eine systematische Literaturrecherche.

Eingabe: Ein Forschungsthema und optionale Leitfragen.

Ausgabe (JSON):
{
  "research_question": "Praezisierte Forschungsfrage",
  "ss_queries": ["Boolean-Query 1", "Boolean-Query 2", ...],
  "exa_queries": ["Natural-Language-Query 1", ...]
}

Regeln:
- ss_queries: Verwende AND/OR Boolean-Operatoren, Synonyme, Akronyme
- exa_queries: Explorative Fragen in natuerlicher Sprache
- Mindestens 3 ss_queries und 2 exa_queries
- Englische Queries (akademische Literatur)
```

**API-Call** (OpenAI Chat Completions Format):
```python
async with httpx.AsyncClient(timeout=config.timeout_s) as client:
    response = await client.post(
        f"{config.base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Thema: {topic}\nLeitfragen: {leitfragen}"},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": config.max_tokens,
            "temperature": 0.3,
        },
    )
```

### Fallback-Kette

```
LLM verfuegbar?
  → Ja: _expand_llm() versuchen
    → Erfolg? → QuerySet(source="llm")
    → Fehler? → _expand_local() + Warning
  → Nein: _expand_local() → QuerySet(source="local")
```

## Integration in `forschungsstand.py`

### Aenderung an `search_papers()`

```python
async def search_papers(
    topic: str,
    *,
    queries: list[str] | None = None,
    config: SearchConfig | None = None,
    screening: ScreeningCriteria | None = None,
    refine: bool = False,           # NEU
    no_validate: bool = True,       # NEU
) -> tuple[list[UnifiedPaper], dict[str, int], PrismaFlow | None]:
```

Wenn `refine=True`:
1. `expand_queries(topic, leitfragen)` aufrufen → `QuerySet`
2. SS-Queries an SS-Client, Exa-Queries an Exa-Client (statt gleiche Queries)
3. Optional: `validate_queries()` Dry-Run
4. Stats um `query_source` erweitern

Wenn `refine=False`: bestehendes Verhalten (identische Queries fuer beide APIs).

### `generate_search_queries()` bleibt

Die Funktion bleibt als Fallback erhalten. `--refine` aktiviert den neuen Pfad,
ohne `--refine` aendert sich nichts.

## CLI-Aenderung in `cli.py`

```python
@app.command()
def search(
    topic: str = typer.Argument(...),
    max_results: int = typer.Option(30, "--max", "-m"),
    use_exa: bool = typer.Option(True, "--exa/--no-exa"),
    year_filter: str = typer.Option(None, "--years", "-y"),
    refine: bool = typer.Option(False, "--refine", "-r",    # NEU
        help="Smart query expansion (lokal + optional LLM)"),
    no_validate: bool = typer.Option(False, "--no-validate", # NEU
        help="Skip dry-run validation of queries"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
```

## Validate Queries (Dry-Run)

```python
async def validate_queries(
    query_set: QuerySet,
    ss_client: SemanticScholarClient,
    exa_client: ExaClient | None = None,
) -> QuerySet:
    """Dry-Run: Prueft ob Queries Ergebnisse liefern."""
    # Pro SS-Query: search_papers(query, limit=1)
    # Bei 0 Ergebnissen: Query entfernen + logger.warning()
    # Garantie: min. 1 SS-Query bleibt (Fallback auf Topic)
```

## Error Handling

| Szenario | Verhalten | Code |
|----------|-----------|------|
| Kein LLM_API_KEY | Stufe 1 (lokal), kein Fehler | Normal |
| LLM Timeout (>30s) | Fallback auf Stufe 1 + Warning | `logger.warning()` |
| LLM gibt kein valides JSON | Fallback auf Stufe 1 + Warning | `logger.warning()` |
| LLM gibt <3 SS-Queries | Lokale Queries ergaenzen bis Min. 3 | Merge |
| Alle Dry-Run Queries 0 Ergebnisse | Topic als Fallback-Query behalten | Garantie |
| httpx.TimeoutException | Wie bestehende Clients (retry + log) | Pattern |

## Config-Dateien

### `config/query_templates/synonyms.json`
Eingebaute Synonym-Map fuer gaengige akademische Terme.
Erweiterbar durch User. ~50 Eintraege initial.

### `config/query_templates/expand_prompt.txt`
System-Prompt fuer LLM-Expansion. Separiert vom Code fuer einfaches Tuning.

## Adversarial Check

1. **Annahmen-Check:** Synonym-Map deckt nur bekannte Terme ab.
   Unbekannte Nischen-Topics profitieren nur von LLM-Stufe.
   → Akzeptabel: Lokale Stufe ist immer noch besser als alte Heuristik.

2. **Alternativen-Check:** Brauchen wir den LLM-Client wirklich?
   → Ja, aber als optionales Upgrade. Lokale Stufe liefert 80% des Werts.
   Der LLM-Client ist <80 Zeilen Code (nur httpx POST + JSON-Parse).

3. **Integrations-Check:** Passt in bestehende Architektur?
   → Ja. Gleiche Patterns wie SS/Exa-Client (async httpx, Pydantic, try/except).
   `search_papers()` bekommt 2 neue optionale Parameter, kein Breaking Change.