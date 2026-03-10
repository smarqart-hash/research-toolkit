# Sprint 3.5 Skizze: Feedback Infrastructure

> Status: SKIZZE (Handover wird vor Implementation geschrieben)
> Aufwand: ~1 Tag
> Abhaengigkeit: Keine (kann auch vor Sprint 3 gemacht werden)
> Quelle: Optionenlandkarte S1+S2+S5+S6

---

## Motivation

Ohne Feedback-Infrastruktur koennen spaetere Sprints ihre Qualitaet nicht
messen. Dieser Sprint legt 4 Grundlagen:

1. Numerische Confidence → messbar statt kategorisch
2. Frontier-Split → ehrlich statt "alles bewertbar"
3. Feedback-Schema → ab sofort Daten sammeln
4. Implizites Tracking → kostenloses Signal

---

## 4 Tasks

### T1: Numerische Confidence (S1) — ~2h

**Wo:** `src/utils/evidence_card.py:37`
**Ist:** `confidence: str = "medium"` (low/medium/high)
**Soll:** `confidence: float = 0.5` (0.0-1.0)

- Pydantic Validator fuer Backward-Compat: `"low"→0.3, "medium"→0.5, "high"→0.8`
- Prompt-Aenderung: "Rate your confidence 0.0-1.0" statt "low/medium/high"
- Alte JSON-Files laden weiterhin

### T2: Dimension-Confidence Split (S2) — ~2h

**Wo:** `src/agents/reviewer.py:62-68` (DimensionResult)
**Ist:** `confidence: Confidence = Confidence.AUTO`
**Soll:** + `automatable: bool = True`

Mapping:
| Dimension | automatable | Begruendung |
|-----------|------------|-------------|
| Structure | True | Regelbasiert pruefbar |
| Clarity | True | Sprachliche Analyse |
| Format | True | Template-Matching |
| Evidence | True (teilweise) | Zitat-Zaehlung, aber nicht Korrektheit |
| Logic | False | Argumentationslogik braucht Domaenwissen |
| Context | False | Einordnung braucht Feld-Expertise |
| Significance | False | Intrinsisch subjektiv |

### T3: Feedback Schema (S5) — ~1h

**Wo:** `config/feedback_schema.json` (NEU)
**Format:**
```json
{
  "topic": "AI traffic control",
  "timestamp": "2026-03-10T12:00:00Z",
  "ranking_method": "specter2_enhanced",
  "top_k_shown": 20,
  "expert_relevant": ["paper_id_1", "paper_id_3", "paper_id_7"],
  "expert_irrelevant": ["paper_id_12"],
  "notes": "Optional freitext"
}
```
Append-only in `feedback.jsonl` (gleiches Pattern wie provenance.jsonl).

### T4: Implizites Feedback (S6) — ~3h

**Wo:** `src/pipeline/provenance.py`
**Was:** Neuer Event-Typ `CITATION_USED`

Wenn Draft fertig: Welche paper_ids aus Evidence Cards werden im
Draft-Markdown tatsaechlich zitiert? Automatischer Abgleich, Log in
provenance.jsonl. Kostet nichts, laeuft im Hintergrund.

---

## Akzeptanzkriterien

- [ ] Alte Evidence Cards (confidence: str) laden weiterhin
- [ ] Neue Evidence Cards: `confidence: float`
- [ ] `DimensionResult.automatable: bool` vorhanden
- [ ] `feedback.jsonl` Schema in config/ dokumentiert
- [ ] `CITATION_USED` Events in provenance.jsonl
- [ ] Alle 248+ bestehenden Tests passing

## Research-Referenz
- [Calibrated Confidence](../research/20260305-calibrated-confidence.md) — Tian 2023, Xiong ICLR 2024
- [Meta-Review Rubrics](../research/20260305-meta-review-rubrics.md) — Shah 2022, Bao 2024
