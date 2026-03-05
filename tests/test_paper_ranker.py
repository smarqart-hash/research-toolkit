"""Tests fuer Paper-Deduplizierung und Ranking."""

from src.agents.exa_client import ExaResult
from src.agents.paper_ranker import (
    UnifiedPaper,
    deduplicate,
    from_exa,
    from_semantic_scholar,
    rank_papers,
)
from src.agents.semantic_scholar import Author, ExternalIds, PaperResult


# --- Fixtures ---


def _ss_paper(
    paper_id: str = "abc123",
    title: str = "Test Paper",
    doi: str | None = "10.1234/test",
    year: int | None = 2024,
    citation_count: int = 50,
    is_open_access: bool = True,
) -> PaperResult:
    return PaperResult(
        paperId=paper_id,
        title=title,
        abstract="Ein Abstract.",
        year=year,
        authors=[Author(authorId="a1", name="Max Mustermann")],
        citationCount=citation_count,
        externalIds=ExternalIds(DOI=doi) if doi else None,
        isOpenAccess=is_open_access,
        fieldsOfStudy=["Computer Science"],
    )


def _exa_result(
    url: str = "https://example.com/paper",
    title: str = "Exa Paper",
    published_date: str | None = "2024-06-15",
) -> ExaResult:
    return ExaResult(
        url=url,
        title=title,
        text="Kurztext des Papers.",
        published_date=published_date,
        author="Anna Autorin",
    )


# --- Konvertierung ---


class TestFromSemanticScholar:
    def test_basic_conversion(self):
        paper = _ss_paper()
        unified = from_semantic_scholar(paper)
        assert unified.title == "Test Paper"
        assert unified.doi == "10.1234/test"
        assert unified.source == "semantic_scholar"
        assert unified.authors == ["Max Mustermann"]
        assert unified.year == 2024
        assert unified.citation_count == 50
        assert unified.is_open_access is True

    def test_without_doi(self):
        paper = _ss_paper(doi=None)
        unified = from_semantic_scholar(paper)
        assert unified.paper_id == "abc123"
        assert unified.doi is None

    def test_with_doi_uses_doi_as_id(self):
        paper = _ss_paper(doi="10.1234/test")
        unified = from_semantic_scholar(paper)
        assert unified.paper_id == "10.1234/test"


class TestFromExa:
    def test_basic_conversion(self):
        result = _exa_result()
        unified = from_exa(result)
        assert unified.title == "Exa Paper"
        assert unified.source == "exa"
        assert unified.authors == ["Anna Autorin"]
        assert unified.year == 2024

    def test_without_date(self):
        result = _exa_result(published_date=None)
        unified = from_exa(result)
        assert unified.year is None

    def test_without_author(self):
        result = ExaResult(url="https://example.com", title="No Author")
        unified = from_exa(result)
        assert unified.authors == []


# --- Dedup-Key ---


class TestDedupKey:
    def test_doi_based_key(self):
        paper = UnifiedPaper(
            paper_id="x", title="Test", source="semantic_scholar", doi="10.1234/ABC"
        )
        assert paper.dedup_key == "doi:10.1234/abc"

    def test_title_based_key_without_doi(self):
        paper = UnifiedPaper(paper_id="x", title="Test Paper", source="exa")
        assert paper.dedup_key.startswith("title:")

    def test_same_title_same_key(self):
        p1 = UnifiedPaper(paper_id="x", title="Machine Learning", source="exa")
        p2 = UnifiedPaper(paper_id="y", title="Machine Learning", source="semantic_scholar")
        assert p1.dedup_key == p2.dedup_key

    def test_normalized_title_matching(self):
        p1 = UnifiedPaper(paper_id="x", title="Machine  Learning!", source="exa")
        p2 = UnifiedPaper(paper_id="y", title="machine learning", source="exa")
        assert p1.dedup_key == p2.dedup_key


# --- Deduplizierung ---


class TestDeduplicate:
    def test_no_duplicates(self):
        papers = [
            UnifiedPaper(paper_id="1", title="Paper A", source="semantic_scholar"),
            UnifiedPaper(paper_id="2", title="Paper B", source="exa"),
        ]
        result = deduplicate(papers)
        assert len(result) == 2

    def test_doi_duplicate_keeps_first(self):
        papers = [
            UnifiedPaper(
                paper_id="1", title="Paper A", source="semantic_scholar", doi="10.1234/x"
            ),
            UnifiedPaper(
                paper_id="2", title="Paper A Copy", source="exa", doi="10.1234/x"
            ),
        ]
        result = deduplicate(papers)
        assert len(result) == 1
        assert result[0].source == "semantic_scholar"

    def test_prefers_semantic_scholar(self):
        papers = [
            UnifiedPaper(
                paper_id="1", title="Paper A", source="exa", doi="10.1234/x"
            ),
            UnifiedPaper(
                paper_id="2",
                title="Paper A",
                source="semantic_scholar",
                doi="10.1234/x",
                citation_count=100,
            ),
        ]
        result = deduplicate(papers)
        assert len(result) == 1
        assert result[0].source == "semantic_scholar"
        assert result[0].citation_count == 100

    def test_title_based_dedup(self):
        papers = [
            UnifiedPaper(paper_id="1", title="Deep Learning Survey", source="semantic_scholar"),
            UnifiedPaper(paper_id="2", title="deep learning survey", source="exa"),
        ]
        result = deduplicate(papers)
        assert len(result) == 1


# --- Ranking ---


class TestRanking:
    def test_higher_citations_ranked_first(self):
        papers = [
            UnifiedPaper(
                paper_id="1", title="Low", source="semantic_scholar", citation_count=5
            ),
            UnifiedPaper(
                paper_id="2", title="High", source="semantic_scholar", citation_count=500
            ),
        ]
        ranked = rank_papers(papers)
        assert ranked[0].title == "High"

    def test_top_k_limits(self):
        papers = [
            UnifiedPaper(paper_id=str(i), title=f"Paper {i}", source="exa")
            for i in range(10)
        ]
        ranked = rank_papers(papers, top_k=3)
        assert len(ranked) == 3

    def test_relevance_score_range(self):
        paper = UnifiedPaper(
            paper_id="1",
            title="Test",
            source="semantic_scholar",
            year=2025,
            citation_count=1000,
            is_open_access=True,
            abstract="Ein Abstract.",
        )
        assert 0 <= paper.relevance_score <= 1.0

    def test_recent_paper_scores_higher(self):
        old = UnifiedPaper(
            paper_id="1", title="Old", source="semantic_scholar", year=2018
        )
        new = UnifiedPaper(
            paper_id="2", title="New", source="semantic_scholar", year=2025
        )
        assert new.relevance_score > old.relevance_score
