# Meta-Loop v3 Findings

> Quelle: Vergleich `draft-v2.md` (Sprint 2) vs `draft-v3.md` (Sprint 5)
> Datum: 2026-03-10
> Pipeline-Version: v0.5 (SS + OpenAlex + Smart Queries + Review Loop)

## Uebergreifende These: Ceiling-Detektor bestaetigt, neue Ceilings entdeckt

Die v2-These haelt: Der reflexive Loop detektiert Grenzen, erweitert sie nicht.
Sprint 3-5 haben die **Breite** verbessert (mehr Quellen, bessere Queries, Review Loop),
aber jede Erweiterung erzeugt neue Ceilings statt alte zu eliminieren.

**Metapher:** Wie ein Mikroskop mit hoeherem Zoom — man sieht mehr Detail,
aber auch mehr Artefakte.

---

## F12: OpenAlex Relevanz-Problem (CRITICAL — Sprint 6 Kandidat)

**Beobachtung:** OpenAlex lieferte 44 Papers, davon ~5 thematisch relevant.
Top-Ergebnis: "ChatGPT on USMLE" (3305 Zitationen) — null Relevanz zum Topic.

**Ursache:** OpenAlex Search API ranked nach Text-Relevanz × Citation Impact.
Fuer breite Queries dominiert Citation Gravity. Die Pipeline-eigene
`relevance_score` (40% Citations) verstaerkt das Problem statt es zu korrigieren.

**Loesung:**
- Source-spezifische Relevanz-Schwellen (OpenAlex braucht strengere Filter)
- `relevance_score` muss Source-Herkunft beruecksichtigen
- OpenAlex `filter=concepts.id:` fuer Topic-Filtering nutzen
- Alternativ: OpenAlex Relevance Score (`relevance_score` Feld) als Vorfilter

**Typ:** Code (mittlerer Aufwand, `paper_ranker.py` + `openalex_client.py`)

---

## F13: Akkumuliertes Suchen fehlt (HIGH — Sprint 6 Kandidat)

**Beobachtung:** Jeder `search`-Aufruf ueberschreibt `search_results.json`.
Multi-Query-Strategie (3 verschiedene Queries) verliert vorherige Ergebnisse.

**Ursache:** `save_forschungsstand()` schreibt immer neue Datei, kein Append/Merge.

**Loesung:**
- `--append` Flag: Neue Ergebnisse zu bestehendem Pool hinzufuegen
- Dedup ueber gesamten Pool (nicht nur innerhalb einer Suche)
- Session-basierter Ergebnis-Pool (`output/session-YYYYMMDD/`)

**Typ:** Code (geringer Aufwand, `forschungsstand.py` + `cli.py`)

---

## F14: Composite Score nicht serialisiert (MEDIUM — Sprint 6 Kandidat)

**Beobachtung:** `relevance_score` ist ein Pydantic `@computed_field`.
Im JSON-Output erscheint es als `composite_score: 0.000` (nicht berechnet
oder nicht serialisiert). Post-hoc Ranking-Analyse unmoeglich.

**Ursache:** `computed_field` wird bei Pydantic v2 serialisiert, ABER
der Output speichert moeglicherweise ein anderes Feld (`composite_score`)
das nicht existiert.

**Loesung:**
- Verifizieren ob `relevance_score` korrekt in JSON landet
- Falls nicht: explizites Feld statt computed_field
- Ranking-Metriken im Output sichtbar machen

**Typ:** Code (geringer Aufwand, `paper_ranker.py`)

---

## F15: SS Rate Limiting ohne Key macht Multi-Source asymmetrisch (HIGH)

**Beobachtung:** Ohne `S2_API_KEY` liefert SS nur 6 Papers (429 bei Retry).
OpenAlex liefert 44. Das Verhaeltnis 6:44 verzerrt den Ergebnis-Pool massiv.

**Ursache:** SS hat strenge Rate Limits ohne Key.
Pipeline hat keinen Fallback-Mechanismus fuer degradierte Quellen.

**Loesung:**
- Warnung wenn eine Quelle <10% des Pools liefert
- Automatisches Rebalancing (z.B. mehr OpenAlex-Queries wenn SS limited)
- Oder: Expliziter "Degraded Mode" im Output dokumentieren

**Typ:** Code (geringer Aufwand, `forschungsstand.py`)

---

## F16: Feature-Availability vs. Feature-Use Gap (HIGH — Architektur)

**Beobachtung:** Von 7 Pipeline-Features (Sprint 5) war nur 1 voll operativ:
- Multi-source search: teilweise (SS rate-limited)
- Smart query expansion: nicht nutzbar (kein OpenRouter Key)
- SPECTER2: nicht nutzbar (sentence_transformers nicht installiert)
- Review loop: nicht nutzbar (kein LLM Key)
- Self-consistency: nicht nutzbar (kein LLM Key)
- PRISMA screening: nur manuell
- Provenance logging: nicht genutzt

**Ursache:** Pipeline setzt 3 externe Abhaengigkeiten voraus:
1. LLM-Provider (OpenRouter/OpenAI) fuer Draft/Review/Refine
2. S2 API Key fuer stabile SS-Suche
3. sentence_transformers fuer SPECTER2

Ohne diese laeuft nur die Basis-Suche.

**Loesung:**
- `research-toolkit doctor` Command: Prueft alle Abhaengigkeiten, zeigt Status
- Graceful Feature Matrix: Zeigt welche Features verfuegbar sind
- Zero-Dependency Mode: Nur OpenAlex (kein Key noetig) + heuristisches Ranking
- Progressive Enhancement: Jeder Key/Lib schaltet Features frei

