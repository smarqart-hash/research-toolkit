# Prompt: Research Toolkit — Codebase Audit

> Erstellt: 2026-03-11 | Mode: FULL | Score: 44/50
> Modell: Claude Opus 4.6 (Subagents) | Kontext: research-toolkit Produktionscode

## Optimierter Prompt

Dieser Prompt ist als **Dispatcher-Prompt** konzipiert: Du fuehrst ihn aus und er
startet 4 parallele Audit-Agents + 1 Synthese-Schritt.

---

### Dispatcher-Anweisung

```
Du fuehrst ein professionelles Code-Audit des Research Toolkit durch.
Scope: src/ + cli.py (Produktionscode, ~26 Python-Dateien).

Starte 4 parallele Subagents (model: "opus") mit den unten definierten Auftraegen.
Jeder Agent schreibt seinen Report nach docs/audit/YYYY-MM-DD-{domain}.md.
Nach Abschluss aller 4: Synthese-Report mit priorisierter Checklist.

Output-Format pro Agent:
- Findings als Checklist: [ ] CRITICAL / HIGH / MEDIUM / LOW
- Pro Finding: Datei:Zeile, Problem, Empfehlung (1-2 Saetze)
- Keine Prosa, nur Findings

Gewichtung der Dimensionen:
1. Code-Qualitaet + Architektur (35%) — hoechste Prio
2. Performance + Effizienz (30%)
3. Robustheit + Error Handling (25%)
4. Security (10%) — CLI-Tool, keine Web-Exposition
```

---

### Agent 1: Code-Qualitaet + Architektur

```xml
<instructions>
Du bist ein Senior Python Code Reviewer. Pruefe den Produktionscode (src/ + cli.py)
auf Architektur-Qualitaet, Wartbarkeit und Konventionen.

Pruefe systematisch:

1. MODULSTRUKTUR
   - Zirkulaere Imports? (Grep: "from src." in allen .py)
   - Coupling zwischen Modulen (agents/ ↔ utils/ ↔ pipeline/)
   - Gibt es God-Modules (>400 Zeilen)?
   - Sind Verantwortlichkeiten klar getrennt?

2. DATENMODELLE
   - Pydantic v2 Best Practices (model_validate, computed_field)
   - Mischung dataclass vs. BaseModel — konsistent?
   - Immutability durchgehend? (kein .append, kein dict-Mutation)
   - Type Annotations vollstaendig?

3. CODE PATTERNS
   - DRY: Duplizierter Code zwischen _search_ss, _search_openalex, _search_exa?
   - Magische Zahlen/Strings ohne Konstante?
   - Funktionslaenge (<50 Zeilen pro Funktion?)
   - Nesting-Tiefe (>4 Levels?)
   - Naming: konsistent Deutsch/Englisch?

4. CLI-ARCHITEKTUR
   - cli.py: Ist die Logik in Agents ausgelagert oder im CLI gebunden?
   - _load_env() vs. python-dotenv — eigener Parser robust genug?
   - Error-UX: Sind Fehlermeldungen hilfreich fuer Endnutzer?

5. KONVENTIONEN (aus CLAUDE.md)
   - `from __future__ import annotations` ueberall?
   - Black/Ruff Compliance
   - Docstrings Deutsch, Code Englisch?
</instructions>

<context>
Stack: Python 3.11+, Pydantic v2, httpx async, Typer CLI, Rich UI.
26 Source-Dateien in src/ + cli.py.
Konventionen: CLAUDE.md im Repo-Root.
Immutability-Pattern: [*list, new] statt .append()
</context>

<output>
docs/audit/2026-03-11-code-quality.md
Format: Checklist nach Priority (CRITICAL > HIGH > MEDIUM > LOW)
Pro Finding: - [ ] [PRIO] datei.py:zeile — Problem. Empfehlung.
</output>
```

---

### Agent 2: Performance + Effizienz

