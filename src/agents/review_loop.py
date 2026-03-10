"""Agentic Review Loop — iterative Draft-Verbesserung mit LLM-Review.

Flow: Draft → Kompakt-Review → Selektive Revision → Re-Review → Done
Konvergenz: Max 2 Revisionen, Score-Abbruch, Self-Consistency Probe.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, Field, computed_field

from src.agents.reviewer import Severity

logger = logging.getLogger(__name__)

# --- Config-Pfade ---

_SUB_QUESTIONS_PATH = (
    Path(__file__).resolve().parent.parent.parent / "config" / "dimensions" / "sub_questions.json"
)

_MAX_REVISIONS_CAP = 2  # Hart, nicht konfigurierbar ueber diesen Wert


# --- Pydantic-Modelle ---


class SubQuestion(BaseModel):
    """Konkrete Ja/Nein-Frage fuer eine Dimension."""

    dimension: str
    question: str
    weight: float = 1.0


class SubQuestionResult(BaseModel):
    """Antwort auf eine Sub-Frage."""

    question: SubQuestion
    answer: bool
    evidence: str = ""


class CompactIssue(BaseModel):
    """Actionable Issue fuer Revision — nur CRITICAL oder HIGH."""

    section: str
    problem: str
    suggestion: str
    severity: Severity


class CompactReview(BaseModel):
    """Kompakter Review — nur actionable Feedback."""

    issues: list[CompactIssue] = Field(default_factory=list)
    sub_question_results: list[SubQuestionResult] = Field(default_factory=list)
    score: int = 0
    iteration: int = 1

    @computed_field
    @property
    def has_blockers(self) -> bool:
        """True wenn CRITICAL Issues vorhanden."""
        return any(i.severity == Severity.CRITICAL for i in self.issues)


class RevisionChangelog(BaseModel):
    """Was wurde in einer Revision geaendert."""

    sections_modified: list[str] = Field(default_factory=list)
    changes: list[str] = Field(default_factory=list)
    issues_addressed: list[str] = Field(default_factory=list)


class ConsistencyResult(BaseModel):
    """Ergebnis der Self-Consistency Probe fuer eine Dimension."""

    dimension: str
    ratings: list[str] = Field(default_factory=list)
    agreement_pct: float = 0.0
    flagged_for_human: bool = False


class ReviseLoopResult(BaseModel):
    """Gesamtergebnis des Review-Loops."""

    final_draft_md: str
    iterations: int = 0
    reviews: list[CompactReview] = Field(default_factory=list)
    changelogs: list[RevisionChangelog] = Field(default_factory=list)
    consistency: list[ConsistencyResult] = Field(default_factory=list)
    aborted: bool = False
    abort_reason: str = ""


# --- Config laden ---


def load_sub_questions(path: Path | None = None) -> list[SubQuestion]:
    """Laedt Sub-Fragen aus config/dimensions/sub_questions.json."""
    config_path = path or _SUB_QUESTIONS_PATH
    if not config_path.exists():
        logger.warning("Sub-Fragen-Config nicht gefunden: %s — leere Liste", config_path)
        return []
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return [SubQuestion.model_validate(item) for item in data]
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Sub-Fragen-Config fehlerhaft: %s — leere Liste", e)
        return []


def compute_score(results: list[SubQuestionResult]) -> int:
    """Berechnet Score (0-50) aus gewichteten Sub-Fragen-Ergebnissen."""
    if not results:
        return 0
    total_weight = sum(r.question.weight for r in results)
    if total_weight == 0:
        return 0
    earned = sum(r.question.weight for r in results if r.answer)
    return round(earned / total_weight * 50)


def compute_agreement(ratings: list[str]) -> float:
    """Berechnet Agreement-Prozentsatz fuer eine Liste von Ratings."""
    if not ratings:
        return 0.0
    counter = Counter(ratings)
    most_common_count = counter.most_common(1)[0][1]
    return most_common_count / len(ratings) * 100


# --- LLM Prompts ---

_REVIEW_SYSTEM_PROMPT = """\
Du bist ein akademischer Reviewer. Bewerte den folgenden Text anhand der gegebenen Sub-Fragen.
Antworte AUSSCHLIESSLICH als JSON-Objekt mit zwei Keys:

{
  "sub_questions": [
    {"question": "...", "answer": true/false, "evidence": "Begruendung"}
  ],
  "issues": [
    {"section": "Sektionsname", "problem": "...", "suggestion": "...", "severity": "CRITICAL|HIGH"}
  ]
}

REGELN:
- Nur Issues mit Severity CRITICAL oder HIGH melden
- Nur Dimensionen bewerten die in den Sub-Fragen genannt werden
- Jedes Issue braucht einen konkreten Verbesserungsvorschlag
- Keine Markdown-Formatierung, nur reines JSON"""

_REVISE_SYSTEM_PROMPT = """\
Du bist ein akademischer Editor. Ueberarbeite den Text basierend auf den genannten Issues.

