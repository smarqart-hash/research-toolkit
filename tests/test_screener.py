"""Tests fuer den Screening-Schritt."""

from __future__ import annotations

import pytest

from src.agents.paper_ranker import UnifiedPaper
from src.agents.screener import (
    PrismaFlow,
    ScreeningCriteria,
    ScreeningDecision,
    ScreeningResult,
    screen_papers,
)


# --- Factories ---


def _paper(
    *,
    paper_id: str = "p1",
    title: str = "Test Paper",
    abstract: str | None = "Ein Abstract.",
    year: int | None = 2024,
    citation_count: int | None = 10,
    source: str = "semantic_scholar",
    tags: list[str] | None = None,
    doi: str | None = None,
) -> UnifiedPaper:
    return UnifiedPaper(
        paper_id=paper_id,
        title=title,
        abstract=abstract,
        year=year,
        citation_count=citation_count,
        source=source,
        tags=tags or [],
        doi=doi,
    )


# --- Tests: Keine Kriterien ---


class TestScreenNoCriteria:
    def test_empty_criteria_includes_all(self):
        papers = [_paper(paper_id="p1"), _paper(paper_id="p2")]
        result = screen_papers(papers, ScreeningCriteria())
        assert len(result.included) == 2
        assert len(result.excluded) == 0

    def test_empty_papers_returns_empty(self):
        result = screen_papers([], ScreeningCriteria())
        assert len(result.included) == 0
        assert result.prisma_flow.screened == 0


# --- Tests: Einzelne Kriterien ---


class TestScreenMinYear:
    def test_excludes_old_papers(self):
        papers = [_paper(paper_id="old", year=2019), _paper(paper_id="new", year=2023)]
        result = screen_papers(papers, ScreeningCriteria(min_year=2020))
        assert len(result.included) == 1
        assert result.included[0].paper_id == "new"

    def test_includes_papers_at_boundary(self):
        papers = [_paper(paper_id="boundary", year=2020)]
        result = screen_papers(papers, ScreeningCriteria(min_year=2020))
        assert len(result.included) == 1

    def test_papers_without_year_excluded(self):
        papers = [_paper(paper_id="no_year", year=None)]
        result = screen_papers(papers, ScreeningCriteria(min_year=2020))
        assert len(result.included) == 0


class TestScreenMaxYear:
    def test_excludes_future_papers(self):
        papers = [_paper(paper_id="p1", year=2025), _paper(paper_id="p2", year=2027)]
        result = screen_papers(papers, ScreeningCriteria(max_year=2026))
        assert len(result.included) == 1
        assert result.included[0].paper_id == "p1"


class TestScreenRequireAbstract:
    def test_excludes_papers_without_abstract(self):
        papers = [
            _paper(paper_id="with", abstract="Exists"),
            _paper(paper_id="without", abstract=None),
            _paper(paper_id="empty", abstract=""),
        ]
        result = screen_papers(papers, ScreeningCriteria(require_abstract=True))
        assert len(result.included) == 1
        assert result.included[0].paper_id == "with"


class TestScreenMinCitations:
    def test_excludes_low_citation_papers(self):
        papers = [
            _paper(paper_id="high", citation_count=50),
            _paper(paper_id="low", citation_count=2),
            _paper(paper_id="none", citation_count=None),
        ]
        result = screen_papers(papers, ScreeningCriteria(min_citation_count=10))
        assert len(result.included) == 1
        assert result.included[0].paper_id == "high"


class TestScreenExcludeFields:
    def test_excludes_matching_fields(self):
        papers = [
            _paper(paper_id="cs", tags=["Computer Science"]),
            _paper(paper_id="bio", tags=["Biology", "Medicine"]),
            _paper(paper_id="mixed", tags=["Computer Science", "Biology"]),
        ]
        result = screen_papers(papers, ScreeningCriteria(exclude_fields=["Biology"]))
        assert len(result.included) == 1
        assert result.included[0].paper_id == "cs"

    def test_case_insensitive(self):
        papers = [_paper(paper_id="bio", tags=["biology"])]
        result = screen_papers(papers, ScreeningCriteria(exclude_fields=["Biology"]))
        assert len(result.included) == 0

    def test_papers_without_tags_included(self):
        papers = [_paper(paper_id="no_tags", tags=[])]
        result = screen_papers(papers, ScreeningCriteria(exclude_fields=["Biology"]))
        assert len(result.included) == 1


