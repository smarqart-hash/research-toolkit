# Sprint 1 Spec: Search Quality

> Branch: `feature/search-quality` | Findings: F1, F6, F2
> Strategie: Verbessern UND Ceiling sichtbar machen

## Ziel

Die Search-Pipeline wird in zwei Dimensionen verbessert:
1. **Qualitaet** — Besseres Ranking (SPECTER2), expliziter Screening-Schritt
2. **Transparenz** — PRISMA-Flow macht Verluste sichtbar, Provenance loggt Entscheidungen

---

## Deliverable 1: Screening-Schritt (F1)

### Was

Nach Ranking und vor Ausgabe: Expliziter Include/Exclude-Schritt mit
konfigurierbaren Kriterien. Macht den PRISMA-Flow sichtbar.

### Dateien

| Datei | Aenderung |
|-------|-----------|
| `src/agents/screener.py` | **NEU** — Screening-Logik |
| `src/agents/forschungsstand.py` | Screening in Pipeline einhaengen |
| `src/pipeline/provenance.py` | Keine Aenderung (API reicht) |
| `tests/test_screener.py` | **NEU** — Tests fuer Screening |
| `tests/test_forschungsstand.py` | Erweitern (Screening-Integration) |

### Datenmodell

```python
# src/agents/screener.py

class ScreeningCriteria(BaseModel):
    """Konfigurierbare Inclusion/Exclusion-Kriterien."""
    min_year: int | None = None
    max_year: int | None = None
    require_abstract: bool = False
    min_citation_count: int | None = None
    exclude_fields: list[str] = Field(default_factory=list)
    # z.B. ["Medicine", "Biology"] um fachfremde Papers auszuschliessen
    include_keywords: list[str] = Field(default_factory=list)
    # Mindestens 1 Keyword in Title/Abstract
    exclude_keywords: list[str] = Field(default_factory=list)

class ScreeningDecision(BaseModel):
    """Einzelne Screening-Entscheidung (fuer Provenance)."""
    paper_id: str
    included: bool
    reason: str  # z.B. "excluded: field Biology", "included: keyword match"

class ScreeningResult(BaseModel):
    """Ergebnis des Screening-Schritts."""
    included: list[UnifiedPaper]
    excluded: list[ScreeningDecision]
    prisma_flow: PrismaFlow

class PrismaFlow(BaseModel):
    """PRISMA-Flow-Statistik."""
    identified: int       # Vor Dedup
    after_dedup: int      # Nach Dedup
    after_ranking: int    # Nach Top-K
    screened: int         # = after_ranking
    included: int         # Nach Screening
    excluded: int         # Screened - Included
    exclusion_reasons: dict[str, int]  # z.B. {"no_abstract": 5, "field_mismatch": 3}
```

### Funktion

```python
def screen_papers(
    papers: Sequence[UnifiedPaper],
    criteria: ScreeningCriteria,
) -> ScreeningResult:
    """Wendet Inclusion/Exclusion-Kriterien an.

    Jede Entscheidung wird als ScreeningDecision protokolliert.
    """
```

### Pipeline-Integration

```python
# forschungsstand.py — search_papers()
# Aktuell: deduplicate -> rank -> return
# Neu:     deduplicate -> rank -> screen (optional) -> return

async def search_papers(
    topic: str,
    *,
    queries: list[str] | None = None,
    config: SearchConfig | None = None,
    screening: ScreeningCriteria | None = None,  # NEU
) -> tuple[list[UnifiedPaper], dict[str, int], PrismaFlow | None]:  # NEU: 3. Rueckgabewert
```

### Provenance

Screening-Entscheidungen werden in provenance.jsonl geloggt:
```json
{
  "phase": "search",
  "agent": "screener",
  "action": "exclude",
  "source": "doi:10.1234/x",
  "metadata": {"reason": "field_mismatch", "field": "Biology"}
}
```

### Tests

- `test_screen_no_criteria` — Alles durchlassen bei leeren Kriterien
- `test_screen_min_year` — Papers vor min_year ausschliessen
- `test_screen_require_abstract` — Papers ohne Abstract ausschliessen
- `test_screen_exclude_fields` — Fachfremde Papers filtern
- `test_screen_keywords` — Keyword-basiertes Include/Exclude
- `test_screen_combined` — Mehrere Kriterien gleichzeitig
- `test_prisma_flow_counts` — Zaehler stimmen
- `test_screening_decisions_logged` — Jede Entscheidung hat reason
- `test_integration_search_with_screening` — End-to-End in forschungsstand

---

## Deliverable 2: Ranking verbessern (F6)

### Was

SPECTER2-Embeddings fuer semantische Relevanz aktivieren. Zusaetzlicher Score-Faktor
neben Citations + Recency. Macht das Ranking testbar: Man kann heuristischen Score
gegen SPECTER2-Score vergleichen.

### Dateien

