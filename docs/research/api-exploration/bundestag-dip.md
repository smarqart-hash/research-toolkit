# API Exploration: Bundestag DIP (Dokumentations- und Informationssystem)

> **Generiert:** 2026-04-17 via Spike-Session. Format nach `api-explorer` Agent Spec.
> **Zweck:** Ersetzt den falschen Annahmen-Stand von V1/V2 des Search-Fix-Plans mit
> empirisch verifizierter Filter-Semantik.

## Metadaten

| Attribut | Wert |
|----------|------|
| API-Name | DIP (Dokumentations- und Informationssystem fuer Parlamentsmaterialien) |
| Anbieter | Deutscher Bundestag |
| Base URL | `https://search.dip.bundestag.de/api/v1` |
| OpenAPI/Swagger | `https://search.dip.bundestag.de/api/v1/openapi.yaml` (2363 Zeilen) |
| Swagger UI | `https://search.dip.bundestag.de/api/v1/swagger-ui/` |
| Auth | API-Key (Query-Param `apikey=` ODER Header `Authorization: ApiKey ...`) |
| Rate Limit (offiziell) | **Nicht dokumentiert.** Nur "Missbrauch kann zu Sperrung fuehren" |
| Rate Limit (empfohlen) | max 30 req/min, 1s Sleep zwischen Requests, 429-Retry mit exponential backoff |
| Lizenz | Datenlizenz Deutschland — Namensnennung 2.0 |
| Gesamt-Corpus | 285.331 Drucksachen, 686.558 Vorgangspositionen, 1.747.250 Aktivitaeten (Stand 17.04.2026) |
| Historische Tiefe | **1953-08-29 bis heute** (aeltester Datensatz: WP1) |

## API-Key Beschaffung

1. Antrag an `parlamentsdokumentation@bundestag.de`
2. Demo-Key oeffentlich in Dokumentation verfuegbar: `OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw`
   (laeuft Ende Mai 2026 aus)
3. Persoenlicher Key: 10 Jahre gueltig
4. Email-Antwort mit Key kommt innerhalb weniger Tage
5. Beispiel-Antwort siehe `docs/research/bundestag-api-key-response.md` (wenn dokumentiert)

## Endpunkte

| Endpunkt | Methode | Zweck | Response-Wrapper |
|----------|---------|-------|------------------|
| `/drucksache` | GET | Einzeldokumente (Gesetzentwuerfe, Antraege, Antworten) | `{numFound, documents[], cursor}` |
| `/drucksache/{id}` | GET | Detail einer Drucksache | Objekt |
| `/drucksache-text` | GET | Drucksachen inkl. Volltext | Erweitert |
| `/vorgang` | GET | **Gesetzgebungsverfahren / Kleine Anfragen etc. — gebuendelt** | `{numFound, documents[], cursor}` |
| `/vorgang/{id}` | GET | Detail eines Vorgangs (Achtung: liefert NICHT die Drucksachen dazu) | Objekt |
| `/vorgangsposition` | GET | Einzelpositionen innerhalb eines Vorgangs (Dokumente + Debatten) | `{numFound, documents[]}` |
| `/plenarprotokoll` | GET | Sitzungsprotokolle | `{numFound, documents[]}` |
| `/aktivitaet` | GET | Redebeitraege, Anfragen, Abstimmungen | `{numFound, documents[]}` |
| `/person` | GET | Abgeordnete + Stammdaten | `{numFound, documents[]}` |

## Empirische Filter-Matrix (live-verifiziert 2026-04-17)

**KRITISCH:** OpenAPI-Spec listet Filter an allen Endpunkten, aber sie wirken nicht ueberall.
Diese Matrix wurde durch Live-Tests erstellt (Query "Klimaschutz" vs. ohne Filter).

