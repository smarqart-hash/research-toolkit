"""Paper-Screening mit konfigurierbaren Inclusion/Exclusion-Kriterien.

Wendet nach Ranking einen expliziten Screening-Schritt an und erzeugt
eine PRISMA-Flow-Statistik. Jede Entscheidung wird protokolliert.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, Field

from src.agents.paper_ranker import UnifiedPaper


class ScreeningCriteria(BaseModel):
    """Konfigurierbare Inclusion/Exclusion-Kriterien."""

    min_year: int | None = None
    max_year: int | None = None
    require_abstract: bool = False
    min_citation_count: int | None = None
    exclude_fields: list[str] = Field(default_factory=list)
    include_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)


class ScreeningDecision(BaseModel):
    """Einzelne Screening-Entscheidung (fuer Provenance)."""

    paper_id: str
    included: bool
    reason: str


class PrismaFlow(BaseModel):
    """PRISMA-Flow-Statistik."""

    identified: int = 0
    after_dedup: int = 0
    after_ranking: int = 0
    screened: int = 0
    included: int = 0
    excluded: int = 0
    exclusion_reasons: dict[str, int] = Field(default_factory=dict)


class ScreeningResult(BaseModel):
    """Ergebnis des Screening-Schritts."""

    included: list[UnifiedPaper] = Field(default_factory=list)
    excluded: list[ScreeningDecision] = Field(default_factory=list)
    prisma_flow: PrismaFlow = Field(default_factory=PrismaFlow)


def _check_paper(
    paper: UnifiedPaper,
    criteria: ScreeningCriteria,
) -> str | None:
    """Prueft ein Paper gegen alle Kriterien.

    Returns:
        Exclusion-Grund als String, oder None wenn inkludiert.
    """
    # Jahresfilter
    if criteria.min_year is not None:
        if paper.year is None or paper.year < criteria.min_year:
            return "min_year"

    if criteria.max_year is not None:
        if paper.year is None or paper.year > criteria.max_year:
            return "max_year"

    # Abstract erforderlich
    if criteria.require_abstract:
        if not paper.abstract or not paper.abstract.strip():
            return "no_abstract"

    # Mindest-Zitationen
    if criteria.min_citation_count is not None:
        if paper.citation_count is None or paper.citation_count < criteria.min_citation_count:
            return "low_citations"

    # Fachgebiete ausschliessen
    if criteria.exclude_fields:
        excluded_lower = [f.lower() for f in criteria.exclude_fields]
        for tag in paper.tags:
            if tag.lower() in excluded_lower:
                return f"field_mismatch:{tag}"

    # Include-Keywords (mindestens 1 muss matchen)
    if criteria.include_keywords:
        searchable = f"{paper.title} {paper.abstract or ''}".lower()
        if not any(kw.lower() in searchable for kw in criteria.include_keywords):
            return "keyword_not_found"

    # Exclude-Keywords
    if criteria.exclude_keywords:
        searchable = f"{paper.title} {paper.abstract or ''}".lower()
        for kw in criteria.exclude_keywords:
            if kw.lower() in searchable:
                return f"excluded_keyword:{kw}"

    return None


def screen_papers(
    papers: Sequence[UnifiedPaper],
    criteria: ScreeningCriteria,
) -> ScreeningResult:
    """Wendet Inclusion/Exclusion-Kriterien an.

    Jede Entscheidung wird als ScreeningDecision protokolliert.
    """
    included: list[UnifiedPaper] = []
    excluded: list[ScreeningDecision] = []
    exclusion_reasons: dict[str, int] = {}

    for paper in papers:
        reason = _check_paper(paper, criteria)
        if reason is None:
            included = [*included, paper]
        else:
            excluded = [*excluded, ScreeningDecision(
                paper_id=paper.paper_id,
                included=False,
                reason=reason,
            )]
            # Zaehle Gruende (ohne Detail nach Doppelpunkt)
            reason_key = reason.split(":")[0]
            exclusion_reasons = {
                **exclusion_reasons,
                reason_key: exclusion_reasons.get(reason_key, 0) + 1,
            }

    prisma_flow = PrismaFlow(
        screened=len(papers),
        included=len(included),
        excluded=len(excluded),
        exclusion_reasons=exclusion_reasons,
    )

    return ScreeningResult(
        included=included,
        excluded=excluded,
        prisma_flow=prisma_flow,
    )
