"""LLM-as-Ranking-Judge — Vergleicht LLM-Relevanz-Bewertung mit Composite Score.

Nutzt ein LLM um Paper-Relevanz fuer eine Query auf einer Skala von 0-10 zu bewerten.
Ergebnis: Rank-Korrelation zwischen LLM-Urteil und heuristischem Score.
Hilft bei Ranking-Kalibrierung und Identifikation von Outliers.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence

import httpx

from pydantic import BaseModel, Field, computed_field

from src.agents.paper_ranker import UnifiedPaper
from src.utils.llm_client import LLMConfig, llm_complete, load_llm_config

logger = logging.getLogger(__name__)

_BATCH_SIZE = 10  # Max Papers pro LLM-Call


class JudgedPaper(BaseModel):
    """Paper mit LLM-Relevanz-Score."""

    paper_id: str
    title: str
    llm_score: float = Field(ge=0.0, le=10.0)
    reasoning: str = ""


class JudgementResult(BaseModel):
    """Gesamtergebnis: LLM-Urteile + Vergleich mit Heuristik."""

    query: str
    judged_papers: list[JudgedPaper] = Field(default_factory=list)
    heuristic_scores: dict[str, float] = Field(default_factory=dict)

    @computed_field
    @property
    def rank_correlation(self) -> float | None:
        """Spearman Rank-Korrelation zwischen LLM- und Heuristik-Ranking.

        None wenn weniger als 3 Papers (Korrelation nicht sinnvoll).
        """
        if len(self.judged_papers) < 3:
            return None

        # Manuelle Spearman-Berechnung (keine scipy-Dependency)
        llm_scores = [jp.llm_score for jp in self.judged_papers]
        heuristic = [self.heuristic_scores.get(jp.paper_id, 0.0) for jp in self.judged_papers]

        llm_ranks = _compute_ranks(llm_scores)
        heur_ranks = _compute_ranks(heuristic)

        n = len(llm_ranks)
        d_squared = sum((lr - hr) ** 2 for lr, hr in zip(llm_ranks, heur_ranks))
        # Spearman: 1 - (6 * sum(d^2)) / (n * (n^2 - 1))
        return round(1 - (6 * d_squared) / (n * (n**2 - 1)), 4)

    @computed_field
    @property
    def mean_score_delta(self) -> float:
        """Mittlere absolute Differenz zwischen LLM (normalisiert 0-1) und Heuristik."""
        if not self.judged_papers:
            return 0.0
        deltas = [
            abs(jp.llm_score / 10.0 - self.heuristic_scores.get(jp.paper_id, 0.0))
            for jp in self.judged_papers
        ]
        return round(sum(deltas) / len(deltas), 4)


def _compute_ranks(values: list[float]) -> list[float]:
    """Berechnet Raenge (1-basiert, Durchschnittsrang bei Gleichheit)."""
    indexed = sorted(enumerate(values), key=lambda x: x[1], reverse=True)
    ranks = [0.0] * len(values)

    i = 0
    while i < len(indexed):
        # Gruppe mit gleichem Wert finden
        j = i
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        # Durchschnittsrang fuer die Gruppe
        avg_rank = sum(range(i + 1, j + 1)) / (j - i)
        for k in range(i, j):
            ranks[indexed[k][0]] = avg_rank
        i = j

    return ranks


# --- Prompt-Building ---

_JUDGE_SYSTEM_PROMPT = """\
Du bist ein akademischer Relevanz-Bewerter. Bewerte wie relevant jedes Paper fuer die \
gegebene Forschungsfrage ist.

Antworte AUSSCHLIESSLICH als JSON:
{
  "judgements": [
    {"paper_id": "...", "score": 0-10, "reasoning": "Kurze Begruendung"}
  ]
}

Score-Skala:
- 0-2: Nicht relevant (anderes Thema, falsche Disziplin)
- 3-4: Marginal relevant (tangiert Thema, aber kein Kern-Beitrag)
- 5-6: Relevant (behandelt Thema, aber nicht zentral)
- 7-8: Sehr relevant (Kern-Beitrag zum Thema)
- 9-10: Hochrelevant (Schluesselarbeit, direkt zum Thema)

Keine Markdown-Formatierung, nur reines JSON."""


def _build_judge_prompt(query: str, papers: Sequence[UnifiedPaper]) -> str:
    """Baut User-Message fuer den Judge-Prompt."""
    lines = [f"Forschungsfrage: {query}\n", "Papers:\n"]
    for i, paper in enumerate(papers, 1):
        abstract_text = paper.abstract or "(Kein Abstract verfuegbar)"
        lines = [
            *lines,
            f"--- Paper {i} (ID: {paper.paper_id}) ---",
            f"Titel: {paper.title}",
            f"Abstract: {abstract_text}",
            f"Jahr: {paper.year or 'unbekannt'}",
            "",
        ]
    return "\n".join(lines)


def _parse_judge_response(
    raw: str,
    papers: Sequence[UnifiedPaper],
) -> list[JudgedPaper]:
    """Parst LLM-Antwort in JudgedPaper-Liste."""
    # Markdown-Wrapper entfernen
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Judge-JSON konnte nicht geparst werden: %s", raw[:80])
        return []

    # Valide Paper-IDs sammeln
    paper_map = {p.paper_id: p for p in papers}

    result: list[JudgedPaper] = []
    for item in data.get("judgements", []):
        pid = item.get("paper_id", "")
        if pid not in paper_map:
            continue
        try:
            score = float(item.get("score", 0))
        except (ValueError, TypeError):
            continue
        # Clamp auf 0-10
        score = max(0.0, min(10.0, score))
        result = [
            *result,
            JudgedPaper(
                paper_id=pid,
                title=paper_map[pid].title,
                llm_score=score,
                reasoning=item.get("reasoning", ""),
            ),
        ]

    return result


# --- Hauptfunktion ---


async def judge_relevance(
    query: str,
    papers: Sequence[UnifiedPaper],
    *,
    config: LLMConfig | None = None,
) -> JudgementResult:
    """Bewertet Paper-Relevanz via LLM und vergleicht mit heuristischem Score.

    Args:
        query: Forschungsfrage.
        papers: Liste der zu bewertenden Papers.
        config: LLM-Konfiguration (Default: aus Env-Vars).

    Returns:
        JudgementResult mit LLM-Scores, Heuristik-Scores und Korrelation.
    """
    if not papers:
        return JudgementResult(query=query)

    llm_config = config or load_llm_config()

    # Heuristik-Scores immer berechnen (auch bei LLM-Fehler)
    heuristic_scores = {p.paper_id: p.relevance_score for p in papers}

    # Batching: max _BATCH_SIZE Papers pro LLM-Call
    all_judged: list[JudgedPaper] = []
    for i in range(0, len(papers), _BATCH_SIZE):
        batch = list(papers[i : i + _BATCH_SIZE])
        try:
            user_msg = _build_judge_prompt(query, batch)
            raw = await llm_complete(
                _JUDGE_SYSTEM_PROMPT,
                user_msg,
                config=llm_config,
            )
            judged = _parse_judge_response(raw, batch)
            all_judged = [*all_judged, *judged]
        except (RuntimeError, httpx.HTTPError, json.JSONDecodeError, ValueError) as e:
            logger.warning("LLM-Judge-Fehler bei Batch %d: %s", i // _BATCH_SIZE + 1, e)

    return JudgementResult(
        query=query,
        judged_papers=all_judged,
        heuristic_scores=heuristic_scores,
    )