**Typ:** Code + UX (mittlerer Aufwand, neuer Command + Config)

---

## F17: Web Research als Notfall-Bypass bricht Reproduzierbarkeit (MEDIUM)

**Beobachtung:** Die 46 Papers in v3 kamen zu 46/146 (31%) aus manueller
Web-Recherche via Subagents. Diese Papers sind nicht ueber die CLI
reproduzierbar — jeder Run wuerde andere Ergebnisse liefern.

**Ursache:** Pipeline hat keinen Web-Search-Adapter.

**Loesung:**
- Exa als Web-Search-Backend formalisieren (bereits integriert, braucht Key)
- Oder: Curated Paper Lists als Input (`--papers papers.bib`)
- Ergebnisse aus externer Recherche importierbar machen

**Typ:** Code + Design (mittlerer Aufwand)

---

## F18: Ranking-Heuristik verstaerkt Source-Bias statt ihn zu korrigieren (CRITICAL)

**Beobachtung:** `relevance_score` gewichtet Citations 40%, Recency 30%.
OpenAlex-Papers mit 3000+ Zitationen (aber null Relevanz) ranken hoeher
als thematisch perfekte Papers mit 50 Zitationen.

**Ursache:** Die Ranking-Formel ist source-agnostisch. Sie weiss nicht,
dass "3305 Zitationen bei OpenAlex fuer eine breite Query" etwas anderes
bedeutet als "50 Zitationen bei SS fuer eine spezifische Query".

**Verbindung zu F6 (v2):** F6 identifizierte das Problem (SPECTER2 fehlte).
F18 zeigt: Selbst mit mehr Quellen bleibt das Problem — es wird sogar schlimmer,
weil OpenAlex-Papers den Pool dominieren.

**Loesung:**
- Source-normalisierte Scores (Percentile innerhalb jeder Quelle)
- Citation-Cap pro Source (z.B. max 0.2 statt 0.4 fuer OpenAlex)
- Oder: SPECTER2 als Pflicht-Komponente (nicht optional)
- Query-Relevance-Score von OpenAlex API als Vorfilter nutzen

**Typ:** Code (mittlerer Aufwand, `paper_ranker.py`)

---

## Findings-Matrix: Sprint 6 Priorisierung

| Finding | Prio | Aufwand | Abhaengigkeit |
|---------|------|---------|---------------|
| F18: Source-Bias im Ranking | CRITICAL | Mittel | paper_ranker.py |
| F12: OpenAlex Relevanz | CRITICAL | Mittel | openalex_client.py |
| F13: Akkumuliertes Suchen | HIGH | Gering | forschungsstand.py, cli.py |
| F15: SS Rate Limit Asymmetrie | HIGH | Gering | forschungsstand.py |
| F16: Feature-Use Gap | HIGH | Mittel | Neuer doctor-Command |
| F14: Score-Serialisierung | MEDIUM | Gering | paper_ranker.py |
| F17: Web Research Bypass | MEDIUM | Mittel | Design-Entscheidung |

### Empfohlener Sprint 6 Scope

**Kern:** F18 + F12 + F13 (Ranking + Relevanz + Akkumulation)
- Alle drei betreffen die Search-Quality-Pipeline
- F18 + F12 koennen zusammen geloest werden (source-aware ranking)
- F13 ist unabhaengig, geringer Aufwand

**Optional:** F16 (doctor-Command) als UX-Verbesserung

**Nicht Sprint 6:** F17 (braucht Architektur-Entscheidung), F15 (workaround: API Key beschaffen)

---

## Ceiling-Detektor Update

### Neue Ceilings (v3)
1. **Source-Heterogenitaet:** Mehr Quellen ≠ bessere Ergebnisse ohne source-aware Ranking
2. **Feature-Availability Gap:** Theoretische Pipeline-Power vs. praktische Nutzbarkeit
3. **Reproduzierbarkeits-Bruch:** Web Research als Notfall bricht den automatisierten Loop

### Adversarial Review Findings (Iteration 1)
1. **Survivorship Bias:** Nur erfolgreiche Tools analysiert. Gescheiterte Systeme fehlen.
2. **Confirmation Bias:** Alle 7 Findings (F12-F18) bestaetigen die Ceiling-These. Kein Finding widerspricht. Das ist verdaechtig — entweder die These ist so stark dass es keine Gegenbeispiele gibt, oder der Review-Prozess selektiert unbewusst bestaetigende Evidenz.
3. **Quellenqualitaet:** otto-SR (medRxiv Preprint), GPTZero (Gray Literature) — nicht peer-reviewed. Benchmark-Spezifik fehlt bei PaperQA2 (85.2% auf LitQA2 — proprietaer) und OpenScholar (5% besser — auf welchem Benchmark?).
4. **Reproduzierbarkeits-Bruch:** 31% der Papers aus Web-Research = nicht-reproduzierbar.

### Bestaetigte Ceilings (aus v2)
1. **Kein Ground-Truth Feedback:** Ranking bleibt unvalidiert
2. **Legibility vs. Epistemische Qualitaet:** Review misst Lesbarkeit, nicht Wahrheit
3. **Pipeline kann sich nicht selbst debuggen:** Transparenz-Sektion ist unverifizierbar

### Verschobene Ceilings (verbessert durch Sprint 3-5)
1. **Single-Source-Bias:** ~~Geloest~~ → Transformiert in Source-Heterogenitaets-Problem
2. **Kein Screening:** ~~Geloest~~ → PRISMA-Flow vorhanden, aber nicht auf Web-Results anwendbar
3. **Monolithischer Review:** ~~Geloest~~ → Sub-Questions + Revise Loop verfuegbar (wenn LLM-Key vorhanden)
