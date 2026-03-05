"""Tests fuer den Document Splitter."""

import pytest

from utils.document_splitter import (
    DocumentSection,
    extract_section_by_name,
    needs_splitting,
    split_markdown,
)


SAMPLE_MARKDOWN = """# Titel des Dokuments

Einleitender Absatz vor dem ersten Kapitel.

## 1. Einleitung

Dies ist die Einleitung. Sie beschreibt das Problem.

### 1.1 Hintergrund

Detaillierter Hintergrund zum Thema.

## 2. Analyse

Hier werden die Handlungsfelder analysiert.

Mit mehreren Absaetzen.

## 3. Handlungsempfehlungen

An die Bundesregierung: Foerderung ausbauen.
An die Wirtschaft: Investitionen erhoehen.

## 4. Fazit

Zusammenfassung der Ergebnisse.
"""

SHORT_MARKDOWN = """## Kurzes Dokument

Ein kurzer Text der nicht gesplittet werden muss.
"""

NO_HEADINGS_MARKDOWN = """Dies ist ein Text ohne jegliche Markdown-Headings.

Er besteht nur aus Absaetzen.
"""


class TestSplitMarkdown:
    def test_splits_at_h2_headings(self) -> None:
        sections = split_markdown(SAMPLE_MARKDOWN)
        headings = [s.heading for s in sections]
        assert "Einleitung" in headings[0] or "1. Einleitung" in headings[1]

    def test_h1_title_becomes_first_section(self) -> None:
        sections = split_markdown(SAMPLE_MARKDOWN)
        assert sections[0].heading == "Titel des Dokuments"
        assert sections[0].level == 1

    def test_subheadings_merged_into_parent(self) -> None:
        sections = split_markdown(SAMPLE_MARKDOWN)
        einleitung = next(s for s in sections if "Einleitung" in s.heading)
        assert "Hintergrund" in einleitung.content

    def test_four_h2_sections_plus_preamble(self) -> None:
        sections = split_markdown(SAMPLE_MARKDOWN)
        # Preamble + 4 Kapitel (H1 wird nicht als Split genutzt bei min_level=2)
        h2_sections = [s for s in sections if s.level == 2]
        assert len(h2_sections) == 4

    def test_no_headings_returns_single_section(self) -> None:
        sections = split_markdown(NO_HEADINGS_MARKDOWN)
        assert len(sections) == 1
        assert sections[0].heading == "Dokument"

    def test_sections_have_correct_indices(self) -> None:
        sections = split_markdown(SAMPLE_MARKDOWN)
        for i, section in enumerate(sections):
            assert section.index == i

    def test_word_count(self) -> None:
        sections = split_markdown(SAMPLE_MARKDOWN)
        for section in sections:
            assert section.word_count > 0

    def test_estimated_pages(self) -> None:
        sections = split_markdown(SAMPLE_MARKDOWN)
        total_pages = sum(s.estimated_pages for s in sections)
        assert total_pages > 0
        assert total_pages < 1  # Kurzes Beispiel

    def test_custom_min_level(self) -> None:
        """Splitting an H1 statt H2."""
        sections = split_markdown(SAMPLE_MARKDOWN, min_level=1)
        h1_sections = [s for s in sections if s.level == 1]
        assert len(h1_sections) >= 1


class TestNeedsSplitting:
    def test_short_document_no_splitting(self) -> None:
        assert not needs_splitting(SHORT_MARKDOWN)

    def test_long_document_needs_splitting(self) -> None:
        long_text = "Wort " * 6000  # > 5000 Woerter
        assert needs_splitting(long_text)

    def test_exact_threshold(self) -> None:
        exact = "Wort " * 5000
        assert not needs_splitting(exact)

        over = "Wort " * 5001
        assert needs_splitting(over)


class TestExtractSectionByName:
    def test_find_by_exact_name(self) -> None:
        sections = split_markdown(SAMPLE_MARKDOWN)
        section = extract_section_by_name(sections, "Handlungsempfehlungen")
        assert section is not None
        assert "Bundesregierung" in section.content

    def test_find_by_partial_name(self) -> None:
        sections = split_markdown(SAMPLE_MARKDOWN)
        section = extract_section_by_name(sections, "Analyse")
        assert section is not None

    def test_case_insensitive(self) -> None:
        sections = split_markdown(SAMPLE_MARKDOWN)
        section = extract_section_by_name(sections, "fazit")
        assert section is not None

    def test_not_found_returns_none(self) -> None:
        sections = split_markdown(SAMPLE_MARKDOWN)
        section = extract_section_by_name(sections, "Nicht vorhanden")
        assert section is None
