---
type: sprint-plan
inputs: bug_reports
touches: none
parent_epic: none
version: 3.1
supersedes: V1 (f.titel-swap), V2 (f.vorgang-Join widerlegt), V3 (Re-Eval-Cmd existierte nicht)
date: 2026-04-17
author: Stefan Marquart + Claude
---

# Bundestag DIP Search-Fix — Sprint Plan V3.1

> **V3.1 Changelog:**
> - V1: `search=` → `f.titel=`. Abgelehnt — Regression bei 60% Queries (0 Hits statt 285k).
> - V2: `/vorgang` + `f.deskriptor` → `/drucksache` via `f.vorgang` Join. **Empirisch widerlegt:** `f.vorgang` am `/drucksache` wird ignoriert.
> - V3: `/vorgang` + `f.deskriptor` → `/vorgangsposition` via `f.vorgang` Join (verifiziert). Deskriptor-Vokabular-Cache cross-project-nutzbar.
> - V3.1: Re-Eval-Strategie ausfuehrbar via `run_benchmark.py` (eval.py hat kein CLI). DoD-Schwellen kalibriert mit Exploration-Daten. Dispatch-Reihenfolge umgedreht: `/dev-team` als Primaer, Agent-direkt als Experiment.

---

## Ziel (1 Satz)

`BundestagClient` liefert fuer Topic-Queries deterministisch relevante Parlamentsdokumente
(Vorgaenge + ihre Positionen/Drucksachen) via Deskriptor-Vokabular, statt Vollbestand (Bug) oder 0 Hits (V1).

---

## Empirische Endpunkt-Matrix (live-verifiziert 2026-04-17)

**DIP-API hat endpunkt-abhaengige Filter-Semantik** — nicht aus OpenAPI-Spec ersichtlich, nur empirisch.

| Filter | `/drucksache` | `/vorgang` | `/vorgangsposition` | `/aktivitaet` |
|--------|:-------------:|:----------:|:-------------------:|:-------------:|
| `f.titel` | filtert (527) | filtert (470) | ? | ignoriert |
| `f.deskriptor` | **ignoriert (285k)** | **filtert (3.644)** | ignoriert | filtert (3.328) |
| `f.sachgebiet` | ignoriert | filtert (7.984) | ? | filtert |
| `f.vorgang` | **ignoriert (285k)** | n/a | **filtert (2-N pro Vorgang)** | ? |
| `f.vorgangstyp` | filtert | filtert | ? | ignoriert |
| `f.drucksachetyp` | filtert | filtert | ? | ignoriert |
| `search` / `q` / `f.volltext` | ignoriert | ignoriert | ignoriert | ignoriert |

(Zahlen fuer Query "Klimaschutz" / total 285k Drucksachen, 17.04.2026)

---

## Architektur (Spike-validiert)

```
Topic: "Klimaschutz"
    ↓
BundestagVocabulary.get/learn("klimaschutz")
    → Deskriptoren: ["Klimaschutz", "Erneuerbare Energie", ...]
    ↓
/vorgang?f.deskriptor=Klimaschutz           [FILTERT, ~3.644 Hits]
    → Liste Vorgaenge mit deskriptor[] + sachgebiet[]
    ↓
Pro Top-N Vorgaenge (optional, bei include_positions=True):
    /vorgangsposition?f.vorgang={vid}       [FILTERT, 2-5 Dokumente]
    → Drucksachen + PDFs + Datum
    ↓
UnifiedPaper[] (Vorgang ODER Vorgangsposition, gerankt nach Recency + Deskriptor-Match)
```

**Warum dieser Pfad:**
- `/vorgang?f.deskriptor` wirkt semantisch (kontrolliertes Vokabular)
- `/vorgangsposition?f.vorgang` ist der einzige verifiziert funktionierende Drucksache-Join
- `/drucksache?f.vorgang` (V2-Annahme) wird ignoriert, **nicht nutzbar**
- `/vorgang/{id}` Detail liefert keine Drucksachen-Links (gegen Plan-V2-Annahme verifiziert)

**Was das bedeutet fuer die briefing-app:**
- Ergebnisse sind primaer **Vorgaenge** (Gesetzgebungsverfahren, Anfragen), nicht rohe Drucksachen
- Fuer Research ist das oft besser: ein Vorgang bundelt alle Dokumente zu einem Thema
- Bei Bedarf: `include_positions=True` liefert die assoziierten Drucksachen als Dokumente

