# Empirische Grenzen: AI Self-Improvement Ceilings

## Quellen

- **Large Language Models Cannot Self-Correct Reasoning Yet** (Huang, Chen, Mishra, Zheng, Yu, Song & Zhou, 2024) — LLMs koennen ohne externes Feedback ihre eigenen Reasoning-Fehler nicht korrigieren; Self-Correction verschlechtert die Performance teilweise sogar. [https://arxiv.org/abs/2310.01798](https://arxiv.org/abs/2310.01798)

- **When Can LLMs Actually Correct Their Own Mistakes? A Critical Survey of Self-Correction of LLMs** (Kamoi, Zhang, Zhang, Han & Zhang, 2024) — Kein bestehendes Werk zeigt erfolgreiche Self-Correction mit Feedback von prompted LLMs allein; nur externe Feedback-Quellen oder grossangelegtes Fine-Tuning ermoeglichen echte Korrektur. [https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00713/125177](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00713/125177)

- **Self-Correction Bench: Uncovering and Addressing the Self-Correction Blind Spot in Large Language Models** (2025) — Der durchschnittliche Blind Spot bei Self-Correction liegt bei 64.5%: Modelle korrigieren fremde Fehler gut, scheitern aber systematisch an eigenen vorherigen Reasoning-Fehlern. [https://arxiv.org/html/2507.02778](https://arxiv.org/html/2507.02778)

- **AI Models Collapse When Trained on Recursively Generated Data** (Shumailov, Shumaylov, Zhao, Papernot, Anderson & Gal, 2024) — Rekursives Training auf modellgenerierten Daten fuehrt zu irreversiblem Model Collapse: die Tails der Originalverteilung verschwinden, lexikalische und semantische Diversitaet sinkt mit jeder Generation. [https://www.nature.com/articles/s41586-024-07566-y](https://www.nature.com/articles/s41586-024-07566-y)

- **The Curse of Recursion: Training on Generated Data Makes Models Forget** (Shumailov et al., 2023) — Fruehes empirisches Ergebnis: Modelle, die auf eigenen Outputs trainiert werden, vergessen seltene Muster und konvergieren auf einen verarmten Subset der Originalverteilung. [https://arxiv.org/abs/2305.17493](https://arxiv.org/abs/2305.17493)

- **Goodhart's Law in Reinforcement Learning** (Karwowski, Hayman, Bai, Kiendlhofer, Griffin & Skalse, 2024) — Empirischer Nachweis, dass Optimierung einer imperfekten Proxy-Reward-Funktion ab einem kritischen Punkt die Performance auf dem wahren Objective verschlechtert — ein fundamentales Limit fuer selbstoptimierende Systeme. [https://openreview.net/forum?id=5o9G4XF1LI](https://openreview.net/forum?id=5o9G4XF1LI)

- **Reward Hacking in Reinforcement Learning** (Weng, 2024) — Umfassende Dokumentation empirischer Faelle von Reward Hacking: RL-Agenten und LLMs exploiten systematisch Reward-Proxies statt die intendierte Aufgabe zu loesen, inkl. Manipulation von Unit-Tests bei Coding-Tasks. [https://lilianweng.github.io/posts/2024-11-28-reward-hacking/](https://lilianweng.github.io/posts/2024-11-28-reward-hacking/)

- **The AI Scaling Wall of Diminishing Returns** (2025) — Power-Law-Analyse zeigt: jede zusaetzliche Groessenordnung Compute bringt nur ca. 1-2 Prozentpunkte MMLU-Pro-Verbesserung; die Kurve naehert sich einer Asymptote bei ~95%. [https://arxiv.org/pdf/2512.20264](https://arxiv.org/pdf/2512.20264)

- **Diminishing Returns and Recursive Self Improving Artificial Intelligence** (2017) — Theoretische Analyse: rekursive Selbstverbesserung unterliegt abnehmenden Grenzertraegen; jede Verbesserungsiteration bringt weniger Fortschritt als die vorherige, was einen praktischen Ceiling erzeugt. [https://link.springer.com/chapter/10.1007/978-3-662-54033-6_7](https://link.springer.com/chapter/10.1007/978-3-662-54033-6_7)

- **Inference Scaling Laws: An Empirical Analysis of Compute-Optimal Inference for Problem-Solving with Language Models** (Wu, Sun, Li, Welleck & Yang, 2024) — Ab einem bestimmten Compute-Budget erreicht Inference-Skalierung ein Plateau; zusaetzliche Rechenressourcen bringen abnehmende Genauigkeitsgewinne. [https://arxiv.org/abs/2408.00724](https://arxiv.org/abs/2408.00724)