```xml
<instructions>
Du bist ein Python Performance Engineer. Pruefe den Produktionscode auf
Performance-Bottlenecks und Effizienz-Probleme.

Pruefe systematisch:

1. ASYNC I/O
   - httpx.AsyncClient: Wird pro Request ein neuer Client erstellt? (Connection Pooling?)
   - asyncio.gather: Werden alle Quellen wirklich parallel abgefragt?
   - Timeout-Konfiguration konsistent?
   - Retry-Logik: Exponential Backoff oder fester Delay?

2. SPECTER2 / ML
   - Model-Loading: Lazy + gecacht? Wird bei jedem Aufruf neu geladen?
   - numpy/torch Operationen: Batch-Processing oder einzeln?
   - Memory: Wird das Model nach Nutzung freigegeben?

3. DATENVERARBEITUNG
   - Deduplizierung: O(n) oder O(n²)?
   - Ranking: Wird relevance_score pro Zugriff neu berechnet (computed_field)?
   - Listen-Operationen: [*list, item] in Schleifen = O(n²) Kopien?
   - JSON Serialisierung: model_dump_json() effizient fuer grosse Paper-Listen?

4. I/O + DATEISYSTEM
   - Dateien: Werden grosse JSON-Files komplett in Memory geladen?
   - Provenance JSONL: read_all() liest gesamte Datei — skaliert das?
   - Encoding: UTF-8 explizit ueberall gesetzt?

5. STARTUP + CLI
   - Lazy Imports in cli.py (from src.agents... innerhalb Commands)?
   - Wie lange dauert ein kalter `research-toolkit doctor`?
   - Unnoetige Imports die Startup verlangsamen?
</instructions>

<context>
Kritische Hot-Paths:
- search_papers() → parallel 3 API-Calls → deduplicate → rank_papers
- rank_papers() mit SPECTER2: Model laden + Embeddings berechnen
- Typische Datenmenge: 50-200 Papers pro Suche

API-Clients: semantic_scholar.py, openalex_client.py, exa_client.py
Ranking: paper_ranker.py (SPECTER2 + Heuristik)
</context>

<output>
docs/audit/2026-03-11-performance.md
Format: Checklist nach Priority (CRITICAL > HIGH > MEDIUM > LOW)
Pro Finding: - [ ] [PRIO] datei.py:zeile — Problem. Empfehlung + geschaetzter Impact.
</output>
```

---

### Agent 3: Robustheit + Error Handling

```xml
<instructions>
Du bist ein Reliability Engineer. Pruefe den Produktionscode auf Robustheit,
Fehlerbehandlung und Edge Cases.

Pruefe systematisch:

1. ERROR HANDLING
   - Welche Exceptions werden gefangen, welche nicht?
   - Gibt es bare `except Exception`? Sind die spezifisch genug?
   - Werden API-Fehler (429, 500, Timeout) konsistent behandelt?
   - Fehler-Zaehlung in stats-Dict: Wird das ausgewertet?

2. INPUT VALIDATION
   - CLI-Inputs: Werden --sources, --years, --max validiert?
   - Pydantic-Modelle: Haben Felder sinnvolle Constraints (Field(ge=1))?
   - Pfad-Inputs: Path.exists() Check ueberall wo noetig?
   - year_filter Format: Wird "2020-2026" vs "2020-" korrekt geparsed?

3. EDGE CASES
   - Leere API-Responses: Was passiert bei 0 Results?
   - Papers ohne Abstract: Crasht SPECTER2?
   - Papers ohne Titel: Crasht dedup_key?
   - Leere BibTeX-Datei: Graceful Handling?
   - Netzwerk-Ausfall waehrend asyncio.gather: Partial Results?

4. STATE + PERSISTENCE
   - State Machine: Kann man in ungueltige Zustaende kommen?
   - save_state atomicity: tmp + replace Pattern korrekt?
   - Provenance: Was bei korrupter JSONL-Zeile?
   - merge_results: Idempotent bei doppeltem --append?

5. GRACEFUL DEGRADATION
   - SPECTER2 nicht installiert: Fallback funktioniert?
   - Alle API Keys fehlen: Sinnvolle Meldung?
   - OpenAlex ohne MAILTO/API_KEY: Funktioniert mit Rate Limits?
   - Exa Free-Tier ueberschritten: Retry oder Skip?
</instructions>

<context>
Externe Abhaengigkeiten: 3 APIs (SS, OA, Exa) + 1 LLM (OpenRouter)
Optional: SPECTER2 (sentence-transformers + torch)
Pipeline: 6-Phasen State Machine mit HITL-Gates
Provenance: Append-only JSONL
</context>

<output>
docs/audit/2026-03-11-robustness.md
Format: Checklist nach Priority (CRITICAL > HIGH > MEDIUM > LOW)
Pro Finding: - [ ] [PRIO] datei.py:zeile — Problem. Empfehlung.
</output>
```

---

### Agent 4: Security (Lightweight)