| Datei | Aenderung |
|-------|-----------|
| `src/agents/paper_ranker.py` | SPECTER2-Score einbauen, Gewichtung anpassen |
| `tests/test_paper_ranker.py` | Erweitern (SPECTER2-Tests, Score-Vergleich) |

### Design-Entscheidung: Graceful Degradation

SPECTER2 ist eine optionale Dependency (`[nlp]`). Das Ranking MUSS auch ohne
funktionieren. Aktuelles Verhalten (heuristische Score) bleibt der Fallback.

```python
# paper_ranker.py

def compute_specter2_similarity(
    query: str,
    papers: Sequence[UnifiedPaper],
) -> dict[str, float]:
    """Berechnet SPECTER2-Cosine-Similarity zwischen Query und Paper-Abstracts.

    Returns:
        Dict von paper_id -> similarity_score (0-1).
        Leeres Dict wenn sentence-transformers nicht installiert.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.info("sentence-transformers nicht installiert, SPECTER2 uebersprungen")
        return {}
    ...
```

### Ranking-Score Anpassung

```python
# Aktuell (Baseline — bleibt als Fallback):
# 40% Citations + 30% Recency + 10% OA + 10% Abstract + 10% SS

# Neu (wenn SPECTER2 verfuegbar):
# 30% SPECTER2 Similarity + 25% Citations + 25% Recency + 10% OA + 10% Abstract

# Der SS-Source-Bonus (10%) faellt weg — SPECTER2 macht ihn obsolet
```

### Testbarkeit (Ceiling sichtbar machen)

```python
def rank_papers(
    papers: Sequence[UnifiedPaper],
    *,
    top_k: int | None = None,
    query: str | None = None,  # NEU: fuer SPECTER2
) -> list[UnifiedPaper]:
    """Rankt Papers. Mit query: SPECTER2-enhanced. Ohne: heuristic fallback."""
```

Neue Tests:
- `test_rank_without_specter2` — Heuristik funktioniert wie bisher
- `test_rank_with_specter2` — SPECTER2-Score beeinflusst Ranking
- `test_rank_specter2_not_installed` — Graceful Fallback auf Heuristik
- `test_score_comparison` — Loggt beide Scores nebeneinander (Ceiling-Test)

### Ceiling-Transparenz

Ein neues Feld in UnifiedPaper:
```python
class UnifiedPaper(BaseModel):
    ...
    specter2_score: float | None = None  # NEU: None wenn nicht berechnet
```

Das erlaubt spaeteres Auswerten: "Wie sehr weichen heuristic und SPECTER2 ab?"
Grosse Abweichungen = Ceiling des heuristischen Rankings.

---

## Deliverable 3: Pipeline-Dokumentation (F2)

### Was

`skills/pipeline.md` erklaert die Skill-Verkettung, State Machine,
und wo die Grenzen des Systems liegen.

### Datei

| Datei | Aenderung |
|-------|-----------|
| `skills/pipeline.md` | **NEU** |

### Inhalt

1. **Pipeline-Ueberblick** — Search -> Draft -> Review -> Check
2. **State Machine** — 6 Phasen, HITL Gates, Checkpoint/Resume
3. **Datenfluss** — Evidence Cards als Kopplung zwischen Skills
4. **Provenance** — Was wird geloggt, warum, PRISMA-trAIce
5. **PRISMA-Flow** — NEU: Screening-Statistik als Teil der Pipeline
6. **Beispiel-Pipeline-Run** — Konkreter Durchlauf mit Zahlen
7. **Ceiling-Transparenz** — Was die Pipeline kann, was nicht
   - Ranking: heuristisch + SPECTER2, aber kein Ground-Truth-Feedback
   - Review: misst Legibility, nicht epistemische Qualitaet
   - HITL Gates: ehrliches Engineering fuer menschliche Entscheidungen

---

## Reihenfolge

1. **Screener** (Deliverable 1) — neues Modul, unabhaengig
2. **Ranking** (Deliverable 2) — aendert paper_ranker.py
3. **Integration** — Screening + neues Ranking in forschungsstand.py einhaengen
4. **pipeline.md** (Deliverable 3) — Doku, nachdem Code steht
5. **Tests** — Begleitend zu jedem Deliverable (TDD)

## Bestehende Tests

207 Tests muessen weiter passing sein. Keine Breaking Changes:
- `search_papers()` bekommt optionale Parameter (Rueckwaertskompatibel)
- `rank_papers()` bekommt optionalen `query` Parameter
- `UnifiedPaper` bekommt optionales `specter2_score` Feld (default None)
- Heuristische Score-Formel aendert sich NUR wenn SPECTER2 verfuegbar

## Abgrenzung (Out of Scope)

- LLM-basiertes Screening (Finding 1 erwaehnt GPT-Screening — wir machen
  regelbasiert, nicht LLM-basiert, weil testbar und deterministisch)
- Ground-Truth-Feedback-Loop fuer Ranking (waere Sprint 3+)
- CLI-Flags (`--screen`, `--specter2`) — API-first, CLI spaeter
