# Meta-Loop Findings

> Quelle: `examples/ai_automated_research/draft.md` (eigenes Meta-Paper)

## Uebergreifende These: Ceiling-Detektor

Der reflexive Loop ist nicht primaer ein Self-Improvement-Mechanismus — er ist ein
**Ceiling-Detektor**. Das System kann seinen Output iterieren, aber nicht seine
eigenen Faehigkeiten erweitern.

**Fundamentale Asymmetrie:**
- Die Pipeline kann Papers suchen, ranken, Drafts generieren, Reviews durchfuehren
- Die Pipeline kann NICHT erkennen, ob ihr Ranking schlecht ist (kein Ground-Truth),
  Evidence Cards auf Halluzination pruefen, oder Review-Kriterien hinterfragen

**Konsequenz fuer die Entwicklung:**
- **Verbessern** wo moeglich (bessere Heuristiken, mehr Signale, Screening-Schritt)
- **Ceiling sichtbar machen** wo fundamental (PRISMA-Flow zeigt Verluste, Ranking
  wird testbar gegen Ground Truth, HITL-Gates dokumentieren menschliche Entscheidungen)

**Goodhart's Law in der Pipeline:**
`compute_delta()` in `reviewer.py` misst ob der Draft den Reviewer zufriedenstellt —
nicht ob er wissenschaftlich besser wird. Das System optimiert auf Legibility, nicht
auf epistemische Qualitaet. Die HITL-Gates in `state.py` sind das ehrlichste
Engineering: Sie gestehen ein, wo die Maschine nicht entscheiden kann.

---

## F1: Screening-Schritt fehlt (HOCH)

**Referenz:** Nykvist et al. (2025) — GPT performt "remarkably well" beim Title/Abstract-Screening

**Problem:** Search-Skill findet und rankt, aber kein expliziter Include/Exclude-Schritt.
Kein PRISMA-Flow ("120 found -> 87 screened -> 20 included").

**Loesung:** Screening-Schritt nach Ranking mit Inclusion/Exclusion-Kriterien.
PRISMA-Flow-Statistik im Output. Screening-Entscheidungen in provenance.jsonl loggen.

**Sprint:** 1

---

## F2: Pipeline-Dokumentation fehlt (MITTEL)

**Problem:** Skills sind isoliert dokumentiert, Verkettung (Search -> Draft -> Review -> Check) nicht.

**Loesung:** `skills/pipeline.md` — erklaert Skill-Kette, State Machine, Beispiel-Pipeline-Run.

**Differenzierer:** Meiste Tools (STORM, PaperQA2) sind monolithisch. Modularitaet ist
Feature, muss aber dokumentiert sein.

**Sprint:** 1

---

## F3: Rubric-Kalibrierung unklar (NIEDRIG)

**Problem:** Ordinale Labels ("stark/angemessen/ausbaufaehig/kritisch") nicht gegen
Benchmark kalibriert. Spearman 0.42 ohne Konfidenzintervall.

**Loesung:** Nicht implementieren, aber transparent dokumentieren (Known Limitations erweitern).

**Sprint:** 2

---

## F4: Automation Paradox (LINKEDIN)

**Kern:** "Wenn AI-Tools die Kosten fuer Literature Reviews senken, koennte das Volumen
wissenschaftlicher Publikationen weiter steigen — ein Feedback-Loop."

**Nutzung:** Philosophischer Kern fuer LinkedIn-Post. Nicht implementieren, kommunizieren.

**Sprint:** Keiner (Content)

---

## F5: Reflexive Analysis als Feature (MITTEL)

**Problem:** Section 6.3 im Meta-Paper reflektiert ueber eigene Grenzen — aber nur
als Beispiel-Output, nicht als wiederholbares Feature.

**Loesung:** `--reflexive` Flag im Draft-Skill. Generiert automatisch Limitations-Sektion
(verwendete Tools, Datenbanken, Known Biases).

**Sprint:** 2

---

## F6: Ranking-Schwaeche (HOCH)

**Problem:** Citation Count + Recency verpasste Kern-Papers (OpenScholar, STORM, Elicit)
zugunsten populaerer Papers aus Nachbar-Feldern (Protein-Design, Hydrologie).

**Detail:** SPECTER2 Embeddings sind als Dependency vorhanden (`[nlp]`),
werden aber nicht im Ranking genutzt.

**Loesung:** SPECTER2-Relevanz-Score in Ranking einbauen. Known Limitations verschaerfen.

**Sprint:** 1
