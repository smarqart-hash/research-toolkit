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

---

## Findings aus v1-v2-Vergleich (Post-Sprint-Reflexion)

> Quelle: Vergleich `examples/ai_automated_research/draft.md` (v1) vs `draft-v2.md` (v2).
> Bestaetigung der Ceiling-Detektor-These: Die Verbesserungen v1→v2 sind
> **Transparenz-Verbesserungen**, keine **epistemischen Verbesserungen**.
> Die Pipeline weiss jetzt besser was sie nicht weiss — aber sie weiss nicht mehr.

---

## F7: Screening-Validierung fehlt (HOCH)

**Problem:** Screening-Kriterien wurden einmalig definiert, nicht gegen Experten validiert.
Borderline-Cases (z.B. Umar & Lano 2024 — Requirements Engineering mit teilweiser
methodischer Uebertragbarkeit) koennten falsch klassifiziert sein.

**Loesung:** Zweiter Reviewer (Mensch oder anderes LLM) fuer Borderline-Entscheidungen.
Inter-Rater-Agreement messen. Kostet externe Validierung — Pipeline kann das nicht selbst.

**Typ:** Empirisch (kein reiner Code-Change)

---

## F8: Multi-Source Search (MITTEL)

**Problem:** Beide Versionen (v1 + v2) nutzen identische 120 Papers aus Semantic Scholar.
Exa war deaktiviert. OpenAlex, PubMed, BASE als Quellen wuerden den Input-Pool diversifizieren
und den English-Language-Bias reduzieren.

**Loesung:** Weitere API-Clients (OpenAlex ist kostenlos, PubMed via E-utilities).
`search_papers()` akzeptiert bereits mehrere Quellen via `from_exa()` / `from_semantic_scholar()` —
Pattern ist erweiterbar.

**Typ:** Code (API-Integration, mittlerer Aufwand)

---

## F9: Evidence Card Verification (HOCH)

**Problem:** Der Check-Skill verifiziert ob Quellen *existieren* (Titel, Autor, Jahr stimmen),
aber nicht ob *Claims korrekt extrahiert* wurden. Ein Evidence Card koennte sagen
"Paper findet 18% Trust-Reduktion" obwohl das Paper das Gegenteil zeigt.

**Loesung:** NLI/Entailment-basierter Verification-Step: Claim aus Evidence Card gegen
Abstract oder Full-Text pruefen (z.B. via Cross-Encoder). Braucht Zugang zu Full-Text
und ein Entailment-Modell.

**Typ:** Code + Forschung (hoher Aufwand)

---

## F10: Ranking Feedback-Loop (HOCH)

**Problem:** `specter2_score` macht die Diskrepanz zwischen heuristischem und semantischem
Ranking sichtbar — aber es gibt keinen Mechanismus zu lernen, welche Methode besser ist.
Fuer das Meta-Paper-Thema rankt Semantic Similarity z.B. ProtAgents (Protein-Design) hoch,
obwohl es thematisch peripher ist.

**Loesung:** A/B-Test gegen Experten-kuratierte Paper-Liste fuer 3-5 Topics.
Precision@K und nDCG messen. Braucht Ground-Truth-Daten — Pipeline kann sich
nicht selbst evaluieren.

**Typ:** Empirisch (kein reiner Code-Change)

---

## F11: Voice Calibration (MITTEL)

**Problem:** v2 klingt immer noch "generisch akademisch". Die Voice-Profile
(`config/voice_profiles/`) definieren Satzlaenge und Formalitaet, aber wurden
nicht gegen echte Venue-Samples kalibriert. Ein Nature-Paper liest sich anders
als ein Policy Brief — dieser Unterschied ist in den Profilen nicht abgebildet.

**Loesung:** Corpus-Analyse: 10 echte Papers pro Venue extrahieren, statistisch
auswerten (Satzlaenge, Passiv-Anteil, Transition-Woerter), Profile daraus ableiten.

**Typ:** Code (Corpus-Analyse-Tool) + Daten (Venue-Samples)
