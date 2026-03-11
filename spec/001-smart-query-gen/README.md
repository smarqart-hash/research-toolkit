# Spec 001: Smart Query Generation

**Datum:** 2026-03-10
**Scope:** Backend (Python-Modul + CLI)
**Quelle:** `docs/plans/sprint-3-handover.md`

LLM-gestuetzte Query-Optimierung fuer `search_papers()`.
Ersetzt die Heuristik in `generate_search_queries()` durch einen
intelligenten Query-Generator mit Synonym-Expansion, getrennten
SS/Exa-Formaten und optionaler Dry-Run-Validierung.