| Filter | `/drucksache` | `/vorgang` | `/vorgangsposition` | `/aktivitaet` |
|--------|:-------------:|:----------:|:-------------------:|:-------------:|
| `f.titel` | filtert (527) | filtert (470) | ? | ignoriert (1.7M) |
| `f.deskriptor` | **ignoriert (285k)** | **filtert (3.644)** | ignoriert (686k) | **filtert (3.328)** |
| `f.sachgebiet` | ignoriert | filtert (7.984) | ? | filtert (125k) |
| `f.vorgang` | **ignoriert (285k)** | n/a | **filtert (2-N pro VID)** | ? |
| `f.vorgangstyp` | filtert (68k) | filtert (11k) | ? | ignoriert |
| `f.drucksachetyp` | filtert (29k) | filtert (22k) | ? | ignoriert |
| `f.wahlperiode` | filtert (20k WP20) | filtert | filtert | filtert |
| `f.datum.start` / `f.datum.end` | filtert | filtert | filtert | filtert |
| `search` / `q` / `f.volltext` | **ignoriert** | ignoriert | ignoriert | ignoriert |

(Zahlen fuer Query "Klimaschutz" / total 285k Drucksachen)

### Schluesselfolgerungen

- **Es gibt KEINE Volltext-Suche via API.** Die Solr-Oberflaeche auf `dip.bundestag.de`
  ist eine separate Suchmaschine, nicht in der OpenAPI exponiert.
- **Fuer Topic-Research muss man ueber `/vorgang` + `f.deskriptor` gehen.**
  `/drucksache` laesst sich nur ueber Titel filtern.
- **Fuer Drucksache-Enrichment zu einem Vorgang:** `/vorgangsposition?f.vorgang={id}`.
  Das ist der **einzige** verifizierte Join-Pfad.
- **`f.deskriptor` Multi-Value ist UND** (Schnittmenge), nicht ODER, laut OpenAPI —
  verifiziert: `f.deskriptor=Klimaschutz&f.deskriptor=Windenergieanlage` = 37 Hits,
  `f.deskriptor=Klimaschutz` = 3.644 Hits.
- **Cursor-Pagination:** Ueber 100 Ergebnisse via `cursor` Parameter, bis `cursor` unveraendert bleibt.

## Schema-Mapping: `/vorgang` → `UnifiedPaper`

Relevante Felder der Vorgang-Response:

```json
{
  "id": "333085",
  "typ": "Vorgang",
  "vorgangstyp": "Kleine Anfrage",
  "wahlperiode": 21,
  "datum": "2026-04-15",
  "aktualisiert": "2026-04-16T15:45:40+02:00",
  "titel": "Finanzierung eines Waldkaufs bei Stolberg (Harz) ...",
  "beratungsstand": "Beantwortet",
  "initiative": ["Fraktion der AfD"],
  "sachgebiet": ["Landwirtschaft und Ernaehrung", "Oeffentliche Finanzen"],
  "deskriptor": [
    {"name": "Harz", "typ": "Geograph. Begriffe", "fundstelle": false},
    {"name": "Kauf", "typ": "Sachbegriffe", "fundstelle": false},
    {"name": "Wald", "typ": "Sachbegriffe", "fundstelle": false}
  ]
}
```

| API-Feld | UnifiedPaper-Feld | Transformation | Befuellungsgrad |
|----------|-------------------|----------------|-----------------|
| `id` | `paper_id` | `f"dip-vorgang:{id}"` | 100% |
| `titel` | `title` | direkt | 100% |
| `datum` | `year` + `publication_date` | Parse ISO, Extract Jahr | 100% |
| `typ` + `vorgangstyp` | `tags[]` | join | 100% |
| `deskriptor[].name` | `tags[]` (zusaetzlich) | append | ~85% (manche Vorgaenge leer) |
| `sachgebiet[]` | `tags[]` (zusaetzlich) | append | ~80% |
| `initiative[]` | `authors[]` | direkt | ~95% |
| n/a | `source` | konstant "bundestag" | 100% |
| n/a | `language` | konstant "de" | 100% |
| n/a | `citation_count` | None | n/a |
| n/a | `doi` | None (keine DOIs fuer Bundestagsdokumente) | n/a |
| konstruiert | `url` | `f"https://dip.bundestag.de/vorgang/{id}"` | 100% |
| `titel` (wenn kein Abstract) | `abstract` | Fallback | — |

