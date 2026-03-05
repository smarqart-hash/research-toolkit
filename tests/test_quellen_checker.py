"""Tests fuer den Quellen-Checker."""

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import httpx

from src.agents.paper_ranker import UnifiedPaper
from src.agents.quellen_checker import (
    CheckStatus,
    QuellenCheckReport,
    ReferenceCheckResult,
    check_against_local,
    compare_metadata,
    format_report_as_markdown,
    load_local_papers,
    save_report,
)
from src.agents.reference_extractor import ReferenceCandidate
from src.agents.semantic_scholar import Author, PaperResult, SearchResponse


# --- Fixtures ---


def _candidate(
    authors: list[str] | None = None,
    year: int | None = 2024,
    title: str | None = None,
    raw_text: str = "(Mueller 2024)",
) -> ReferenceCandidate:
    return ReferenceCandidate(
        raw_text=raw_text,
        authors=authors or ["Mueller"],
        year=year,
        title=title,
        location="Kap. 1",
    )


def _paper(
    title: str = "Test Paper",
    year: int = 2024,
    authors: list[str] | None = None,
    doi: str | None = None,
) -> UnifiedPaper:
    return UnifiedPaper(
        paper_id=doi or "abc",
        title=title,
        year=year,
        authors=authors or ["Mueller"],
        source="semantic_scholar",
        doi=doi,
    )


# --- Metadaten-Vergleich ---


class TestCompareMetadata:
    def test_matching(self):
        candidate = _candidate()
        paper = _paper()
        assert compare_metadata(candidate, paper) == []

    def test_year_mismatch(self):
        candidate = _candidate(year=2024)
        paper = _paper(year=2023)
        mismatches = compare_metadata(candidate, paper)
        assert any("Jahr" in m for m in mismatches)

    def test_author_mismatch(self):
        candidate = _candidate(authors=["Schmidt"])
        paper = _paper(authors=["Weber"])
        mismatches = compare_metadata(candidate, paper)
        assert any("Autor" in m for m in mismatches)

    def test_author_partial_match(self):
        candidate = _candidate(authors=["Mueller"])
        paper = _paper(authors=["Max Mueller", "Anna Schmidt"])
        mismatches = compare_metadata(candidate, paper)
        assert not any("Autor" in m for m in mismatches)

    def test_title_mismatch(self):
        candidate = _candidate(title="Completely Different Title Here")
        paper = _paper(title="Machine Learning Survey Paper")
        mismatches = compare_metadata(candidate, paper)
        assert any("Titel" in m for m in mismatches)

    def test_title_close_match(self):
        candidate = _candidate(title="Adaptive Traffic Control")
        paper = _paper(title="Adaptive Traffic Control with Deep RL")
        mismatches = compare_metadata(candidate, paper)
        # Genug Ueberlappung — kein Mismatch
        assert not any("Titel" in m for m in mismatches)


# --- Lokaler Lookup ---


class TestLocalLookup:
    def test_match_by_author_year(self):
        candidate = _candidate(authors=["Mueller"], year=2024)
        local_papers = {"key": _paper(authors=["Mueller"], year=2024)}
        result = check_against_local(candidate, local_papers)
        assert result is not None
        assert result.status == CheckStatus.VERIFIED

    def test_match_by_title(self):
        candidate = _candidate(title="Test Paper")
        paper = _paper(title="Test Paper")
        local_papers = {"test paper": paper}
        result = check_against_local(candidate, local_papers)
        assert result is not None
        assert result.status == CheckStatus.VERIFIED

    def test_no_match(self):
        candidate = _candidate(authors=["Unbekannt"], year=1999)
        local_papers = {"key": _paper(authors=["Mueller"], year=2024)}
        result = check_against_local(candidate, local_papers)
        assert result is None

    def test_mismatch_detected(self):
        candidate = _candidate(authors=["Mueller"], year=2023)
        local_papers = {"key": _paper(authors=["Mueller"], year=2024)}
        result = check_against_local(candidate, local_papers)
        assert result is not None
        assert result.status == CheckStatus.METADATA_MISMATCH


# --- Load Local Papers ---


class TestLoadLocalPapers:
    def test_load_valid_file(self, tmp_path: Path):
        data = {
            "papers": [
                {
                    "paper_id": "abc",
                    "title": "Test Paper",
                    "year": 2024,
                    "authors": ["Mueller"],
                    "source": "semantic_scholar",
                }
            ]
        }
        path = tmp_path / "forschungsstand.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        result = load_local_papers(path)
        assert len(result) >= 1

    def test_nonexistent_file(self, tmp_path: Path):
        path = tmp_path / "nope.json"
        result = load_local_papers(path)
        assert result == {}


# --- Report ---


class TestReport:
    def test_compute_stats(self):
        report = QuellenCheckReport(
            document="test.md",
            results=[
                ReferenceCheckResult(
                    status=CheckStatus.VERIFIED, candidate=_candidate()
                ),
                ReferenceCheckResult(
                    status=CheckStatus.NOT_FOUND,
                    candidate=_candidate(authors=["Unbekannt"]),
                ),
                ReferenceCheckResult(
                    status=CheckStatus.METADATA_MISMATCH,
                    candidate=_candidate(year=2020),
                    mismatches=["Jahr: 2020 vs. 2024"],
                ),
            ],
        )
        report.compute_stats()
        assert report.total_references == 3
        assert report.verified == 1
        assert report.not_found == 1
        assert report.metadata_mismatch == 1

    def test_format_markdown(self):
        report = QuellenCheckReport(
            document="draft.md",
            results=[
                ReferenceCheckResult(
                    status=CheckStatus.VERIFIED,
                    candidate=_candidate(),
                ),
                ReferenceCheckResult(
                    status=CheckStatus.NOT_FOUND,
                    candidate=_candidate(
                        authors=["Unbekannt"], raw_text="(Unbekannt 2020)"
                    ),
                ),
            ],
        )
        report.compute_stats()
        md = format_report_as_markdown(report)
        assert "Quellen-Check" in md
        assert "verifiziert" in md
        assert "nicht gefunden" in md

    def test_save_report(self, tmp_path: Path):
        report = QuellenCheckReport(document="test.md")
        report.compute_stats()
        path = save_report(report, tmp_path)
        assert path.exists()
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["document"] == "test.md"