```xml
<instructions>
Du bist ein Security Reviewer. Leichtgewichtiger Check — das ist ein CLI-Tool
ohne Web-Exposition. Fokus auf die relevanten Risiken.

Pruefe:

1. SECRETS
   - API Keys in Code hardcoded? (Grep: api_key, secret, password, token)
   - .env in .gitignore?
   - Werden Keys in Logs/Fehlermeldungen geleakt?
   - Bearer Token in HTTP Headers: Wird HTTPS erzwungen?

2. INPUT SANITIZATION
   - CLI-Argumente: Path Traversal moeglich (--input ../../../etc/passwd)?
   - BibTeX Parser: Injection-Risiko bei manipulierten .bib-Dateien?
   - _load_env(): Werden Werte ungefiltert in os.environ gesetzt?

3. DEPENDENCY RISK
   - Bekannte CVEs in Dependencies? (httpx, pydantic, typer, bibtexparser)
   - Pinned Versions oder floating?
   - Optional Dependencies (torch) — Supply Chain Risk?

4. OUTPUT SAFETY
   - Werden API-Responses vor Persistierung validiert?
   - JSON-Output: Kann ein manipuliertes Paper XSS-Payload enthalten
     (relevant wenn Output in Web-UI landet)?
</instructions>

<output>
docs/audit/2026-03-11-security.md
Format: Checklist nach Priority (CRITICAL > HIGH > MEDIUM > LOW)
Erwartung: Wenige Findings da CLI-Tool. Trotzdem dokumentieren.
</output>
```

---

### Synthese-Schritt (nach allen 4 Agents)

```
Lies alle 4 Audit-Reports aus docs/audit/2026-03-11-*.md.
Erstelle eine konsolidierte Checklist:

docs/audit/2026-03-11-audit-summary.md

Format:
## Research Toolkit — Audit Summary (2026-03-11)

### CRITICAL (sofort fixen)
- [ ] Finding aus Agent X...

### HIGH (naechster Sprint)
- [ ] Finding...

### MEDIUM (Backlog)
- [ ] Finding...

### LOW (Nice-to-have)
- [ ] Finding...

### Metriken
| Dimension | Findings | CRIT | HIGH | MED | LOW |
|-----------|----------|------|------|-----|-----|
| Code-Qualitaet | X | X | X | X | X |
| Performance | X | X | X | X | X |
| Robustheit | X | X | X | X | X |
| Security | X | X | X | X | X |
| **Gesamt** | **X** | **X** | **X** | **X** | **X** |

Duplikate zwischen Agents zusammenfuehren.
Findings nach Impact sortieren, nicht nach Agent.
```

---

## Test Cases

| # | Input | Expected Output | Edge Case? |
|---|-------|-----------------|------------|
| 1 | Normaler Lauf mit allen 4 Agents | 4 Domain-Reports + 1 Summary, Findings priorisiert | Nein |
| 2 | Codebase hat 0 CRITICAL Findings | Summary mit leerer CRITICAL-Sektion, kein false positive | Ja |
| 3 | Zwei Agents finden gleiches Problem (z.B. httpx Client pro Request) | Summary dedupliziert, verweist auf beide Dimensionen | Ja |

## Scoring

| Dimension | Score | Notiz |
|-----------|-------|-------|
| **Clarity** — Ist die Aufgabe eindeutig? | 9/10 | Klare Rollen, klare Outputs |
| **Specificity** — Genuegend Constraints? | 9/10 | Konkrete Pruefpunkte pro Agent |
| **Context** — Hat das Modell genug Hintergrund? | 9/10 | Codebase-spezifische Dateien/Patterns referenziert |
| **Structure** — XML-Tags, Sections, Format? | 9/10 | XML-Tags, Dispatcher + 4 Agents + Synthese |
| **Completeness** — Edge Cases, Output-Def? | 8/10 | Test Cases vorhanden, koennte mehr Few-Shot haben |
| **Gesamt** | **44/50** | Production-ready |

## Context Sources

- `src/agents/forschungsstand.py` — Haupt-Orchestrierung, Search-Pipeline
- `src/agents/paper_ranker.py` — Ranking + SPECTER2 + Dedup
- `src/agents/semantic_scholar.py` — SS API Client Pattern
- `src/agents/exa_client.py` — Exa API Client Pattern
- `src/utils/llm_client.py` — LLM-Integration, API Key Handling
- `src/pipeline/state.py` — State Machine
- `src/pipeline/provenance.py` — Audit Trail
- `cli.py` — CLI Entry Point
- `CLAUDE.md` — Projekt-Konventionen

## Revision History

- v1: Initiale Version — 4-Agent Dispatcher mit gewichteten Dimensionen
