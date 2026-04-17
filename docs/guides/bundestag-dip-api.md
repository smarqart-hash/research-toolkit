# Bundestag DIP API — Integrations-Guide

> **Zweck:** Praktische Anleitung fuer die Nutzung des `BundestagClient` +
> `BundestagVocabulary` im research-toolkit. Enthaelt empirisch verifizierte
> Filter-Matrix, Rate-Limit-Strategie und Nutzungs-Patterns.
>
> **Quelle:** docs/research/api-exploration/bundestag-dip.md (Live-Exploration 2026-04-17)

## 1. Was ist DIP?

**DIP** (Dokumentations- und Informationssystem fuer Parlamentsmaterialien) ist die offizielle
Suchschnittstelle des Deutschen Bundestags fuer Drucksachen, Plenarprotokolle, Anfragen
und Gesetzgebungsverfahren ab 1953.

- **Base-URL:** `https://search.dip.bundestag.de/api/v1`
- **Swagger UI:** https://search.dip.bundestag.de/api/v1/swagger-ui/
- **Lizenz:** Datenlizenz Deutschland — Namensnennung 2.0
- **Corpus-Groesse (Stand 17.04.2026):** 285k Drucksachen, 686k Vorgangspositionen, 1.7M Aktivitaeten

**Wann nutzen?** Fuer deutschsprachige Policy-Research, parlamentarische
Beratungsstaende, Gesetzgebungshistorie.

## 2. API-Key

**Oeffentlicher Demo-Key** (als Default im Client hinterlegt, gueltig bis Mai 2026):

```
OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw
```

**Persoenlicher Key (empfohlen fuer Produktion):**

1. Email an `parlamentsdokumentation@bundestag.de` mit Projekt-Kontext
2. Antwort kommt innerhalb weniger Tage
3. Gueltigkeit: 10 Jahre
4. Setzen via ENV-Variable: `BUNDESTAG_API_KEY=...`

Client-Prioritaet: Konstruktor-Arg > ENV-Var > Demo-Key.

## 3. Endpunkt-Matrix (empirisch verifiziert)

**KRITISCH:** DIP-API hat endpunkt-abhaengige Filter-Semantik. Die OpenAPI-Spec listet
Filter an allen Endpunkten, aber sie wirken nicht ueberall. Diese Matrix wurde durch
Live-Tests erstellt (Query "Klimaschutz" vs. ohne Filter, 17.04.2026):

| Filter | `/drucksache` | `/vorgang` | `/vorgangsposition` | `/aktivitaet` |
|--------|:-------------:|:----------:|:-------------------:|:-------------:|
| `f.titel` | filtert | filtert | ? | ignoriert |
| `f.deskriptor` | **ignoriert** | **filtert** | ignoriert | filtert |
| `f.sachgebiet` | ignoriert | filtert | ? | filtert |
| `f.vorgang` | **ignoriert** | n/a | **filtert** | ? |
| `f.vorgangstyp` | filtert | filtert | ? | ignoriert |
| `f.drucksachetyp` | filtert | filtert | ? | ignoriert |
| `f.wahlperiode` | filtert | filtert | filtert | filtert |
| `f.datum.start` / `f.datum.end` | filtert | filtert | filtert | filtert |
| `search` / `q` / `f.volltext` | **ignoriert** | ignoriert | ignoriert | ignoriert |

### Kritische Regeln

- **Keine Volltext-Suche via API** — `search=` wird durchgaengig ignoriert (liefert Vollbestand!)
- **Topic-Research via `/vorgang?f.deskriptor`** — einziger semantisch wirksamer Pfad
- **Drucksache-Join:** nur `/vorgangsposition?f.vorgang={id}` funktioniert
- **`f.deskriptor` Multi-Value = UND** (Schnittmenge), nicht ODER — laut OpenAPI verifiziert

## 4. Deskriptor-Vokabular

DIP pflegt ein **kontrolliertes Vokabular** aus ~80.000 Deskriptoren (Sachbegriffe,
Personen, Geograph. Begriffe). Im Response-JSON pro Vorgang:

```json
"deskriptor": [
  {"name": "Klimaschutz", "typ": "Sachbegriffe", "fundstelle": false},
  {"name": "Harz", "typ": "Geograph. Begriffe", "fundstelle": false}
]
```

