# Design: Agentic Review Loop (003)

## Datenfluss

```
DraftResult
    │
    ▼
review_for_revision(draft, rubric, sub_questions)
    │  LLM: "Bewerte mit Sub-Fragen, nur automatable Dimensionen"
    ▼
CompactReview (CRITICAL + HIGH Issues only)
    │
    ├── Score >= 35/50 oder 0 Issues → DONE
    ├── Score sinkt vs. vorherige Runde → ABORT
    │
    ▼
revise_draft(draft_md, compact_issues)
    │  LLM: "Ueberarbeite NUR diese Sektionen"
    ▼
RevisedDraft + RevisionChangelog
    │
    ▼
Re-Review (max 2 Runden)
    │
    ├── Borderline (30-40/50) → self_consistency_probe()
    │       3x Review mit T=0.3/0.7/1.0
    │       Agreement < 60% → requires_human Flag
    │
    ▼
Finaler DraftResult + ReviewResult + Provenance
```

## Neue Pydantic-Modelle

### `src/agents/review_loop.py` (NEUES Modul — ~250 Zeilen)

```python
class SubQuestion(BaseModel):
    """Konkrete Ja/Nein-Frage fuer eine Dimension."""
    dimension: str
    question: str          # z.B. "Jeder Claim hat min. 1 Zitat?"
    weight: float = 1.0    # Gewicht fuer Score-Berechnung

class SubQuestionResult(BaseModel):
    """Antwort auf eine Sub-Frage."""
    question: SubQuestion
    answer: bool           # True = erfuellt
    evidence: str = ""     # Begruendung

class CompactIssue(BaseModel):
    """Actionable Issue fuer Revision."""
    section: str           # Betroffene Sektion
    problem: str           # Was ist falsch
    suggestion: str        # Konkreter Fix-Vorschlag
    severity: Severity     # Nur CRITICAL oder HIGH

class CompactReview(BaseModel):
    """Kompakter Review — nur actionable Feedback."""
    issues: list[CompactIssue] = Field(default_factory=list)
    sub_question_results: list[SubQuestionResult] = Field(default_factory=list)
    score: int = 0         # 0-50, berechnet aus Sub-Fragen
    iteration: int = 1

    @computed_field
    @property
    def has_blockers(self) -> bool:
        return any(i.severity == Severity.CRITICAL for i in self.issues)

class RevisionChangelog(BaseModel):
    """Was wurde in einer Revision geaendert."""
    sections_modified: list[str] = Field(default_factory=list)
    changes: list[str] = Field(default_factory=list)  # "Sektion X: Zitat ergaenzt"
    issues_addressed: list[str] = Field(default_factory=list)  # Issue-Beschreibungen

class ConsistencyResult(BaseModel):
    """Ergebnis der Self-Consistency Probe."""
    dimension: str
    ratings: list[str]          # z.B. ["stark", "angemessen", "stark"]
    agreement_pct: float        # 0-100
    flagged_for_human: bool     # True wenn agreement < 60%

class ReviseLoopResult(BaseModel):
    """Gesamtergebnis des Review-Loops."""
    final_draft_md: str
    iterations: int = 0
    reviews: list[CompactReview] = Field(default_factory=list)
    changelogs: list[RevisionChangelog] = Field(default_factory=list)
    consistency: list[ConsistencyResult] = Field(default_factory=list)
    aborted: bool = False
    abort_reason: str = ""
```

## Funktionen in `review_loop.py`

```python
# --- Config ---
def load_sub_questions(path: Path | None = None) -> list[SubQuestion]:
    """Laedt Sub-Fragen aus config/dimensions/sub_questions.json."""

# --- FA-1: Kompakt-Review ---
async def review_for_revision(
    draft_md: str,
    sub_questions: list[SubQuestion],
    *,
    config: LLMConfig | None = None,
) -> CompactReview:
    """LLM-basierter Review mit Sub-Fragen. Nur automatable Dimensionen."""

# --- FA-2: Selektive Revision ---
async def revise_draft(
    draft_md: str,
    issues: list[CompactIssue],
    *,
    config: LLMConfig | None = None,
) -> tuple[str, RevisionChangelog]:
    """LLM ueberarbeitet nur betroffene Sektionen. Returns (new_md, changelog)."""

# --- FA-3: Orchestrierung ---
async def run_revise_loop(
    draft_md: str,
    sub_questions: list[SubQuestion],
    *,
    max_revisions: int = 2,
    score_threshold: int = 35,
    config: LLMConfig | None = None,
    provenance: ProvenanceLogger | None = None,
) -> ReviseLoopResult:
    """Hauptfunktion: Review → Revise → Re-Review Loop."""

# --- FA-4: Self-Consistency ---
async def self_consistency_probe(
    draft_md: str,
    sub_questions: list[SubQuestion],
    *,
    config: LLMConfig | None = None,
) -> list[ConsistencyResult]:
    """3x Review mit T=0.3/0.7/1.0, Agreement messen."""
```

## `run_revise_loop()` Algorithmus

