# Research Toolkit — Audit Summary (2026-03-11)

Scope: `src/` + `cli.py` (28 Dateien, ~5700 LOC)
Agents: Code-Qualitaet, Performance, Robustheit, Security

---

## CRITICAL (sofort fixen)

- [ ] `cli.py:301` — `extract_references` existiert nicht. Korrekt: `extract_all_references`. **check-Command ist kaputt.** *(Code-Quality + Robustheit)*
- [ ] `cli.py:272` — `load_all_rubrics` existiert nicht + `find_rubric_for_venue` wird mit falschem Kwarg `rubrics=` statt `rubrics_dir=` aufgerufen. **review --venue ist kaputt.** *(Code-Quality + Robustheit)*
- [ ] `cli.py:261` — `ReviewConfig` existiert nicht in `reviewer.py`. **review-Command Import crasht.** *(Code-Quality)*
- [ ] `citation_tracker.py:12` — `from utils.evidence_card` statt `from src.utils.evidence_card`. **Falscher Import-Pfad.** *(Code-Quality)*
- [ ] `drafting.py:603` — `from utils.citation_tracker` statt `from src.utils.citation_tracker`. **Falscher Import-Pfad.** *(Code-Quality + Robustheit)*
- [ ] `semantic_scholar.py:129` / `exa_client.py:104` / `openalex_client.py:141` — **Neuer `httpx.AsyncClient` pro Request** (sogar innerhalb Retry-Loop). Kein Connection Pooling. ~1-3s Performance-Verlust pro Search. *(Performance)*

**Gesamt CRITICAL: 8 (5 Import-Fehler + 3 Connection Pooling)**

---

## HIGH (naechster Sprint)

### Immutability-Verstoesse
- [ ] `forschungsstand.py:167+` — `stats` Dict wird als mutable Argument durchgereicht und in-place mutiert (20+ Stellen). Empfehlung: Stats als Return-Value.
- [ ] `forschungsstand.py:340-349` — `search_tasks.append()` und `sources_used.append()` statt `[*list, item]`.
- [ ] `quellen_checker.py:57-65` — `compute_stats()` mutiert `self` in-place.
- [ ] `drafting.py:144-148` — `DraftResult.compute_stats()` mutiert `self` in-place.
- [ ] `state.py:81-116` — Alle State-Methoden mutieren `self.phases[...]` in-place.

### Performance
- [ ] `paper_ranker.py:60-102` — `relevance_score` als `computed_field` wird bei jedem Zugriff neu berechnet (4-5x pro Paper).
- [ ] `paper_ranker.py:375-381` — O(n²) Listen-Aufbau in `rank_papers()` via `[*updated, item]`-Loop.
- [ ] `forschungsstand.py:166,250,358` — O(n²) `[*papers, *batch]` in Query-Loops.
- [ ] `provenance.py:64-72` — `read_all()` liest komplette Datei + O(n²) Listenaufbau. `filter_by_*` liest Datei jeweils erneut.
- [ ] `llm_client.py:93` — Neuer Client pro `llm_complete()` Call (bis 6x bei Review-Loop).

### Robustheit
- [ ] `provenance.py:69` — Keine `JSONDecodeError`-Behandlung pro JSONL-Zeile. Eine kaputte Zeile macht gesamte History unlesbar.
- [ ] `feedback_logger.py:46` — Gleiches JSONL-Parsing-Problem.
- [ ] `llm_client.py:106` — `choices[0]["message"]["content"]` ohne Bounds-Check.
- [ ] `cli.py:120` — `--sources` wird nicht gegen erlaubte Werte validiert.
- [ ] `cli.py:77` — `--max 0` oder `--max -5` wird akzeptiert (kein `min=1`).
- [ ] `forschungsstand.py:68-78` — `SearchConfig` ist `dataclass` ohne Constraints.
- [ ] `paper_ranker.py:54` — Leerer Titel erzeugt identischen `dedup_key` fuer alle titellosen Papers.
- [ ] `cli.py:164` — `--append` Pfad-Bug: `output_path` ist Datei, nicht Verzeichnis.
- [ ] `state.py:81-115` — State Machine hat keine Transitions-Validierung.
- [ ] `state.py:118-122` — `tmp.replace()` nicht atomar auf Windows.
- [ ] `doctor.py:85` — Prueft `OPENROUTER_API_KEY` statt `LLM_API_KEY` (Primary Key).
- [ ] `openalex_client.py:203` — relevance_score Default 0.0 filtert ALLE Papers wenn Score fehlt.

### Code-Qualitaet
- [ ] `paper_ranker.py:196` — Globale mutable Variable fuer SPECTER2-Cache. Empfehlung: `functools.lru_cache`.
- [ ] `paper_ranker.py:67,272` — `import math` innerhalb computed_field. Modul-Level-Import bevorzugen.
- [ ] `paper_ranker.py:72-77,278-283` — `_citation_caps` Dict dupliziert in 2 Funktionen.
- [ ] `openalex_client.py:71` — Abstract-Property rekonstruiert bei jedem Zugriff aus Inverted Index.

**Gesamt HIGH: 27**

---

## MEDIUM (Backlog)