**Problem:** Es gibt KEINEN Catalog-Endpunkt fuer das Vokabular. Wer Topic-spezifisch
suchen will, muss das passende Deskriptor-Label kennen.

**Loesung:** `BundestagVocabulary` lernt via Sampling:

```python
from src.agents.bundestag_vocabulary import BundestagVocabulary

vocab = BundestagVocabulary()  # laedt data/vocabularies/bundestag_deskriptoren.json
tv = await vocab.learn("klimaschutz", sample_size=50, min_freq=3)
#    → sucht /vorgang?f.titel=klimaschutz&rows=50
#    → aggregiert deskriptor[].name + sachgebiet[] ueber alle Vorgaenge
#    → filtert min_freq=3 → cached als TopicVocab
vocab.save()  # persistiert nach data/vocabularies/...
```

Cache-Format (`bundestag_deskriptoren.json`):

```json
{
  "version": 1,
  "updated": "2026-04-17T10:00:00Z",
  "topics": {
    "klimaschutz": {
      "topic": "klimaschutz",
      "descriptors": [
        {"name": "Klimaschutz", "freq": 37, "typ": "Sachbegriffe"},
        {"name": "Erneuerbare Energien", "freq": 14, "typ": "Sachbegriffe"}
      ],
      "sachgebiete": [{"name": "Umwelt", "freq": 22}],
      "sample_size": 50,
      "learned_at": "2026-04-17T10:00:00Z"
    }
  }
}
```

**Stale-Check:** Eintraege aelter als 30 Tage werden ignoriert (`get()` gibt `None`).
Re-Learning bei naechstem `get_or_learn()`.

## 5. Nutzungs-Patterns

### 5.1 Topic-Research (Empfohlen)

```python
from src.agents.bundestag_client import BundestagClient
from src.agents.bundestag_vocabulary import BundestagVocabulary

vocab = BundestagVocabulary()
async with BundestagClient() as client:
    papers = await client.search_topic(
        "Klimaschutz",
        rows=50,
        vocabulary=vocab,
        include_positions=False,  # True fuer Drucksachen inkl. PDFs
    )
vocab.save()
# papers: list[UnifiedPaper], gerankt nach Recency + Deskriptor-Freq
```

**Algorithmus:** Cache-first Vocab-Lookup → `/vorgang?f.deskriptor=<top-1>` →
Dedup + Ranking. Fallback auf `f.titel` wenn Vocabulary leer.

### 5.2 Titel-Suche (einfach, schlicht)

```python
response = await client.search_drucksachen(
    "Klimaschutz",
    typ="Gesetzentwurf",
    datum_start="2024-01-01",
    rows=20,
)
# response.documents: list[DIPDrucksache]
```

Sendet `f.titel=Klimaschutz&f.drucksachetyp=Gesetzentwurf`. Keine semantische Expansion.

### 5.3 Vorgang-Detail mit Deskriptoren

```python
vorgang = await client.get_vorgang("333085")
# vorgang.deskriptor: list[Deskriptor]
# vorgang.sachgebiet: list[str]
```

### 5.4 Drucksache-Enrichment (PDFs zu einem Vorgang)

```python
response = await client.get_vorgangspositionen("333578", rows=20)
for pos in response.documents:
    if pos.fundstelle:
        print(pos.fundstelle.dokumentnummer, pos.fundstelle.pdf_url)
```

### 5.5 Pipeline-Integration (forschungsstand.py)

`_search_bundestag()` in `forschungsstand.py` nutzt intern `search_topic` mit
persistentem Vocabulary. Aktivierung via CLI:

```bash
research-toolkit search "Klimaschutz" --sources ss,openalex,bundestag
```

## 6. Known Quirks

