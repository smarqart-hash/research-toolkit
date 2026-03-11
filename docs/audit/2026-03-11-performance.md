# Performance Audit — Research Toolkit

**Datum:** 2026-03-11
**Scope:** `src/` + `cli.py` (Produktionscode)
**Typische Last:** 50-200 Papers, 3 API-Quellen parallel

---

## 1. ASYNC I/O

### httpx.AsyncClient — Connection Pooling

- [ ] **CRITICAL** `semantic_scholar.py:129` — Neuer `httpx.AsyncClient` pro Request (innerhalb Retry-Loop). TCP-Handshake + TLS pro Call, kein Connection-Reuse. Bei 3 Queries a 2 Retries = 9 separate Connections. **Empfehlung:** Client als Instanzvariable in `__init__` erstellen, in `__aenter__`/`__aexit__` schliessen (Context Manager Pattern). **Impact:** ~200-500ms pro zusaetzlichem Request durch TLS-Handshake.

- [ ] **CRITICAL** `exa_client.py:104` — Gleiches Problem: `async with httpx.AsyncClient(timeout=30) as client` innerhalb Retry-Loop. Neuer Client pro Versuch. **Empfehlung:** Wie oben, Client als Instanzvariable. **Impact:** ~200-500ms pro Request.

- [ ] **CRITICAL** `openalex_client.py:141` — Gleiches Problem: Neuer Client pro Request+Retry. **Empfehlung:** Shared Client. **Impact:** ~200-500ms pro Request.

- [ ] **HIGH** `llm_client.py:93` — Neuer Client pro `llm_complete()` Call. Bei `self_consistency_probe` (3 Calls) und `run_revise_loop` (bis 6 Calls) summiert sich das. **Empfehlung:** Client als Parameter oder Modul-Level-Instanz mit Lazy Init. **Impact:** ~100-300ms pro LLM-Call.

### Parallelitaet

- [x] `forschungsstand.py:351` — `asyncio.gather(*search_tasks)` korrekt implementiert. SS, OA, Exa laufen wirklich parallel.

- [ ] **MEDIUM** `forschungsstand.py:157-178` — Queries pro Quelle werden sequentiell abgearbeitet (for-Loop). Bei 5 SS-Queries: 5 serielle Requests statt parallel. **Empfehlung:** `asyncio.gather` auch fuer Queries innerhalb einer Quelle (mit Semaphore fuer Rate Limits). **Impact:** Bei 5 Queries ~3-5s Latenz-Reduktion (von ~10s auf ~2-3s).

- [ ] **MEDIUM** `review_loop.py:336-339` — `self_consistency_probe` fuehrt 3 Reviews sequentiell aus. Temperatures sind unabhaengig. **Empfehlung:** `asyncio.gather` fuer die 3 Parallel-Reviews. **Impact:** ~60-70% Latenz-Reduktion bei Consistency-Check.

- [ ] **LOW** `quellen_checker.py:321-330` — Referenz-Checks laufen sequentiell (for-Loop ueber candidates). **Empfehlung:** `asyncio.gather` mit Semaphore (max 5 parallel). **Impact:** Bei 20 Refs: ~15s → ~3s.

### Timeout-Konfiguration

- [x] Konsistent: 30s Timeout bei SS, OA, Exa, LLM. OK fuer typische Nutzung.

### Retry-Logik

- [ ] **LOW** `semantic_scholar.py:109-110` — Fester Delay (2.0s), kein Exponential Backoff. MAX_RETRIES=1 (also nur 1 Retry). **Empfehlung:** Exponential Backoff (2s, 4s) und MAX_RETRIES=2 fuer robustere API-Interaktion. Gleich bei OA und Exa. **Impact:** Minimal bei aktuellem MAX_RETRIES=1.

---

## 2. SPECTER2 / ML

### Model-Loading

- [x] `paper_ranker.py:190-202` — Lazy Loading + Modul-Level-Cache (`_specter2_model`). Korrekt implementiert. Wird nur einmal geladen.

### Batch-Processing

- [x] `paper_ranker.py:233-234` — Embeddings werden als Batch berechnet (`model.encode(texts, ...)`). Korrekt — alle Abstracts + Query in einem Call.

### numpy-Operationen

- [x] `paper_ranker.py:239` — `np.dot(paper_embs, query_emb)` ist vectorized. Korrekt.

### Memory

- [ ] **LOW** `paper_ranker.py:26` — Model bleibt global im RAM (~200-400MB). Kein Cleanup nach Nutzung. Bei CLI-Tool akzeptabel (Prozess endet nach Command). **Empfehlung:** Nur relevant falls als Library verwendet — dann `del _specter2_model` + `gc.collect()` nach Ranking. **Impact:** Minimal fuer CLI-Nutzung.

