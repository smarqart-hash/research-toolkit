# Multi-Query-Workflow (--refine)

## Uebersicht

`--refine` aktiviert 2-stufige Query-Expansion fuer besseren Recall:

1. **Lokal** (immer): Synonym-Map + Boolean-Queries + Exa Natural Language + OA Freitext
2. **LLM** (optional): OpenRouter generiert diverse, DACH-aware Queries

## Voraussetzungen

- `OPENROUTER_API_KEY` oder `LLM_API_KEY` in `.env` (nur fuer Stufe 2)
- Ohne Key: Fallback auf lokale Expansion (funktioniert immer)

## Nutzung

```bash
# Basis: lokale Expansion (Synonym-Map)
research-toolkit search "machine learning fairness" --refine

# Alle Quellen + LLM-Expansion
research-toolkit search "KI in der Verwaltung" --refine --sources ss,openalex,exa

# Schnell ohne Dry-Run-Validierung
research-toolkit search "topic" --refine --no-validate

# Akkumuliert: neue Ergebnisse zu bestehendem Pool
research-toolkit search "topic" --refine --append
```

## Query-Typen

| Typ | Format | Ziel | Beispiel |
|-----|--------|------|----------|
| `ss_queries` | Boolean (`AND`/`OR`) | Semantic Scholar | `"RL AND (traffic OR Verkehr)"` |
| `oa_queries` | Freitext (kein Boolean) | OpenAlex | `"reinforcement learning traffic"` |
| `exa_queries` | Natural Language | Exa Search | `"What are recent advances in RL?"` |

## Architektur

```
Topic + Leitfragen
    |
    v
expand_queries()
    |
    +-- Stufe 1: _expand_local()     (immer)
    +-- Stufe 2: _expand_llm()       (wenn API Key vorhanden)
    |
    v
QuerySet { ss_queries, oa_queries, exa_queries }
    |
    v (optional: --no-validate ueberspringt)
validate_queries()  — Dry-Run, entfernt leere Queries
    |
    v
Parallele Suche: SS | OpenAlex | Exa
```

## Konfiguration

| Variable | Zweck | Default |
|----------|-------|---------|
| `LLM_API_KEY` | API Key fuer LLM-Expansion | — |
| `OPENROUTER_API_KEY` | Fallback fuer LLM_API_KEY | — |
| `LLM_MODEL` | LLM-Modell | `google/gemini-2.0-flash-001` |
| `LLM_BASE_URL` | API-Endpoint | `https://openrouter.ai/api/v1` |

## Troubleshooting

- **"LLM expansion failed"** — Key pruefen. Fallback auf lokal ist OK, kein Datenverlust.
- **Wenige Ergebnisse** — `--refine` + `--sources ss,openalex,exa` + `--append` kombinieren.
- **Queries validieren** — Ohne `--no-validate` wird jede Query mit limit=1 getestet. Langsamer, aber nur valide Queries werden genutzt.
