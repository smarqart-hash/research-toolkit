# Ranking Feedback Loops — Lernen aus menschlichem Urteil

> Wie kann ein Paper-Ranking-System aus Experten-Feedback lernen?
> Aktueller Stand: Feste Gewichtung (SPECTER2 30%, Citations 25%, Recency 25%, OA 10%, Abstract 10%). Kein Feedback-Mechanismus.

---

## Kernliteratur

### Burges et al. (2005) — "Learning to Rank using Gradient Descent" (RankNet)
Pairwise Learning-to-Rank: Modell lernt aus Paaren (Paper A > Paper B).
Braucht O(n^2) Paare, aber in der Praxis reichen ~50-100 annotierte Paare
pro Query fuer brauchbare Ergebnisse.
**Relevanz:** Paarweise Vergleiche ("Welches Paper ist relevanter?") sind fuer
Experten leichter zu beantworten als absolute Scores.

### Cao et al. (2007) — "Learning to Rank: From Pairwise Approach to Listwise Approach"
ListNet: Statt Paare ganze Rankings vergleichen. Braucht weniger Annotationen,
konvergiert schneller. Aber: Komplexere Implementierung.
**Relevanz:** Bei nur 10-20 Experten-Urteilen pro Topic waere Listwise effizienter.

### Joachims et al. (2017) — "Unbiased Learning to Rank with Biased Feedback"
Click-Daten sind biased (Position Bias, Trust Bias). Propensity Scoring korrigiert.
**Relevanz:** Wenn das Toolkit Usage-Daten sammelt (welche Papers werden tatsaechlich
im Draft zitiert?), ist das implizites Feedback — aber biased.

### Settles (2012) — "Active Learning" (Survey)
Uncertainty Sampling: System fragt gezielt nach den Papers wo es sich am unsichersten
ist. Reduziert Annotationsaufwand um 50-80% gegenueber Random Sampling.
**Relevanz:** Statt alle 120 Papers bewerten zu lassen, nur die 15-20 wo das
Ranking am unsichersten ist. Maximaler Informationsgewinn.

### Qin et al. (2024) — "Large Language Models are Effective Text Rankers with Pairwise Ranking Prompting"
LLMs als Zero-Shot Ranker: Paarweise Vergleiche via Prompting (A vs B, welches
ist relevanter?). Competitive mit fine-tuned Modellen. GPT-4 erreicht ~0.75 nDCG@10
auf TREC-Benchmarks.
**Relevanz:** Statt menschliche Experten koennte ein zweites LLM als "Ranking-Judge"
dienen. Guenstiger, aber nicht Ground-Truth.

### Semantic Scholar Relevance (2023) — SPECTER2 + S2AG
Semantic Scholar nutzt SPECTER2 fuer Embedding-Similarity, kombiniert mit
Citation-Graph-Features, Recency und personalisierte Signale. Keine festen
Gewichtungen — ML-Modell auf Click-Through-Daten trainiert.
**Relevanz:** Das ist das Ziel-Architektur-Pattern. Aber braucht Millionen
von Interaktionen — unrealistisch fuer ein CLI-Tool.

### Elicit / Consensus Approach
Elicit nutzt Semantic Scholar + OpenAlex (200M+ Papers), Ranking via Relevanz-Modell.
Consensus nutzt Keyword + ANN-Vektorsuche auf Titeln/Abstracts, ergaenzt durch
SJR-Rankings und SciScore-Indikatoren. Beide nutzen S2-Infrastruktur.
**Relevanz:** Claim-basiertes Ranking (Consensus) vs. Paper-basiert (Elicit) sind
zwei verschiedene Paradigmen. Unser Toolkit koennte beides unterstuetzen.

### Zero-Shot LLM Reranking (NAACL/SIGIR 2024)
[NAACL Paper](https://aclanthology.org/2024.naacl-short.31.pdf) |
[SIGIR Paper](https://dl.acm.org/doi/10.1145/3626772.3657813) |
Setwise und In-Context Reranking: LLMs vergleichen mehrere Dokumente gleichzeitig.
ICR braucht nur 2 Forward-Passes fuer N Dokumente — 60%+ schneller als RankGPT.
Fine-grained Relevance Labels (statt binaer) verbessern Ranking-Qualitaet.
**Relevanz:** LLM-Reranking als Post-Processing nach SPECTER2 — guenstig, effektiv.

### Online Iterative RLHF (2025)
Statt einmaliges Offline-Training: kontinuierliche Feedback-Collection und
Model-Updates. RLTHF (Targeted Human Feedback) kombiniert LLM-basierte
Erstanpassung mit selektiven menschlichen Korrekturen — minimiert Annotationsaufwand.
**Relevanz:** Hybrid-Ansatz passt zu unserem Setup: LLM-Judge fuer Bulk,
Mensch nur fuer die schwierigen Faelle.

### LLM-based Active Learning Survey (ACL 2025)
[Paper](https://aclanthology.org/2025.acl-long.708.pdf) |
LLMs koennen sowohl Queries generieren (welche Samples annotieren?) als auch
Labels vergeben. Hybride Human+LLM-Annotation ist effizienter als nur-Mensch.
**Relevanz:** Active Learning mit LLM-Vorauswahl fuer Ranking-Feedback.

---

## Evaluation-Metriken

| Metrik | Was sie misst | Minimum Ground-Truth |
|--------|--------------|---------------------|
| Precision@K | Anteil relevanter Papers in Top-K | K * Anzahl_Topics |
| nDCG@10 | Position-gewichtete Relevanz | 10+ Urteile pro Topic |
| MAP | Mean Average Precision | Vollstaendige Relevanz-Urteile |
| Kendall's Tau | Ranking-Korrelation mit Experte | 2 komplette Rankings |

---

## Implications for Research Toolkit

### Sofort machbar
1. **Paarweise Preference Collection** — Nach jedem `search`-Run: "Welche 3 Papers
   sind am relevantesten?" Speichern in `feedback.jsonl`. Kostet 30 Sekunden pro Run.
2. **Implizites Feedback** — Welche Papers landen tatsaechlich im Draft? Automatisch
   trackbar via Evidence Cards -> Draft -> Citation-Match.
3. **LLM-as-Ranking-Judge** — Zweites LLM bewertet Top-20 paarweise. Kein Experte
   noetig, aber auch kein Ground-Truth. Kostet ~$0.50 pro Run.

### Mittelfristig (10-50 annotierte Topics)
4. **Gewichtungs-Optimierung** — Mit 10+ Topics mit Experten-Ranking: Grid Search
   ueber die 5 Gewichtungsparameter, Optimierung auf nDCG@10. Einfach, interpretierbar.
5. **Active Learning** — System identifiziert Papers wo Ranking unsicher ist,
   fragt gezielt nach. Halbiert Annotationsaufwand.

### Langfristig (100+ Topics)
6. **Learned Ranking Model** — LambdaMART oder Neural LTR auf gesammelten Feedback-
   Daten. Ersetzt feste Gewichtungen komplett.
7. **Personalisierte Gewichtungen** — Pro-User oder Pro-Venue Ranking-Profile.

### Empfohlener erster Schritt
`feedback.jsonl` Schema definieren + implizites Feedback (Draft-Citations) tracken.
Kostet fast keinen Aufwand, sammelt ab sofort Trainingsdaten fuer spaeter.
