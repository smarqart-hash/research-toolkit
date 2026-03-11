# Meta-Loop v4 — Findings (2026-03-11)

> Search mit allen 3 Quellen (SS + OpenAlex + Exa) nach Sprint 7 (F17).
> Ziel: Pruefen ob F17 + Sprint 6 den Recall verbessert haben.

## Setup

- **Query**: "reflexive AI-assisted research toolkits"
- **Sources**: SS, OpenAlex, Exa (alle 3 aktiv)
- **Config**: `--max 50 --sources ss,openalex,exa`
- **Keys**: Exa OK, OpenAlex API Key OK, SS ohne Key (Rate Limited)
- **SPECTER2**: nicht verfuegbar (kein sentence-transformers)
- **Smart Queries**: nicht aktiv (kein LLM Key)

## Ergebnisse

| Metrik | v3 (Sprint 5) | v4 (Sprint 7) |
|--------|---------------|----------------|
| Quellen | SS + OA (2) | SS + OA + Exa (3) |
| Total Found | ~110 | 120 |
| After Dedup | 46 (4 Runs) | 50 (1 Run) |
| Exa Papers im Ergebnis | — | 0 (verdraengt) |
| Abstract-Quote | ~80% | 100% |
| Open Access | ~50% | 68% |

### Source-Verteilung (Run 1)

| Source | Raw | After Dedup | After Ranking |
|--------|-----|-------------|---------------|
| Semantic Scholar | ~50 | 21 | 21 (42%) |
| OpenAlex | ~50 | 29 | 29 (58%) |
| Exa | 20 | ~17 | **0** (0%) |

## Findings

### F19: Exa-Verdraengung durch Source-Aware Scoring (MEDIUM)

Exa liefert 20 Papers, aber **0 schaffen es ins Top-50 Ranking**. Ursache:
Exa Citation-Cap (0.05) ist so niedrig, dass Exa-Papers systematisch von
SS (0.4) und OA (0.15) Papers verdraengt werden.

**Ceiling**: Source-Aware Scoring schuetzt vor Citation-Inflation, aber
eliminiert gleichzeitig den Mehrwert von Exa als Grey-Literature-Quelle.

**Moegliche Fixes**:
- Source-Quota: Mindestens N Papers pro Quelle garantieren (z.B. 5 Exa)
- Exa Citation-Cap erhoehen (0.05 → 0.10)
- Separater Exa-Pool der nicht mit SS/OA konkurriert

### F20: Query-Divergenz — Verschiedene Queries finden komplett verschiedene Paper-Sets (HIGH)

v3 nutzte 4 verschiedene Queries, v4 nur 1. Overlap zwischen Queries: **0-1%**.
Das bestaetigt: eine einzelne Query reicht nicht fuer umfassenden Recall.

**Ceiling**: Selbst mit 3 Quellen ist der Recall einer Einzel-Query begrenzt.
`--refine` (Smart Query Expansion) koennte helfen, braucht aber LLM Key.
`--append` (akkumuliertes Suchen) ist der manuelle Workaround.

**Empfehlung**: Default-Workflow sollte 3-5 Queries mit `--append` sein,
nicht eine einzelne Query. Dokumentation/Skill anpassen.

### F21: SS Rate Limits ohne API Key (LOW)

Zweiter Run innerhalb von Minuten lieferte 0 SS-Papers (Rate Limit).
Ohne `S2_API_KEY` ist SS unzuverlaessig bei mehrfachen Runs.

**Workaround**: S2 API Key besorgen (kostenlos) oder Delay zwischen Runs.

## Ceiling-Detektor Update

v4 bestaetigt die These: Jede Erweiterung verschiebt Ceilings.

| Sprint | Ceiling verschoben | Neues Ceiling |
|--------|--------------------|---------------|
| Sprint 5 (Multi-Source) | Nur 1 Quelle | Exa wird verdraengt (F19) |
| Sprint 6 (Source-Aware) | Citation-Inflation | Grey Literature eliminiert (F19) |
| Sprint 7 (BibTeX Import) | Manuelle Papers nicht integrierbar | Nutzer muss wissen welche fehlen |
| Smart Queries (Sprint 3) | Nur 1 Query | Braucht LLM Key (F20) |

**Kern-Erkenntnis v4**: Das Toolkit hat jetzt alle Bausteine (3 Quellen,
Import, Smart Queries, Append), aber der **Workflow** ist entscheidend.
Ein einzelner `search` Call reicht nicht — der Nutzer braucht einen
Multi-Query-Workflow mit Append.

## Naechste Schritte

1. **F19 fixen**: Source-Quota oder Exa-Cap anpassen (Quickwin)
2. **Workflow dokumentieren**: Multi-Query Best Practice in Skill/README
3. **S2 API Key**: In .env eintragen fuer zuverlaessige Runs
4. **Meta-Loop v5**: Nach F19-Fix mit `--refine` + LLM Key testen
