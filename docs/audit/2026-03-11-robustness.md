# Robustness Audit — 2026-03-11

Scope: `src/` + `cli.py` (Produktionscode, 28 Python-Dateien).
Methode: Systematische Pruefung aller Error Paths, Input Boundaries, Edge Cases.

---

## 1. ERROR HANDLING

### CRITICAL

- [ ] **CRITICAL** `cli.py:301` — `from src.agents.reference_extractor import extract_references` importiert eine Funktion die nicht existiert. Korrekt: `extract_all_references`. Der `check`-Command crasht bei jedem Aufruf mit `ImportError`.
- [ ] **CRITICAL** `cli.py:272` — `from src.utils.rubric_loader import find_rubric_for_venue, load_all_rubrics` importiert `load_all_rubrics` die nicht existiert. Der `review`-Command crasht wenn `--venue` gesetzt ist. Zusaetzlich wird `find_rubric_for_venue(venue, rubrics=rubrics)` aufgerufen, aber die Signatur erwartet `rubrics_dir`, nicht `rubrics`.
- [ ] **CRITICAL** `drafting.py:603` — `from utils.citation_tracker import track_citations` nutzt falschen Import-Pfad (fehlt `src.`). Crasht zur Laufzeit wenn `evidence_cards` und `provenance_logger` uebergeben werden.

### HIGH

- [ ] **HIGH** `provenance.py:69` — `read_all()` faengt keine `json.JSONDecodeError` bei korrupten JSONL-Zeilen. Eine einzige kaputte Zeile macht die gesamte Provenance-History unlesbar. Empfehlung: try/except pro Zeile mit Warning.
- [ ] **HIGH** `feedback_logger.py:46` — `read_feedback()` hat dasselbe Problem: keine Exception-Behandlung pro Zeile bei JSONL-Parsing.
- [ ] **HIGH** `forschungsstand.py:351` — `asyncio.gather(*search_tasks, return_exceptions=True)` faengt Exceptions korrekt ab, ABER: nur `Exception`-Subklassen werden als Warning geloggt. `BaseException` (z.B. `KeyboardInterrupt`, `SystemExit`) wird verschluckt und als leere Paperliste behandelt.
- [ ] **HIGH** `llm_client.py:106` — `choices[0]["message"]["content"]` greift ohne Bounds-Check auf die Response-Struktur zu. Wenn das API ein unerwartetes Format liefert (z.B. kein `message` Key), crasht es mit `KeyError` statt einer verstaendlichen Fehlermeldung.
- [ ] **HIGH** `semantic_scholar.py:128-143` — Retry-Loop erstellt pro Versuch einen neuen `httpx.AsyncClient`. Bei `MAX_RETRIES > 0` und Response 429: `response` ist in der letzten Iteration definiert, aber `response.request` kann stale sein weil der Client schon geschlossen wurde. Empfehlung: `response` nach `raise_for_status()` Fehler sofort in Variable sichern.

### MEDIUM

- [ ] **MEDIUM** `quellen_checker.py:84` — `except Exception:` (bare) bei `load_local_papers()` verschluckt alle Fehler inkl. `PermissionError`, `MemoryError`. Zu breit. Empfehlung: `except (json.JSONDecodeError, ValueError, KeyError)`.
- [ ] **MEDIUM** `venues` Command (`cli.py:362`) — `except Exception:` (bare) bei JSON-Parsing. Verschluckt alles. Empfehlung: `except (json.JSONDecodeError, KeyError)`.
- [ ] **MEDIUM** Alle drei API-Clients (SS, OA, Exa) — `MAX_RETRIES = 1` bedeutet nur 1 Retry bei 429. Kein Retry bei 500/502/503 (Server-Fehler). Empfehlung: Retry auch bei 5xx.
- [ ] **MEDIUM** `review_loop.py:264` — `Severity(severity_str)` kann `ValueError` werfen wenn LLM einen unbekannten Severity-String liefert. Nicht gefangen. Empfehlung: try/except oder Default.
- [ ] **MEDIUM** Stats-Dict in `forschungsstand.py` — Fehler-Zaehler (`ss_errors`, `openalex_errors`, `exa_errors`) werden geschrieben aber nirgendwo ausgewertet (nur bei `total_found == 0` in einer Warning). Empfehlung: Stats in CLI-Output anzeigen.

