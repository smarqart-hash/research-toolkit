# Kalibrierte Confidence in AI-Systemen

> Wie macht man LLM-generierte Confidence-Labels testbar gegen Outcomes?
> Aktueller Stand: Evidence Cards nutzen `confidence: str = "medium"` — unkalibriert.

---

## Kernliteratur

### Guo et al. (2017) — "On Calibration of Modern Neural Networks"
Moderne DNNs sind systematisch overconfident. Temperature Scaling (ein einziger gelernter
Parameter) reicht oft fuer Post-Hoc-Kalibrierung. Einfach, effektiv, Standard-Baseline.
**Relevanz:** Temperature Scaling ist der minimale erste Schritt — aber setzt numerische
Logits voraus, die bei LLM-Text-Outputs nicht direkt verfuegbar sind.

### Kadavath et al. (2022) — "Language Models (Mostly) Know What They Know"
LLMs koennen ihre eigene Unsicherheit einschaetzen ("P(True)"-Probing). Groessere Modelle
sind besser kalibriert. Verbalized Confidence ("Wie sicher bist du?") korreliert mit
Accuracy, aber nicht perfekt — systematischer Overconfidence-Bias.
**Relevanz:** Direkt anwendbar. Man kann den LLM bei Claim-Extraktion nach Confidence
fragen und bekommt brauchbare (nicht perfekte) Signale.

### Tian et al. (2023) — "Just Ask for Calibration"
Verbalized Confidence (LLM gibt Zahl 0-100 aus) ist besser kalibriert als Token-
Wahrscheinlichkeiten bei instruction-tuned Modellen. Einfacher Prompt-Zusatz genuegt.
**Relevanz:** Niedrigste Implementierungshuerde. Statt "low/medium/high" einfach
"Confidence 0-100" im Prompt anfordern. Sofort testbar gegen Outcomes.

### Angelopoulos & Bates (2023) — "Conformal Prediction: A Gentle Introduction"
Distribution-free Uncertainty Quantification: Statt Punktschaetzung liefert Conformal
Prediction garantierte Coverage-Intervalle. Braucht nur ein Kalibrierungsset (Exchangeability).
**Relevanz:** Theoretisch elegant, aber braucht Ground-Truth-Labels fuer Kalibrierung.
Fuer Evidence Cards muesste man ~100+ manuell bewertete Claims haben.

### Lin et al. (2022) — "Teaching Models to Express Their Uncertainty in Words"
Training von LLMs auf verbalized uncertainty. Fine-tuning auf Kalibrierungsdaten
verbessert ECE signifikant. Aber: Braucht Trainingsdaten mit Ground-Truth-Confidence.
**Relevanz:** Zu aufwaendig fuer ein CLI-Tool. Eher fuer grosse Plattformen.

### Xiong et al. (ICLR 2024) — "Can LLMs Express Their Uncertainty?"
[Paper](https://arxiv.org/abs/2306.13063) |
Umfassender Benchmark: GPT-4 ist besser kalibriert als GPT-3.5, aber alle Modelle
sind bei schwierigen Fragen overconfident. Self-consistency (mehrfach samplen, Varianz
messen) verbessert Kalibrierung signifikant. Verbalized Confidence ist oft miscalibriert —
"80% confidence" bei nur 50% Accuracy.
**Relevanz:** Self-consistency ist implementierbar: Gleiche Extraktion 3x laufen,
Agreement als Confidence-Proxy. Teurer, aber robust.

### ICLR 2025 — "Do LLMs Estimate Uncertainty Well?"
[Paper](https://proceedings.iclr.cc/paper_files/paper/2025/file/ef472869c217bf693f2d9bbde66a6b07-Paper-Conference.pdf) |
Skalierung verbessert Kalibrierung und Failure Prediction, aber bleibt weit
von idealer Performance entfernt. Overconfidence ist ein persistentes Problem
auch bei SOTA-Modellen.
**Relevanz:** Selbst mit besten Modellen braucht man externe Validierung.

### CISC (ACL 2025) — "Confidence Improves Self-Consistency"
[Paper](https://aclanthology.org/2025.findings-acl.1030.pdf) |
Self-Consistency braucht 18.6 Samples im Schnitt. CISC (Confidence-weighted
majority vote) erreicht gleiche Accuracy mit nur 10 Samples — 46% Kostenreduktion.
**Relevanz:** Macht Self-Consistency praktikabel fuer ein CLI-Tool.
3 Samples statt 1 ist realistisch.

### Conformal Prediction for NLP (TACL 2024)
[Survey](https://arxiv.org/abs/2405.01976) |
Umfassender Survey: Conformal Prediction liefert distribution-free Garantien
fuer NLP-Tasks. Anwendbar auf Klassifikation, Generation, QA.
Braucht Kalibrierungsset, aber keine Modellannahmen.
**Relevanz:** Fuer Evidence Card Confidence: Conformal Sets statt Punktschaetzungen.
"Claim X ist mit 90% Wahrscheinlichkeit in {SUPPORTS, NEUTRAL}" statt "confidence: 0.8".

### SteerConf (2025) — "Steering LLMs for Confidence Elicitation"
[Paper](https://arxiv.org/pdf/2503.02863) |
Methode um LLM-Confidence gezielt zu steuern und zu kalibrieren.
**Relevanz:** Neuester Ansatz — potenziell besser als einfaches "rate 0-100".

---

## Kalibrierungs-Metriken

| Metrik | Formel | Interpretation |
|--------|--------|----------------|
| ECE (Expected Calibration Error) | Gewichteter Mittelwert von |confidence - accuracy| pro Bin | Standard-Metrik, < 0.05 ist gut |
| Brier Score | Mean Squared Error der Wahrscheinlichkeiten | 0 = perfekt, 1 = schlecht |
| AUROC | Area Under ROC fuer "korrekt vs. inkorrekt" | Diskriminierung, nicht Kalibrierung |

---

## Implications for Research Toolkit

### Sofort machbar (Sprint-tauglich)
1. **Verbalized Confidence (0-100)** statt kategorischer Labels — Prompt-Aenderung,
   kein neuer Code. Tian et al. zeigen: funktioniert out-of-the-box.
2. **Confidence-Felder numerisch machen** — `confidence: float` statt `str` in
   EvidenceCard. Backwards-compatible via Pydantic Validator.

### Mittelfristig (braucht Daten)
3. **Self-Consistency Scoring** — Claim 3x extrahieren, Agreement messen.
   Teurer (3x API-Calls), aber robusteste Methode ohne Ground-Truth.
4. **ECE-Tracking** — Wenn manuell bewertete Claims gesammelt werden (z.B. 50+),
   kann man ECE berechnen und Kalibrierung messen.

### Langfristig (braucht Ground-Truth)
5. **Conformal Prediction** — Garantierte Coverage, aber braucht ~100+ gelabelte
   Beispiele. Erst sinnvoll wenn systematisch Feedback gesammelt wird.
6. **Fine-tuned Calibration** — Eigenes Kalibrierungsmodell. Unrealistisch fuer CLI-Tool.

### Empfohlener erster Schritt
`confidence: float` (0.0-1.0) + Verbalized Confidence im Prompt + ECE-Logging
in provenance.jsonl. Kostet fast nichts, macht Kalibrierung messbar.
