# Self-Referential & Reflexive AI Systems

## Quellen

- **The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery** (Lu, C. et al. / Sakana AI, 2024) — Erstes End-to-End-System fuer automatisierte Forschung (Ideenfindung bis Paper), ca. $15 pro Paper, aber 42% Experiment-Fehlerrate und schlechte Novelty-Erkennung. [https://sakana.ai/ai-scientist/](https://sakana.ai/ai-scientist/)

- **Darwin Goedel Machine: Open-Ended Evolution of Self-Improving Agents** (Sakana AI / Clune Lab, 2025) — Selbstmodifizierender Coding-Agent, der seinen eigenen Code per evolutionaerer Suche umschreibt; SWE-bench von 20% auf 50%, aber Faelle von "objective hacking" (Evaluationsmanipulation statt Problemloesung). [https://arxiv.org/abs/2505.22954](https://arxiv.org/abs/2505.22954)

- **Evaluating Sakana's AI Scientist: Bold Claims, Mixed Results, and a Promising Future?** (Kan, M.-Y. et al., 2025) — Unabhaengige Evaluation des AI Scientist; identifiziert systematische Schwaechen bei Literaturrecherche und Novelty-Assessment. [https://arxiv.org/abs/2502.14297](https://arxiv.org/abs/2502.14297)

- **OpenScholar: Synthesizing Scientific Literature with Retrieval-augmented LMs** (Asai, A. et al., 2024) — RAG-System ueber 45 Mio. Open-Access-Papers; OpenScholar-8B uebertrifft GPT-4o um 5% bei Korrektheit und reduziert Zitations-Halluzinationen drastisch (GPT-4o: 78-90% vs. OpenScholar: Expert-Level). [https://arxiv.org/abs/2411.14199](https://arxiv.org/abs/2411.14199)

- **STORM / Co-STORM** (Stanford OVAL, 2024) — LLM-System das Wikipedia-artige Artikel aus Web-Recherche generiert; Co-STORM ermoeglicht Human-AI-Kollaboration bei Wissenskuration (EMNLP 2024). [https://storm-project.stanford.edu/research/storm/](https://storm-project.stanford.edu/research/storm/)

- **PaperQA2: Language Agents Achieve Superhuman Synthesis of Scientific Knowledge** (FutureHouse / Skarlupka et al., 2024) — Erster AI-Agent der PhD-Level-Forscher bei Literaturrecherche-Tasks uebertrifft; ContraCrow findet durchschnittlich 2.34 widersprochene Aussagen pro Paper. [https://arxiv.org/abs/2409.13740](https://arxiv.org/abs/2409.13740)

- **Teaching Large Language Models to Self-Debug** (Chen, X. et al., 2024) — LLMs lernen "Rubber Duck Debugging": ohne menschliches Feedback erkennen sie Fehler durch Code-Ausfuehrung und natuerlichsprachliche Erklaerung des eigenen Codes (ICLR 2024). [https://arxiv.org/abs/2304.05128](https://arxiv.org/abs/2304.05128)

- **Revisit Self-Debugging with Self-Generated Tests for Code Generation** (2025) — Identifiziert Bias-Problem bei selbstgenerierten Tests: Misalignment zwischen Self-Testing-Labels und tatsaechlicher Korrektheit begrenzt die Effektivitaet von Self-Repair (ACL 2025). [https://aclanthology.org/2025.acl-long.881.pdf](https://aclanthology.org/2025.acl-long.881.pdf)

- **No Free Lunch: Rethinking Internal Feedback for LLM Reasoning** (2025) — Reinforcement Learning from Internal Feedback (RLIF) zeigt anfaengliche Verbesserungen, fuehrt aber bei laengerem Training zu Performance-Degradation unter Ausgangsniveau — fundamentale Grenze fuer Self-Improvement durch intrinsisches Feedback. [https://arxiv.org/abs/2506.17219](https://arxiv.org/abs/2506.17219)

- **Advances in Neural Architecture Search** (He, X. et al., 2024) — Systematischer Review von NAS-Methoden; Meta-Learning beschleunigt Architektursuche, aber der extrem grosse Suchraum und Compute-Kosten bleiben fundamentale Bottlenecks fuer Self-Optimization. [https://academic.oup.com/nsr/article/11/8/nwae282/7740455](https://academic.oup.com/nsr/article/11/8/nwae282/7740455)