---

## 3. DATENVERARBEITUNG

### Deduplizierung

- [x] `paper_ranker.py:174-184` — O(n) via Dict-Lookup. Korrekt.
- [ ] **MEDIUM** `paper_ranker.py:49-56` — `dedup_key` ist `@computed_field` und berechnet SHA256 bei jedem Zugriff. Kein Caching. `deduplicate()` ruft `paper.dedup_key` pro Paper auf = 1x OK. Aber Pydantic `computed_field` cached nicht. Falls `dedup_key` mehrfach pro Paper zugegriffen wird (z.B. Serialisierung), wird SHA256 wiederholt. **Empfehlung:** Explizites `functools.cached_property` oder dedup_key als normales Feld mit `model_validator`. **Impact:** Gering bei 200 Papers (~0.1ms pro SHA256), aber sauberer.

### Ranking — relevance_score Berechnung

- [ ] **HIGH** `paper_ranker.py:60-102` — `relevance_score` ist `@computed_field @property`. Wird bei JEDEM Zugriff neu berechnet: im `rank_papers()` Sort-Lambda, in `_apply_source_quota()` Sort-Lambda, bei `model_dump_json()` Serialisierung, und bei jedem `heuristic_scores` Dict-Build. Bei 200 Papers und 4-5 Zugriffen pro Paper = 800-1000 Berechnungen statt 200. Enthaelt `import math` bei jedem Aufruf. **Empfehlung:** Score einmal berechnen und als normales Feld speichern (oder Dict-Lookup wie bei SPECTER2). **Impact:** Bei 200 Papers ~5-10ms verschwendet, plus haeufiges `import math` Lookup.

- [ ] **MEDIUM** `paper_ranker.py:68` — `import math` innerhalb `relevance_score` Property. Wird bei jedem Aufruf ausgefuehrt (Python cached Modul-Lookup, aber `import` Statement hat trotzdem Overhead). Gleiches Problem in `_compute_enhanced_score:272`. **Empfehlung:** `import math` an den Dateianfang verschieben. **Impact:** ~0.5-1ms total bei 200 Papers.

### Listen-Operationen — O(n^2) Kopien

- [ ] **HIGH** `paper_ranker.py:375-381` — `rank_papers()` baut `updated` Liste mit `[*updated, paper.model_copy(...)]` in Schleife. Bei 200 Papers: 200 Kopien mit wachsender Listengroesse = O(n^2). `model_copy()` erstellt zudem eine Deep-Copy jedes Papers. **Empfehlung:** List Comprehension: `updated = [p.model_copy(update={...}) for p in papers]`. **Impact:** Bei 200 Papers ~10-50ms verschwendet.

- [ ] **HIGH** `forschungsstand.py:166,250,358` — `papers = [*papers, *batch]` in for-Loops ueber Queries. Bei 3 Queries mit je 100 Papers: Kopiert 100, dann 200, dann 300 = 600 Kopien statt 300 Appends. **Empfehlung:** `papers.extend(batch)` oder List Comprehension. **Impact:** ~5-20ms bei typischer Last.

- [ ] **MEDIUM** `_apply_source_quota:349` — `reserved = [*reserved, paper]` und `reserved_ids = {*reserved_ids, paper.paper_id}` in Schleife. Set wird bei jeder Iteration komplett neu erstellt. **Empfehlung:** `.append()` und `.add()`. **Impact:** Gering bei kleinem reserved-Set (~10 Elemente).

- [ ] **MEDIUM** Durchgaengiges Pattern in `screener.py:122-134`, `review_loop.py:243-250,253-266`, `query_generator.py:69,89,119,137`, `reference_extractor.py:110-119,140-150,193-201`, `evidence_card.py:69`, `bias_test.py:108,181,198`, `ranking_judge.py:163,215` — `list = [*list, item]` statt `.append()`. Immutability-Pattern ist konsistent, aber erzeugt O(n^2) bei Listen-Aufbau in Schleifen. **Empfehlung:** Fuer lokale Listen innerhalb einer Funktion ist `.append()` performanter und semantisch korrekt (keine externe Referenz die mutiert wird). Immutability-Pattern nur fuer uebergebene Parameter. **Impact:** In Summe ~10-50ms ueber den gesamten Hot-Path.

### OpenAlex Abstract-Rekonstruktion

- [ ] **MEDIUM** `openalex_client.py:59-73` — `abstract` Property rekonstruiert Text aus Inverted Index bei jedem Zugriff. Erstellt Liste von Tuples, sortiert, joined. Wird mehrfach aufgerufen: in `from_openalex()`, ggf. in Serialisierung. **Empfehlung:** `functools.cached_property` oder einmaliges Berechnen in `model_post_init`. **Impact:** Bei 200 OA-Papers mit je ~200 Woertern: ~10-50ms bei Mehrfachzugriff.