### LOW

- [ ] **LOW** `paper_ranker.py:220-223` — Zweites `except Exception` faengt alle Fehler bei SPECTER2-Import. Akzeptabel wegen Python 3.14 torch-Bug, aber sollte mindestens `AssertionError` + `RuntimeError` spezifizieren statt blanket-catch.
- [ ] **LOW** `ranking_judge.py:216` — `except Exception as e:` bei LLM-Judge-Batch. Akzeptabel fuer LLM-Fehler, aber faengt auch `KeyboardInterrupt` via Subklassen-Hierarchie nicht — was korrekt ist (`Exception` faengt kein `KeyboardInterrupt`).
- [ ] **LOW** `query_generator.py:260` — `refine_topic()` faengt `except Exception` und gibt Topic unveraendert zurueck. Akzeptabler Graceful Degradation, aber loggt nur Warning ohne Exception-Typ.

---

## 2. INPUT VALIDATION

### HIGH

- [ ] **HIGH** `cli.py:120` — `source_list` wird nicht validiert. Ungueltige Sources (z.B. `--sources foo,bar`) werden stillschweigend akzeptiert und fuehren zu 0 Ergebnissen ohne Warnung. Empfehlung: Validierung gegen erlaubte Werte `{"ss", "openalex", "exa"}`.
- [ ] **HIGH** `cli.py:77` — `max_results` hat keinen unteren Bound. `--max 0` oder `--max -5` wird akzeptiert. Empfehlung: `min=1` in typer.Option.
- [ ] **HIGH** `forschungsstand.py:69-78` — `SearchConfig` ist ein `dataclass`, keine Pydantic-Model. Felder haben keine Constraints (z.B. `top_k` kann negativ sein, `max_results_per_query` kann 0 sein).

### MEDIUM

- [ ] **MEDIUM** `year_filter` Parsing — wird direkt an SS/OA APIs durchgereicht ohne lokale Validierung. Format "2020-2026" funktioniert, aber "abc" oder "2026-2020" (umgekehrt) werden ohne Warnung gesendet. SS API akzeptiert es evtl., OA-Filter koennte scheitern. Empfehlung: Regex-Validierung `\d{4}(-\d{4})?`.
- [ ] **MEDIUM** `bibtex_parser.py:71` — `path.read_text(encoding="utf-8")` kann bei Non-UTF-8 .bib-Dateien (z.B. latin-1 aus Zotero) mit `UnicodeDecodeError` crashen. Empfehlung: `errors="replace"` oder spezifischen Error-Handler.
- [ ] **MEDIUM** `evidence_card.py:48-59` — `confidence` Validator akzeptiert beliebige Floats ohne Range-Check. `confidence=999.9` wird akzeptiert. Empfehlung: `Field(ge=0.0, le=1.0)`.
- [ ] **MEDIUM** `rubric_loader.py:86-93` — `find_rubric_for_venue()` wirft `FileNotFoundError` wenn keine Rubric passt. Sollte besser `None` zurueckgeben (wie Docstring in cli.py impliziert mit `if matched:`).

### LOW

- [ ] **LOW** `DraftingConfig.venue_id` (`drafting.py:125`) — Default ist leerer String `""`. Kein Validator. Leerer venue_id fuehrt zu harmlosem Fallback (leeres VenueProfile), aber koennte verwirren.
- [ ] **LOW** `LLMConfig.max_tokens` (`llm_client.py:29`) — Kein oberes Limit. User koennte theoretisch sehr hohen Wert setzen.

---

## 3. EDGE CASES

### HIGH

