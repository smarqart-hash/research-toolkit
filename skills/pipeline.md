# Pipeline — Limitationen & Ceiling-Transparenz

## Was die Pipeline kann
- Effizient suchen (3 APIs parallel, Dedup, SPECTER2/Heuristik-Ranking)
- Strukturierte Drafts in verschiedenen Venue-Formaten generieren
- Qualitaetsdimensionen systematisch pruefen (7 Dims + Sub-Questions)
- Zitationen verifizieren + Claims per FactScore-Pattern pruefen
- Jede Entscheidung nachvollziehbar dokumentieren (Provenance)

## Was die Pipeline NICHT kann
- **Ranking evaluieren:** Kein Ground-Truth-Vergleich. SPECTER2 + Heuristik
  sind bessere Schaetzungen, aber nicht validiert.
- **Epistemische Qualitaet messen:** Der Review misst Legibility (liest sich
  wie gute Forschung), nicht ob die Schlussfolgerungen stimmen.
  `compute_delta()` zeigt Fortschritt gegenueber dem eigenen Reviewer —
  Goodhart's Law in Reinform.
- **Evidence Cards auf Halluzination pruefen:** Der Check verifiziert ob
  Quellen existieren, nicht ob Claims korrekt extrahiert wurden.
- **Review-Kriterien hinterfragen:** Die 7 Dimensionen und Rubrics sind
  statisch. Kein Meta-Review der Dimensionen selbst.
- **HITL Gates eliminieren:** Die Gates in `state.py` sind bewusste
  Eingestaendnisse, dass bestimmte Entscheidungen menschliches Urteil
  erfordern. Das ist Feature, nicht Bug.

## Implikation
Die Pipeline verbessert die **Form** (Output sieht professionell aus),
aber der **epistemische Ceiling** ist bounded by the weakest component.
Kein Component kann sich selbst debuggen.

## Archiv
Alte Skill-Instruktionen (search, draft, review, check): `skills/_archive/`
Diese wurden durch CLI `--help` + CLAUDE.md ersetzt.
