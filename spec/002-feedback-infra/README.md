# Spec 002: Feedback Infrastructure

**Datum:** 2026-03-10
**Scope:** Backend (Python-Module)
**Aufwand:** ~1 Tag
**Abhaengigkeit:** Keine (kann unabhaengig von Sprint 3 implementiert werden)
**Quelle:** `docs/plans/sprint-3.5-skizze.md`, Optionenlandkarte S1+S2+S5+S6

Feedback-Infrastruktur fuer spaetere Qualitaetsmessung.
4 Grundlagen: numerische Confidence, Frontier-Split (automatable-Flag),
Feedback-Schema (JSONL), implizites Citation-Tracking.

Voraussetzung fuer Sprint 4 (Agentic Review Loop), der das
`automatable`-Flag und numerische Confidence nutzt.
