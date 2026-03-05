# Reflexiver Meta-Loop

Dieses Toolkit hat ein Paper ueber sich selbst generiert
(`examples/ai_automated_research/draft.md`) — eine Literaturuebersicht zu
"AI-Assisted Automated Research". Aus diesem Paper wurden 6 Findings abgeleitet,
die als Basis fuer eine traceable Weiterentwicklung dienen.

## Der Loop

```
Toolkit generiert Meta-Paper
  -> Paper analysiert AI Research Automation
  -> Findings zeigen Schwaechen des Toolkits auf
  -> Findings werden als Specs implementiert
  -> Git-History dokumentiert den Loop
```

## Sprints

| Sprint | Branch | Findings | Status |
|--------|--------|----------|--------|
| 1: Search Quality | `feature/search-quality` | F1 + F6 + F2 | Geplant |
| 2: Reflexivitaet | `feature/reflexive-loop` | F5 + F3 | Geplant |

## Dateien

| Datei | Zweck |
|-------|-------|
| `findings.md` | Die 6 Findings (sauber formatiert) |
| `iteration-1-spec.md` | Spec Sprint 1 |
| `iteration-1-review.md` | Review nach Sprint 1 |
| `iteration-2-spec.md` | Spec Sprint 2 |
| `iteration-2-review.md` | Review nach Sprint 2 |

## Warum?

1. **Dogfooding** — Das Toolkit verbessert sich selbst
2. **Traceability** — Jede Aenderung ist auf ein Finding zurueckfuehrbar
3. **Content** — Der Loop selbst ist kommunizierbarer Output (LinkedIn, README)
