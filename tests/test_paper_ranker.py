"""Tests fuer Paper-Deduplizierung und Ranking."""

from unittest.mock import patch

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

    def test_ss_scores_higher_than_openalex_same_signals(self):
        """SS erhalt hoeheren Score als OpenAlex bei gleichen Signalen (source-aware caps)."""
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
        # SS hat hoehere Citation-Cap (0.4) + hoeheren Metadaten-Bonus (0.1 vs 0.05)
        assert ss_paper.relevance_score > oa_paper.relevance_score

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


class TestSourceAwareRelevanceScore:
    """Testet source-normalisierte Scores."""

    def test_openalex_citation_cap(self):
        """OpenAlex Citation-Beitrag ist auf 0.15 gedeckelt (statt 0.4)."""
        paper = UnifiedPaper(
            paper_id="oa1",
            title="Highly Cited OA",
            citation_count=5000,
            source="openalex",
            year=2024,
            abstract="Test abstract",
        )
        assert paper.relevance_score <= 0.75

    def test_ss_citation_weight_unchanged(self):
        """SS Citation-Gewicht bleibt bei max 0.4."""
        paper = UnifiedPaper(
            paper_id="ss1",
            title="SS Paper",
            citation_count=100,
            source="semantic_scholar",
            year=2024,
            abstract="Test",
            is_open_access=True,
        )
        assert paper.relevance_score > 0.5

    def test_openalex_high_cite_lower_than_ss_moderate_cite(self):
        """OA-Paper mit 3000 Cites rankt niedriger als SS mit 50 + OA + Abstract."""
        oa_paper = UnifiedPaper(
            paper_id="oa",
            title="Off-topic OA",
            citation_count=3000,
            source="openalex",
            year=2023,
        )
        ss_paper = UnifiedPaper(
            paper_id="ss",
            title="On-topic SS",
            citation_count=50,
            source="semantic_scholar",
            year=2024,
            abstract="Relevant abstract",
            is_open_access=True,
        )
        assert ss_paper.relevance_score > oa_paper.relevance_score

    def test_exa_no_citations_still_ranks(self):
        """Exa-Paper ohne Citations bekommt Score aus anderen Signalen."""
        paper = UnifiedPaper(
            paper_id="exa1",
            title="Exa Paper",
            source="exa",
            year=2025,
            abstract="Abstract vorhanden",
        )
        assert paper.relevance_score > 0.0


class TestScoreSerialization:
    """Testet dass relevance_score im JSON-Output erscheint."""

    def test_relevance_score_in_json(self):
        """computed_field relevance_score ist im model_dump enthalten."""
        paper = UnifiedPaper(
            paper_id="test",
            title="Test Paper",
            citation_count=100,
            source="semantic_scholar",
            year=2024,
            abstract="Abstract",
        )
        dumped = paper.model_dump()
        assert "relevance_score" in dumped
        assert dumped["relevance_score"] > 0.0

    def test_relevance_score_in_json_string(self):
        """relevance_score erscheint in model_dump_json."""
        paper = UnifiedPaper(
            paper_id="test",
            title="Test",
            citation_count=50,
            source="openalex",
            year=2024,
        )
        json_str = paper.model_dump_json()
        assert '"relevance_score"' in json_str

    def test_specter2_score_in_json(self):
        """specter2_score wird serialisiert (auch wenn None)."""
        paper = UnifiedPaper(
            paper_id="test",
            title="Test",
            source="semantic_scholar",
        )
        dumped = paper.model_dump()
        assert "specter2_score" in dumped
        assert dumped["specter2_score"] is None


class TestEnhancedScoreSourceAware:
    """Testet dass SPECTER2 enhanced scoring source-aware ist."""

    def test_openalex_citation_cap_in_enhanced(self):
        """OpenAlex Citation-Cap auch bei SPECTER2-Scoring."""
        oa_paper = UnifiedPaper(
            paper_id="oa1",
            title="OA Paper",
            citation_count=5000,
            source="openalex",
            year=2024,
            abstract="Abstract",
        )
        ss_paper = UnifiedPaper(
            paper_id="ss1",
            title="SS Paper",
            citation_count=50,
            source="semantic_scholar",
            year=2024,
            abstract="Abstract",
            is_open_access=True,
        )
        # Gleicher SPECTER2-Score, aber SS sollte hoeher ranken
        mock_scores = {"oa1": 0.5, "ss1": 0.5}
        with patch(
            "src.agents.paper_ranker.compute_specter2_similarity",
            return_value=mock_scores,
        ):
            ranked = rank_papers([oa_paper, ss_paper], query="test query")
        assert ranked[0].paper_id == "ss1"

    def test_exa_citation_cap_in_enhanced(self):
        """Exa hat niedrigsten Citation-Cap bei SPECTER2-Scoring."""
        from src.agents.paper_ranker import _compute_enhanced_score

        exa_paper = UnifiedPaper(
            paper_id="exa1",
            title="Exa Paper",
            citation_count=5000,
            source="exa",
            year=2024,
            abstract="Abstract",
        )
        ss_paper = UnifiedPaper(
            paper_id="ss1",
            title="SS Paper",
            citation_count=5000,
            source="semantic_scholar",
            year=2024,
            abstract="Abstract",
        )
        scores = {"exa1": 0.5, "ss1": 0.5}
        exa_score = _compute_enhanced_score(exa_paper, scores)
        ss_score = _compute_enhanced_score(ss_paper, scores)
        assert ss_score > exa_score