---

## Cross-Project Nutzen (ehrlich)

**Primaere Nutzer (verifiziert):**

| Projekt | Nutzungsart | Nutzen |
|---------|------------|--------|
| **briefing-app** | Source via `forschungsstand.py` | Bessere Policy-Hits im Brief |
| **research-toolkit CLI** | `research-toolkit search --sources bundestag` | Direkt |

**Artefakt mit Cross-Project-Wert:**
- `data/vocabularies/bundestag_deskriptoren.json` — JSON-Cache ist API-agnostisch, jedes Projekt kann ihn lesen
- `docs/guides/bundestag-dip-api.md` — Endpunkt-Matrix + Nutzungs-Patterns hilft jedem DE-Policy-Projekt

**Nicht ueberverkaufen:**
- Frontier Scraper, acatech Projekte etc. sind potenzielle zukuenftige Nutzer. Jetzt nicht verifiziert, nicht als Ziel setzen.

---

## Abhaengigkeiten

- research-toolkit master clean (ausser feature-list.json + research drafts, unrelated)
- briefing-app importiert via `pip install -e` — Fix wirkt nach Worker-Neustart
- Kein DB-/Schema-Touch, keine parallelen Sprints
- Kein Breaking-Change: Legacy-Methoden bleiben mit Bug-Fix erhalten

## Pre-Flight Checks (vor Sprint-Start)

Diese Kommandos MUESSEN gruen sein bevor der Sprint dispatcht wird:

```bash
# 1. Re-Eval-Tool existiert + laeuft (Settings load OK)?
cd "c:/Users/stefa/Documents/Claude Code Test/briefing-app"
python -c "import sys; sys.path.insert(0, 'src'); from briefing_app.config import settings; print('OK, bundestag_key:', bool(settings.bundestag_api_key))"
# Erwartet: 'OK, bundestag_key: True'
# Falls ValidationError: bundestag_api_key-Feld fehlt in Settings-Model.
# Fix bereits durchgefuehrt 2026-04-17: config.py:43 ergaenzt.

# 2. Benchmark-Topics verfuegbar?
ls data/benchmarks/topics.json
# Erwartet: Datei existiert mit Topic-Liste.

# 3. BUNDESTAG_API_KEY gesetzt?
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('OK' if os.environ.get('BUNDESTAG_API_KEY') else 'MISSING')"
# Erwartet: OK

# 4. research-toolkit editable installation aktiv + agents-Submodule erreichbar?
# (research-toolkit legt nur src/ als Package-Root — agents-Subpackages brauchen sys.path Setup)
cd "c:/Users/stefa/Documents/Claude Code Test/research-toolkit"
python -c "import sys; sys.path.insert(0, 'src'); from agents.bundestag_client import BundestagClient; print('OK')"
# Erwartet: 'OK'. Falls ModuleNotFoundError: research-toolkit nicht editable installiert (pip install -e .)

# 5. pytest collecting sauber?
cd "c:/Users/stefa/Documents/Claude Code Test/research-toolkit"
pytest --co -q 2>&1 | tail -5
# Erwartet: "N tests collected", keine Errors

# 6. Worktree-Basis clean?
git status --short
# Erwartet: keine Uncommitted-Changes in Files die der Plan anfasst
```

**Wenn eine Pre-Flight-Check fehlschlaegt:** STOPP, erst beheben, dann dispatchen.

---

## Betroffene Dateien (gegen HEAD verifiziert)

| Datei | Aktion | Was |
|-------|--------|-----|
| `src/agents/bundestag_client.py` | Edit | Task 1, 2, 3, 4 |
| `src/agents/bundestag_vocabulary.py` | **Create** | Task 3 |
| `data/vocabularies/bundestag_deskriptoren.json` | **Create** | Task 8 (seed), committed ins Repo |
| `tests/test_bundestag_client.py` | Edit | Regression + Neue Tests |
| `tests/test_bundestag_vocabulary.py` | **Create** | Unit-Tests |
| `tests/test_bundestag_live.py` | **Create** | `@pytest.mark.live` |
| `scripts/build_bundestag_vocab.py` | **Create** | Seed-Script |
| `src/agents/forschungsstand.py` | Edit | `_search_bundestag` nutzt `search_topic` |
| `docs/guides/bundestag-dip-api.md` | **Create** | Guide + Endpunkt-Matrix |
| `docs/plans/feature-list.json` | Edit | Feature-Eintrag |
| `docs/plans/retro.md` | Append | Sprint-Retro |
| briefing-app `CLAUDE.md` | Edit | "Bundestag 200 Hits" Known-Issue-Eintrag anpassen |
| briefing-app `docs/plans/2026-03-30-pipeline-quality-epic.md` | Edit | Q1.5 Re-Eval-Eintrag |