| Quirk | Impact | Workaround |
|-------|--------|-----------|
| `search=` wird ignoriert | Liefert Vollbestand 285k | `f.titel` nutzen (via `search_drucksachen`) |
| `f.deskriptor` ignoriert an `/drucksache` | Keine Deskriptor-basierte Drucksachen-Suche | Ueber `/vorgang` gehen |
| `f.vorgang` ignoriert an `/drucksache` | Kein direkter Drucksache-per-Vorgang-Abruf | `/vorgangsposition?f.vorgang` nutzen |
| `/vorgang/{id}` ohne Drucksachen-Links | Kein Enrichment via Detail-Call | Separater `/vorgangsposition`-Call |
| Multi-Value `f.deskriptor` = UND | Unintuitiv, kann zu 0-Hits fuehren | Einzelne Requests + Client-Side Union |
| Rate-Limit nicht offengelegt | Sperrungsrisiko bei Missbrauch | 1s Sleep + max 30 req/min |
| Aeltere Datensaetze (vor ~2000) ohne Deskriptoren | Vocabulary-Learning reduziert bei WP1-10 | `min_freq`-Filter, `f.titel`-Fallback |
| `f.drucksachetyp` statt `f.typ` (Parameter-Name) | Legacy-Code in Pre-V3 sendete `f.typ` | Client fixed in V3 |

## 7. Cross-Project Wiederverwendung

Fuer andere DE-Policy-Projekte:

### Portable Artefakte

- `data/vocabularies/bundestag_deskriptoren.json` — JSON-Cache, API-agnostisch
- `src/agents/bundestag_client.py` — Client mit Models
- `src/agents/bundestag_vocabulary.py` — Cache-Manager

### Import-Pattern (outside project)

```python
# Vocabulary-Cache kann einfach kopiert werden
from pathlib import Path
vocab = BundestagVocabulary(cache_path=Path("/shared/bundestag_vocab.json"))
```

### Embedding-Kandidaten (Future Work)

- Deskriptoren als Embeddings fuer Topic-Matching (statt Titel-Fuzzy-Match)
- SPARQL-Endpunkt fuer DIP (aktuell nur REST)
- Delta-Feeds (WP21 Live-Updates)

## 8. Rate-Limit-Strategie

DIP hat **keine offiziellen Rate-Limits**. Konservative Defaults im Client:

| Scope | Strategie |
|-------|-----------|
| Client | 1s Sleep zwischen Bulk-Calls (`TOPIC_RATE_LIMIT_SLEEP_S`) |
| HTTP 429 | Exponential backoff, max 3 Retries |
| Vocabulary-Learning | 1s Sleep pro `learn()`-Call |
| Seed-Scripts | 30 Topics × 1 Call = 30 Requests ≈ 30s |
| Pipeline | Max 5 parallele Topics, 5s Batch-Sleep |

**Sperrungs-Risiko:** Burst > 30 req/min koennte temporaere Sperrung ausloesen.
Exakte Grenzen nicht bekannt — konservativ bleiben.

## 9. Testing

### Mock-Tests

`tests/test_bundestag_client.py` — 33 Tests (Models, Regression, Converter, search_topic).

### Vocabulary-Unit

`tests/test_bundestag_vocabulary.py` — 18 Tests (Cache Round-Trip, Learning, Stale).

### Live-Tests (optional)

```bash
pytest tests/test_bundestag_live.py -m live -v
# Benoetigt Internet. Demo-Key reicht.
```

Testet 10 realistische Policy-Topics gegen echte DIP. DoD:
- `>= 70%` liefern 5–50k Hits
- `0%` liefern > 50k (Regression-Guard gegen V1-Bug)
- Median zwischen 10 und 10k

## 10. Migration von Pre-V3

### Breaking Changes

**Keine.** Die Legacy-Methoden (`search_drucksachen`, `search_vorgaenge`) sind
weiterhin verfuegbar, nur intern auf die korrekten Parameter umgestellt.

### Empfohlene Migration

```diff
  from src.agents.bundestag_client import BundestagClient

  async with BundestagClient() as client:
-     result = await client.search_drucksachen("Klimaschutz", rows=50)
-     for doc in result.documents: ...
+     from src.agents.bundestag_vocabulary import BundestagVocabulary
+     vocab = BundestagVocabulary()
+     papers = await client.search_topic("Klimaschutz", rows=50, vocabulary=vocab)
+     vocab.save()
```

Topic-Pipelines profitieren deutlich (2-3x relevantere Hits in Exploration).
Titel-Suchen (z.B. "Bundeswehr" → Gesetzentwurf X) bleiben bei `search_drucksachen`.

### briefing-app Integration

Die briefing-app importiert `research_toolkit` via `pip install -e`. Nach
Merge auf master wirkt der Fix nach Worker-Neustart. Known-Issue-Eintrag in
briefing-app `CLAUDE.md` ("Bundestag 200 Hits Regression") kann entfernt werden.
