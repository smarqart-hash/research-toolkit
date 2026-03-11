# Requirements: Smart Query Generation

**Scope:** Backend (Python-Modul + CLI) | **Erstellt:** 2026-03-10

## Zweck

LLM-gestuetzte Query-Optimierung fuer die Paper-Suche. Ersetzt die
Heuristik in `generate_search_queries()` durch einen intelligenten
Generator mit Synonym-Expansion, getrennten SS/Exa-Formaten und
optionaler Dry-Run-Validierung.

## Modul-API

### Neues Modul: `src/agents/query_generator.py`

**Eingabe:**
| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|--------------|
| topic | `str` | Ja | Freitext-Thema |
| leitfragen | `list[str]` | Nein | Optionale Leitfragen |
| scope | `SearchScope` | Nein | Jahr, Sprache, Venues |

**Ausgabe:** `QuerySet` (Pydantic v2 BaseModel)
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| research_question | `str` | Praezisierte Forschungsfrage |
| ss_queries | `list[str]` | Boolean-Format fuer Semantic Scholar |
| exa_queries | `list[str]` | Natural-Language-Format fuer Exa |
| scope | `SearchScope` | Angewendeter Suchbereich |

### Funktionen

1. **`refine_topic(topic, leitfragen?) -> str`** (async)
   - Vages Topic → praezise Research Question
   - **Lokal:** Leitfragen-Kern extrahieren, Topic anreichern
   - **LLM-enhanced:** PICO/SPIDER-Framework, kreative Umformulierung
   - Fallback: gibt `topic` unveraendert zurueck bei Fehler

2. **`expand_queries(research_question, scope?) -> QuerySet`** (async)
   - Research Question → mehrere Queries mit Synonymen + Akronymen
   - **Lokal:** Eingebaute Synonym-Maps, regelbasierte Boolean-Queries
   - **LLM-enhanced:** Kreativere Synonyme, Akronyme, verwandte Konzepte
   - SS-Queries: Boolean-Operatoren (AND/OR), Field-of-Study-Tags
   - Exa-Queries: Natural Language, explorativer
   - Min. 3 SS-Queries + 2 Exa-Queries

3. **`validate_queries(query_set, ss_client, exa_client?) -> QuerySet`** (async)
   - Dry-Run: Top-1 Ergebnis pro Query pruefen
   - Bei 0 Ergebnissen: Query entfernen + Warning loggen
   - Optional (kann uebersprungen werden via `--no-validate`)

### CLI-Integration

| Flag | Typ | Default | Beschreibung |
|------|-----|---------|--------------|
| `--refine` | bool | False | LLM-Query-Generierung aktivieren |
| `--no-validate` | bool | False | Dry-Run-Validierung ueberspringen |

Ohne `--refine`: alte Heuristik (kein Breaking Change).

## LLM-Provider

**2-Stufen-Architektur:**

1. **Lokal (Default, kein API-Key noetig):**
   - Template-basierte Synonym-Expansion (eingebaute Synonym-Maps)
   - Regelbasiertes Boolean-Query-Building fuer SS
   - Natural-Language-Umformulierung fuer Exa
   - Laeuft immer, offline, kostenlos

2. **LLM-enhanced (optional, mit API-Key):**
   - Kreativere Synonyme, Akronyme, verwandte Konzepte
   - Bessere Topic-Refinement (PICO/SPIDER)
   - Aktiviert wenn `OPENROUTER_API_KEY` oder `LLM_API_KEY` gesetzt

**Provider:** OpenAI-kompatibles API via `httpx` (bereits installiert).
Keine neue Dependency noetig.

| Env-Var | Default | Beschreibung |
|---------|---------|--------------|
| `LLM_BASE_URL` | `https://openrouter.ai/api/v1` | API-Endpoint |
| `LLM_API_KEY` | — | API-Key (OpenRouter, OpenAI, Ollama etc.) |
| `LLM_MODEL` | `google/gemini-2.0-flash-exp:free` | Modell-ID |

**Empfohlene Free-Tier-Modelle (OpenRouter):**
- `google/gemini-2.0-flash-exp:free` (Default)
- `meta-llama/llama-3.3-70b-instruct:free`

**Kein neues Package.** Nur `httpx` (schon da) + OpenAI-Chat-Completions-Format.

## Error Cases

| Bedingung | Verhalten |
|-----------|-----------|
| `--refine` ohne API-Key | Lokale Expansion (Stufe 1), kein Fehler |
| LLM-Timeout (>30s) | Fallback auf Heuristik + Warning |
| LLM gibt unbrauchbare Queries | Fallback auf Heuristik + Warning |
| Dry-Run: alle Queries 0 Ergebnisse | Warning, Heuristik-Queries als Backup |
| Kein Netzwerk | Wie bisher (httpx-Fehler werden geloggt) |

## Nicht in diesem Feature (Scope Guard)

- [x] Kein neuer CLI-Command (bleibt `search`)
- [x] Keine Aenderung an Ranking/Screening/Deduplizierung
- [x] Kein LLM-gestuetztes Clustering oder Zusammenfassung
- [x] Keine persistente Query-History oder Caching
- [x] Kein interaktiver Modus (Query-Feedback-Loop)

## Erfolgskriterien

- [ ] `--refine` generiert min. 5 Queries (3 SS + 2 Exa)
- [ ] Queries enthalten Synonyme die in der Heuristik fehlen
- [ ] Dry-Run erkennt irrelevante Queries (>= 1 Test-Case)
- [ ] Ohne `--refine`: identisches Verhalten (Regression)
- [ ] Ohne API-Key: lokale Expansion funktioniert (min. 5 Queries)
- [ ] Mit API-Key: LLM-enhanced Queries sind qualitativ besser
- [ ] Zero neue Dependencies (nur httpx)
- [ ] Tests: >= 90% Coverage fuer `query_generator.py`
- [ ] `pytest tests/ -v` — alle bestehenden 248 Tests passing
- [ ] Graceful Degradation bei LLM-Fehler → Heuristik-Fallback

## Dependency Check Ergebnisse

| Check | Ergebnis |
|-------|----------|
| Feature existiert? | `generate_search_queries()` in forschungsstand.py:191 (Heuristik) |
| Kein `query_generator.py` | Korrekt, muss neu erstellt werden |
| Libraries | httpx vorhanden, keine neue Dependency noetig |
| Bestehende Patterns | Async httpx, Pydantic v2, immutable lists |
| Test-Patterns | pytest, @patch fuer APIs, lokale Helfer-Factories |
| Branch | master, clean working tree |
| Alte Branches | feature/search-quality, feature/reflexive-loop (noch vorhanden) |