---

## Konkrete Tasks

### Task 0 — Pre-Implementation Empirical Check (DONE)

**Status: DONE 2026-04-17 als Spike.** Vollstaendiges Ergebnis:
`docs/research/api-exploration/bundestag-dip.md` (formales api-explorer-Format).

### Task 1 — Legacy-Bug fixen

`search_drucksachen` + `search_vorgaenge`: `search=` Parameter entfernen, durch `f.titel` ersetzen.

- Wenn `query` leer/whitespace: Parameter weglassen (Browse-Modus bleibt)
- Docstring aktualisieren: `query` = Titel-Phrase (mehrere Woerter = Phrase-Match)
- Note im Docstring: "Fuer Topic-Suche besser `search_topic()` nutzen"

**Korrektur-Note:** Im V2-Plan war `f.drucksachetyp` statt `f.typ` genannt — gegen OpenAPI verifizieren:
- OpenAPI Zeile 697: `f.drucksachetyp` (Antrag, Gesetzentwurf, ...)
- Aktuelle Client-Zeile 173: `params["f.typ"] = typ` — **existiert nicht in OpenAPI**. Muss zu `f.drucksachetyp` werden.

### Task 2 — Neue Basis-Methoden

```python
async def get_vorgang(self, vorgang_id: str) -> DIPVorgang:
    """Detail-Abruf eines Vorgangs. Liefert Deskriptoren + Sachgebiete."""

async def get_vorgangspositionen(
    self, vorgang_id: str, rows: int = 20
) -> DIPVorgangspositionResponse:
    """Dokumente (Drucksachen + Plenarprotokolle) zu einem Vorgang.

    VERIFIZIERTER Join-Pfad (17.04.2026):
    /vorgangsposition?f.vorgang={id} liefert 2-N Positionen mit
    fundstelle.pdf_url + dokumentnummer + drucksachetyp.
    """
```

**Neue Models:**
- `DIPVorgang` erweitern: `deskriptor: list[Deskriptor]`, `sachgebiet: list[str]`
- `Deskriptor` Model: `name: str, typ: str, fundstelle: bool`
- `DIPVorgangsposition`: `id, vorgang_id, titel, datum, fundstelle: Fundstelle`
- `Fundstelle`: `dokumentnummer, pdf_url, drucksachetyp, urheber`

### Task 3 — BundestagVocabulary Modul

Neue Datei `src/agents/bundestag_vocabulary.py` (~150 Zeilen).

```python
class BundestagVocabulary:
    """Deskriptor-Vokabular-Cache fuer Topic-Queries.

    DIP liefert kontrolliertes Vokabular nur in /vorgang Response-Feldern.
    Dieses Modul lernt via Sampling und cached fuer Pipeline-Reuse.
    """
    def __init__(self, cache_path: Path | None = None, client: BundestagClient | None = None): ...
    async def learn(self, topic: str, sample_size: int = 50, min_freq: int = 3) -> TopicVocab: ...
    def get(self, topic: str) -> TopicVocab | None: ...
    def save(self) -> None: ...

@dataclass
class TopicVocab:
    topic: str
    descriptors: list[DescriptorEntry]  # name, freq, typ
    sachgebiete: list[SachgebietEntry]
    sample_size: int
    learned_at: datetime

# Cache-JSON-Schema:
# {
#   "version": 1, "updated": "2026-04-17T10:00:00Z",
#   "topics": { "klimaschutz": { "descriptors": [...], ... } }
# }
```

**Edge-Cases explizit:**
- Kaltstart (kein Cache-Eintrag): automatisch `learn()` aufrufen
- Learning liefert 0 Deskriptoren (Topic zu nischig): Fallback auf `f.titel`-Only, Eintrag trotzdem cachen (`descriptors: []`)
- Stale-Check: `learned_at` > 30 Tage → Re-Learn beim naechsten get (konfigurierbar)
- Rate-Limit: Sleep 1s zwischen learn-Requests, HTTP-429-Retry mit exponential backoff (max 3 Versuche)

