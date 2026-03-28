"""Tests fuer neue Venue-Profile: quick_impuls_de und executive_brief_en."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.drafting import VenueProfile, load_venue_profile

PROFILES_DIR = Path("config/venue_profiles")


# --- Helfer ---


def _load(venue_id: str) -> VenueProfile:
    """Laedt ein echtes Profil aus config/venue_profiles/."""
    return load_venue_profile(venue_id, profiles_dir=PROFILES_DIR)


# --- quick_impuls_de ---


class TestQuickImpulsDe:
    def test_loads_successfully(self):
        profile = _load("quick_impuls_de")
        assert profile.venue_id == "quick_impuls_de"

    def test_name(self):
        profile = _load("quick_impuls_de")
        assert profile.name == "Quick Impuls (DE)"

    def test_type(self):
        profile = _load("quick_impuls_de")
        assert profile.type == "briefing"

    def test_language(self):
        profile = _load("quick_impuls_de")
        assert profile.language == "de"

    def test_page_range(self):
        profile = _load("quick_impuls_de")
        assert profile.page_range == [2, 3]

    def test_citation_style(self):
        profile = _load("quick_impuls_de")
        assert profile.citation_style == "apa"

    def test_citation_format(self):
        profile = _load("quick_impuls_de")
        assert profile.citation_format == "(Autor, Jahr)"

    def test_sections(self):
        profile = _load("quick_impuls_de")
        assert profile.sections == [
            "Kernaussage",
            "Hintergrund",
            "Analyse",
            "Fazit & Ausblick",
            "Quellen",
        ]

    def test_no_handlungsempfehlungen(self):
        """Keine Handlungsempfehlungen — Format zu kurz."""
        profile = _load("quick_impuls_de")
        assert profile.handlungsempfehlungen == {}

    def test_review_criteria(self):
        profile = _load("quick_impuls_de")
        assert "evidence_quality" in profile.review_criteria
        assert "clarity" in profile.review_criteria
        assert "completeness" in profile.review_criteria

    def test_ai_disclosure_required(self):
        profile = _load("quick_impuls_de")
        assert profile.ai_disclosure_required is True

    def test_is_valid_venue_profile(self):
        """Pydantic-Schema-Validierung erfolgreich."""
        profile = _load("quick_impuls_de")
        assert isinstance(profile, VenueProfile)


# --- executive_brief_en ---


class TestExecutiveBriefEn:
    def test_loads_successfully(self):
        profile = _load("executive_brief_en")
        assert profile.venue_id == "executive_brief_en"

    def test_name(self):
        profile = _load("executive_brief_en")
        assert profile.name == "Executive Brief (EN)"

    def test_type(self):
        profile = _load("executive_brief_en")
        assert profile.type == "briefing"

    def test_language(self):
        profile = _load("executive_brief_en")
        assert profile.language == "en"

    def test_page_range(self):
        profile = _load("executive_brief_en")
        assert profile.page_range == [1, 2]

    def test_citation_style(self):
        profile = _load("executive_brief_en")
        assert profile.citation_style == "numeric"

    def test_citation_format(self):
        profile = _load("executive_brief_en")
        assert profile.citation_format == "[1], [2]"

    def test_sections(self):
        profile = _load("executive_brief_en")
        assert profile.sections == [
            "Executive Summary",
            "Key Findings",
            "Implications",
            "Recommended Actions",
            "Sources",
        ]

    def test_handlungsempfehlungen_format(self):
        profile = _load("executive_brief_en")
        assert "format" in profile.handlungsempfehlungen
        assert profile.handlungsempfehlungen["format"] == "Numbered actions with owner/timeline"

    def test_handlungsempfehlungen_example(self):
        profile = _load("executive_brief_en")
        assert "example" in profile.handlungsempfehlungen
        assert "[Action]" in profile.handlungsempfehlungen["example"]

    def test_review_criteria(self):
        profile = _load("executive_brief_en")
        assert "actionability" in profile.review_criteria
        assert "clarity" in profile.review_criteria
        assert "evidence_quality" in profile.review_criteria

    def test_ai_disclosure_required(self):
        profile = _load("executive_brief_en")
        assert profile.ai_disclosure_required is True

    def test_is_valid_venue_profile(self):
        """Pydantic-Schema-Validierung erfolgreich."""
        profile = _load("executive_brief_en")
        assert isinstance(profile, VenueProfile)
