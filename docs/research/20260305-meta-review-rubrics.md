# Meta-Review & Rubrik-Evolution

> Sind Structure, Evidence, Logic, Context, Clarity, Format die richtigen Dimensionen?
> Wie wuerde ein System das selbst herausfinden?

---

## Kernliteratur

### Shah et al. (2022) — "Rethinking the Peer Review Process" (NeurIPS)
Analyse von 10.000+ NeurIPS-Reviews: Inter-Rater Agreement ist niedrig (Cohen's
Kappa ~0.2). Reviewer bewerten "Novelty" und "Significance" inkonsistent.
"Clarity" und "Reproducibility" haben hoechste Agreement-Werte.
**Relevanz:** Dimensionen mit niedrigem Agreement sind fuer ein AI-Tool noch
problematischer — wenn Menschen sich nicht einig sind, kann ein LLM es nicht besser.

### Bao et al. (2024) — "A Systematic Study of LLMs as Automated Reviewers"
GPT-4 als Reviewer erreicht moderate Korrelation mit menschlichen Reviews
(Spearman ~0.3-0.5 je nach Dimension). Staerkste Korrelation bei "Clarity" und
"Presentation", schwaechste bei "Novelty" und "Significance".
**Relevanz:** Bestaetigt die Ceiling-These: LLMs koennen Oberflaechenqualitaet
bewerten, aber nicht epistemische Tiefe. Die Rubrik-Dimensionen sollten das abbilden.

### Liang et al. (2024) — "Can Large Language Models Provide Useful Feedback on Research Papers?"
1500+ ICLR-Paper analysiert. LLM-Feedback ueberlappt zu ~30% mit menschlichem Review.
LLMs finden formatische Probleme zuverlaessig, uebersehen konzeptuelle Schwaechen.
Kernfinding: LLMs sind bessere "Copy Editors" als "Peer Reviewers".
**Relevanz:** Die Rubrik sollte explizit zwischen "automatisch bewertbar" und
"braucht menschliches Urteil" trennen. Aktuell mischt der Reviewer beides.

### Rogers & Augenstein (2020) — "What Can We Do to Improve Peer Review in NLP?"
Meta-Analyse: Review-Qualitaet korreliert mit Spezifitaet der Kriterien.
Vage Dimensionen ("Significance") fuehren zu beliebigen Urteilen.
Handlungsorientierte Fragen ("Sind alle Claims durch Evidenz gestuetzt?") sind zuverlaessiger.
**Relevanz:** Die Rubrik-Dimensionen von "Evidence" auf konkretere Unterfragen
umstellen (z.B. "Jeder Claim hat min. 1 Zitat" statt "Evidence: stark/schwach").

### Zheng et al. (NeurIPS 2023) — "Judging LLM-as-a-Judge with MT-Bench"
[Paper](https://arxiv.org/abs/2306.05685) |
LLM-as-Judge Kalibrierung: Position Bias, Verbosity Bias, Self-Enhancement Bias.
GPT-4 erreicht >80% Agreement mit Menschen — gleiches Level wie Inter-Human Agreement.
Grading Rubrics, Few-Shot Examples und Chain-of-Thought verbessern Zuverlaessigkeit.
**Relevanz:** Der Review-Skill hat alle drei Biases. Rubric-basierte Prompts +
CoT koennen das mildern. Self-Enhancement bleibt Problem beim reflexiven Loop.

### OpenReviewer (2024) — Specialized LLM for Paper Reviews
[Paper](https://arxiv.org/html/2412.11948v3) |
Spezialisiertes LLM fuer Paper-Reviews, trainiert auf NeurIPS 2024 / ICLR 2025 Daten.
Test auf 400 Hold-Out-Papers. Problem: Peer Review hat grundsaetzlich niedrige
Inter-Reviewer-Agreement — Acceptance-Entscheidungen variieren fast zufaellig.
**Relevanz:** Bestaetigt: Auch mit dediziertem Modell bleibt Review subjektiv.
Das Toolkit sollte diese Unsicherheit transparent machen, nicht verstecken.

### OpenReview-Analysen (NeurIPS 2024)
Grosse Datensaetze auf OpenReview: Reviewer-Assignment via Text-Similarity-Modell
(Paper-Text vs. Reviewer-Publikationen). "Soundness" und "Significance" staerkste
Praediktoren fuer Accept/Reject, nicht "Clarity" oder "Presentation".
Superficial Reviews schlimmer als kein Review — tragen nur Noise bei.
**Relevanz:** Die aktuelle Rubrik gewichtet alle Dimensionen gleich. Empirisch
sind manche wichtiger. Und: schlechte automatische Reviews schaden aktiv.

---

## Ansaetze zur Rubrik-Evolution

### 1. Empirische Dimension Discovery
- Topic Modeling auf existierenden Reviews (LDA/BERTopic auf OpenReview-Daten)
- Clustering von Review-Kommentaren → emergente Dimensionen
- Problem: Braucht grossen Datensatz eigener Reviews

### 2. Inter-Rater Agreement pro Dimension
- Gleichen Text 3x reviewen (verschiedene Prompts/Temperaturen)
- Cohen's Kappa pro Dimension berechnen
- Dimensionen mit Kappa < 0.4 als "requires_human" flaggen
- **Sofort machbar, sehr aufschlussreich**

### 3. Meta-Review (Review des Reviews)
- Zweites LLM bewertet: "Ist dieses Review spezifisch, handlungsorientiert, fair?"
- Vergleich mit menschlichem Meta-Review
- Problem: Wer bewertet den Meta-Reviewer?

### 4. Outcome-basierte Validierung
- Korrelation: Fuehrt das Review zu besseren Revisionen?
- Braucht Vorher/Nachher-Vergleich + menschliche Qualitaetsbewertung
- Gold Standard, aber teuer

---

## Implications for Research Toolkit

### Sofort machbar
1. **Dimension-Confidence Split** — Jede DimensionResult bekommt explizites
   `automatable: bool`. "Clarity" und "Structure" = auto, "Significance" = human.
   Ist bereits angedeutet durch `Confidence.AUTO` vs `Confidence.REQUIRES_HUMAN`.
2. **Inter-Rater via Temperature** — Gleichen Review 3x mit Temperature 0.3/0.7/1.0
   laufen lassen, Agreement pro Dimension messen. Instabile Dimensionen markieren.
3. **Handlungsorientierte Sub-Fragen** — "Evidence: stark" ersetzen durch
   "Jeder Claim hat Quellenangabe: ja/nein", "Methodenbeschreibung reproduzierbar: ja/nein".

### Mittelfristig
4. **Self-Enhancement-Bias Test** — Gleichen Text von einem anderen LLM generieren
   lassen, dann reviewen. Vergleich mit Review des eigenen Outputs.
5. **Dimension-Gewichtung** — Nicht alle Dimensionen gleich gewichten. Empirisch:
   "Evidence" und "Logic" sollten 2x so stark zaehlen wie "Format".

### Langfristig
6. **Emergente Dimensionen** — BERTopic auf gesammelten Reviews, neue Dimensionen
   entdecken die nicht in der initialen Rubrik waren.
7. **Venue-spezifische Rubrics** — NeurIPS-Rubrik ≠ Policy-Brief-Rubrik.
   Dimensionen und Gewichtungen pro Venue-Profil.

### Empfohlener erster Schritt
Inter-Rater-Agreement messen (3x reviewen) + `automatable`-Flag pro Dimension.
Macht die Ceiling-Grenze explizit statt implizit.