- [ ] **HIGH** `paper_ranker.py:54` — `dedup_key` greift auf `self.title` zu. Wenn `title` leer ist (`""`), wird ein Hash ueber einen leeren normalisierten String erzeugt — alle Papers ohne Titel bekommen denselben dedup_key und werden bis auf eins dedupliziert. Empfehlung: `paper_id` als Fallback wenn Titel leer.
- [ ] **HIGH** `cli.py:164` — `output_path / slugify(topic) / "forschungsstand.json"`: `output_path` ist `output_dir / "search_results.json"` (eine Datei, kein Verzeichnis). Bei `--append` wird versucht, einen Unterordner einer Datei zu oeffnen. Empfehlung: `output_dir / slugify(topic) / "forschungsstand.json"` statt `output_path / ...`.
- [ ] **HIGH** `openalex_client.py:203` — `w.relevance_score >= min_oa_relevance` — wenn OpenAlex den relevance_score nicht liefert, ist der Default 0.0 und ALLE Papers werden gefiltert. Das passiert z.B. bei Filter-basierten Queries ohne `search=`. Empfehlung: Score-Check nur wenn > 0.

### MEDIUM

- [ ] **MEDIUM** `paper_ranker.py:228-230` — Papers ohne Abstract bekommen `specter2_score = 0.0`. Das ist korrekt, ABER: In `_compute_enhanced_score` ist 30% SPECTER2-Gewichtung. Papers ohne Abstract verlieren 30% ihres potenziellen Scores — staerker bestraft als der `abstract`-Bonus von 10%. Kein Bug, aber Design-Imbalance.
- [ ] **MEDIUM** `bibtex_parser.py:49-62` — Leere BibTeX-Datei (`""`) wird korrekt behandelt (gibt `[]` zurueck). Leere Datei mit nur Whitespace auch. Korrekt.
- [ ] **MEDIUM** `forschungsstand.py:351` — Bei Netzwerk-Ausfall waehrend `asyncio.gather` mit `return_exceptions=True`: Partial Results werden korrekt gesammelt. ABER: Wenn ALLE Tasks fehlschlagen, bekommt der User 0 Papers + eine Warnung — ohne zu wissen welche Quellen fehlschlugen (nur generische Warnung). Empfehlung: Fehlgeschlagene Quellen namentlich loggen.

### LOW

- [ ] **LOW** `paper_ranker.py:85-86` — Recency-Score: `max(0, self.year - 2018) / 8`. Hardcoded `2018` und `8` (implizit 2026). Ab 2027 muesste die Formel angepasst werden. Empfehlung: `current_year` dynamisch.
- [ ] **LOW** `reference_extractor.py:104` — `year = int(match.group("year"))` ohne try/except. Regex garantiert `\d{4}`, also sicher — aber theoretisch koennte `9999` als Jahr reinkommen.
- [ ] **LOW** `slugify()` (`forschungsstand.py:439`) — Nicht-ASCII-Zeichen (z.B. japanische/chinesische Zeichen) werden komplett entfernt. Topic "AI在交通" wird zu leerer String `""`. Leerer Slug erzeugt leeren Ordnernamen.

---

## 4. STATE + PERSISTENCE

### HIGH

- [ ] **HIGH** `state.py:81-115` — State Machine hat keine Transitions-Validierung. Man kann `complete_phase(Phase.REVIEW)` aufrufen ohne je `start_phase(Phase.REVIEW)` auszufuehren. Oder `start_phase()` zweimal hintereinander. `current_phase` wird immer ueberschrieben. Empfehlung: Assert dass Phase IN_PROGRESS ist vor complete/fail.
- [ ] **HIGH** `state.py:118-122` — `save_state()` nutzt `tmp_path.replace(path)` — atomisch auf Unix, ABER auf Windows kann `replace()` mit `PermissionError` scheitern wenn eine andere Instanz die Datei geoeffnet hat. Empfehlung: try/except mit Retry oder `os.replace()`.

### MEDIUM

