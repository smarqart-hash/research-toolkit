"""Tests fuer den Referenz-Extraktor."""

from src.agents.reference_extractor import (
    ReferenceCandidate,
    extract_all_references,
    extract_bibliography,
    extract_inline_citations,
    _find_bibliography_section,
    _parse_authors,
)


# --- Autor-Parsing ---


class TestParseAuthors:
    def test_single_author(self):
        assert _parse_authors("Mueller") == ["Mueller"]

    def test_et_al(self):
        assert _parse_authors("Mueller et al.") == ["Mueller"]

    def test_slash_separated(self):
        assert _parse_authors("Mueller/Schmidt") == ["Mueller", "Schmidt"]

    def test_comma_separated(self):
        assert _parse_authors("Mueller, Schmidt") == ["Mueller", "Schmidt"]

    def test_trailing_comma(self):
        assert _parse_authors("Mueller,") == ["Mueller"]


# --- Inline-Zitate ---


class TestInlineCitations:
    def test_simple_parenthetical(self):
        text = "Dies zeigt eine Studie (Mueller 2024)."
        results = extract_inline_citations(text)
        assert len(results) == 1
        assert results[0].authors == ["Mueller"]
        assert results[0].year == 2024

    def test_et_al(self):
        text = "Laut (Mueller et al. 2023) ist das korrekt."
        results = extract_inline_citations(text)
        assert len(results) == 1
        assert results[0].authors == ["Mueller"]
        assert results[0].year == 2023

    def test_with_page(self):
        text = "Wie beschrieben (Schmidt 2024, S. 15)."
        results = extract_inline_citations(text)
        assert len(results) == 1
        assert results[0].page_ref == "S. 15"

    def test_narrative_citation(self):
        text = "Mueller (2024) zeigt, dass dies funktioniert."
        results = extract_inline_citations(text)
        assert len(results) == 1
        assert results[0].authors == ["Mueller"]

    def test_multiple_citations(self):
        text = "Laut (Mueller 2024) und (Schmidt 2023) ist das klar."
        results = extract_inline_citations(text)
        assert len(results) == 2

    def test_deduplication(self):
        text = "Erstens (Mueller 2024). Zweitens (Mueller 2024)."
        results = extract_inline_citations(text)
        assert len(results) == 1  # Dedupliziert

    def test_section_location(self):
        text = "## 2. Methodik\n\nLaut (Mueller 2024) ist das so."
        results = extract_inline_citations(text)
        assert "Methodik" in results[0].location

    def test_german_umlauts(self):
        text = "Wie (Müller 2024) zeigt."
        results = extract_inline_citations(text)
        assert len(results) == 1
        assert results[0].authors == ["Müller"]


# --- Literaturverzeichnis ---


class TestBibliography:
    def test_standard_entry(self):
        text = """## Literaturverzeichnis

- Mueller et al. (2024): Adaptive Traffic Control with Deep RL. Transportation Research.
- Schmidt (2023): Urban Mobility Solutions. Nature Cities.
"""
        results = extract_bibliography(text)
        assert len(results) == 2
        assert results[0].title == "Adaptive Traffic Control with Deep RL"
        assert results[0].year == 2024
        assert results[0].from_bibliography is True

    def test_alternative_heading(self):
        text = """## Quellen

- Weber (2022): Ein Paper. Journal.
"""
        results = extract_bibliography(text)
        assert len(results) == 1

    def test_no_bibliography(self):
        text = "Normaler Text ohne Literaturverzeichnis."
        results = extract_bibliography(text)
        assert results == []

    def test_dash_variants(self):
        text = """## Literatur

– Weber (2022): Ein Paper. Ein Journal.
"""
        results = extract_bibliography(text)
        assert len(results) == 1


# --- Biblio-Section-Finder ---


class TestFindBibliographySection:
    def test_literaturverzeichnis(self):
        text = "## Literaturverzeichnis\n- Eintrag"
        assert _find_bibliography_section(text) >= 0

    def test_quellen(self):
        text = "## Quellen\n- Eintrag"
        assert _find_bibliography_section(text) >= 0

    def test_references_english(self):
        text = "## References\n- Entry"
        assert _find_bibliography_section(text) >= 0

    def test_not_found(self):
        text = "## Einleitung\nNormaler Text."
        assert _find_bibliography_section(text) == -1


# --- Merge-Logik ---


class TestExtractAllReferences:
    def test_merge_inline_with_biblio(self):
        text = """## 1. Einleitung

Laut (Mueller 2024) ist das korrekt.

## Literaturverzeichnis

- Mueller et al. (2024): Adaptive Traffic Control. Transportation Research.
"""
        results = extract_all_references(text)
        # Inline-Zitat sollte Titel aus Biblio bekommen
        inline_results = [r for r in results if not r.from_bibliography]
        assert len(inline_results) == 1
        assert inline_results[0].title == "Adaptive Traffic Control"

    def test_biblio_only_entry(self):
        text = """## Einleitung

Kein Inline-Zitat hier.

## Literaturverzeichnis

- Weber (2023): Unzitiertes Paper. Journal.
"""
        results = extract_all_references(text)
        # Biblio-Eintrag ohne Inline-Match bleibt als Biblio-Eintrag erhalten
        assert len(results) == 1
        assert results[0].authors == ["Weber"]
        assert results[0].year == 2023
        assert results[0].title == "Unzitiertes Paper"

    def test_sample_fixture(self):
        text = """# KI-basierte Verkehrssteuerung

## 1. Einleitung

Emissionen um bis zu 30% reduzieren.

## Literaturverzeichnis

- Mller et al. (2024): Adaptive Traffic Control with Deep RL. Transportation Research.
- Stadt Hamburg (2025): Evaluationsbericht ITS-Pilotprojekt.
- European Commission (2023): Sustainable Urban Mobility Plans.
"""
        results = extract_all_references(text)
        assert len(results) == 3  # Alle 3 Biblio-Eintraege
