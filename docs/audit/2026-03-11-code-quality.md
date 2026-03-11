# Code-Qualitaets-Audit — 2026-03-11

Scope: `src/` + `cli.py` (28 Python-Dateien, ~5700 LOC)

## CRITICAL

- [ ] **[CRITICAL]** cli.py:296 — `extract_references` existiert nicht in `reference_extractor.py`. Die Funktion heisst `extract_all_references`. Import schlaegt zur Laufzeit fehl.
- [ ] **[CRITICAL]** cli.py:272 — `load_all_rubrics` existiert nicht in `rubric_loader.py`. Funktion nicht definiert. `find_rubric_for_venue` hat keinen `rubrics=` Parameter — Signatur ist `(venue_id, rubrics_dir=None)`.
- [ ] **[CRITICAL]** cli.py:261 — `ReviewConfig` existiert nicht in `reviewer.py`. Import schlaegt fehl wenn `review` Command ausgefuehrt wird.
- [ ] **[CRITICAL]** citation_tracker.py:12 — `from utils.evidence_card import EvidenceCard` — falscher Import-Pfad. Muss `from src.utils.evidence_card` sein (konsistent mit Rest der Codebase).
- [ ] **[CRITICAL]** drafting.py:603 — `from utils.citation_tracker import track_citations` — gleicher falscher Import-Pfad. Muss `from src.utils.citation_tracker` sein.

## HIGH

- [ ] **[HIGH]** forschungsstand.py:167 — `stats["ss_total"] += len(batch)` mutiert dict in-place (insgesamt 20+ Stellen in `_search_ss`, `_search_openalex`, `_search_exa`, `search_papers`). stats-Dict wird als mutable Argument durchgereicht und mutiert. Widerspricht Immutability-Konvention. Empfehlung: stats als Return-Value statt in-place Mutation.
- [ ] **[HIGH]** forschungsstand.py:340-349 — `search_tasks.append()` und `sources_used.append()` — list mutation statt `[*list, item]`. 6 Stellen. Inkonsistent mit dem eigenen Immutability-Pattern das ueberall sonst genutzt wird.
- [ ] **[HIGH]** paper_ranker.py:67,272 — `import math` innerhalb von `@computed_field` bzw. `_compute_enhanced_score()`. Modul-Level-Import bevorzugen. Wird bei jedem Aufruf von `relevance_score` neu importiert (Performance bei vielen Papers).
- [ ] **[HIGH]** paper_ranker.py:72-77,278-283 — `_citation_caps` Dict wird identisch in `relevance_score` und `_compute_enhanced_score` dupliziert (nur Werte unterscheiden sich). Empfehlung: Modul-Level-Konstanten `HEURISTIC_CITATION_CAPS` und `ENHANCED_CITATION_CAPS`.
- [ ] **[HIGH]** paper_ranker.py:196 — `_specter2_model` globale mutable Variable mit `global`-Statement. Empfehlung: functools.lru_cache oder Klassen-Pattern statt global.
- [ ] **[HIGH]** quellen_checker.py:57-65 — `compute_stats()` mutiert `self` in-place (`self.verified = ...`). Pydantic-Model sollte immutable sein. Empfehlung: `@computed_field` oder neues Objekt via `model_copy()`.
- [ ] **[HIGH]** drafting.py:144-148 — `DraftResult.compute_stats()` mutiert `self` in-place (`self.total_word_count = ...`). Gleicher Immutability-Verstoss.
- [ ] **[HIGH]** state.py:81-116 — `ResearchState.start_phase()`, `complete_phase()`, `halt_for_human()`, `resolve_hitl()`, `fail_phase()` — alle mutieren `self.phases[...]` in-place. Empfehlung: neue PhaseRecord-Objekte via `model_copy()`.
- [ ] **[HIGH]** openalex_client.py:71 — `positions.append((idx, word))` in `abstract` Property. Mutation einer lokalen Liste ist akzeptabel, aber Property rekonstruiert Abstract bei jedem Zugriff (teuer). Empfehlung: Caching oder computed_field.

## MEDIUM