### Task 4 — search_topic() High-Level API

```python
async def search_topic(
    self,
    topic: str,
    *,
    rows: int = 50,
    include_positions: bool = False,
    vocabulary: BundestagVocabulary | None = None,
    wahlperiode: int | None = None,
) -> list[UnifiedPaper]:
    """Topic-zentrierte Suche ueber Deskriptor-Vokabular.

    Algorithm:
    1. Vocab lookup (cache-first)
    2. Falls cold: vocab.learn(topic) — extrahiert Deskriptoren aus /vorgang?f.titel=topic
    3. /vorgang?f.deskriptor=<top-1-desc>&[f.wahlperiode]  [wirkt semantisch]
    4. Dedup via Vorgang-ID
    5. Wenn include_positions: pro Top-10 Vorgaenge /vorgangsposition?f.vorgang abrufen
    6. Ranking: recency desc + descriptor-freq (aus Cache)
    7. Return: UnifiedPaper[] (source='bundestag', type='Vorgang'|'Vorgangsposition')
    """
```

**Dedup-Logik:**
- Pro Vorgang-ID: nur 1 Eintrag (auch bei Multi-Deskriptor-Queries)
- Pro Drucksache-Nummer: nur 1 Eintrag (wenn include_positions)

**Rate-Limit & Dedup als explizite Helper:**
- `_rate_limited_request()` in client: 1s sleep bei Bursts, 429-Retry
- `_dedupe_vorgaenge(lists) -> list`: union via set(id)

### Task 5 — forschungsstand.py Umstellung

`_search_bundestag` (Zeilen 381-414) nutzt `search_topic`:

```python
async def _search_bundestag(queries, config, stats):
    vocab = BundestagVocabulary()  # liest Repo-Cache
    async with BundestagClient() as bt_client:
        papers = []
        for query in queries:
            try:
                topic_papers = await bt_client.search_topic(
                    query, rows=min(config.max_results_per_query, 50),
                    vocabulary=vocab, include_positions=False  # Vorgaenge reichen
                )
                papers.extend(topic_papers)
                stats["bundestag_total"] += len(topic_papers)
            except httpx.HTTPStatusError as e:
                stats["bundestag_errors"] += 1
                logger.warning("DIP HTTP %d '%s': %s", e.response.status_code, query, e.response.text[:200])
            except httpx.TimeoutException:
                stats["bundestag_errors"] += 1
                logger.warning("DIP Timeout '%s'", query)
        vocab.save()  # persistiert neu gelernte Topics
        return papers
```

### Task 6 — Tests

**Mock-Tests** (`tests/test_bundestag_client.py`):
- `test_search_drucksachen_sends_f_titel_not_search` — Regression V1
- `test_search_drucksachen_uses_f_drucksachetyp_not_f_typ` — Regression (vorher war `f.typ` falsch)
- `test_get_vorgang_parses_deskriptoren` — Model
- `test_get_vorgangspositionen_uses_f_vorgang` — Model + Param-Name
- `test_search_topic_uses_vocabulary` — Vocab-Aufruf
- `test_search_topic_learns_on_cold_cache` — Fallback-Learning
- `test_search_topic_dedupes_across_descriptor_variants` — Dedup-Logik

**Vocabulary-Unit-Tests** (`tests/test_bundestag_vocabulary.py`):
- Cache load/save (Round-Trip)
- `learn()` aggregiert + sortiert nach Frequenz
- `min_freq` filtert seltene aus
- Stale-Check (Timestamp > 30 Tage)
- 0-Deskriptor-Topic wird trotzdem gecached (leere Liste)

**Live-Tests** (`tests/test_bundestag_live.py`, `@pytest.mark.live`):
- 10 realistische Queries (aus briefing-app benchmark-runs)
- Assertions:
  - `>= 70%` liefern `5-1000` Hits
  - `0%` liefern `> 50.000`
  - Median zwischen 10 und 1000
  - Bei Graceful-Degradation (0 Deskriptoren gelernt): Fallback loggt Warnung, crasht nicht
- Skippable via `pytest -m "not live"`
- `BUNDESTAG_API_KEY` Env-Var als Gate

### Task 7 — Dokumentation

**`docs/guides/bundestag-dip-api.md`** (~200 Zeilen):