```python
async def run_revise_loop(...) -> ReviseLoopResult:
    result = ReviseLoopResult(final_draft_md=draft_md)
    current_md = draft_md
    prev_score = -1

    for i in range(max_revisions):
        # 1. Review
        review = await review_for_revision(current_md, sub_questions, config=config)
        result.reviews = [*result.reviews, review]

        # 2. Provenance loggen
        if provenance:
            provenance.log_action(
                phase="synthesis", agent="review-loop",
                action="REVIEW_COMPLETED",
                metadata={"iteration": i + 1, "score": review.score, "issues": len(review.issues)},
            )

        # 3. Konvergenz pruefen
        if not review.issues:
            break  # Keine Issues → fertig

        if review.score >= score_threshold and not review.has_blockers:
            break  # Score gut genug

        if prev_score > 0 and review.score <= prev_score:
            result.aborted = True
            result.abort_reason = f"Score nicht verbessert: {prev_score} → {review.score}"
            break

        prev_score = review.score

        # 4. Revision
        new_md, changelog = await revise_draft(current_md, review.issues, config=config)
        result.changelogs = [*result.changelogs, changelog]
        current_md = new_md
        result.iterations += 1

    # 5. Self-Consistency bei Borderline
    final_review = result.reviews[-1] if result.reviews else None
    if final_review and 30 <= final_review.score <= 40:
        consistency = await self_consistency_probe(current_md, sub_questions, config=config)
        result.consistency = consistency

    result.final_draft_md = current_md
    return result
```

## Sub-Fragen Config

**`config/dimensions/sub_questions.json`**:
```json
[
  {"dimension": "Evidence", "question": "Jeder faktische Claim hat mindestens 1 Quellenbeleg?", "weight": 2.0},
  {"dimension": "Evidence", "question": "Zitate sind korrekt formatiert (Autor Jahr)?", "weight": 1.0},
  {"dimension": "Structure", "question": "Jede Sektion hat eine klare These/Argument?", "weight": 1.5},
  {"dimension": "Structure", "question": "Uebergaenge zwischen Sektionen sind logisch?", "weight": 1.0},
  {"dimension": "Clarity", "question": "Keine Saetze ueber 40 Woerter?", "weight": 1.0},
  {"dimension": "Clarity", "question": "Fachbegriffe werden bei Erstnennung erklaert?", "weight": 1.0},
  {"dimension": "Logic", "question": "Schlussfolgerungen folgen aus den praemstierten Daten?", "weight": 2.0},
  {"dimension": "Context", "question": "Gegenposition/Limitationen werden adressiert?", "weight": 1.5},
  {"dimension": "Format", "question": "Venue-spezifische Formatvorgaben eingehalten?", "weight": 1.0}
]
```

Score-Berechnung: `sum(weight if answer else 0) / sum(weight) * 50`
→ ergibt 0-50 Punkte, kompatibel mit Score-Schwelle 35/50.

## LLM Prompts

### Review-Prompt (FA-1)
```
System: Du bist ein akademischer Reviewer. Bewerte den folgenden Text
anhand der gegebenen Sub-Fragen. Antworte als JSON.

Fuer jede Sub-Frage: {"question": "...", "answer": true/false, "evidence": "..."}
Fuer jedes Issue (nur CRITICAL/HIGH): {"section": "...", "problem": "...", "suggestion": "...", "severity": "CRITICAL|HIGH"}

WICHTIG: Nur Dimensionen bewerten wo automatable=true.
```

### Revision-Prompt (FA-2)
```
System: Du bist ein akademischer Editor. Ueberarbeite NUR die genannten Sektionen.
Aendere NICHTS an anderen Teilen. Behalte Stil und Zitierweise bei.

Issues:
{json_issues}

Antworte mit dem vollstaendigen ueberarbeiteten Text.
Am Ende: JSON-Changelog: {"sections_modified": [...], "changes": [...]}
```

## State Machine Erweiterung (FA-6)

```python
# In state.py — neues Enum
class SynthesisSubPhase(str, Enum):
    DRAFTING = "drafting"
    REVIEWING = "reviewing"
    REVISING = "revising"
    CONSISTENCY_CHECK = "consistency_check"
    COMPLETED = "completed"

# PhaseRecord bekommt optionales Feld
class PhaseRecord(BaseModel):
    ...
    sub_phase: str | None = None  # Nur fuer SYNTHESIS relevant
```

## CLI Erweiterung (FA-7)

```python
# In cli.py — draft command erweitern
@app.command()
def draft(
    ...
    revise: bool = typer.Option(False, "--revise", help="Review-Loop nach Draft"),
    max_revisions: int = typer.Option(2, "--max-revisions", help="Max Revisionen (1-2)"),
):
    ...
    if revise:
        from src.agents.review_loop import run_revise_loop, load_sub_questions
        sub_questions = load_sub_questions()
        loop_result = asyncio.run(
            run_revise_loop(draft_md, sub_questions, max_revisions=min(max_revisions, 2))
        )
        # Output speichern + Rich-Tabelle anzeigen
```

## Dateien-Uebersicht

| Datei | Aktion | Zeilen (ca.) |
|-------|--------|-------------|
| `src/agents/review_loop.py` | NEU | ~250 |
| `config/dimensions/sub_questions.json` | NEU | ~20 |
| `src/pipeline/state.py` | EDIT | +10 |
| `cli.py` | EDIT | +25 |
| `tests/test_review_loop.py` | NEU | ~300 |

## Adversarial Check

1. **Annahme: LLM kann selektiv revidieren** — Risiko: LLM schreibt ganzen Text um.
   Mitigation: Prompt explizit "NUR genannte Sektionen", Changelog-Validation.

2. **Einfachere Alternative?** — Ohne Self-Consistency (FA-4) waere 80% des Werts da.
   Aber: Self-Enhancement Bias ist das Kernproblem. FA-4 bleibt, nur bei Borderline.

3. **Integration:** Alles additiv, kein Breaking Change. `review_loop.py` ist eigenstaendig,
   importiert nur aus bestehenden Modulen.
