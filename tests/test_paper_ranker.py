"""Tests fuer Paper-Deduplizierung und Ranking."""

from unittest.mock import patch

import pytest

from src.agents.exa_client import ExaResult
from src.agents.openalex_client import OpenAlexAuthorship, OpenAlexOpenAccess, OpenAlexWork
from src.agents.paper_ranker import (
    UnifiedPaper,
    compute_specter2_similarity,
    deduplicate,
    from_exa,
    from_openalex,
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


def _openalex_work_paper(
    work_id: str = "https://openalex.org/W99",
    doi: str | None = "https://doi.org/10.1234/oa",
    display_name: str = "OpenAlex Test Paper",
    publication_year: int | None = 2023,
    cited_by_count: int = 88,
    is_oa: bool = True,
    authors: list[str] | None = None,
) -> OpenAlexWork:
    """Factory fuer OpenAlexWork in paper_ranker Tests."""
    authorship_list = [
        OpenAlexAuthorship.model_validate({"author": {"display_name": name}})
        for name in (authors or ["OpenAlex Author"])
    ]
    return OpenAlexWork(
        id=work_id,
        doi=doi,
        display_name=display_name,
        publication_year=publication_year,
        cited_by_count=cited_by_count,
        open_access=OpenAlexOpenAccess(is_oa=is_oa),
        authorships=authorship_list,
        abstract_inverted_index={"Test": [0], "abstract": [1]},
    )


class TestFromOpenAlex:
    def test_basic_conversion(self):
        work = _openalex_work_paper()
        unified = from_openalex(work)
        assert unified.title == "OpenAlex Test Paper"
        assert unified.source == "openalex"
        assert unified.year == 2023
        assert unified.citation_count == 88
        assert unified.is_open_access is True

    def test_doi_normalized(self):
        """DOI wird aus URL-Form normalisiert."""
        work = _openalex_work_paper(doi="https://doi.org/10.1234/oa")
        unified = from_openalex(work)
        assert unified.doi == "10.1234/oa"
        assert unified.paper_id == "10.1234/oa"

    def test_doi_http_normalized(self):
        """Auch http:// doi.org URLs werden normalisiert."""
        work = _openalex_work_paper(doi="http://doi.org/10.5678/test")
        unified = from_openalex(work)
        assert unified.doi == "10.5678/test"

    def test_doi_none_uses_openalex_id(self):
        """Ohne DOI wird die OpenAlex-ID als paper_id genutzt."""
        work = _openalex_work_paper(doi=None)
        unified = from_openalex(work)
        assert unified.doi is None
        assert unified.paper_id == "https://openalex.org/W99"

    def test_authors_extracted(self):
        work = _openalex_work_paper(authors=["Anna Mueller", "Ben Schmidt"])
        unified = from_openalex(work)
        assert unified.authors == ["Anna Mueller", "Ben Schmidt"]

    def test_url_is_openalex_id(self):
        """OpenAlex-ID wird als URL gespeichert."""
        work = _openalex_work_paper(work_id="https://openalex.org/W999")
        unified = from_openalex(work)
        assert unified.url == "https://openalex.org/W999"

    def test_abstract_from_inverted_index(self):
        """Abstract wird aus Inverted Index rekonstruiert."""
        work = _openalex_work_paper()
        unified = from_openalex(work)
        assert unified.abstract == "Test abstract"

    def test_no_abstract_when_none(self):
        work = OpenAlexWork(
            id="https://openalex.org/W1",
            display_name="No Abstract Work",
        )
        unified = from_openalex(work)
        assert unified.abstract is None

    def test_openalex_scores_same_as_ss(self):
        """OpenAlex erhalt denselben Metadaten-Bonus wie Semantic Scholar."""
        oa_paper = UnifiedPaper(
            paper_id="oa1",
            title="OpenAlex",
            source="openalex",
            year=2024,
            citation_count=100,
            is_open_access=True,
            abstract="Abstract",
        )
        ss_paper = UnifiedPaper(
            paper_id="ss1",
            title="SS",
            source="semantic_scholar",
            year=2024,
            citation_count=100,
            is_open_access=True,
            abstract="Abstract",
        )
        assert oa_paper.relevance_score == ss_paper.relevance_score

    def test_exa_no_metadata_bonus(self):
        """Exa-Papers haben keinen Metadaten-Bonus."""
        exa_paper = UnifiedPaper(
            paper_id="exa1",
            title="Exa",
            source="exa",
            year=2024,
            citation_count=100,
            is_open_access=True,
            abstract="Abstract",
        )
        oa_paper = UnifiedPaper(
            paper_id="oa1",
            title="OA",
            source="openalex",
            year=2024,
            citation_count=100,
            is_open_access=True,
            abstract="Abstract",
        )
        assert oa_paper.relevance_score > exa_paper.relevance_score


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

    def test_rank_with_query_uses_specter2(self):
        """SPECTER2-Score beeinflusst Ranking wenn query angegeben."""
        papers = [
            UnifiedPaper(
                paper_id="1",
                title="Protein Folding",
                abstract="Protein structure prediction",
                source="semantic_scholar",
                citation_count=500,
                year=2024,
            ),
            UnifiedPaper(
                paper_id="2",
                title="AI Research Automation",
                abstract="Automated literature review with AI",
                source="semantic_scholar",
                citation_count=10,
                year=2024,
            ),
        ]
        # Mit Mock: SPECTER2 gibt hohen Score fuer Paper 2
        mock_scores = {"1": 0.1, "2": 0.95}
        with patch(
            "src.agents.paper_ranker.compute_specter2_similarity",
            return_value=mock_scores,
        ):
            ranked = rank_papers(papers, query="AI automated research")
        # Paper 2 sollte trotz weniger Citations oben sein
        assert ranked[0].paper_id == "2"

    def test_rank_without_query_ignores_specter2(self):
        """Ohne query: heuristisches Ranking wie bisher."""
        papers = [
            UnifiedPaper(
                paper_id="1", title="Low Cite", source="semantic_scholar", citation_count=5
            ),
            UnifiedPaper(
                paper_id="2", title="High Cite", source="semantic_scholar", citation_count=500
            ),
        ]
        ranked = rank_papers(papers)
        assert ranked[0].paper_id == "2"

    def test_specter2_score_stored_on_paper(self):
        """SPECTER2-Score wird auf UnifiedPaper gespeichert."""
        papers = [
            UnifiedPaper(
                paper_id="1",
                title="Test",
                abstract="Test abstract",
                source="semantic_scholar",
            ),
        ]
        mock_scores = {"1": 0.85}
        with patch(
            "src.agents.paper_ranker.compute_specter2_similarity",
            return_value=mock_scores,
        ):
            ranked = rank_papers(papers, query="test query")
        assert ranked[0].specter2_score == 0.85


# --- SPECTER2 ---


class TestSpecter2:
    def test_returns_empty_when_not_installed(self):
        """Graceful Degradation: leeres Dict ohne sentence-transformers."""
        with patch(
            "src.agents.paper_ranker._load_specter2_model",
            side_effect=ImportError("No module"),
        ):
            result = compute_specter2_similarity("test query", [])
            assert result == {}

    def test_papers_without_abstract_get_zero(self):
        """Papers ohne Abstract bekommen Score 0."""
        papers = [
            UnifiedPaper(
                paper_id="no_abs",
                title="No Abstract",
                abstract=None,
                source="semantic_scholar",
            ),
        ]
        mock_model = _MockSentenceTransformer()
        with patch(
            "src.agents.paper_ranker._load_specter2_model",
            return_value=mock_model,
        ):
            result = compute_specter2_similarity("test query", papers)
        assert result.get("no_abs", 0.0) == 0.0

    def test_specter2_score_default_none(self):
        """Neues Feld specter2_score ist default None."""
        paper = UnifiedPaper(paper_id="1", title="Test", source="exa")
        assert paper.specter2_score is None


class _MockSentenceTransformer:
    """Mock fuer SentenceTransformer.encode()."""

    def encode(self, texts, **kwargs):
        import numpy as np

        return np.random.rand(len(texts), 768).astype(np.float32)
