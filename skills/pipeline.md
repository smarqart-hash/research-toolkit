# Pipeline — Skill-Verkettung und Datenfluss

## Ueberblick

Das Research Toolkit besteht aus 4 unabhaengigen Skills, die ueber
strukturierte Daten (Evidence Cards, ForschungsstandResult) kommunizieren:

```
Search ──→ Evidence Cards ──→ Draft ──→ Review ──→ Check
  │              │                        │
  ├─ Dedup       ├─ Claims               ├─ 7 Dimensionen
  ├─ Ranking     ├─ Methoden             ├─ Issues + Severity
  ├─ Screening   └─ Metriken            └─ Verdict
  └─ PRISMA-Flow
```

## Pipeline-Schritte

### 1. Search (Forschungsstand)

**Eingabe:** Topic + optionale Leitfragen + Konfiguration
**Ausgabe:** Gerankte Papers + Statistiken + PRISMA-Flow

```
Queries generieren
  → Semantic Scholar (parallel pro Query)
  → Exa (optional, Top-2 Queries)
  → Alle Ergebnisse sammeln
  → Deduplizieren (DOI > Title-Hash)
  → Ranking (SPECTER2-enhanced oder heuristisch)
  → Screening (optional, konfigurierbare Kriterien)
  → PRISMA-Flow-Statistik
```

**Ranking-Modi:**
- **Ohne SPECTER2:** 40% Citations + 30% Recency + 10% OA + 10% Abstract + 10% SS
- **Mit SPECTER2:** 30% Semantische Aehnlichkeit + 25% Citations + 25% Recency + 10% OA + 10% Abstract

**Screening-Kriterien (optional):**
- Jahresbereich (min/max)
- Abstract erforderlich
- Mindest-Zitationen
- Fachgebiete ausschliessen
- Keywords (Include/Exclude)

### 2. Draft (Entwurf)

**Eingabe:** Topic + Venue/Voice Profile + Search-Ergebnisse
**Ausgabe:** Markdown-Draft + Self-Check + Provenance

```
Venue Profile laden (Sektionen, Seitenzahl, Citation Style)
  → Voice Profile laden (Satzlaenge, Formalitaet, Tonalitaet)
  → Kapitelstruktur generieren
  → Pro Kapitel: Inhalt schreiben (LLM-gestuetzt)
  → Self-Check pro Sektion (Clarity, Evidence, Argumentation)
  → Self-Check global (Completeness, AI-Disclosure)
  → Speichern: draft.md + selfcheck.json + provenance.json
```

### 3. Review (Qualitaetskontrolle)

**Eingabe:** Dokument + Venue + Rubric
**Ausgabe:** 7-Dimensionen-Bewertung + Issues + Verdict

```
Dokument laden (Markdown oder Pandoc-konvertiert)
  → Rubric fuer Venue laden
  → Splitting (< 5000 Words: 1-Pass, > 5000: Kapitelweise + Synthese)
  → Pro Dimension: Rating (stark/angemessen/ausbaufaehig/kritisch)
  → Issues identifizieren (CRITICAL/HIGH/MEDIUM/LOW)
  → Delta zu vorherigem Review (falls vorhanden)
  → Verdict: READY / REVISION_NEEDED / MAJOR_REWORK
```

### 4. Check (Quellenverifikation)

**Eingabe:** Dokument + optionaler Context-Flag
**Ausgabe:** Verifikationsergebnisse pro Quelle

```
Referenzen extrahieren (Regex + Heuristik)
  → Pro Referenz: Semantic Scholar Lookup
  → Vergleich: Titel, Autor, Jahr, DOI
  → Status: VERIFIED / NOT_FOUND / METADATA_MISMATCH / CONTEXT_MISMATCH
```

## State Machine

Die Pipeline wird durch eine State Machine mit 6 Phasen orchestriert:

```
IDEATION → INGESTION → EXPERIMENT → SYNTHESIS → REVIEW → TYPESETTING
```

Jede Phase hat Status: NOT_STARTED, IN_PROGRESS, HALTED_FOR_HUMAN, COMPLETED, FAILED.

**HITL Gates (Human-in-the-Loop):**
Bestimmte Entscheidungen erfordern menschliches Urteil. Die State Machine
haelt an und wartet auf `resolve_hitl(decision)`.

Beispiele:
- "Soll die Hypothese pivotiert werden?"
- "Sind diese 20 Papers die richtigen?"
- "Ist der Draft bereit fuer externes Review?"

**Checkpoint/Resume:**
State wird als JSON persistiert. Bei Absturz oder Unterbrechung kann die
Pipeline an der letzten Phase fortgesetzt werden.

## Provenance (Herkunftskette)

Jede Agent-Aktion wird in `provenance.jsonl` geloggt (append-only):

```json
{
  "timestamp": "2026-03-05T14:30:00Z",
  "phase": "search",
  "agent": "screener",
  "action": "exclude",
  "source": "doi:10.1234/x",
  "metadata": {"reason": "field_mismatch", "field": "Biology"}
}
```

**PRISMA-trAIce Compliance:** Der Provenance Trail dokumentiert jede
Entscheidung in der Pipeline — von der ersten Suche bis zum finalen Check.

## PRISMA-Flow

Der Screening-Schritt erzeugt eine PRISMA-Flow-Statistik:

```
Identified: 150 (SS: 120, Exa: 30)
  → After Dedup: 98
  → After Ranking (Top-30): 30
  → Screened: 30
  → Included: 22
  → Excluded: 8
    - field_mismatch: 3
    - no_abstract: 2
    - low_citations: 2
    - excluded_keyword: 1
```

## Ceiling-Transparenz

### Was die Pipeline kann
- Effizient suchen (2 APIs parallel, Dedup, Ranking)
- Strukturierte Drafts in verschiedenen Venue-Formaten generieren
- Qualitaetsdimensionen systematisch pruefen
- Zitationen verifizieren
- Jede Entscheidung nachvollziehbar dokumentieren

### Was die Pipeline NICHT kann
- **Ranking evaluieren:** Kein Ground-Truth-Vergleich. SPECTER2 + Heuristik
  sind bessere Schaetzungen, aber nicht validiert. Das `specter2_score`-Feld
  macht die Diskrepanz zwischen beiden Methoden sichtbar.
- **Epistemische Qualitaet messen:** Der Review misst Legibility (liest sich
  wie gute Forschung), nicht ob die Schlussfolgerungen stimmen.
  `compute_delta()` zeigt Fortschritt gegenueber dem eigenen Reviewer —
  Goodhart's Law in Reinform.
- **Evidence Cards auf Halluzination pruefen:** Der Check verifiziert ob
  Quellen existieren, nicht ob Claims korrekt extrahiert wurden.
- **Review-Kriterien hinterfragen:** Die 7 Dimensionen und Rubrics sind
  statisch. Kein Meta-Review der Dimensionen selbst.
- **HITL Gates eliminieren:** Die Gates in `state.py` sind bewusste
  Eingestaendnisse, dass bestimmte Entscheidungen menschliches Urteil
  erfordern. Das ist Feature, nicht Bug.

### Implikation
Die Pipeline verbessert die **Form** (Output sieht professionell aus),
aber der **epistemische Ceiling** ist bounded by the weakest component.
Kein Component kann sich selbst debuggen.
