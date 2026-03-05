# Recursive Self-Improvement — Grenzen und Moeglichkeiten

> Wo endet der reflexive Loop? Was ist echtes Self-Improvement,
> was ist nur Transparenz-Iteration?

---

## Kernliteratur

### Huang et al. (ICLR 2024) — "Large Language Models Cannot Self-Correct Reasoning Yet"
[Paper](https://arxiv.org/abs/2310.01798) |
Intrinsische Selbstkorrektur (ohne externes Feedback) verbessert Performance
nicht oder verschlechtert sie sogar — bei Arithmetic Reasoning, QA, Code Generation,
Plan Generation. Bottleneck: LLMs koennen kein zuverlaessiges Feedback ueber
eigene Antworten generieren, nur durch Prompting.
**Relevanz:** Direkt anwendbar auf den reflexiven Loop: Wenn das Toolkit sein eigenes
Draft reviewt, kann es Oberflaechenfehler finden, aber nicht epistemische Qualitaet
beurteilen. Die HITL-Gates in `state.py` sind die korrekte Antwort.

### Self-Correction Blind Spot (2025)
[Paper](https://arxiv.org/html/2507.02778v1) |
LLMs koennen Fehler in *externem* Input korrigieren, aber nicht in *eigenen* Outputs.
Ein "Self-Correction Blind Spot" — das System sieht eigene Fehler systematisch nicht.
**Relevanz:** Erklaert warum der Review-Skill den Draft-Skill besser bewertet als
einen externen Text. Self-Enhancement Bias + Blind Spot = systematische Overfitting-
Gefahr beim reflexiven Loop.

### Shumailov et al. (Nature 2024) — "AI Models Collapse When Trained on Recursively Generated Data"
[Paper](https://www.nature.com/articles/s41586-024-07566-y) |
Rekursives Training auf eigenen Outputs fuehrt zu irreversiblem Modell-Kollaps.
Die Tails der Verteilung (seltene, aber wichtige Datenpunkte) verschwinden zuerst.
Gilt fuer LLMs, VAEs und Gaussian Mixture Models.
**Relevanz:** Der reflexive Loop trainiert nicht im technischen Sinne, aber:
Wenn das Toolkit seine eigenen Outputs als Input fuer die naechste Iteration nimmt,
riskiert es konzeptuellen "Collapse" — die seltenen Perspektiven gehen verloren.

### Anmerkung zu Shumailov: Dohmatob et al. (2024)
[Paper](https://arxiv.org/abs/2410.12954) |
Nuancierung: Model Collapse tritt vor allem auf wenn synthetische Daten *ersetzen*
(statt ergaenzen). Mixing mit echten Daten stabilisiert. Ausserdem: Collapse
haengt von der Qualitaet des Generators ab — bessere Modelle kollabieren langsamer.
**Relevanz:** Fuer das Toolkit: Solange echte Papers (S2, Exa) den Kern bilden
und LLM-Output nur ergaenzt, ist Collapse unwahrscheinlich. Aber: Wenn Drafts
als "Quellen" fuer den naechsten Draft dienen — Vorsicht.

### Dell'Acqua et al. (Harvard/BCG 2023) — "Jagged Technological Frontier"
[Paper](https://www.hbs.edu/ris/Publication%20Files/24-013_d9b45b68-9e74-42d6-a1c6-c72fb70c7282.pdf) |
758 BCG-Consultants, randomisiert. Innerhalb der AI-Frontier: +12.2% Tasks, 25.1%
schneller, 40% hoehere Qualitaet. Ausserhalb: -19 Prozentpunkte schlechter als ohne AI.
Kern: "Mis-calibrated Trust" — Menschen vertrauen AI genau dort am meisten wo sie
am schwaechsten ist. Die Frontier ist unsichtbar bis man drueber ist.
**Relevanz:** Das Toolkit operiert genau an dieser Grenze. Search + Screening =
innerhalb der Frontier. Epistemische Bewertung (Ist der Claim korrekt? Ist das
Ranking-Kriterium das richtige?) = ausserhalb. Ceiling-Detection macht die Grenze sichtbar.

### Constitutional AI / RLAIF (Anthropic 2022, Updates 2024)
[Paper](https://arxiv.org/abs/2212.08073) |
Self-Improvement via AI-Feedback: Modell kritisiert sich selbst anhand von Prinzipien,
revidiert, Fine-tuned auf Revisionen. Funktioniert fuer Harmlessness/Alignment,
NICHT fuer faktische Korrektheit oder epistemische Qualitaet.
**Relevanz:** RLAIF zeigt wo Self-Improvement funktioniert: Bei klar definierbaren
Regeln (Prinzipien). Versagt bei offenen Bewertungen ("Ist dieses Ranking gut?").

### Self-Consistency als Pseudo-Self-Improvement
[RELIC Paper (CHI 2024)](https://dl.acm.org/doi/10.1145/3613904.3641904) |
Self-Consistency (mehrfach samplen) ist kein echtes Self-Improvement, aber macht
Unsicherheit sichtbar. RELIC zeigt: Varianz in LLM-Outputs ist ein brauchbares
Signal fuer "hier ist das System unsicher".
**Relevanz:** Nicht versuchen sich selbst zu verbessern, sondern Unsicherheit
transparent machen — genau die Ceiling-Detektor-These.

---

## Wo funktioniert Self-Improvement? Wo nicht?

| Bereich | Funktioniert? | Warum? |
|---------|--------------|--------|
| Code-Debugging | Ja (teilweise) | Tests geben binäres externes Feedback |
| Harmlessness/Safety | Ja (RLAIF) | Klare Regeln als Prinzipien formulierbar |
| Formatting/Structure | Ja | Oberflaechenmerkmale, regelbasiert pruefbar |
| Factual Correctness | Nein | Kein internes Signal ob Fakt stimmt |
| Ranking Quality | Nein | Kein Ground-Truth ohne externen Vergleich |
| Epistemische Tiefe | Nein | "Ist dieser Schluss korrekt?" braucht Domaenenwissen |
| Novelty/Significance | Nein | Intrinsisch subjektiv, niedrige Inter-Rater-Agreement |

---

## Implications for Research Toolkit

### Die fundamentale Asymmetrie (bestaetigt durch Literatur)
Das Toolkit kann innerhalb der Frontier iterieren:
- Bessere Prompts, bessere Screening-Kriterien, transparentere Dokumentation
- Formatfehler finden, Strukturprobleme identifizieren, Missing Citations flaggen

Das Toolkit kann NICHT ueber die Frontier hinaus:
- Ob das Ranking die richtigen Papers priorisiert (braucht Experte)
- Ob extrahierte Claims korrekt sind (braucht Entailment + Full-Text)
- Ob die Rubrik-Dimensionen die richtigen sind (braucht Meta-Review-Daten)

### Was das fuer "3 Schritte weiter" bedeutet
1. **Die Frontier sichtbar machen** — Jedes Feature in der Pipeline als
   "innerhalb/ausserhalb der Frontier" klassifizieren. Transparenz > Ambition.
2. **Minimale externe Feedback-Loops** — Nicht mehr Self-Improvement,
   sondern Human-in-the-Loop-Daten systematisch sammeln (feedback.jsonl).
3. **Self-Consistency als Ceiling-Signal** — Wo das System instabil ist
   (verschiedene Runs → verschiedene Rankings), dort HITL-Gate vorschlagen.
