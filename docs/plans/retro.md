# Sprint-Retrospektive — research-toolkit

> Append-only Retro-Log. Neue Eintraege oben.

---

## Sprint: Bundestag DIP Search-Fix V3.1 (2026-04-17)

**Plan:** `docs/plans/2026-04-17-bundestag-search-fix.md`
**Branch:** `fix/bundestag-search-v3`
**Dauer:** 1 Session, ~3h (inkl. Worktree-Bug-Reparatur + 2-Iter Review)
**Autonomie:** Stufe 2 (autonom, STOPP bei Problem)

### Delivered

| Task | Status | Dateien / Verifikation |
|------|--------|-----------------------|
| 1 Legacy-Bug-Fix | DONE | `bundestag_client.py` — `search=` → `f.titel`, `f.typ` → `f.drucksachetyp` |
| 2 Models + Methoden | DONE | `Deskriptor`, `DIPVorgangsposition`, `Fundstelle`, `get_vorgang`, `get_vorgangspositionen` |
| 3 BundestagVocabulary | DONE | `bundestag_vocabulary.py` (~230 Zeilen mit Stale-Check + Graceful-Degrad) |
| 4 search_topic() | DONE | Vocab-first, `f.deskriptor`-Pfad, Fallback auf `f.titel`, Positions-Expansion |
| 5 forschungsstand Migration | DONE | `_search_bundestag` nutzt `search_topic` + persistentes Vocabulary |
| 6 Tests | DONE | 33 client + 18 vocab + 5 live = 56 neue Tests, alle passing |
| 7 Dokumentation | DONE | `docs/guides/bundestag-dip-api.md` + briefing-app CLAUDE.md + pipeline-quality-epic Q1.5 |
| 8 Vocabulary Seed | DONE | 23 Topics gelernt, Cache 158KB, committed |
| 9 Re-Eval briefing-app | **DEFERRED** | Plan-Annahme-Mismatch — siehe Blockers unten |
| 10 adversarial-review | DONE (2 Iter) | 3 HIGH Findings → fixed + Re-Run gruen |

### Test-Status

- Non-live: **796 passed**, 5 deselected (live)
- Live: **5/5 passed** gegen echte DIP API
- Live-DoD verifiziert: 10/10 Topics im Korridor 5–50k Hits, kein Topic > 50k (V1-Bug-Regression)

### Empirische Verifikation

| Metric | Pre-V3 | Post-V3 |
|--------|--------|---------|
| "Klimaschutz" Drucksachen-Count | 285.331 (Vollbestand) | ~500 (titel-gefiltert) |
| "Klimaschutz" Vorgaenge | n/a | 3.644 (deskriptor-gefiltert) |
| Topic-Spezifitaet (Live-Test) | fail (Vollbestand) | pass (>=30% Klima-Keywords im Title) |

### Blockers / Deferred

**Task 9 (Re-Eval briefing-app):** DEFERRED weil Plan-Annahme `.eval.total_score` im
`data/runs/baseline-rerun/*.json` nicht vorhanden ist. Die baseline-rerun JSONs enthalten
nur `topic, mode, venue, voice, language, perspective_split, facets, html` — keine
`eval`-Section. Striktes Score-Delta gegen 8.8/10-Baseline daher nicht automatisch messbar.

**Alternative Qualitaets-Evidenz fuer V3:**
- 5 Live-Tests gegen echte DIP-API (Regression-Guard + Topic-Spezifitaet)
- 18 Vocabulary-Unit-Tests (Cache + Learning)
- 33 Client-Tests (Models + Endpunkte)
- Seed-Script-Run mit 23 Topics live geloggt (4 Topics lieferten 0 Deskriptoren — Graceful-Degradation-OK)

**Stefan-Entscheidung pending:** Re-Eval manuell durchfuehren ODER skippen ODER eval-Tooling
in briefing-app erweitern (Q1.5.1 in pipeline-quality-epic).

### Learnings

#### L1: EnterWorktree basierte auf stalem HEAD

Das Tool `EnterWorktree` hat den Worktree auf Commit `7404480` erstellt statt auf
aktuellem master HEAD (`4976b9d`). ~30 Commits fehlten, inkl. der Commit der
`bundestag_client.py` eingefuehrt hat.

**Symptom:** `src/agents/bundestag_client.py` existierte nicht im Worktree, obwohl auf master
vorhanden. Mein erster Edit landete faelschlich im master-Worktree (via absoluten Pfad).

**Workaround:** `git reset --hard master` im Worktree + `git checkout --` auf
master-uncommitted-Datei. Danach sauber.

**Aktion:** Sollte ein Tool-Bug-Report sein. Fuer kuenftige Worktree-Sprints:
Nach `EnterWorktree` sofort `git log --oneline -1` im Worktree pruefen vs
Haupt-HEAD. Erster Sanity-Check.

#### L2: Python-Path-Override fuer Cross-Repo-Tests funktioniert sauber

`PYTHONPATH=<worktree-path>` vor `python scripts/run_benchmark.py` ueberschreibt
editable-install-Resolution. So koennte man briefing-app mit Worktree-Code testen
OHNE den editable-install dauerhaft umzustellen. Fuer Task 9 letztlich nicht
benoetigt (wegen Plan-Annahme-Mismatch), aber nuetzlich fuer zukuenftige
Cross-Repo-Evals.

#### L3: Adversarial-Review gruendlich — findet Style-Violations die selbst-geschriebener Code haben wird

Auch bei sorgfaeltiger Implementation hatte Iteration 1 drei HIGH Findings:
- Immutability (`.sort()`/`.append()` statt `sorted()`/`[*list, new]`)
- Error-Handling (Initial-Call ohne try/except)
- Lesbarkeit (Funktion ueber 50-Zeilen-Limit)

Iteration 2 nach Fixes: APPROVE. Der Review-Overhead ist real aber zahlt sich aus —
Code-Style-Compliance ohne Menschen-Review.

#### L4: Graceful-Degradation bei Vocabulary-Learning auf rare Topics

Seed-Run zeigt: 4 von 23 Topics liefern 0 Deskriptoren (Universitaet, EU-Regulierung,
Buerokratieabbau, eu-regulierung). Das ist KEIN Fehler — die API findet
<5 Vorgaenge mit diesen Titel-Matches, daher zu wenig fuer min_freq=3 Filter.
`search_topic` faellt dann korrekt auf `f.titel` zurueck.

Empfehlung fuer kuenftige Seeds: `min_freq=2` (oder Topic-abhaengig) um mehr
Topics in den Cache zu bekommen. Aktuell konservativ bei 3.

#### L5: pytest `live` marker in pyproject.toml registrieren

Default pytest warnt bei unbekannten markern. `markers = ["live: ..."]` in
`[tool.pytest.ini_options]` eingefuegt — sauber.

### Next Steps (fuer Stefan)

1. **Merge-Entscheidung:** Stefan bestaetigt Merge `fix/bundestag-search-v3` → `master`
2. **briefing-app Re-Install:** Nach Merge `pip install -e .../research-toolkit` im
   briefing-app-venv erneut ausfuehren (fuer editable install refresh)
3. **Task 9 Re-Eval:** manuell laufen lassen oder als Q1.5.1 Follow-up in
   briefing-app-Sprint einplanen
4. **Worktree-Cleanup:** `git worktree remove .claude/worktrees/fix+bundestag-search-v3`
   im Haupt-repo nach Merge