### Architektur
- [ ] `drafting.py` (676 Zeilen), `forschungsstand.py` (557), `review_loop.py` (486) — ueber 400-Zeilen-Limit.
- [ ] `forschungsstand.py:68` — `SearchConfig` ist einziger `dataclass` unter lauter `BaseModel`s.
- [ ] `forschungsstand.py:146-262` — `_search_ss/openalex/exa` ~80% identisch. DRY-Verletzung.
- [ ] `reviewer.py:134` / `review_loop.py:22` — Fragile `.parent.parent.parent` Config-Pfade.

### Magic Numbers
- [ ] `forschungsstand.py:202` — OA Relevanz-Schwelle `0.3` ohne Konstante.
- [ ] `paper_ranker.py:85` — Recency `2018` und `8` ohne Konstante.
- [ ] `drafting.py:357` — Woerter pro Seite `250` ohne Konstante.

### Performance
- [ ] `forschungsstand.py:157-178` — Queries pro Quelle sequentiell statt parallel.
- [ ] `review_loop.py:336-339` — `self_consistency_probe` 3 Reviews sequentiell.
- [ ] `openalex_client.py:59-73` — Abstract-Rekonstruktion ohne Caching.
- [ ] `cli.py:10-20` — Rich-Imports bei jedem Command inkl. `--help`.
- [ ] `feedback_logger.py:45-52` — O(n²) Listenaufbau bei `read_feedback()`.
- [ ] `paper_ranker.py:349` — `reserved` + `reserved_ids` in Loop komplett neu erstellt.

### Robustheit
- [ ] `year_filter` — Keine lokale Format-Validierung.
- [ ] `bibtex_parser.py:71` — Non-UTF-8 .bib crasht mit `UnicodeDecodeError`.
- [ ] `evidence_card.py:48-59` — `confidence` ohne Range-Check (0.0-1.0).
- [ ] `review_loop.py:264` — `Severity(severity_str)` kann `ValueError` werfen.
- [ ] `forschungsstand.py` — Stats-Fehler-Zaehler werden nie angezeigt.
- [ ] `quellen_checker.py:84` — Bare `except Exception` zu breit.
- [ ] `cli.py:362` — Bare `except Exception` bei venues JSON-Parsing.
- [ ] API-Clients — Kein Retry bei 5xx Server-Fehlern.
- [ ] `provenance.py:38` — Append nicht atomar bei parallelen Writes.
- [ ] `merge_results()` — `total_found` additiv statt nach Merge neu berechnet.
- [ ] `semantic_scholar.py:117` — S2_API_KEY Warnung erscheint bei jedem Client-Aufruf.
- [ ] `cli.py:39` — `_load_env()` handelt Quotes nicht (`"value"` bleibt mit Anfuehrungszeichen).
- [ ] `cli.py:289` — `output_dir` in check-Command zugewiesen aber nie genutzt.

### Security
- [ ] `openalex_client.py:125` — API Key als URL-Query-Parameter (OpenAlex-Konvention).

**Gesamt MEDIUM: 28**

---

## LOW (Nice-to-have)

- [ ] `_load_env()` ohne Key-Whitelist (Security)
- [ ] Kein Path-Traversal-Schutz (irrelevant bei CLI)
- [ ] Floating Dependency Versions (kein Lockfile)
- [ ] torch Supply-Chain-Risiko (gross, aber offiziell)
- [ ] XSS in Markdown-Output (nur bei Web-Integration relevant)
- [ ] SPECTER2 Model bleibt im RAM (OK bei CLI)
- [ ] Hardcoded Recency-Year `2018` wird 2027 veraltet
- [ ] `slugify()` mit nicht-ASCII → leerer String moeglich
- [ ] Diverse Code-Hygiene (inline imports, unused imports, Stilbrueche)

**Gesamt LOW: 15+**

---

## Metriken

| Dimension | Findings | CRIT | HIGH | MED | LOW |
|-----------|----------|------|------|-----|-----|
| Code-Qualitaet | 40 | 5 | 9 | 15 | 11 |
| Performance | 20 | 3 | 5 | 9 | 3 |
| Robustheit | 34 | 3 | 11 | 13 | 7 |
| Security | 5 | 0 | 0 | 1 | 4 |
| **Gesamt (dedupliziert)** | **~78** | **8** | **27** | **28** | **15+** |

*Hinweis: Einige Findings ueberlappen zwischen Dimensionen (z.B. Import-Fehler = Code-Quality + Robustheit, Connection Pooling = Performance + Code-Quality). Deduplizierte Zahlen in der Gesamt-Zeile.*

---

## Top-5 Quick Wins (Impact/Aufwand)

| # | Fix | Aufwand | Impact |
|---|-----|---------|--------|
| 1 | Import-Fehler fixen (check/review Commands) | ~30min | check + review funktionieren wieder |
| 2 | Connection Pooling (3 API Clients) | ~1h | ~1-3s schnellere Suche |
| 3 | `--sources` Validierung + `--max min=1` | ~15min | Keine stillen Fehlschlaege |
| 4 | JSONL-Parsing robust machen (try/except pro Zeile) | ~15min | Korrupte History kein Totalausfall |
| 5 | `import math` + List Comprehension statt O(n²) Loops | ~30min | ~50-200ms + sauberer Code |