- [ ] **[MEDIUM]** drafting.py:676 — 676 Zeilen. Ueber 400-Zeilen-Empfehlung. Empfehlung: `_format.py` (Output-Formatierung) und `_reflexive.py` (Reflexive-Sektion) extrahieren.
- [ ] **[MEDIUM]** forschungsstand.py:557 — 557 Zeilen. Ueber 400-Zeilen-Empfehlung. Empfehlung: `_search_orchestration.py` (search_papers + _search_* Funktionen) extrahieren.
- [ ] **[MEDIUM]** review_loop.py:486 — 486 Zeilen. Ueber 400-Zeilen-Empfehlung. Empfehlung: `_prompts.py` und `_parsing.py` extrahieren.
- [ ] **[MEDIUM]** forschungsstand.py:68 — `SearchConfig` ist `dataclass` waehrend alle anderen Datenmodelle Pydantic `BaseModel` sind. Inkonsistent. Empfehlung: zu BaseModel migrieren fuer Validierung + Serialisierung.
- [ ] **[MEDIUM]** reference_extractor.py:11 — `ReferenceCandidate` ist `BaseModel`, aber der `@dataclass` Import in Zeile 10 ist unbenutzt. Aufraumen.
- [ ] **[MEDIUM]** forschungsstand.py:146-262 — `_search_ss`, `_search_openalex`, `_search_exa` haben identische try/except-Struktur mit nur variierenden Client-Calls und stats-Keys. ~35 Zeilen pro Funktion, ~80% identisch. Empfehlung: generische `_search_source()` mit Client-Adapter-Pattern.
- [ ] **[MEDIUM]** forschungsstand.py:202 — Magic Number `0.3` (OpenAlex Relevanz-Schwelle) ohne Konstante. Empfehlung: `MIN_OA_RELEVANCE = 0.3` als Modul-Konstante.
- [ ] **[MEDIUM]** paper_ranker.py:85 — Magic Numbers `2018` und `8` in Recency-Berechnung ohne Konstante. Wiederholt in Zeile 289. Empfehlung: `RECENCY_BASE_YEAR = 2018`, `RECENCY_RANGE = 8`.
- [ ] **[MEDIUM]** drafting.py:357 — Magic Number `250` (Woerter pro Seite) ohne Konstante. Empfehlung: `WORDS_PER_PAGE = 250`.
- [ ] **[MEDIUM]** document_splitter.py:10 — `import subprocess` ohne Nutzung in `split_markdown()`. Nur fuer `convert_docx_to_markdown()` benoetigt. Empfehlung: Lazy Import oder Shell-Injection-Risiko dokumentieren.
- [ ] **[MEDIUM]** forschungsstand.py:28 — `logger` Definition zwischen zwei Import-Bloecken. Empfehlung: nach allen Imports platzieren.
- [ ] **[MEDIUM]** cli.py:289 — `output_dir` wird zugewiesen aber nie verwendet im `check`-Command. Dead Code.
- [ ] **[MEDIUM]** cli.py:39 — `_load_env()` parst `.env` manuell — Quotes (`"value"`, `'value'`) werden nicht gehandelt. `KEY="value"` wird als `"value"` mit Anfuehrungszeichen gespeichert. Empfehlung: python-dotenv oder Quote-Stripping.
- [ ] **[MEDIUM]** reviewer.py:134 — `_AUTOMATABLE_CONFIG_PATH` hardcoded relativer Pfad mit 3x `.parent`. Fragil bei Package-Reorganisation. Empfehlung: Konfigurationspfad als Parameter.
- [ ] **[MEDIUM]** review_loop.py:22-23 — `_SUB_QUESTIONS_PATH` gleicher fragiler `.parent.parent.parent`-Pattern.

## LOW

- [ ] **[LOW]** forschungsstand.py:68 vs. 45 — `SearchConfig` (dataclass) neben `ThemeCluster` und `ForschungsstandResult` (BaseModel) im gleichen Modul. Stilbruch.
- [ ] **[LOW]** drafting.py:625-627 — `_split_sentences()` importiert `re` inline statt auf Modul-Level. `re` ist bereits auf Modul-Level nicht importiert (fehlt dort), waehrend `reference_extractor.py` es korrekt importiert.
- [ ] **[LOW]** screener.py:131-133 — `exclusion_reasons` Dict-Update via Spread-Operator ist korrekt immutable, aber schwer lesbar. `{**d, key: d.get(key, 0) + 1}` Empfehlung: Counter aus collections nutzen.
- [ ] **[LOW]** semantic_scholar.py:129 — `httpx.AsyncClient` wird pro Request neu erstellt (innerhalb der Retry-Schleife). Empfehlung: Client einmal erstellen, Retry-Logik um den Request herum.
- [ ] **[LOW]** exa_client.py:104 — Gleicher Pattern: `httpx.AsyncClient` pro Retry-Versuch. Gilt auch fuer openalex_client.py:141.
- [ ] **[LOW]** cli.py:148 — `_source_labels` Dict bei jedem search-Aufruf neu erstellt. Empfehlung: Modul-Level-Konstante.
- [ ] **[LOW]** drafting.py:469 — `if not any([...])` erstellt eine unnoetige Liste. Empfehlung: `if not any((...))` mit Tuple oder Generator.
- [ ] **[LOW]** paper_ranker.py:225 — `import numpy as np` innerhalb von `compute_specter2_similarity()`. Akzeptabel wegen optionaler Dependency, aber Kommentar waere hilfreich.
- [ ] **[LOW]** document_splitter.py:10 — `from dataclasses import dataclass` plus `import subprocess` — subprocess ist Modul-Level importiert obwohl nur in einer optionalen Funktion genutzt.
- [ ] **[LOW]** quellen_checker.py:255 — Return-Type `object | None` statt `PaperResult | None`. Erzwingt isinstance-Check intern, verliert Typsicherheit fuer Caller.
- [ ] **[LOW]** forschungsstand.py:27 — `logger = logging.getLogger(__name__)` steht zwischen zwei Import-Gruppen. Sollte nach allen Imports stehen (PEP 8 / Ruff Konvention).

## Zusammenfassung

| Kategorie | Count |
|-----------|-------|
| CRITICAL  | 5     |
| HIGH      | 9     |
| MEDIUM    | 15    |
| LOW       | 11    |
| **Total** | **40**|

### Positiv

- `from __future__ import annotations` in allen 24 Dateien vorhanden
- Konsistente Pydantic v2 API (`model_validate`, `model_dump_json`, `computed_field`, `model_copy`)
- Keine zirkulaeren Imports erkannt
- Naming-Konvention (Deutsch Docstrings, Englisch Code) durchgehend eingehalten
- Immutability-Pattern `[*list, item]` in ~95% der Faelle korrekt angewendet
- Kein God-Module (groesstes: drafting.py mit 676 Zeilen, akzeptabel)
- Coupling: agents/ importiert aus utils/ und pipeline/ — keine Rueckwaerts-Abhaengigkeiten
- Error-UX im CLI: Rich-Panels, farbige Fehlermeldungen, hilfreiche Exit-Codes
