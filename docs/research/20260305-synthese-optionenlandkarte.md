# Optionenlandkarte: 3+ Schritte ueber den Ceiling-Detektor hinaus

> Synthese aus 5 Research-Docs. Alle Optionen, egal wie gross.
> Sortiert nach: Impact x Machbarkeit. Entscheidung beim Menschen.

---

## Die Kernfrage

Paper 2 (Feedback zum Toolkit) identifiziert 3 Achsen wo "echter"
recursive Self-Improvement anfangen wuerde:

1. **Kalibrierte Confidence** — Predictions testbar gegen Outcomes
2. **Ranking Feedback-Loop** — Lernen welche Papers wirklich relevant sind
3. **Rubrik-Dimensionen hinterfragen** — Meta-Reviews der eigenen Reviews

Die Forschung (Huang ICLR 2024, Shumailov Nature 2024, Dell'Acqua Harvard 2023)
zeigt: Echtes Self-Improvement braucht *externes Signal*. Ohne Ground-Truth
dreht sich das System im Kreis. Die Frage ist nicht "wie verbessert sich
das System selbst?" sondern "wie sammelt es minimales externes Feedback
um die richtigen Stellschrauben zu finden?"

---

## Alle Optionen — nach Zeitrahmen

### Sofort (1-2 Tage, kein externer Input noetig)

| # | Option | Was | Aufwand | Impact |
|---|--------|-----|---------|--------|
| S1 | Numerische Confidence | `confidence: float` statt `str` auf EvidenceCard + Verbalized Confidence im Prompt | 2h | Macht Kalibrierung messbar. Prerequisite fuer alles Weitere. |
| S2 | Dimension-Confidence Split | `automatable: bool` pro DimensionResult. Clarity/Structure = auto, Significance = human. | 2h | Macht die Frontier explizit. Ehrlicher als "alles bewertbar". |
| S3 | Self-Consistency Probe | Review 3x mit Temperature-Varianz laufen lassen, Agreement pro Dimension messen | 4h | Zeigt empirisch wo der Reviewer stabil ist und wo nicht. |
| S4 | Handlungsorientierte Sub-Fragen | "Evidence: stark" → "Jeder Claim hat min. 1 Zitat: ja/nein" | 3h | Hoeheres Inter-Rater-Agreement, praeziseres Feedback. |
| S5 | feedback.jsonl Schema | Feedback-Format definieren: Topic, Expert-Ranking, Timestamp | 1h | Prerequisite fuer Ranking-Feedback. Ab sofort Daten sammeln. |
| S6 | Implizites Feedback tracken | Welche Papers landen im Draft? Evidence Card → Citation-Match automatisch loggen | 3h | Kostenloses Feedback-Signal, sofort nutzbar. |

### Mittelfristig (1-2 Wochen, braucht etwas externe Validierung)

| # | Option | Was | Aufwand | Impact |
|---|--------|-----|---------|--------|
| M1 | Abstract-Level Claim Verification | NLI via LLM-Prompt: Claim aus Evidence Card gegen Abstract pruefen. SUPPORTS/REFUTES/NEI. | 1 Woche | Schliesst Finding F9. Erkennt Halluzinationen in Evidence Cards. |
| M2 | LLM-as-Ranking-Judge | Zweites LLM bewertet Top-20 paarweise. Vergleich mit aktuellem Ranking. | 3 Tage | Guenstiges Proxy-Feedback (~$0.50/Run). Kein Ground-Truth, aber Signal. |
| M3 | Self-Enhancement Bias Test | Gleichen Text von anderem LLM generieren, dann reviewen. Delta zum eigenen Output messen. | 3 Tage | Quantifiziert den groessten Bias im reflexiven Loop. |
| M4 | ECE-Tracking | Manuell 50 Claims bewerten (korrekt/inkorrekt), ECE berechnen | 1 Woche | Erste echte Kalibrierungszahl. Baseline fuer Verbesserungen. |
| M5 | CORE/Unpaywall Integration | Full-Text-Zugang fuer ~30% OA Papers. Claims gegen Volltext statt nur Abstract. | 1 Woche | Claim Verification wird substantiell besser. |
| M6 | Atomic Claim Extraction | FactScore-Pattern: Draft in atomare Claims zerlegen, jeder einzeln verifizierbar | 3 Tage | Feinkoernigere Verifikation. Prerequisite fuer M1/M5. |

### Ambitioniert (1+ Monat, braucht systematisches Feedback)

| # | Option | Was | Aufwand | Impact |
|---|--------|-----|---------|--------|
| A1 | Gewichtungs-Optimierung | 10+ Topics mit Experten-Ranking: Grid Search ueber 5 Gewichtungsparameter | 2 Wochen | Empirisch optimiertes Ranking statt Bauchgefuehl-Gewichtung. |
| A2 | SciFact Benchmark | Check-Skill auf SciFact evaluieren, Baseline-Zahlen dokumentieren | 1 Woche | Objektiver Vergleich mit SOTA (F1 0.72-0.88). |
| A3 | Inter-Rater mit zweitem LLM | Gleichen Review von Claude + GPT-4 + Gemini erstellen, Agreement messen | 1 Woche | Cross-Model Agreement als Proxy fuer Zuverlaessigkeit. |
| A4 | Conformal Prediction Sets | Statt Punkt-Confidence: Set-Predictions mit garantierter Coverage | 2 Wochen | Theoretisch sauber. Braucht ~100+ gelabelte Claims. |
| A5 | Fine-tuned NLI (DeBERTa) | Optionale Dependency `[verify]`, F1 ~0.88 auf SciFact | 2 Wochen | Praeziseste Claim Verification. Aber: 400MB Modell-Dependency. |
| A6 | Venue-spezifische Rubrics | Dimensionen + Gewichtungen pro Venue-Profil (NeurIPS ≠ Policy Brief) | 2 Wochen | Review-Qualitaet wird venue-angepasst statt one-size-fits-all. |

### Visionaer (Forschungsprojekt, nicht Sprint)

| # | Option | Was | Aufwand | Impact |
|---|--------|-----|---------|--------|
| V1 | Learned Ranking Model | LambdaMART/Neural LTR auf gesammeltem Feedback | Monate | Ersetzt feste Gewichtungen komplett. Braucht 100+ Topics. |
| V2 | Emergente Dimensionen | BERTopic auf gesammelten Reviews, neue Dimensionen entdecken | Monate | Das System entdeckt Review-Dimensionen die wir nicht kannten. |
| V3 | Active Learning Pipeline | System fragt gezielt nach den Papers/Claims wo es am unsichersten ist | Monate | Minimaler menschlicher Aufwand, maximaler Lern-Effekt. |
| V4 | Cross-Encoder Full-Text Verification | Claim + Full-Text → Entailment mit GPU-Modell | Monate | Goldstandard fuer Claim Verification. Braucht Infrastruktur. |
| V5 | Provenance Chain | Jeder Draft-Claim → Evidence Card → Paper → Section → Sentence | Monate | Vollstaendige Nachvollziehbarkeit. Research Integrity Feature. |

---

## Die 3 Achsen aus Paper 2 — Forschungsstand

### Achse 1: Kalibrierte Confidence
**SOTA:** Verbalized Confidence funktioniert (Tian 2023, Xiong ICLR 2024),
ist aber systematisch overconfident. Self-Consistency (CISC, ACL 2025) reduziert
Kosten um 46%. Conformal Prediction (TACL 2024 Survey) liefert Garantien,
braucht aber Kalibrierungsdaten.

**Fuer das Toolkit:** S1 (numerisch) → M4 (ECE messen) → A4 (Conformal Sets).
Schrittweise, jeder Schritt baut auf dem vorherigen auf.

### Achse 2: Ranking Feedback-Loop
**SOTA:** LLM-Reranking (NAACL/SIGIR 2024) ist competitive mit Fine-tuned Modellen.
Online Iterative RLHF (2025) mit Targeted Human Feedback minimiert Annotationsaufwand.
Elicit/Consensus nutzen S2-Infrastruktur + eigene Relevanz-Modelle.

**Fuer das Toolkit:** S5+S6 (Feedback sammeln) → M2 (LLM-Judge) → A1 (Optimierung).
Der Engpass ist nicht der Algorithmus, sondern die Daten.

### Achse 3: Rubrik-Dimensionen hinterfragen
**SOTA:** Inter-Rater Agreement bei Peer Review ist niedrig (Kappa ~0.2, Shah 2022).
LLMs korrelieren moderat mit Menschen (Spearman 0.3-0.5, Bao 2024). "Soundness"
und "Significance" sind wichtiger als "Clarity" (OpenReview-Daten).
Self-Enhancement Bias ist dokumentiert (Zheng NeurIPS 2023).

**Fuer das Toolkit:** S2+S3+S4 (Dimensionen klassifizieren) → M3 (Bias messen) → A3+A6.
Die ehrlichste Verbesserung: Sagen wo die Rubrik unzuverlaessig ist.

---

## Empfohlene Reihenfolge (wenn alles offen ist)

### Sprint 3a: "Feedback Infrastructure" (S1+S5+S6+S2)
Numerische Confidence + Feedback-Schema + Implizites Tracking +
Dimension-Confidence-Split. **~1 Tag.** Sammelt ab sofort Daten und
macht die Frontier explizit. Prerequisite fuer alles Weitere.

### Sprint 3b: "Claim Verification" (M6+M1+A2)
Atomic Claims + Abstract-Level NLI + SciFact Benchmark.
**~2 Wochen.** Schliesst das groesste Loch: F9 (Claims nicht verifiziert).
Hoher Impact, weil es ein komplett neues Feature ist.

### Sprint 3c: "Ranking Intelligence" (M2+S3+M3)
LLM-Judge fuer Ranking + Self-Consistency-Probe + Bias-Test.
**~1 Woche.** Macht den Reviewer und Ranker empirisch testbar.

### Sprint 3d: "Ground Truth" (M4+A1+M5)
ECE messen + Gewichtungs-Optimierung + Full-Text-Zugang.
**~3 Wochen.** Erste echte Feedback-Loops mit externen Daten.

---

## Meta-Einsicht: Der Ceiling-Detektor wird zum Frontier-Mapper

Die urspruengliche These war: "Der reflexive Loop ist ein Ceiling-Detektor."
Die Forschung bestaetigt das — und erweitert es:

**Stufe 1 (abgeschlossen):** System findet eigene Schwaechen (Meta-Paper).
**Stufe 2 (abgeschlossen):** System fixt was es selbst fixen kann (Sprint 1+2).
**Stufe 3 (diese Optionen):** System kartografiert wo es *nicht mehr selbst fixen kann*
und baut die minimale Infrastruktur um externes Feedback zu integrieren.

Das ist kein Self-Improvement. Das ist **Frontier-Mapping** — die Karte der
eigenen Grenzen wird das wertvollste Feature des Toolkits.

---

## Quellen (Auswahl der wichtigsten)

- [Huang et al. ICLR 2024 — Self-Correction Limits](https://arxiv.org/abs/2310.01798)
- [Shumailov et al. Nature 2024 — Model Collapse](https://www.nature.com/articles/s41586-024-07566-y)
- [Dell'Acqua et al. Harvard 2023 — Jagged Frontier](https://www.hbs.edu/ris/Publication%20Files/24-013_d9b45b68-9e74-42d6-a1c6-c72fb70c7282.pdf)
- [Xiong et al. ICLR 2024 — LLM Uncertainty](https://arxiv.org/abs/2306.13063)
- [ICLR 2025 — Do LLMs Estimate Uncertainty Well](https://proceedings.iclr.cc/paper_files/paper/2025/file/ef472869c217bf693f2d9bbde66a6b07-Paper-Conference.pdf)
- [CISC ACL 2025 — Confidence Self-Consistency](https://aclanthology.org/2025.findings-acl.1030.pdf)
- [Conformal Prediction NLP Survey TACL 2024](https://arxiv.org/abs/2405.01976)
- [Zheng et al. NeurIPS 2023 — MT-Bench](https://arxiv.org/abs/2306.05685)
- [Kosprdic et al. 2024 — SciFact NLI](https://www.scitepress.org/Papers/2024/129000/129000.pdf)
- [Fact-Checking Survey 2026](https://www.arxiv.org/pdf/2601.02574)
- [LLM Active Learning Survey ACL 2025](https://aclanthology.org/2025.acl-long.708.pdf)
- [Self-Correction Blind Spot 2025](https://arxiv.org/html/2507.02778v1)
- [OpenReviewer 2024](https://arxiv.org/html/2412.11948v3)
- [ACM Survey UQ for LLMs 2025](https://dl.acm.org/doi/10.1145/3744238)