class TestScreenKeywords:
    def test_include_keywords_in_title(self):
        papers = [
            _paper(paper_id="match", title="Deep Learning for NLP"),
            _paper(paper_id="no_match", title="Protein Folding Analysis"),
        ]
        result = screen_papers(papers, ScreeningCriteria(include_keywords=["deep learning"]))
        assert len(result.included) == 1
        assert result.included[0].paper_id == "match"

    def test_include_keywords_in_abstract(self):
        papers = [
            _paper(paper_id="p1", title="Generic", abstract="Uses deep learning methods"),
        ]
        result = screen_papers(papers, ScreeningCriteria(include_keywords=["deep learning"]))
        assert len(result.included) == 1

    def test_exclude_keywords(self):
        papers = [
            _paper(paper_id="ok", title="AI Research Automation"),
            _paper(paper_id="bad", title="Protein Folding with AI"),
        ]
        result = screen_papers(papers, ScreeningCriteria(exclude_keywords=["protein"]))
        assert len(result.included) == 1
        assert result.included[0].paper_id == "ok"

    def test_keywords_case_insensitive(self):
        papers = [_paper(paper_id="p1", title="DEEP LEARNING")]
        result = screen_papers(papers, ScreeningCriteria(include_keywords=["deep learning"]))
        assert len(result.included) == 1


# --- Tests: Kombinierte Kriterien ---


class TestScreenCombined:
    def test_multiple_criteria_all_applied(self):
        papers = [
            _paper(paper_id="perfect", year=2023, abstract="AI text", citation_count=20),
            _paper(paper_id="old", year=2018, abstract="AI text", citation_count=20),
            _paper(paper_id="no_abstract", year=2023, abstract=None, citation_count=20),
            _paper(paper_id="low_cite", year=2023, abstract="AI text", citation_count=1),
        ]
        criteria = ScreeningCriteria(
            min_year=2020,
            require_abstract=True,
            min_citation_count=5,
        )
        result = screen_papers(papers, criteria)
        assert len(result.included) == 1
        assert result.included[0].paper_id == "perfect"
        assert len(result.excluded) == 3


# --- Tests: PRISMA Flow ---


class TestPrismaFlow:
    def test_counts_correct(self):
        papers = [
            _paper(paper_id="p1", year=2023),
            _paper(paper_id="p2", year=2019),
            _paper(paper_id="p3", year=2024),
        ]
        result = screen_papers(papers, ScreeningCriteria(min_year=2020))
        flow = result.prisma_flow
        assert flow.screened == 3
        assert flow.included == 2
        assert flow.excluded == 1

    def test_exclusion_reasons_counted(self):
        papers = [
            _paper(paper_id="p1", year=2019),
            _paper(paper_id="p2", abstract=None),
            _paper(paper_id="p3", year=2018),
        ]
        criteria = ScreeningCriteria(min_year=2020, require_abstract=True)
        result = screen_papers(papers, criteria)
        flow = result.prisma_flow
        assert flow.exclusion_reasons.get("min_year", 0) >= 2
        assert flow.excluded == 3


# --- Tests: Screening Decisions ---


class TestScreeningDecisions:
    def test_every_exclusion_has_reason(self):
        papers = [_paper(paper_id="p1", year=2019)]
        result = screen_papers(papers, ScreeningCriteria(min_year=2020))
        assert len(result.excluded) == 1
        decision = result.excluded[0]
        assert decision.paper_id == "p1"
        assert decision.included is False
        assert "min_year" in decision.reason

    def test_decisions_are_screening_decision_type(self):
        papers = [_paper(paper_id="p1", abstract=None)]
        result = screen_papers(papers, ScreeningCriteria(require_abstract=True))
        assert all(isinstance(d, ScreeningDecision) for d in result.excluded)
