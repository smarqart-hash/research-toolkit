# Claim Verification — NLI fuer wissenschaftliche Texte

> Wie verifiziert man ob extrahierte Claims korrekt sind?
> Aktuell: Check-Skill prueft ob Quellen *existieren*, nicht ob Claims *stimmen*.

---

## Kernliteratur

### SciFact (Allen AI, 2020) — Benchmark
[Dataset](https://github.com/allenai/scifact) |
1.4K Experten-geschriebene wissenschaftliche Claims, gepaart mit
Evidence-Abstracts und Labels (SUPPORTS/REFUTES/NOT_ENOUGH_INFO).
Standard-Benchmark fuer Scientific Claim Verification.
**Relevanz:** Direkt nutzbar als Evaluation-Benchmark fuer den Check-Skill.
Wenn wir NLI einbauen, messen wir Accuracy auf SciFact.

### Kosprdic et al. (2024) — "Scientific Claim Verification with Fine-Tuned NLI Models"
[Paper](https://www.scitepress.org/Papers/2024/129000/129000.pdf) |
Fine-tuned DeBERTa auf SciFact erreicht F1 = 0.88. RoBERTa Large und
XLM-RoBERTa ebenfalls stark. Alle besser als Zero-Shot-LLMs fuer
diesen spezifischen Task.
**Relevanz:** Ein Fine-tuned NLI-Modell (DeBERTa, ~400MB) waere die
praeziseste Loesung. Aber: Dependency-Groesse vs. Accuracy Tradeoff.

### MultiVerS (Allen AI, 2022)
Multi-granular Claim Verification: Prueft Claims gegen ganze Abstracts,
nicht nur einzelne Saetze. Erreicht F1 = 0.72 auf SciFact.
**Relevanz:** Robuster als Satz-Level-NLI, weil wissenschaftliche Claims
oft mehrere Saetze im Abstract brauchen um gestuetzt zu werden.

### FactScore (Min et al., 2023)
Zerlegt LLM-Output in atomare Fakten, verifiziert jedes gegen Wikipedia.
Interpretierbar, aber: Wikipedia als einzige Wissensquelle.
**Relevanz:** Das Pattern (atomare Claims → Verify) ist direkt uebertragbar.
Statt Wikipedia: Semantic Scholar Abstracts als Wissensquelle.

### FActool (Chern et al., 2023)
Tool-augmented Fact-Checking: LLM extrahiert Sub-Claims, nutzt dann
externe Tools (Search, Code Execution, etc.) zur Verifikation.
**Relevanz:** Architektur-Pattern passt zum Toolkit: Der Check-Skill
koennte Atomic Claims extrahieren und gegen S2-Abstracts pruefen.

### FactCheck-GPT / SelfCheckGPT (2024)
[Hallucination Detection Survey](https://arxiv.org/pdf/2508.03860) |
LLM-basierte Verification ohne externes Wissen: Self-Consistency ueber
mehrere Generierungen. Wenn der Claim in verschiedenen Runs variiert,
ist er wahrscheinlich halluziniert.
**Relevanz:** Kombinierbar mit Self-Consistency-Scoring aus dem
Confidence-Research. Billiger als NLI-Modell, aber weniger praezise.

### SciClaims (2025) — End-to-End Biomedical Claim Analysis
[Paper](https://arxiv.org/pdf/2503.18526) |
Generatives System fuer biomedizinische Claim-Analyse: Extraktion,
Verifikation und Erklaerung in einem Pipeline-Schritt.
**Relevanz:** Zeigt den SOTA fuer domainspezifische Claim-Verification.
Biomedizin-fokussiert, aber Architektur uebertragbar.

### Fact-Checking with LLMs (2026 Preprint)
[Paper](https://www.arxiv.org/pdf/2601.02574) |
Umfassender Survey zu LLM-basiertem Fact-Checking. Vergleich von
Pipeline-Ansaetzen (Claim → Evidence → Verify) vs. End-to-End-LLM.
Ergebnis: Pipelines sind zuverlaessiger, End-to-End ist schneller.
**Relevanz:** Best Practice fuer unseren Check-Skill: Pipeline-Ansatz
beibehalten, LLM nur fuer Claim-Extraktion nutzen, NLI fuer Verify.

---

## Full-Text-Zugang (Voraussetzung fuer Claim Verification)

| API | Coverage | Kosten | Zugang |
|-----|----------|--------|--------|
| Unpaywall | ~30% OA Papers | Kostenlos | E-Mail-basiert |
| CORE | 250M+ Full-Texts | Kostenlos (API Key) | API |
| OpenAlex Full-Text | Wachsend | Kostenlos | API |
| Semantic Scholar | Nur Abstracts | Kostenlos | API |
| Sci-Hub | ~85%+ | Legal problematisch | — |

**Problem:** Ohne Full-Text-Zugang ist Claim Verification auf
Abstract-Level beschraenkt. Viele Claims beziehen sich auf Methoden
oder Ergebnisse die nur im Volltext stehen.

---

## Implications for Research Toolkit

### Sofort machbar
1. **Abstract-Level NLI** — Claim aus Evidence Card gegen Abstract pruefen
   mit DeBERTa-NLI (oder Zero-Shot via LLM). Labels: SUPPORTS/REFUTES/NEI.
   Ergebnis als `verification_status` auf EvidenceCard speichern.
2. **Atomic Claim Extraction** — Im Draft-Skill: Claims atomarisieren
   (FactScore-Pattern). Jeder atomare Claim bekommt eigene Verifikation.
3. **Self-Consistency Verification** — Claim 3x extrahieren, bei Varianz
   als "uncertain" flaggen. Billig, kein externes Modell noetig.

### Mittelfristig
4. **CORE/Unpaywall Integration** — Full-Text-Zugang fuer ~30% der Papers.
   Claim Verification gegen Volltext statt nur Abstract.
5. **Fine-tuned NLI-Modell** — DeBERTa auf SciFact fine-tunen, als
   optionale Dependency `[verify]`. F1 ~0.88 statt ~0.70 Zero-Shot.
6. **SciFact Benchmark** — Den Check-Skill auf SciFact evaluieren,
   Baseline-Zahlen dokumentieren, Progress messen.

### Langfristig
7. **Cross-Encoder Verification** — Claim + Full-Text → Entailment Score.
   Braucht Full-Text + GPU. Hochpraezise, aber teuer.
8. **Provenance-Chain** — Jeder Claim im Draft trackt: Evidence Card →
   Paper → Section → Sentence. Vollstaendige Nachvollziehbarkeit.

### Empfohlener erster Schritt
Abstract-Level NLI via LLM-Prompt (Zero-Shot) + `verification_status`
Feld auf EvidenceCard. Atomare Claims im Draft. SciFact als Benchmark.
