"""Tests fuer den Forschungsstand-Generator."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from src.agents.forschungsstand import (
    ForschungsstandResult,
    SearchConfig,
    ThemeCluster,
    _check_source_balance,
    format_as_markdown,
    generate_search_queries,
    load_forschungsstand,
    merge_results,
    save_forschungsstand,
    search_papers,
    slugify,
)
from src.agents.paper_ranker import UnifiedPaper


# --- Fixtures ---


def _sample_papers() -> list[UnifiedPaper]:
    return [
        UnifiedPaper(
            paper_id="doi:10.1234/a",
            title="Deep RL Traffic Control",
            abstract="DRL fuer Ampelsteuerung.",
            year=2024,
            authors=["Mueller", "Schmidt"],
            citation_count=42,
            source="semantic_scholar",
            doi="10.1234/a",
        ),
        UnifiedPaper(
            paper_id="doi:10.1234/b",
            title="Computer Vision in Urban Traffic",
            abstract="CV-basierte Verkehrserfassung.",
            year=2023,
            authors=["Weber"],
            citation_count=15,
            source="semantic_scholar",
            doi="10.1234/b",
        ),
    ]


def _sample_result() -> ForschungsstandResult:
    papers = _sample_papers()
    return ForschungsstandResult(
        topic="KI-basierte Verkehrssteuerung",
        leitfragen=["Welche DRL-Ansaetze gibt es?", "Wie skaliert das?"],
        clusters=[
            ThemeCluster(
                theme="Deep Reinforcement Learning",
                description="DRL-Methoden zur Ampelsteuerung zeigen vielversprechende Ergebnisse.",
                papers=["doi:10.1234/a"],
                key_findings=["30% Reduktion der Wartezeiten"],
                open_questions=["Skalierung auf groessere Netze"],
            ),
            ThemeCluster(
                theme="Computer Vision",
                description="CV-basierte Verkehrserfassung als Alternative zu Induktionsschleifen.",
                papers=["doi:10.1234/b"],
                key_findings=["95% Erkennungsrate bei Fussgaengern"],
                open_questions=["Datenschutz bei kamerabasierter Erfassung"],
            ),
        ],
        papers=papers,
        total_found=87,
        total_after_dedup=54,
        sources_used=["Semantic Scholar", "Exa"],
    )


# --- Query-Generierung ---


class TestGenerateSearchQueries:
    def test_topic_only(self):
        queries = generate_search_queries("KI Verkehr", [])
        assert queries == ["KI Verkehr"]

    def test_with_leitfragen(self):
        queries = generate_search_queries(
            "KI Verkehr",
            ["Welche DRL-Ansaetze gibt es?", "Wie skaliert das System?"],
        )
        assert len(queries) == 3
        assert queries[0] == "KI Verkehr"
        # Fragewoerter entfernt
        assert "Welche" not in queries[1]
        assert "Wie" not in queries[2]

    def test_preserves_topic_in_queries(self):
        queries = generate_search_queries("Traffic AI", ["What approaches exist?"])
        # Freitext-Fragen ohne deutsches Prafix bleiben erhalten
        assert "Traffic AI" in queries[0]


# --- Markdown-Formatierung ---


class TestFormatAsMarkdown:
    def test_contains_topic(self):
        result = _sample_result()
        md = format_as_markdown(result)
        assert "KI-basierte Verkehrssteuerung" in md

    def test_contains_clusters(self):
        result = _sample_result()
        md = format_as_markdown(result)
        assert "Deep Reinforcement Learning" in md
        assert "Computer Vision" in md

    def test_contains_leitfragen(self):
        result = _sample_result()
        md = format_as_markdown(result)
        assert "Welche DRL-Ansaetze gibt es?" in md

    def test_contains_key_findings(self):
        result = _sample_result()
        md = format_as_markdown(result)
        assert "30% Reduktion der Wartezeiten" in md

    def test_contains_open_questions(self):
        result = _sample_result()
        md = format_as_markdown(result)
        assert "Skalierung auf groessere Netze" in md

    def test_contains_sources(self):
        result = _sample_result()
        md = format_as_markdown(result)
        assert "Mueller et al." in md
        assert "Weber" in md

    def test_source_count_in_intro(self):
        result = _sample_result()
        md = format_as_markdown(result)
        assert "54" in md  # total_after_dedup

    def test_markdown_structure(self):
        result = _sample_result()
        md = format_as_markdown(result)
        assert md.startswith("## Stand der Forschung:")
        assert "### 1." in md
        assert "### 2." in md
        assert "### Quellenverzeichnis" in md


# --- Persistenz ---


class TestSlugify:
    def test_basic(self):
        assert slugify("KI-basierte Verkehrssteuerung") == "ki-basierte-verkehrssteuerung"

    def test_spaces_and_special_chars(self):
        assert slugify("Space-Based Data Centers!") == "space-based-data-centers"

    def test_umlauts_normalized(self):
        # Unicode-Normalisierung: Ü→U, ö→o, ß→ gestripped (kein ASCII-Aequivalent)
        slug = slugify("Über Größe")
        assert " " not in slug
        assert slug == "uber-groe"

    def test_max_length(self):
        long_text = "a" * 100
        assert len(slugify(long_text, max_length=30)) <= 30

    def test_no_trailing_dash(self):
        slug = slugify("test---end---", max_length=10)
        assert not slug.endswith("-")


class TestPersistence:
    def test_save_and_load(self, tmp_path: Path):
        result = _sample_result()
        path = save_forschungsstand(result, tmp_path)
        loaded = load_forschungsstand(path)
        assert loaded.topic == result.topic
        assert len(loaded.clusters) == 2
        assert len(loaded.papers) == 2
        assert loaded.total_found == 87

    def test_creates_topic_subdirectory(self, tmp_path: Path):
        result = _sample_result()
        save_forschungsstand(result, tmp_path)
        expected = tmp_path / "ki-basierte-verkehrssteuerung" / "forschungsstand.json"
        assert expected.exists()

    def test_custom_slug(self, tmp_path: Path):
        result = _sample_result()
        save_forschungsstand(result, tmp_path, slug="custom-slug")
        assert (tmp_path / "custom-slug" / "forschungsstand.json").exists()

    def test_creates_nested_directory(self, tmp_path: Path):
        result = _sample_result()
        output_dir = tmp_path / "nested" / "dir"
        save_forschungsstand(result, output_dir)
        assert (output_dir / "ki-basierte-verkehrssteuerung" / "forschungsstand.json").exists()


# --- SearchConfig ---


class TestSearchConfig:
    def test_defaults(self):
        config = SearchConfig()
        assert config.max_results_per_query == 50
        assert config.top_k == 30
        assert config.sources == ["ss", "openalex"]
        assert config.languages == ["en", "de"]
        assert config.year_filter is None

    def test_custom_config(self):
        config = SearchConfig(
            max_results_per_query=20,
            year_filter="2022-2026",
            fields_of_study=["Computer Science"],
            top_k=15,
        )
        assert config.year_filter == "2022-2026"
        assert config.top_k == 15

    def test_custom_sources(self):
        config = SearchConfig(sources=["ss", "exa"])
        assert "exa" in config.sources
        assert "openalex" not in config.sources

    def test_custom_languages(self):
        config = SearchConfig(languages=["en"])
        assert config.languages == ["en"]


class TestSearchPapersErrorStats:
    """Tests fuer differenzierte Fehlerbehandlung in search_papers."""

    def test_http_errors_counted_in_stats(self):
        """HTTP-Fehler werden in ss_errors gezaehlt, nicht stumm geschluckt."""
        config = SearchConfig(sources=["ss"])

        async def mock_search(*args, **kwargs):
            raise httpx.HTTPStatusError(
                "Rate Limit",
                request=httpx.Request("GET", "https://test.com"),
                response=httpx.Response(429, content=b"Too Many Requests"),
            )

        async def run():
            with patch(
                "src.agents.forschungsstand.SemanticScholarClient.search_papers",
                side_effect=mock_search,
            ):
                papers, stats, _prisma = await search_papers("test", config=config)
                assert stats["ss_errors"] >= 1
                assert stats["ss_total"] == 0
                assert len(papers) == 0

        asyncio.run(run())

    def test_timeout_counted_in_stats(self):
        """Timeouts werden in ss_errors gezaehlt."""
        config = SearchConfig(sources=["ss"])

        async def mock_search(*args, **kwargs):
            raise httpx.TimeoutException("Timeout")

        async def run():
            with patch(
                "src.agents.forschungsstand.SemanticScholarClient.search_papers",
                side_effect=mock_search,
            ):
                papers, stats, _prisma = await search_papers("test", config=config)
                assert stats["ss_errors"] >= 1

        asyncio.run(run())


class TestSearchPapersMultiSource:
    """Tests fuer parallele Multi-Source-Suche."""

    def _make_ss_paper(self):
        """Minimales Semantic Scholar Paper-Mock."""
        from unittest.mock import MagicMock

        paper = MagicMock()
        paper.doi = "10.1234/ss"
        paper.paperId = "ss123"
        paper.title = "SS Paper"
        paper.abstract = "Abstract SS"
        paper.year = 2023
        paper.authors = []
        paper.citationCount = 5
        paper.isOpenAccess = False
        paper.arxiv_id = None
        paper.fieldsOfStudy = []
        return paper

    def _make_oa_work(self):
        """Minimales OpenAlex Work-Mock."""
        from src.agents.openalex_client import (
            OpenAlexOpenAccess,
            OpenAlexWork,
        )

        return OpenAlexWork(
            id="https://openalex.org/W123",
            doi="https://doi.org/10.1234/oa",
            display_name="OA Paper",
            publication_year=2022,
            cited_by_count=10,
            open_access=OpenAlexOpenAccess(is_oa=True),
            relevance_score=1.0,  # Pre-Filter passieren
        )

    def test_ss_only_source(self):
        """sources=["ss"] — nur SS wird abgefragt."""
        config = SearchConfig(sources=["ss"])
        ss_paper = self._make_ss_paper()

        async def mock_ss_search(*args, **kwargs):
            from unittest.mock import MagicMock

            resp = MagicMock()
            resp.data = [ss_paper]
            return resp

        async def run():
            with patch(
                "src.agents.forschungsstand.SemanticScholarClient.search_papers",
                side_effect=mock_ss_search,
            ):
                papers, stats, _ = await search_papers("test", config=config)
                assert stats["ss_total"] >= 1
                assert stats["openalex_total"] == 0
                assert stats["exa_total"] == 0

        asyncio.run(run())

    def test_ss_and_openalex_combined(self):
        """sources=["ss", "openalex"] — beide Quellen liefern Papers."""
        config = SearchConfig(sources=["ss", "openalex"])
        ss_paper = self._make_ss_paper()
        oa_work = self._make_oa_work()

        async def mock_ss_search(*args, **kwargs):
            from unittest.mock import MagicMock

            resp = MagicMock()
            resp.data = [ss_paper]
            return resp

        async def mock_oa_search(*args, **kwargs):
            from src.agents.openalex_client import OpenAlexSearchResponse

            return OpenAlexSearchResponse(results=[oa_work])

        async def run():
            with (
                patch(
                    "src.agents.forschungsstand.SemanticScholarClient.search_papers",
                    side_effect=mock_ss_search,
                ),
                patch(
                    "src.agents.forschungsstand.OpenAlexClient.search_works",
                    side_effect=mock_oa_search,
                ),
            ):
                papers, stats, _ = await search_papers("test", config=config)
                assert stats["ss_total"] >= 1
                assert stats["openalex_total"] >= 1
                assert len(papers) >= 1  # nach Dedup

        asyncio.run(run())

    def test_openalex_error_graceful_degradation(self):
        """OpenAlex-Fehler stoppt nicht SS-Ergebnis."""
        config = SearchConfig(sources=["ss", "openalex"])
        ss_paper = self._make_ss_paper()

        async def mock_ss_search(*args, **kwargs):
            from unittest.mock import MagicMock

            resp = MagicMock()
            resp.data = [ss_paper]
            return resp

        async def mock_oa_search(*args, **kwargs):
            raise httpx.TimeoutException("OA Timeout")

        async def run():
            with (
                patch(
                    "src.agents.forschungsstand.SemanticScholarClient.search_papers",
                    side_effect=mock_ss_search,
                ),
                patch(
                    "src.agents.forschungsstand.OpenAlexClient.search_works",
                    side_effect=mock_oa_search,
                ),
            ):
                papers, stats, _ = await search_papers("test", config=config)
                # SS hat Ergebnis trotz OA-Fehler
                assert stats["ss_total"] >= 1
                assert stats["openalex_errors"] >= 1
                assert len(papers) >= 1

        asyncio.run(run())

    def test_stats_contain_openalex_keys(self):
        """Stats enthalten openalex_total und openalex_errors."""
        config = SearchConfig(sources=["ss"])

        async def run():
            with patch(
                "src.agents.forschungsstand.SemanticScholarClient.search_papers",
                return_value=type("R", (), {"data": []})(),
            ):
                _, stats, _ = await search_papers("test", config=config)
                assert "openalex_total" in stats
                assert "openalex_errors" in stats

        asyncio.run(run())


class TestOpenAlexPreFilter:
    """Testet OpenAlex Relevanz-Vorfilterung."""

    def test_low_relevance_filtered(self):
        """Papers mit OA relevance_score < 0.3 werden vor Ranking entfernt."""
        from src.agents.forschungsstand import _search_openalex
        from src.agents.openalex_client import (
            OpenAlexSearchResponse,
            OpenAlexWork,
        )

        mock_works = [
            OpenAlexWork(
                id="W1",
                display_name="Relevant Paper",
                relevance_score=0.8,
                publication_year=2024,
            ),
            OpenAlexWork(
                id="W2",
                display_name="Irrelevant Paper",
                relevance_score=0.1,
                publication_year=2024,
            ),
            OpenAlexWork(
                id="W3",
                display_name="Borderline Paper",
                relevance_score=0.3,
                publication_year=2024,
            ),
        ]
        mock_response = OpenAlexSearchResponse(results=mock_works)

        async def run():
            with patch(
                "src.agents.forschungsstand.OpenAlexClient"
            ) as mock_oa_client:
                instance = mock_oa_client.return_value
                instance.search_works = AsyncMock(return_value=mock_response)

                config = SearchConfig()
                stats = {"openalex_total": 0, "openalex_errors": 0}
                return await _search_openalex(["test query"], config, stats)

        papers = asyncio.run(run())

        # W2 (relevance_score=0.1) sollte gefiltert sein
        assert len(papers) == 2
        titles = [p.title for p in papers]
        assert "Relevant Paper" in titles
        assert "Borderline Paper" in titles
        assert "Irrelevant Paper" not in titles


class TestAccumulatedSearch:
    """Testet akkumuliertes Speichern von Suchergebnissen."""

    def test_save_and_load_roundtrip(self, tmp_path):
        """Normaler Save/Load funktioniert weiterhin."""
        result = ForschungsstandResult(topic="Test", papers=[], total_found=0)
        path = save_forschungsstand(result, tmp_path)
        loaded = load_forschungsstand(path)
        assert loaded.topic == "Test"

    def test_merge_results_deduplicates(self):
        """merge_results entfernt Duplikate aus zwei Result-Sets."""
        paper_a = UnifiedPaper(
            paper_id="doi:10.1",
            title="Paper A",
            source="semantic_scholar",
            doi="10.1",
        )
        paper_b = UnifiedPaper(
            paper_id="doi:10.2",
            title="Paper B",
            source="openalex",
            doi="10.2",
        )
        paper_a_dup = UnifiedPaper(
            paper_id="doi:10.1",
            title="Paper A",
            source="openalex",
            doi="10.1",
        )
        existing = ForschungsstandResult(
            topic="Test",
            papers=[paper_a],
            total_found=1,
        )
        new = ForschungsstandResult(
            topic="Test",
            papers=[paper_b, paper_a_dup],
            total_found=2,
        )
        merged = merge_results(existing, new)
        assert len(merged.papers) == 2
        # SS-Version von Paper A bleibt (bessere Metadaten)
        paper_a_result = [p for p in merged.papers if p.doi == "10.1"][0]
        assert paper_a_result.source == "semantic_scholar"

    def test_merge_accumulates_total_found(self):
        """merge_results addiert total_found."""
        existing = ForschungsstandResult(topic="T", papers=[], total_found=50)
        new = ForschungsstandResult(topic="T", papers=[], total_found=30)
        merged = merge_results(existing, new)
        assert merged.total_found == 80

    def test_merge_unifies_sources(self):
        """merge_results vereinigt sources_used Listen."""
        existing = ForschungsstandResult(
            topic="T", papers=[], total_found=10,
            sources_used=["Semantic Scholar"],
        )
        new = ForschungsstandResult(
            topic="T", papers=[], total_found=20,
            sources_used=["OpenAlex", "Semantic Scholar"],
        )
        merged = merge_results(existing, new)
        assert "Semantic Scholar" in merged.sources_used
        assert "OpenAlex" in merged.sources_used
        # Keine Duplikate
        assert len(merged.sources_used) == 2

    def test_merge_preserves_leitfragen(self):
        """merge_results vereinigt Leitfragen ohne Duplikate."""
        existing = ForschungsstandResult(
            topic="T", papers=[], total_found=0,
            leitfragen=["Frage 1", "Frage 2"],
        )
        new = ForschungsstandResult(
            topic="T", papers=[], total_found=0,
            leitfragen=["Frage 2", "Frage 3"],
        )
        merged = merge_results(existing, new)
        assert len(merged.leitfragen) == 3


class TestSourceBalanceWarning:
    """Warnung wenn eine Quelle <10% des Pools liefert."""

    def test_imbalanced_sources_logged(self):
        """Warnung bei SS=2, OA=40 Papers."""
        stats = {"ss_total": 2, "openalex_total": 40, "exa_total": 0}
        warnings = _check_source_balance(stats)
        assert len(warnings) >= 1
        assert "semantic" in warnings[0].lower() or "ss" in warnings[0].lower()

    def test_balanced_sources_no_warning(self):
        """Keine Warnung bei SS=20, OA=25."""
        stats = {"ss_total": 20, "openalex_total": 25, "exa_total": 0}
        warnings = _check_source_balance(stats)
        assert len(warnings) == 0

    def test_single_source_no_warning(self):
        """Keine Warnung bei nur einer aktiven Quelle."""
        stats = {"ss_total": 0, "openalex_total": 50, "exa_total": 0}
        warnings = _check_source_balance(stats)
        assert len(warnings) == 0

    def test_all_sources_imbalanced(self):
        """Warnung fuer jede unterrepresentierte Quelle."""
        stats = {"ss_total": 1, "openalex_total": 1, "exa_total": 98}
        warnings = _check_source_balance(stats)
        assert len(warnings) == 2  # SS und OA beide unter 10%


class TestPaperImport:
    """Tests fuer --papers Import-Integration."""

    def test_search_config_papers_file_default_none(self):
        config = SearchConfig()
        assert config.papers_file is None

    def test_imported_papers_merged_into_results(self, tmp_path):
        """Importierte Papers werden in den Ergebnis-Pool gemerged."""
        import textwrap

        bib_content = textwrap.dedent("""\
            @article{test2023,
                author = {Test, Author},
                title = {Imported Paper Title},
                year = {2023},
                doi = {10.9999/test},
            }
        """)
        bib_file = tmp_path / "refs.bib"
        bib_file.write_text(bib_content, encoding="utf-8")

        config = SearchConfig(papers_file=bib_file, sources=[])
        papers, stats, _ = asyncio.run(
            search_papers("test topic", config=config)
        )
        assert len(papers) == 1
        assert papers[0].source == "import"
        assert stats["import_total"] == 1

    def test_import_total_stat_default_zero(self):
        """import_total ist 0 wenn kein Import."""
        config = SearchConfig(sources=[])
        papers, stats, _ = asyncio.run(
            search_papers("test topic", config=config)
        )
        assert stats["import_total"] == 0


class TestLowRecallWarning:
    """Tests fuer Low-Recall-Warnung."""

    def test_no_warning_above_threshold(self):
        from src.agents.forschungsstand import _check_low_recall

        warnings = _check_low_recall(20, has_exa=True, has_import=True)
        assert warnings == []

    def test_warning_below_threshold(self):
        from src.agents.forschungsstand import _check_low_recall

        warnings = _check_low_recall(8, has_exa=True, has_import=False)
        assert len(warnings) >= 1
        assert "8" in warnings[0]

    def test_warning_suggests_exa_when_missing(self):
        from src.agents.forschungsstand import _check_low_recall

        warnings = _check_low_recall(5, has_exa=False, has_import=False)
        assert any("EXA_API_KEY" in w for w in warnings)

    def test_warning_suggests_import_when_missing(self):
        from src.agents.forschungsstand import _check_low_recall

        warnings = _check_low_recall(5, has_exa=True, has_import=False)
        assert any("--papers" in w for w in warnings)

    def test_no_suggestions_when_all_active(self):
        from src.agents.forschungsstand import _check_low_recall

        warnings = _check_low_recall(5, has_exa=True, has_import=True)
        assert len(warnings) == 1  # Nur Hauptwarnung, keine Empfehlungen
