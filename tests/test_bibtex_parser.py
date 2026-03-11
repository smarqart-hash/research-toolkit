"""Tests fuer BibTeX-Parser."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from src.utils.bibtex_parser import parse_bibtex_file, parse_bibtex_string

BIB_ENTRY = textwrap.dedent("""\
    @article{smith2023deep,
        author = {Smith, John and Doe, Jane},
        title = {Deep Learning for Traffic Control},
        year = {2023},
        journal = {Nature Machine Intelligence},
        doi = {10.1234/nmi.2023.001},
        abstract = {We present a novel approach to traffic signal optimization.},
    }
""")

BIB_MINIMAL = textwrap.dedent("""\
    @inproceedings{lee2024,
        author = {Lee, Alice},
        title = {Minimal Entry Without DOI},
        year = {2024},
    }
""")

BIB_MULTI = BIB_ENTRY + "\n" + BIB_MINIMAL


class TestParseBibtexString:
    def test_single_entry(self):
        papers = parse_bibtex_string(BIB_ENTRY)
        assert len(papers) == 1
        paper = papers[0]
        assert paper.title == "Deep Learning for Traffic Control"
        assert paper.source == "import"
        assert paper.doi == "10.1234/nmi.2023.001"
        assert paper.year == 2023
        assert paper.authors == ["Smith, John", "Doe, Jane"]
        assert "novel approach" in paper.abstract

    def test_minimal_entry_no_doi(self):
        papers = parse_bibtex_string(BIB_MINIMAL)
        assert len(papers) == 1
        paper = papers[0]
        assert paper.doi is None
        assert paper.source == "import"
        assert paper.authors == ["Lee, Alice"]

    def test_multiple_entries(self):
        papers = parse_bibtex_string(BIB_MULTI)
        assert len(papers) == 2

    def test_empty_string(self):
        papers = parse_bibtex_string("")
        assert papers == []

    def test_paper_id_uses_doi_when_available(self):
        papers = parse_bibtex_string(BIB_ENTRY)
        assert papers[0].paper_id == "10.1234/nmi.2023.001"

    def test_paper_id_fallback_without_doi(self):
        papers = parse_bibtex_string(BIB_MINIMAL)
        assert papers[0].paper_id.startswith("import:")


class TestParseBibtexFile:
    def test_file_parse(self, tmp_path: Path):
        bib_file = tmp_path / "refs.bib"
        bib_file.write_text(BIB_ENTRY, encoding="utf-8")
        papers = parse_bibtex_file(bib_file)
        assert len(papers) == 1
        assert papers[0].source == "import"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_bibtex_file(Path("/nonexistent/refs.bib"))

    def test_malformed_entry_skipped(self):
        malformed = "@article{broken, title = }\n" + BIB_ENTRY
        papers = parse_bibtex_string(malformed)
        assert len(papers) >= 1