REGELN:
- NUR die genannten Sektionen ueberarbeiten
- Andere Teile UNVERAENDERT lassen
- Stil und Zitierweise beibehalten
- Am Ende des Textes: JSON-Block mit Changelog:
```json
{"sections_modified": ["..."], "changes": ["..."], "issues_addressed": ["..."]}
```"""


# --- Kern-Funktionen ---


async def review_for_revision(
    draft_md: str,
    sub_questions: list[SubQuestion],
    *,
    config: object | None = None,
    temperature: float | None = None,
) -> CompactReview:
    """LLM-basierter Kompakt-Review mit Sub-Fragen.

    Bewertet nur automatable Dimensionen. Gibt Score + actionable Issues zurueck.
    """
    from src.utils.llm_client import LLMConfig, llm_complete, load_llm_config

    llm_config = config if isinstance(config, LLMConfig) else load_llm_config()

    if temperature is not None:
        llm_config = LLMConfig(
            base_url=llm_config.base_url,
            api_key=llm_config.api_key,
            model=llm_config.model,
            timeout_s=llm_config.timeout_s,
            max_tokens=llm_config.max_tokens,
            temperature=temperature,
        )

    questions_json = json.dumps(
        [{"dimension": q.dimension, "question": q.question} for q in sub_questions],
        ensure_ascii=False,
    )
    user_msg = f"Sub-Fragen:\n{questions_json}\n\n---\n\nText:\n{draft_md}"

    raw = await llm_complete(_REVIEW_SYSTEM_PROMPT, user_msg, config=llm_config)

    return _parse_review_response(raw, sub_questions)


def _parse_review_response(raw: str, sub_questions: list[SubQuestion]) -> CompactReview:
    """Parst LLM-Antwort in CompactReview."""
    try:
        # JSON aus Antwort extrahieren (kann in Markdown-Block stehen)
        json_str = raw.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()
        data = json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        preview = raw[:200] if raw else "(leer)"
        logger.warning("Review-JSON konnte nicht geparst werden: %s", preview)
        return CompactReview(score=0)

    # Sub-Fragen-Ergebnisse parsen
    sq_map = {q.question: q for q in sub_questions}
    sq_results: list[SubQuestionResult] = []
    for item in data.get("sub_questions", []):
        question_text = item.get("question", "")
        matched_q = sq_map.get(question_text)
        if matched_q:
            sq_results = [
                *sq_results,
                SubQuestionResult(
                    question=matched_q,
                    answer=bool(item.get("answer", False)),
                    evidence=item.get("evidence", ""),
                ),
            ]

    # Issues parsen
    issues: list[CompactIssue] = []
    for item in data.get("issues", []):
        severity_str = item.get("severity", "HIGH").upper()
        if severity_str not in ("CRITICAL", "HIGH"):
            continue
        issues = [
            *issues,
            CompactIssue(
                section=item.get("section", ""),
                problem=item.get("problem", ""),
                suggestion=item.get("suggestion", ""),
                severity=Severity(severity_str),
            ),
        ]

    score = compute_score(sq_results)
    return CompactReview(
        issues=issues,
        sub_question_results=sq_results,
        score=score,
    )


async def revise_draft(
    draft_md: str,
    issues: list[CompactIssue],
    *,
    config: object | None = None,
) -> tuple[str, RevisionChangelog]:
    """LLM ueberarbeitet nur betroffene Sektionen. Immutable — neuer String."""
    if not issues:
        return draft_md, RevisionChangelog()

    from src.utils.llm_client import LLMConfig, llm_complete, load_llm_config

    llm_config = config if isinstance(config, LLMConfig) else load_llm_config()

    issues_json = json.dumps(
        [{"section": i.section, "problem": i.problem, "suggestion": i.suggestion} for i in issues],
        ensure_ascii=False,
    )
    user_msg = f"Issues:\n{issues_json}\n\n---\n\nText:\n{draft_md}"

    raw = await llm_complete(_REVISE_SYSTEM_PROMPT, user_msg, config=llm_config)

    return _parse_revision_response(raw)


def _parse_revision_response(raw: str) -> tuple[str, RevisionChangelog]:
    """Extrahiert revidierten Text und Changelog aus LLM-Antwort."""
    changelog = RevisionChangelog()

    # Changelog-JSON am Ende extrahieren
    if "```json" in raw:
        parts = raw.rsplit("```json", 1)
        text_part = parts[0].strip()
        try:
            json_str = parts[1].split("```")[0].strip()
            cl_data = json.loads(json_str)
            changelog = RevisionChangelog(
                sections_modified=cl_data.get("sections_modified", []),
                changes=cl_data.get("changes", []),
                issues_addressed=cl_data.get("issues_addressed", []),
            )
        except (json.JSONDecodeError, IndexError):
            logger.warning("Revision-Changelog konnte nicht geparst werden")
            text_part = raw
    else:
        text_part = raw

    return text_part, changelog


async def self_consistency_probe(
    draft_md: str,
    sub_questions: list[SubQuestion],
    *,
    config: object | None = None,
) -> list[ConsistencyResult]:
    """3x Review mit T=0.3/0.7/1.0, Agreement pro Dimension messen."""
    temperatures = [0.3, 0.7, 1.0]
    reviews: list[CompactReview] = []

    for temp in temperatures:
        review = await review_for_revision(
            draft_md, sub_questions, config=config, temperature=temp
        )
        reviews = [*reviews, review]

    # Agreement pro Dimension berechnen
    dimensions = {q.dimension for q in sub_questions}
    results: list[ConsistencyResult] = []

    for dim in sorted(dimensions):
        ratings: list[str] = []
        for review in reviews:
            dim_results = [r for r in review.sub_question_results if r.question.dimension == dim]
            # Aggregiere: Mehrheit True → "erfuellt", sonst "nicht_erfuellt"
            if dim_results:
                fulfilled = sum(1 for r in dim_results if r.answer)
                rating = "erfuellt" if fulfilled > len(dim_results) / 2 else "nicht_erfuellt"
            else:
                rating = "keine_daten"
            ratings = [*ratings, rating]

        agreement = compute_agreement(ratings)
        results = [
            *results,
            ConsistencyResult(
                dimension=dim,
                ratings=ratings,
                agreement_pct=agreement,
                flagged_for_human=agreement < 60.0,
            ),
        ]

    return results


async def run_revise_loop(
    draft_md: str,
    sub_questions: list[SubQuestion],
    *,
    max_revisions: int = 2,
    score_threshold: int = 35,
    config: object | None = None,
    provenance: object | None = None,
) -> ReviseLoopResult:
    """Hauptfunktion: Review → Score-Check → Revise → Re-Review Loop.

    Konvergenz-Kriterien:
    - Max 2 Revisionen (hart)
    - Score sinkt → sofortiger Abbruch
    - Keine CRITICAL/HIGH Issues → Stop
    - Score >= score_threshold und kein Blocker → Stop
    """
    effective_max = min(max_revisions, _MAX_REVISIONS_CAP)
    result = ReviseLoopResult(final_draft_md=draft_md)
    current_md = draft_md
    prev_score = -1

    for i in range(effective_max):
        # 1. Review
        review = await review_for_revision(current_md, sub_questions, config=config)
        review = CompactReview(
            issues=review.issues,
            sub_question_results=review.sub_question_results,
            score=review.score,
            iteration=i + 1,
        )
        result.reviews = [*result.reviews, review]

        # 2. Provenance loggen
        if provenance is not None:
            provenance.log_action(
                phase="synthesis",
                agent="review-loop",
                action="REVIEW_COMPLETED",
                metadata={
                    "iteration": i + 1,
                    "score": review.score,
                    "issues_count": len(review.issues),
                    "has_blockers": review.has_blockers,
                },
            )

        # 3. Konvergenz pruefen
        if not review.issues:
            logger.info("Iteration %d: Keine Issues — Loop beendet", i + 1)
            break

        if review.score >= score_threshold and not review.has_blockers:
            logger.info(
                "Iteration %d: Score %d >= %d — Loop beendet",
                i + 1, review.score, score_threshold,
            )
            break

        if prev_score > 0 and review.score <= prev_score:
            result.aborted = True
            result.abort_reason = (
                f"Score nicht verbessert: {prev_score} -> {review.score}"
            )
            logger.warning("Iteration %d: %s — Abbruch", i + 1, result.abort_reason)
            if provenance is not None:
                provenance.log_action(
                    phase="synthesis",
                    agent="review-loop",
                    action="LOOP_ABORTED",
                    metadata={"reason": result.abort_reason},
                )
            break

        prev_score = review.score

        # 4. Revision
        new_md, changelog = await revise_draft(current_md, review.issues, config=config)
        result.changelogs = [*result.changelogs, changelog]
        current_md = new_md
        result.iterations += 1

        if provenance is not None:
            provenance.log_action(
                phase="synthesis",
                agent="review-loop",
                action="REVISION_APPLIED",
                metadata={
                    "iteration": i + 1,
                    "sections_modified": changelog.sections_modified,
                    "changes_count": len(changelog.changes),
                },
            )

    # 5. Self-Consistency bei Borderline
    final_review = result.reviews[-1] if result.reviews else None
    if final_review and 30 <= final_review.score <= 40:
        logger.info("Borderline-Score %d — starte Self-Consistency Probe", final_review.score)
        consistency = await self_consistency_probe(current_md, sub_questions, config=config)
        result.consistency = consistency

        if provenance is not None:
            flagged = [c.dimension for c in consistency if c.flagged_for_human]
            provenance.log_action(
                phase="synthesis",
                agent="review-loop",
                action="CONSISTENCY_CHECK",
                metadata={
                    "flagged_dimensions": flagged,
                    "agreements": {c.dimension: c.agreement_pct for c in consistency},
                },
            )

    result.final_draft_md = current_md
    return result