1. **Einstieg:** Was ist DIP, wann nutzen
2. **API-Key:** Demo-Key-Ablauf (Mai 2026), persoenlicher Key beantragen
3. **Endpunkt-Matrix** (Tabelle oben, aktuell gehalten)
4. **Filter-Wirksamkeit pro Endpunkt** (Liste)
5. **Deskriptor-Vokabular** — Konzept, Beispiel-Eintraege, Typ-Liste
6. **Nutzungs-Pattern:**
   - Simple Titel-Suche: `search_drucksachen(query)`
   - Topic-Research: `search_topic(topic, vocabulary=vocab)`
   - Drucksache-Enrichment: `get_vorgangspositionen(vorgang_id)`
7. **Known Quirks:**
   - `search=` wird ignoriert (V1-Bug, jetzt intern via f.titel gefixt)
   - `f.vorgang` am `/drucksache` ignoriert — kein symmetrischer Join
   - `f.deskriptor` nur an `/vorgang` + `/aktivitaet` wirksam
   - Multi-Value `f.deskriptor` ist UND nicht ODER (laut OpenAPI)
8. **Cross-Project-Wiederverwendung:**
   - Vocabulary-Cache `data/vocabularies/bundestag_deskriptoren.json` ist portabel
   - `bundestag_client.py` + `bundestag_vocabulary.py` = 2 Dateien, einfach kopierbar
9. **Rate-Limits:** Keine offiziellen Zahlen in DIP-Doku. Konservativ: max 30 req/min. Implementierung hat 1s-Sleep.

**briefing-app Updates:**
- `CLAUDE.md` Bekannte Issues: "Bundestag 200 Hits bei Policy" → "Fixed 2026-04-17 (V3 mit Vocabulary)"
- `docs/plans/2026-03-30-pipeline-quality-epic.md`: Q1.5 Eintrag "Re-Eval Baseline (Pre vs. Post Bundestag-Fix)"

### Task 8 — Vocabulary Seed

`scripts/build_bundestag_vocab.py`:
- Liest Topic-Liste aus `data/seed_topics.json` (~20-30 Topics, Kuratier-Input):
  - Klimaschutz, Klimawandel, Energiewende, Erneuerbare Energien
  - Digitalisierung, Kuenstliche Intelligenz, Cybersicherheit
  - Migration, Asyl, Integration
  - Bundeswehr, Verteidigung, NATO
  - Gesundheitspolitik, Pflege, Impfung
  - Bildung, Schule, Universitaet
  - Wohnen, Mietpreisbremse
  - EU-Regulierung, Buerokratieabbau
- Fuer jedes Topic: `BundestagVocabulary.learn(topic, sample_size=100, min_freq=3)`
- 1s Sleep zwischen Topics (rate-limit-safe, 30 req/min)
- Persistiert nach `data/vocabularies/bundestag_deskriptoren.json`
- **Committed im Repo** (kleine Datei, <100KB geschaetzt)

---

## Definition of Done

Alle Checks messbar + ausfuehrbar:

- [ ] `grep -n "search.*:.*query" src/agents/bundestag_client.py` liefert keine Treffer
- [ ] `grep -n '"f.typ"' src/agents/bundestag_client.py` liefert keine Treffer (f.typ → f.drucksachetyp)
- [ ] Mock-Tests: alle bisherigen + 7 neue PASS
  - `pytest tests/test_bundestag_client.py tests/test_bundestag_vocabulary.py -v`
- [ ] Live-Tests (mit API-Key), **Schwellen kalibriert mit exploration-Doc**:
  - `pytest tests/test_bundestag_live.py -m live -v` auf 10 Topics
  - Min. 7/10 Topics liefern `>= 5` Hits (Topic lernbar + findet was)
  - **0 Topics** liefern `> 50000` Hits (kein Vollbestand)
  - Median ueber alle 10 Topics: zwischen `100` und `2000` (realistisch fuer DE-Policy, siehe exploration: Klimaschutz=3.644, KI=109, Digitalisierung=21)
  - Graceful-Degradation: 0-Deskriptor-Topics loggen Warnung, crashen nicht
- [ ] Vocabulary-Cache committed: `data/vocabularies/bundestag_deskriptoren.json`
  - Min. 20 Topics, Schema-Version 1, UTF-8, <100KB