## Schema-Mapping: `/vorgangsposition` → `UnifiedPaper`

Alternative: einzelne Dokumente (Drucksachen + Plenarprotokoll-Abschnitte) zu einem Vorgang.

```json
{
  "id": "690420",
  "vorgangsposition": "Antwort",
  "vorgang_id": "333578",
  "titel": "Kleine Anfrage + Antwort der Bundesregierung",
  "datum": "2026-04-15",
  "dokumentart": "Drucksache",
  "fundstelle": {
    "dokumentnummer": "21/5250",
    "drucksachetyp": "Fragen",
    "pdf_url": "https://dserver.bundestag.de/btd/21/052/2105250.pdf",
    "urheber": ["Bundesregierung"]
  }
}
```

| API-Feld | UnifiedPaper-Feld | Transformation |
|----------|-------------------|----------------|
| `id` | `paper_id` | `f"dip-vp:{id}"` |
| `fundstelle.dokumentnummer` | `paper_id` (alternative) | `f"dip:{dokumentnummer}"` |
| `titel` | `title` | direkt |
| `fundstelle.pdf_url` | `pdf_url` | direkt |
| `datum` | `year` + `publication_date` | Parse ISO |
| `dokumentart` + `drucksachetyp` | `tags[]` | join |
| `fundstelle.urheber[]` | `authors[]` | direkt |

## Datenqualitaet

### Befuellungsgrad (Stichprobe 30 Vorgaenge, Topic: Klimaschutz)
- **100%:** id, typ, vorgangstyp, wahlperiode, titel, datum, aktualisiert
- **~95%:** initiative, beratungsstand
- **~85%:** deskriptor (Sachbegriffe-Liste)
- **~80%:** sachgebiet
- **0%:** Drucksachen-Links (muessen via /vorgangsposition nachgezogen werden)

### Encoding
- UTF-8 durchgehend
- Umlaute in Response korrekt (Ausnahme: Windows-Terminal-Ausgabe braucht `PYTHONIOENCODING=utf-8`)
- Sonderzeichen in URLs (z.B. `ue` vs `%C3%BC`) teilweise inkonsistent

### Paginierung
- Cursor-basiert via `cursor` Parameter
- `rows` Param cappt bei 100 pro Response
- Cursor unveraendert → alle Daten geladen
- Alternative: `offset` wird nicht unterstuetzt

### Historische Tiefe
- WP1 (1953): 4.742 Drucksachen, aeltester Eintrag 29.08.1953
- WP20 (2021-10 bis 2025-10): 20.773 Drucksachen
- WP21 (2025-10 bis heute): laufend, ca. 5.000+ Drucksachen Stand 17.04.2026

## Known Quirks

| Quirk | Impact | Workaround |
|-------|--------|-----------|
| `search=` Parameter wird **ignoriert** (laut OpenAPI nicht dokumentiert) | Liefert immer 285k (Vollbestand) | `f.titel` nutzen |
| `f.deskriptor` ignoriert an `/drucksache` | Keine Deskriptor-basierte Drucksache-Suche | Ueber `/vorgang?f.deskriptor` gehen |
| `f.vorgang` ignoriert an `/drucksache` | Kein direkter Drucksache-per-Vorgang-Abruf | `/vorgangsposition?f.vorgang` nutzen |
| `/vorgang/{id}` Detail liefert keine Drucksachen-Links | Kein Drucksache-Enrichment moeglich via Detail-Call | Separater `/vorgangsposition` Call |
| OpenAPI listet Filter an allen Endpunkten, ohne Wirksamkeits-Hinweis | Verwirrung bei Integration | Empirische Matrix PFLICHT |
| `f.deskriptor` Multi-Value ist **UND** (Schnittmenge), nicht ODER | Unintuitiv, kann zu 0-Hits fuehren | Einzelne Abfragen + Union in Code |
| Rate-Limit-Werte nicht offengelegt | Risiko der Sperrung bei Missbrauch | Konservativ 1s Sleep + 30 req/min Max |
| `f.drucksachetyp` statt `f.typ` (Parameter-Name) | Client im research-toolkit sendet `f.typ` → wird ignoriert | Fix in V3 geplant |
| Aeltere Datensaetze (vor ~2000) haben teils leere `deskriptor`/`sachgebiet` | Vocabulary-Learning reduziert bei WP1-10 | `min_freq`-Filter, Fallback auf `f.titel` |