class TestSourceQuota:
    """Testet Source-Quota im Ranking (F19 Fix)."""

    def test_exa_papers_preserved_with_quota(self):
        """20 SS + 5 Exa, top_k=15 → mindestens 3 Exa im Ergebnis."""
        ss_papers = [
            UnifiedPaper(
                paper_id=f"ss{i}",
                title=f"SS Paper {i}",
                source="semantic_scholar",
                citation_count=1000,
                year=2025,
                abstract="Abstract",
                is_open_access=True,
            )
            for i in range(20)
        ]
        exa_papers = [
            UnifiedPaper(
                paper_id=f"exa{i}",
                title=f"Exa Paper {i}",
                source="exa",
                year=2024,
            )
            for i in range(5)
        ]
        ranked = rank_papers([*ss_papers, *exa_papers], top_k=15)
        exa_count = sum(1 for p in ranked if p.source == "exa")
        assert len(ranked) == 15
        assert exa_count >= 3

    def test_quota_does_not_exceed_available(self):
        """20 SS + 1 Exa, top_k=15 → genau 1 Exa (nicht mehr als vorhanden)."""
        ss_papers = [
            UnifiedPaper(
                paper_id=f"ss{i}",
                title=f"SS Paper {i}",
                source="semantic_scholar",
                citation_count=1000,
                year=2025,
                abstract="Abstract",
            )
            for i in range(20)
        ]
        exa_papers = [
            UnifiedPaper(
                paper_id="exa0",
                title="Exa Paper 0",
                source="exa",
                year=2024,
            )
        ]
        ranked = rank_papers([*ss_papers, *exa_papers], top_k=15)
        exa_count = sum(1 for p in ranked if p.source == "exa")
        assert len(ranked) == 15
        assert exa_count == 1

    def test_quota_respects_top_k(self):
        """30 Papers (10 pro Quelle), top_k=10 → genau 10 zurueck."""
        papers: list[UnifiedPaper] = []
        for src in ("semantic_scholar", "openalex", "exa"):
            for i in range(10):
                papers = [
                    *papers,
                    UnifiedPaper(
                        paper_id=f"{src}{i}",
                        title=f"{src} Paper {i}",
                        source=src,
                        year=2024,
                    ),
                ]
        ranked = rank_papers(papers, top_k=10)
        assert len(ranked) == 10

    def test_small_top_k_does_not_overflow(self):
        """top_k=5 mit 3 Quellen → genau 5 Papers, kein Overflow."""
        papers = []
        for src in ("semantic_scholar", "openalex", "exa"):
            for i in range(10):
                papers = [
                    *papers,
                    UnifiedPaper(
                        paper_id=f"{src}{i}",
                        title=f"{src} Paper {i}",
                        source=src,
                        year=2024,
                    ),
                ]
        ranked = rank_papers(papers, top_k=5)
        assert len(ranked) == 5
        # Jede Quelle hat mindestens 1 Paper (effective_min = 5//3 = 1)
        sources_in_result = {p.source for p in ranked}
        assert len(sources_in_result) >= 2  # Mindestens 2 Quellen vertreten

    def test_no_quota_without_top_k(self):
        """Kein top_k → alle Papers zurueck, keine Quota-Filterung."""
        papers = [
            UnifiedPaper(
                paper_id=f"p{i}",
                title=f"Paper {i}",
                source="semantic_scholar",
                year=2024,
            )
            for i in range(5)
        ]
        ranked = rank_papers(papers)
        assert len(ranked) == 5


class TestLanguageField:
    """Testet das language-Feld in UnifiedPaper."""

    def test_unified_paper_has_language(self):
        """UnifiedPaper akzeptiert language-Feld."""
        paper = UnifiedPaper(
            paper_id="lang1",
            title="Deutsches Paper",
            source="openalex",
            language="de",
        )
        assert paper.language == "de"

    def test_unified_paper_language_default_none(self):
        """language ist standardmaessig None."""
        paper = UnifiedPaper(paper_id="1", title="No Language", source="semantic_scholar")
        assert paper.language is None

    def test_from_openalex_passes_language(self):
        """from_openalex() uebertraegt language aus OpenAlexWork."""
        work = OpenAlexWork(
            id="https://openalex.org/W1",
            display_name="German Paper",
            language="de",
        )
        unified = from_openalex(work)
        assert unified.language == "de"


class _MockSentenceTransformer:
    """Mock fuer SentenceTransformer.encode()."""

    def encode(self, texts, **kwargs):
        import numpy as np

        return np.random.rand(len(texts), 768).astype(np.float32)