- [ ] Guide-Doc: `docs/guides/bundestag-dip-api.md` mit Endpunkt-Matrix + Nutzungs-Patterns
- [ ] briefing-app `CLAUDE.md` Known-Issues-Eintrag aktualisiert
- [ ] **Re-Eval briefing-app (reduziert, ausfuehrbar)**:
  - Tool: `scripts/run_benchmark.py --topic eu-ai-act` (existing CLI, geprueft in Pre-Flight)
  - Auf Feature-Branch VOR Merge, 2 Smoke-Topics: `eu-ai-act`, `agentic-ai-verwaltung`
  - Manuelle Score-Extraktion aus `data/runs/{run-id}/{topic}.json`, Delta zu baseline-rerun dokumentieren
  - Volle Eval (alle 5 Topics) als Follow-up Q1.5 in briefing-app
  - Rollback-Trigger: Avg-Regress > 0.5 Pkt gegen 8.8/10-Baseline auf den 2 Smoke-Topics
- [ ] Commit auf Feature-Branch `fix/bundestag-search-v3`, nicht master
- [ ] adversarial-review auf Code-Ergebnis (Profil: code) vor Merge
- [ ] retro.md append-only Eintrag mit Learnings
- [ ] **Worktree-Cleanup:** nach Merge `git worktree remove ../research-toolkit-v3-fix`

---

## Risiken & Mitigation

| # | Risiko | Wahrscheinlichkeit | Severity | Mitigation |
|---|--------|:------------------:|:--------:|-----------|
| R1 | DIP aendert Filter-Semantik ohne API-Version-Bump | NIEDRIG | HOCH | Live-Tests in CI-skippable Form; bei Live-Fail: Guide-Doc aktualisieren, Client anpassen |
| R2 | Vocabulary-Cache wird stale (neue Deskriptoren in DIP) | MITTEL | NIEDRIG | `learned_at` Timestamp, 30-Tage-Stale-Check, Re-Learn On-Demand |
| R3 | Rate-Limit-Exzess beim Seeding (20 Topics) oder Live-Learning | MITTEL | MITTEL | 1s-Sleep zwischen Requests, 429-Retry, Sampling-Size 50-100 statt mehr |
| R4 | Briefing-app Eval-Score faellt nach Umstellung | MITTEL | HOCH | Re-Eval VOR Merge auf Feature-Branch (nicht nach), Rollback-Schwelle 0.5 Pkt gegen 8.8-Baseline |
| R5 | Topics ohne brauchbare Deskriptoren (zu spezifisch, englisch) | MITTEL | NIEDRIG | Graceful-Degradation: `learn()` cached leere Deskriptor-Liste, `search_topic` fallback auf `f.titel` |
| R6 | Legacy-Caller erwartet buggy 285k-Ergebnisse | NIEDRIG | NIEDRIG | Alte Methoden preserved, nur intern gefixt. Kein Breaking-Change. Legacy-User bekommt jetzt ehrliche Titel-Hits. |
| R7 | `/vorgangsposition?f.vorgang` Semantik aendert sich | NIEDRIG | HOCH | Spike-verifiziert, Live-Test deckt Regression ab |
| R8 | Worktree-Setup (Entry/Exit) kostet mehr Zeit als geschaetzt | NIEDRIG | NIEDRIG | Skill `using-git-worktrees` nutzen, 5min Puffer eingeplant |
| R9 | Scope-Creep: jemand will Semantic Search / Embeddings dazu | MITTEL | MITTEL | Explizit in "Nicht im Scope" gelistet, Review gates auf Plan-Konformitaet |
| R10 | **Worktree divergiert von master** (Sprint dauert mehrere Tage, master-Fixes) | MITTEL | MITTEL | Vor Merge: `git fetch origin && git rebase origin/master` im Worktree. Bei > 3 Commits Divergenz oder Konflikten: STOPP, Stefan entscheidet (Rebase vs. Merge-Commit). Cleanup `git worktree remove` erst nach Merge-Bestaetigung. |
| R11 | **Agent-Team-Erstnutzung** (portiert 2026-04-17, nie live getestet) | HOCH | MITTEL | Dispatch-Variante B (`/dev-team` Skill) als **Primaer**-Route, Variante A (direkte Agent-Files) als Experiment. Bei Fehler in Variante A: sofort B nutzen, nicht debuggen. Agent-Tuning als separates Follow-up. |

---

## Nicht im Scope

