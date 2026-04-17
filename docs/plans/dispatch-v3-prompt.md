/dev-team

Sprint: Bundestag DIP Search-Fix V3.1
Plan: docs/plans/2026-04-17-bundestag-search-fix.md
Exploration: docs/research/api-exploration/bundestag-dip.md

WICHTIG: Agent-Team liegt in .claude/agents/ (connector-builder, test-runner, quality-gate) und ist gitignored — im Worktree vorhanden, nicht auf GitHub. Kann als Referenz genutzt werden, muss aber nicht zwangsweise per Agent tool dispatcht werden. Einfacher: dev-team orchestriert Tasks 1-10 sequenziell aus dem Plan.

Autonomie: Stufe 2 (autonom, STOPP bei Live-Test-Fail, API-Quirk, Build-Fehler).
Feature-Branch: fix/bundestag-search-v3 (NICHT master).

Pre-Flight: alle 6 Checks am 17.04.2026 gruen, config.py-Fix bereits auf master.

Tasks aus Plan sequenziell:
1. Legacy-Bug-Fix (search= -> f.titel, f.typ -> f.drucksachetyp)
2. Neue Basis-Methoden (get_vorgang, get_vorgangspositionen) + Models
3. BundestagVocabulary Modul (data/vocabularies/bundestag_deskriptoren.json)
4. search_topic() High-Level-API mit Rate-Limit + Dedup
5. forschungsstand.py Umstellung auf search_topic
6. Tests (Mock + Vocab + Live mit @pytest.mark.live)
7. Docs (docs/guides/bundestag-dip-api.md + briefing-app CLAUDE.md Updates)
8. Vocabulary-Seed Script + initial Cache (20+ Topics)
9. Re-Eval briefing-app (2 Smoke-Topics via run_benchmark.py)
10. quality-gate (adversarial-review Profil: code)

DoD siehe Plan-Section Definition of Done.

Nach Abschluss:
- docs/plans/retro.md append mit Learnings
- NICHT auf master mergen — Stefan bestaetigt Merge
- Worktree-Cleanup macht Stefan nach Merge