- [ ] **MEDIUM** `provenance.py:38` — Append-Modus (`"a"`) ist nicht atomar. Bei gleichzeitigen Writes (z.B. parallele Agents) koennen Zeilen verschraenkt werden. Empfehlung: File-Lock oder JSONL-Zeile atomar schreiben.
- [ ] **MEDIUM** `forschungsstand.py:477-500` — `merge_results()` ist idempotent bezueglich Dedup (gleiches Paper wird nicht doppelt gespeichert). ABER: `total_found` wird additiv akkumuliert — zweimal `--append` mit denselben Ergebnissen verdoppelt `total_found` obwohl Papers dedupliziert werden. Empfehlung: `total_found` nach Merge neu berechnen.

### LOW

- [ ] **LOW** `state.py:127-129` — `load_state()` faengt keine `json.JSONDecodeError`. Korrupte State-Datei crasht mit unklarer Fehlermeldung. Empfehlung: try/except mit `logger.error()`.
- [ ] **LOW** `provenance.py:69` — `read_all()` liest gesamte Datei in Memory. Bei sehr langer Provenance-History (10k+ Eintraege) koennte das problematisch werden. Empfehlung: Streaming/Iterator-Alternative.

---

## 5. GRACEFUL DEGRADATION

### Positiv (funktioniert)

- [x] SPECTER2 nicht installiert: Fallback auf heuristisches Ranking (`paper_ranker.py:217-223`). Sauber implementiert.
- [x] Exa API Key fehlt: `ExaClient.is_available` gibt `False`, wird uebersprungen (`forschungsstand.py:239-241`).
- [x] LLM API Key fehlt: Query-Expansion faellt auf lokale Expansion zurueck (`query_generator.py:281-288`).
- [x] OpenAlex ohne Key/Mailto: Funktioniert mit Standard Rate Limits.
- [x] Leere API-Responses: 0 Papers werden korrekt behandelt.
- [x] BibTeX-Import leere Datei: Gibt leere Liste zurueck.

### HIGH

- [ ] **HIGH** `doctor.py:85` — `LLM_API_KEY` wird NICHT geprueft. Stattdessen werden `OPENROUTER_API_KEY` und `OPENAI_API_KEY` gecheckt. Aber `llm_client.py:42` nutzt `LLM_API_KEY` als primaeren Key (mit `OPENROUTER_API_KEY` als Fallback). Doctor meldet "MISSING" obwohl LLM funktioniert wenn `LLM_API_KEY` gesetzt ist.

### MEDIUM

- [ ] **MEDIUM** Alle API-Clients — Kein Retry bei Exa Free-Tier-Limit (HTTP 402/403). Exa-Suche schlaegt fehl und wird als generischer HTTP-Fehler behandelt. Empfehlung: Spezifische Warnung "Exa Free-Tier-Limit erreicht".
- [ ] **MEDIUM** `semantic_scholar.py:117-118` — Warnung "S2_API_KEY nicht gesetzt" erscheint bei JEDEM `SemanticScholarClient()`-Aufruf. Da pro Query ein neuer Client erstellt wird (z.B. in `_search_ss`), kann die Warnung 3-5x erscheinen. Empfehlung: Warning nur einmal (z.B. via `warnings.warn` mit Filter).

---

## Zusammenfassung

| Prioritaet | Anzahl | Kernthemen |
|------------|--------|------------|
| CRITICAL   | 3      | Import-Fehler (check/review Commands kaputt), falscher Import-Pfad |
| HIGH       | 11     | Fehlende Input-Validierung, JSONL-Parsing, State Machine, Edge Cases |
| MEDIUM     | 13     | API-Retry-Luecken, Encoding, Stats, Locking, Degradation |
| LOW        | 7      | Hardcoded Year, Exception-Spezifitaet, Memory |

**Sofort-Fix (CRITICAL):** Die 3 Import-Fehler machen `check` und `review` Commands komplett kaputt.
Sie sind entweder nie im Production-Pfad getestet worden, oder die CLI-Tests mocken die Imports.