---

## 4. I/O + DATEISYSTEM

### JSON-Serialisierung

- [ ] **MEDIUM** `forschungsstand.py:466` — `result.model_dump_json(indent=2)` fuer grosse Paper-Listen (200 Papers mit Abstracts). Pydantic serialisiert komplett in Memory. **Empfehlung:** Bei >500 Papers: Streaming-Serialisierung erwaegen. Bei aktueller Last (50-200) OK. **Impact:** ~50-200ms bei 200 Papers, akzeptabel.

### Provenance JSONL

- [ ] **HIGH** `provenance.py:64-72` — `read_all()` liest gesamte Datei als String, splittet an Newlines, parst jede Zeile einzeln. `entries = [*entries, ...]` Pattern = O(n^2). Zudem: `filter_by_phase()` und `filter_by_agent()` rufen jeweils `read_all()` auf = Datei wird komplett neu gelesen und geparst fuer jeden Filter. **Empfehlung:** 1) `.append()` statt `[*entries, ...]`. 2) `read_all()` cachen oder Filter direkt beim Lesen anwenden. **Impact:** Bei 1000 Eintraegen: ~100ms pro Aufruf, potentiell 3x wenn mehrere Filter.

- [ ] **MEDIUM** `feedback_logger.py:45-52` — Gleiches Pattern: `entries = [*entries, entry]` bei `read_feedback()`. **Impact:** Gering bei typischer Feedback-Menge (<100 Eintraege).

### Encoding

- [x] UTF-8 explizit ueberall gesetzt. Konsistent in allen `read_text()`, `write_text()`, `open()` Calls.

---

## 5. STARTUP + CLI

### Lazy Imports

- [x] `cli.py:109-118` — `from src.agents.forschungsstand import ...` innerhalb `search()` Command. Korrekt lazy.
- [x] `cli.py:215` — Drafting-Import innerhalb `draft()`. Korrekt.
- [x] `cli.py:263-264` — Reviewer-Import innerhalb `review()`. Korrekt.
- [x] `cli.py:297` — Reference-Extractor innerhalb `check()`. Korrekt.
- [x] `cli.py:373` — Doctor-Import innerhalb `doctor()`. Korrekt.

### Startup-Overhead

- [ ] **MEDIUM** `cli.py:10-20` — Top-Level-Imports: `asyncio, json, logging, sys, Path, typer, Console, Panel, Table`. Rich + Typer werden bei JEDEM Command geladen, auch bei `--help`. **Empfehlung:** Rich-Imports (`Panel`, `Table`) lazy innerhalb der Commands laden. `Console` kann top-level bleiben. **Impact:** ~100-200ms Startup-Reduktion bei `--help` und `doctor`.

- [ ] **LOW** `doctor.py:65` — `import sentence_transformers` beim Doctor-Check. Laedt ggf. torch als Side-Effect (~2-5s). Ist innerhalb try/except, also kein Crash. Aber: `doctor` sollte schnell sein. **Empfehlung:** Nur Importierbarkeit pruefen, nicht das ganze Package laden: `importlib.util.find_spec("sentence_transformers")`. **Impact:** ~2-5s Speedup bei `doctor` wenn SPECTER2 installiert.

---

## Zusammenfassung nach Prioritaet

| Prio | Count | Geschaetzter Gesamt-Impact |
|------|-------|---------------------------|
| CRITICAL | 3 | ~1-3s pro Search (Connection Pooling) |
| HIGH | 5 | ~50-200ms + Skalierungsprobleme |
| MEDIUM | 9 | ~50-300ms total |
| LOW | 3 | Minimal, Code-Hygiene |

### Top-3 Quick Wins

1. **Connection Pooling** (3x CRITICAL): `httpx.AsyncClient` als Instanzvariable in SS/OA/Exa Clients. Aenderung: ~20 Zeilen pro Client. Impact: ~1-3s pro Search.
2. **Intra-Source Parallelisierung** (MEDIUM): `asyncio.gather` fuer Queries innerhalb einer Quelle. Impact: ~3-5s bei --refine mit 5 Queries.
3. **`import math` an Dateianfang** + **List Comprehension statt `[*list, item]` Loop** (HIGH+MEDIUM): Einfache Refactorings. Impact: ~20-100ms.

### Nicht-Probleme (Bestaetigt OK)

- SPECTER2 Lazy Loading + Caching
- Deduplizierung O(n)
- Parallele Quellen-Abfrage via `asyncio.gather`
- Lazy CLI-Imports
- UTF-8 Encoding konsistent
- Timeout-Konfiguration einheitlich
