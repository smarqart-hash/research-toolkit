# Sprint 6 Handover: Search Quality Fixes

> Status: COMPLETE | Branch: `worktree-sprint-6-search-quality` | Tests: 439 passing

## Findings adressiert

| Finding | Fix | Dateien |
|---------|-----|---------|
| F18: Source-Bias im Ranking | Source-spezifische Citation-Caps (SS: 0.4, OA: 0.15, Exa: 0.05) | `paper_ranker.py` |
| F12: OpenAlex Relevanz | Pre-Filter bei relevance_score < 0.3 | `openalex_client.py`, `forschungsstand.py` |
| F13: Akkumuliertes Suchen | `merge_results()` + `--append` CLI Flag | `forschungsstand.py`, `cli.py` |
| F14: Score-Serialisierung | Tests bestaetigen Pydantic v2 serialisiert computed_field | `test_paper_ranker.py` |
| F15: Source-Balance | `_check_source_balance()` warnt bei <10% Anteil | `forschungsstand.py` |

## Commits (8)

1. `bc5f1ff` — feat: source-aware relevance scoring (F18+F12)
2. `9871f89` — test: verify relevance_score serialization (F14)
3. `f3bd61b` — feat: OpenAlex relevance pre-filter at 0.3 threshold (F12)
4. `4432450` — feat: merge_results for accumulated search (F13)
5. `a3b1e71` — feat: source balance warning for asymmetric results (F15)
6. `56080bf` — feat: --append flag for accumulated search (F13)
7. `15744a4` — chore: remove deprecated --exa/--no-exa flag
8. `a8690fb` — fix: QG2 review fixes (path mismatch + duplicate function)

## Quality Gates

- **QG1 (T1-T3):** PASS — 430 Tests, keine Issues
- **QG2 (T4-T7):** PASS after fixes — 1 CRITICAL (Pfad-Mismatch --append) + 1 Important (doppelte Funktion) gefunden und behoben

## Neue Tests: 19

- `TestSourceAwareRelevanceScore` (4 Tests)
- `TestScoreSerialization` (3 Tests)
- `TestOpenAlexRelevanceFilter` (2 Tests)
- `TestOpenAlexPreFilter` (1 Test)
- `TestAccumulatedSearch` (5 Tests)
- `TestSourceBalanceWarning` (4 Tests)

## Offene Punkte (Sprint 7 Kandidaten)

- `_compute_enhanced_score` (SPECTER2-Pfad) noch nicht source-aware
- `doctor` Command fuer Feature-Availability Check (F16)
- Web Research Adapter formalisieren (F17)
