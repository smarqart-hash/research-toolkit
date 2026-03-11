# Meta-Loop v5 — Findings (2026-03-11)

> Search mit allen 3 Quellen + Smart Queries (--refine) nach M2+M3 Quickwins.
> Ziel: Volles Feature-Set testen (SS + OA + Exa + LLM Query Expansion + SPECTER2).

## Setup

- **Query**: "reflexive AI-assisted research toolkits"
- **Sources**: SS, OpenAlex, Exa (alle 3 aktiv)
- **Config**: `--max 50 --sources ss,openalex,exa --refine`
- **Keys**: Exa OK, OpenAlex OK, SS OK (aber Rate Limited), OpenRouter OK
- **SPECTER2**: Aktiv (CPU, ~8min fuer 600 Papers)
- **Smart Queries**: Aktiv (LLM-Expansion via OpenRouter/Gemini Flash)

## Ergebnisse

| Metrik | v4 (Sprint 7) | v5 (M2+M3) |
|--------|---------------|-------------|
| Quellen | SS + OA + Exa (3) | SS + OA + Exa (3) + Smart Queries |
| Total Found | 120 | 745 |
| After Dedup+Ranking | 50 | 50 |
| Smart Queries | Nein | Ja (5 SS, 5 OA, 5 Exa) |
| SPECTER2 | Nein | Ja (CPU) |
| SS Papers im Ergebnis | 21 (42%) | ~2 (<1%) — Rate Limited |
| Abstract-Quote | 100% | ~95% |

### Source-Verteilung

| Source | Raw | After Ranking |
|--------|-----|---------------|
| Semantic Scholar | ~2 | ~2 (<1%) |
| OpenAlex | ~500+ | ~45 (90%) |
| Exa | ~240 | ~3 (6%) |

## Findings

### F22: SS API Key leer in .env (HIGH — User-Action)

`S2_API_KEY=` in `.env` ist leer (Laenge 0). Kein Code-Bug —
der Nutzer muss einen API Key bei Semantic Scholar beantragen.

**Auswirkung**: SS liefert nur 2/745 Papers. Source-Balance komplett zerstoert.
**Fix**: SS API Key unter https://www.semanticscholar.org/product/api beantragen
und in `.env` eintragen.

### F23: Smart Query Expansion erzeugt zu breite Queries (MEDIUM)

Die LLM-generierten Queries sind thematisch zu breit:
- "large language models" AND "academic writing"
- "human-AI collaboration" AND "research tools"
- "AI for science" AND "research productivity"

Ergebnis: 745 Papers, aber die meisten sind "AI in Healthcare/Education"
Review-Papers die nichts mit Research Toolkits zu tun haben.

**Ceiling**: Smart Query Expansion maximiert Recall auf Kosten der Precision.
Der `expand_prompt.txt` koennte einen staerkeren Spezifizitaets-Constraint brauchen.

### F24: SPECTER2 rettet Precision teilweise (POSITIVE)

Trotz 745 roher Papers sind die Top-50 nach SPECTER2-Ranking thematisch
besser als die Raw-Ergebnisse. Allerdings dominieren immer noch breite
"AI in X" Survey-Papers mit hohen Citation-Counts.

**Ceiling**: SPECTER2 allein kann keine schlechte Query-Precision kompensieren.
Semantische Aehnlichkeit bevorzugt breite Survey-Papers die viele Keywords abdecken.

### F25: Exa Source-Quota funktioniert (POSITIVE)

Exa hat 3 Papers in den Top-50 (6%) — besser als v4 (0%).
Die Source-Quota-Logik aus dem Search Quality Sprint greift.

## Ceiling-Detektor Update

v5 bestaetigt: Smart Queries + SPECTER2 zusammen sind maechtig, aber
die Kombination verstaerkt das Recall-Precision-Tradeoff.

| Feature | Vorteil | Neues Ceiling |
|---------|---------|---------------|
| Smart Queries | 6x mehr Papers (120 → 745) | Breite statt Tiefe |
| SPECTER2 | Semantisches Ranking | Bevorzugt Surveys |
| Source-Quota | Exa nicht mehr verdraengt | SS-Ausfall nicht kompensiert |

## Naechste Schritte

1. **F22 debuggen**: SS API Key laden pruefen (python-dotenv? .env Format?)
2. **F23**: `expand_prompt.txt` mit Precision-Constraint erweitern
3. **Meta-Loop v5 wiederholen** nach F22-Fix (mit funktionierendem SS)
4. **M2 (Ranking-Judge) testen**: Top-50 durch LLM bewerten lassen