- Volltext-Suche ueber alle Drucksachen (DIP bietet es nicht, nur Solr-Web-UI)
- Semantic Search via Embeddings (separates Feature)
- Live-Updates des Vocabulary-Caches als Cron (eigener Task spaeter)
- UI fuer Vocabulary-Inspektion (JSON ist lesbar genug)
- PyPI-Release als eigenes Package (nur wenn Cross-Project-Demand steigt)
- `f.deskriptor` UND-Semantik zu ODER aufbohren (braucht Multi-Request-Sequenz, Follow-up)

---

## Migration-Strategie briefing-app

**Re-Eval-Workflow vor Merge:**

1. Nach Task 5 (forschungsstand.py Umstellung) auf Feature-Branch:
   ```bash
   cd "c:\Users\stefa\Documents\Claude Code Test\briefing-app"
   # Pre-Fix Baseline abrufen (aus vorherigem Q2-Run)
   cat data/runs/baseline-rerun/agentic-ai-verwaltung.json | jq '.eval.total_score'
   # Post-Fix Re-Run mit neuem Code
   python -m briefing_app.eval --rule --topics agentic-ai-verwaltung,eu-ai-act
   ```
2. Score-Delta dokumentieren im PR-Body
3. **Rollback-Trigger:** Avg-Delta < -0.5 Punkte gegen 8.8-Baseline
4. Rollback-Mechanik: `git revert <commit-sha>` auf Feature-Branch, nicht destruktiv
5. Bei Rollback: retro.md Eintrag mit Learnings + V4-Ideen

**Feature-Flag-Alternative:** Environment-Variable `BUNDESTAG_SEARCH_MODE=legacy|topic` in Client, Default `topic`. Falls Score-Regress: Env-Var auf `legacy` fuer schnellen Fallback ohne Revert.

---

## Aufwand-Schaetzung (ehrlich, V3.1)

| Task | Zeit |
|------|------|
| 0. Pre-Spike + Exploration-Doc (DONE 2026-04-17) | — (bereits erledigt) |
| Pre-Flight Checks (6 Kommandos) | 10min |
| 1. Legacy-Bug-Fix (+ f.typ → f.drucksachetyp) | 20min |
| 2. Neue Basis-Methoden + Models | 45min |
| 3. BundestagVocabulary Modul | 90min |
| 4. search_topic() + Rate-Limit + Dedup | 75min |
| 5. forschungsstand.py Umstellung | 25min |
| 6. Tests (Mock + Vocab + Live) | 120min |
| 7. Dokumentation (Guide + briefing-app Updates) | 75min |
| 8. Vocabulary Seed Script + initial Run + Cache | 60min |
| 9. Re-Eval briefing-app (2 Smoke-Topics via run_benchmark.py) | 30min |
| 10. adversarial-review code-Profil + Fix-Loop | 45min |
| Agent-Team-Erstnutzung-Puffer (Variante A Fallback auf B) | 30min |
| **Total** | **~11h** |

**Parallelisierung moeglich:** Task 7 (Docs) parallel zu Task 6 (Tests) via separaten Builder — spart 60min.
**Nicht im Sprint-Cost:** Agent-Team-Portierung (30min, bereits getaetigt, Cross-Project-Invest).

---

## Stefan-Gate Punkte (bestaetigt)

1. ✅ Cache-Location: `research-toolkit/data/vocabularies/`
2. ✅ Vocabulary-Cache committed ins Git
3. ✅ Legacy-API behalten (fixed, nicht deprecated)
4. ✅ Worktree `fix/bundestag-search-v3`

---

## Agent-Team (portiert von locallens-v2, 2026-04-17)

Fuer diesen Sprint nutzen wir das frisch portierte research-toolkit Agent-Team:

| Agent | Aufgabe in diesem Sprint | Wann |
|-------|-------------------------|------|
| `api-explorer` | Done (Task 0). Output: `docs/research/api-exploration/bundestag-dip.md` | Vor Sprint-Start |
| `connector-builder` | Tasks 1-5 + 8 (Code + Seed) | Worktree-isoliert |
| `test-runner` | Task 6 (Tests wenn connector-builder nicht komplett) | Nach builder |
| `quality-gate` | Task 10 (Review vor Merge) | Finaler Gate |
| `orchestrator` | Nicht noetig fuer 1 Sprint | — |

## Terminal-Dispatch