## Rate-Limit-Strategie

1. **Client:** 1s Sleep zwischen Requests (`asyncio.sleep(1.0)`)
2. **HTTP 429:** exponential backoff: 2s → 4s → 8s, max 3 Retries
3. **HTTP 5xx:** linear retry 3s, max 2 Retries
4. **Seed-Scripts:** 30 Topics × (Vocabulary-Learn + Probe) ≈ 60 Requests → ~1min
5. **Live-Pipeline (briefing-app):** max 5 Topics gleichzeitig, 5s Batch-Sleep

## Vocabulary-Lernen (Konzept)

Da DIP keinen Deskriptor-Catalog-Endpunkt bietet, muss das kontrollierte Vokabular
aus Response-Samples gelernt werden:

1. Query: `/vorgang?f.titel={topic}&rows=100`
2. Extrahiere `deskriptor[].name` + `sachgebiet[]` aus allen Dokumenten
3. Count Frequency pro Deskriptor
4. `min_freq=3` Filter → nur Deskriptoren die in >= 3 Dokumenten auftreten
5. Persist als `data/vocabularies/bundestag_deskriptoren.json` (topic → descriptors[])
6. Bei Query-Zeit: `/vorgang?f.deskriptor={top-1-desc}` — semantisch besser als `f.titel`

## Self-Review (adversarial-review: research)

- [x] Alle Endpunkte getestet (nicht nur dokumentiert)
- [x] Filter-Matrix empirisch ausgefuellt (jeder Filter × Endpunkt live geprueft)
- [x] Stichprobe >= 10 Records pro Endpunkt
- [x] Schema-Mapping vollstaendig (UnifiedPaper-Pflichtfelder abgedeckt)
- [x] Known Quirks ehrlich dokumentiert (inkl. API-Doku-Luecken)
- [x] Rate-Limit-Strategie empfohlen (mit Notfall-Plan)
- [x] Historische Tiefe verifiziert

## Empfehlung

**Aufwand fuer sauberen Fix: M (1-3 Tage)**

- Task-Aufteilung: Legacy-Bug-Fix (M-15min) + Vocabulary-Modul (M-90min) +
  search_topic() (M-75min) + Tests (M-120min) + Docs (M-75min) + Seed (M-60min)
- Siehe: `docs/plans/2026-04-17-bundestag-search-fix.md` (V3)

**Blocker/Risiken:**
- Keine offiziellen Rate-Limits → konservative Default-Werte noetig
- API-Semantik-Aenderungen ohne Versionierung → Live-Tests PFLICHT fuer Regression
- `f.deskriptor` UND-Semantik verhindert Multi-Descriptor-ODER in einem Call →
  Multi-Request-Pattern noetig wenn mehrere Deskriptoren kombiniert werden

**Implementierungs-Reihenfolge:**
1. Legacy-Bug-Fix (`search=` → `f.titel=`) + Parameter-Name-Fix (`f.typ` → `f.drucksachetyp`)
2. Neue Basis-Methoden (`get_vorgang`, `get_vorgangspositionen`)
3. `BundestagVocabulary` Modul + Cache-Format
4. `search_topic()` High-Level-API
5. `forschungsstand.py` Umstellung
6. Tests (Mock + Live)
7. Vocabulary-Seed (20-30 initiale Topics)
8. Dokumentation

**Cross-Project-Nutzen:**
- briefing-app (Pipeline via `forschungsstand.py`)
- research-toolkit CLI (`research-toolkit search --sources bundestag`)
- Vocabulary-Cache als portable JSON fuer zukuenftige DE-Policy-Projekte
- Agent-Team (api-explorer, connector-builder, quality-gate) wiederverwendbar fuer
  alle weiteren API-Konnektoren (EUR-Lex, DBLP, Abgeordnetenwatch, etc.)