**PRIMAER: Variante B (`/dev-team` Skill — erprobt).**
Variante A (direkte Agent-Files) ist experimentell — erst testen wenn B laeuft.

### Setup

```bash
cd "c:\Users\stefa\Documents\Claude Code Test\research-toolkit"

# Pre-Flight Checks durchfuehren (siehe Abschnitt oben)
# ... alle 6 Checks muessen gruen sein

# Worktree anlegen
git worktree add ../research-toolkit-v3-fix fix/bundestag-search-v3
cd ../research-toolkit-v3-fix

# Session starten
claude
```

### Variante B — Primaer (`/dev-team` Skill)

Im Chat-Fenster:

```
/dev-team

Sprint: Bundestag DIP Search-Fix V3.1
Plan: docs/plans/2026-04-17-bundestag-search-fix.md
Exploration: docs/research/api-exploration/bundestag-dip.md
Agent-Team verfuegbar in .claude/agents/ (connector-builder, test-runner, quality-gate)

Autonomie: Stufe 2 (autonom, STOPP bei Live-Test-Fail, API-Quirk, Build-Fehler).
Feature-Branch: fix/bundestag-search-v3 (NICHT master).

Tasks aus Plan sequenziell: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10.
Pre-Flight Checks sind bereits durchgefuehrt (Stefan hat bestaetigt).

Nach Completion:
- briefing-app CLAUDE.md Known-Issues-Eintrag updaten
- briefing-app docs/plans/2026-03-30-pipeline-quality-epic.md: Q1.5 Re-Eval-Followup eintragen
- research-toolkit docs/plans/retro.md append mit Learnings
- NICHT auf master mergen, Stefan bestaetigt Merge.
```

### Variante A — Experimentell (direkte Agent-Dispatch)

Erst nach erfolgreichem Variante-B-Dispatch oder wenn Variante B unklar ist.
**Falls Variante A fehlschlaegt: sofort auf B wechseln, nicht debuggen.**

```
Ich moechte die portierten Agents in .claude/agents/ testen.

Dispatche connector-builder Agent (aus .claude/agents/connector-builder.md)
fuer Tasks 1-5 + 8 aus docs/plans/2026-04-17-bundestag-search-fix.md.
Input: docs/research/api-exploration/bundestag-dip.md
Isolation: worktree (bereits aktiv).
Bei Completion: dispatche quality-gate Agent fuer Review.
```

### Nach Merge (alle Varianten)

```bash
# Worktree cleanup
cd "c:\Users\stefa\Documents\Claude Code Test\research-toolkit"
git worktree remove ../research-toolkit-v3-fix

# Bei Master-Divergenz > 3 Commits waehrend Sprint: STOPP vorher, Stefan entscheidet
```

---

## Commit-Vorschlag (Haupt-Commit)

```
fix(bundestag): topic-aware search with descriptor vocabulary (V3)

Previous search_drucksachen sent "search=query" which DIP silently
ignored, returning full 285,331-doc inventory regardless of topic.
V1 (f.titel-only) would have regressed 60% of queries to 0 hits.
V2 (f.vorgang Join via /drucksache) was empirically refuted:
/drucksache ignores f.vorgang filter.

V3 uses DIP's verified architecture:
- /vorgang supports f.deskriptor (controlled vocabulary)
- /vorgangsposition?f.vorgang returns associated documents (verified join)
- Descriptor vocabulary cached per topic, learned from vorgang samples
- Cache is project-agnostic JSON, reusable across projects

New: search_topic(), get_vorgang(), get_vorgangspositionen(),
     BundestagVocabulary class, scripts/build_bundestag_vocab.py,
     data/vocabularies/bundestag_deskriptoren.json (seeded)
Fixed: search_drucksachen uses f.titel, f.drucksachetyp (not f.typ)
Breaking: none (legacy methods preserved with bug fix)
Docs: docs/guides/bundestag-dip-api.md (endpoint matrix + patterns)

Empirical endpoint matrix (verified 2026-04-17):
| Filter | /drucksache | /vorgang | /vorgangsposition | /aktivitaet |
| f.deskriptor | IGNORED | FILTERS | IGNORED | FILTERS |
| f.vorgang | IGNORED | n/a | FILTERS | ? |
| f.titel | FILTERS | FILTERS | ? | IGNORED |

Live-verified: search_topic("Klimaschutz") -> 3,644 vorgaenge
(was: 285,331 random docs).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```
