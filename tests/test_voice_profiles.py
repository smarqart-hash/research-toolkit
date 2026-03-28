"""Tests fuer die neuen Voice-Profile (F-002).

Prueft Schema-Validierung und korrekte Felder fuer:
- konservativ_de
- progressiv_de
- b1_de
- executive_en
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.drafting import VoiceProfile, load_voice_profile

PROFILES_DIR = Path(__file__).parent.parent / "config" / "voice_profiles"

# --- Hilfsfunktion ---


def _load(name: str) -> VoiceProfile:
    """Laedt Profil aus dem Test-Verzeichnis."""
    return load_voice_profile(name, profiles_dir=PROFILES_DIR)


# --- Schema-Validierung fuer alle neuen Profile ---


class TestKonservativDe:
    """Tests fuer konservativ_de Voice-Profil."""

    def test_loads_without_error(self) -> None:
        profile = _load("konservativ_de")
        assert isinstance(profile, VoiceProfile)

    def test_name_correct(self) -> None:
        profile = _load("konservativ_de")
        assert profile.name == "konservativ_de"

    def test_required_fields_non_empty(self) -> None:
        profile = _load("konservativ_de")
        assert profile.description != ""
        assert profile.formality != ""
        assert profile.passive_ratio != ""
        assert profile.tone != ""

    def test_typical_phrases_non_empty(self) -> None:
        profile = _load("konservativ_de")
        assert len(profile.typical_phrases) >= 5

    def test_dos_donts_non_empty(self) -> None:
        profile = _load("konservativ_de")
        assert len(profile.dos) >= 3
        assert len(profile.donts) >= 3

    def test_structural_patterns_has_keys(self) -> None:
        profile = _load("konservativ_de")
        assert "opening" in profile.structural_patterns
        assert "body" in profile.structural_patterns
        assert "conclusion" in profile.structural_patterns

    def test_sentence_length_has_avg(self) -> None:
        profile = _load("konservativ_de")
        assert "avg" in profile.sentence_length

    def test_passive_ratio_range(self) -> None:
        """Passivrate soll 20-30% sein (ordnungspolitisch weniger passiv als akademisch)."""
        profile = _load("konservativ_de")
        assert "20" in profile.passive_ratio or "30" in profile.passive_ratio

    def test_ordnungspolitische_phrasen(self) -> None:
        """Mindestens eine ordnungspolitische Phrase vorhanden."""
        profile = _load("konservativ_de")
        joined = " ".join(profile.typical_phrases).lower()
        assert any(term in joined for term in ["marktwirtschaft", "eigenverantwortung", "subsidiarit", "ordnung"])


class TestProgressivDe:
    """Tests fuer progressiv_de Voice-Profil."""

    def test_loads_without_error(self) -> None:
        profile = _load("progressiv_de")
        assert isinstance(profile, VoiceProfile)

    def test_name_correct(self) -> None:
        profile = _load("progressiv_de")
        assert profile.name == "progressiv_de"

    def test_required_fields_non_empty(self) -> None:
        profile = _load("progressiv_de")
        assert profile.description != ""
        assert profile.formality != ""
        assert profile.passive_ratio != ""
        assert profile.tone != ""

    def test_typical_phrases_non_empty(self) -> None:
        profile = _load("progressiv_de")
        assert len(profile.typical_phrases) >= 5

    def test_dos_donts_non_empty(self) -> None:
        profile = _load("progressiv_de")
        assert len(profile.dos) >= 3
        assert len(profile.donts) >= 3

    def test_structural_patterns_has_keys(self) -> None:
        profile = _load("progressiv_de")
        assert "opening" in profile.structural_patterns
        assert "body" in profile.structural_patterns
        assert "conclusion" in profile.structural_patterns

    def test_sentence_length_has_avg(self) -> None:
        profile = _load("progressiv_de")
        assert "avg" in profile.sentence_length

    def test_passive_ratio_range(self) -> None:
        """Passivrate soll 25-35% sein."""
        profile = _load("progressiv_de")
        assert "25" in profile.passive_ratio or "35" in profile.passive_ratio

    def test_soziale_phrasen(self) -> None:
        """Mindestens eine sozialpolitische Phrase vorhanden."""
        profile = _load("progressiv_de")
        joined = " ".join(profile.typical_phrases).lower()
        assert any(term in joined for term in ["teilhabe", "chancen", "strukturell", "solidar", "inklusion"])


class TestB1De:
    """Tests fuer b1_de Voice-Profil (Einfache Sprache)."""

    def test_loads_without_error(self) -> None:
        profile = _load("b1_de")
        assert isinstance(profile, VoiceProfile)

    def test_name_correct(self) -> None:
        profile = _load("b1_de")
        assert profile.name == "b1_de"

    def test_required_fields_non_empty(self) -> None:
        profile = _load("b1_de")
        assert profile.description != ""
        assert profile.formality != ""
        assert profile.passive_ratio != ""
        assert profile.tone != ""

    def test_typical_phrases_non_empty(self) -> None:
        profile = _load("b1_de")
        assert len(profile.typical_phrases) >= 5

    def test_dos_donts_non_empty(self) -> None:
        profile = _load("b1_de")
        assert len(profile.dos) >= 3
        assert len(profile.donts) >= 3

    def test_structural_patterns_has_keys(self) -> None:
        profile = _load("b1_de")
        assert "opening" in profile.structural_patterns
        assert "body" in profile.structural_patterns
        assert "conclusion" in profile.structural_patterns

    def test_kurze_saetze(self) -> None:
        """B1-Profil muss kurze Saetze haben (avg <= 15)."""
        profile = _load("b1_de")
        avg = profile.sentence_length.get("avg", 99)
        assert avg <= 15, f"B1-Profil soll avg <= 15 Woerter haben, hat aber {avg}"

    def test_niedrige_passivrate(self) -> None:
        """B1-Profil soll niedrige Passivrate haben (5-10%)."""
        profile = _load("b1_de")
        assert "5" in profile.passive_ratio or "10" in profile.passive_ratio

    def test_einfache_phrasen(self) -> None:
        """Mindestens eine alltagsnahe Phrase vorhanden."""
        profile = _load("b1_de")
        joined = " ".join(profile.typical_phrases).lower()
        assert any(term in joined for term in ["das bedeutet", "zum beispiel", "einfach gesagt"])

    def test_paragraph_length_kurz(self) -> None:
        """B1-Absaetze sollen kurz sein."""
        profile = _load("b1_de")
        avg = profile.paragraph_length.get("avg_sentences", "")
        # "2-3" oder aehnliches, jedenfalls kein "4-6"
        assert avg != "", "paragraph_length.avg_sentences fehlt"
        assert "2" in str(avg), f"B1-Absaetze sollen bei 2-3 Saetzen liegen, hat: {avg}"


class TestExecutiveEn:
    """Tests fuer executive_en Voice-Profil."""

    def test_loads_without_error(self) -> None:
        profile = _load("executive_en")
        assert isinstance(profile, VoiceProfile)

    def test_name_correct(self) -> None:
        profile = _load("executive_en")
        assert profile.name == "executive_en"

    def test_required_fields_non_empty(self) -> None:
        profile = _load("executive_en")
        assert profile.description != ""
        assert profile.formality != ""
        assert profile.passive_ratio != ""
        assert profile.tone != ""

    def test_typical_phrases_non_empty(self) -> None:
        profile = _load("executive_en")
        assert len(profile.typical_phrases) >= 5

    def test_dos_donts_non_empty(self) -> None:
        profile = _load("executive_en")
        assert len(profile.dos) >= 3
        assert len(profile.donts) >= 3

    def test_structural_patterns_has_keys(self) -> None:
        profile = _load("executive_en")
        assert "opening" in profile.structural_patterns
        assert "body" in profile.structural_patterns
        assert "conclusion" in profile.structural_patterns

    def test_kurze_saetze(self) -> None:
        """Executive-Profil muss sehr kurze Saetze haben (avg <= 14)."""
        profile = _load("executive_en")
        avg = profile.sentence_length.get("avg", 99)
        assert avg <= 14, f"Executive-Profil soll avg <= 14 Woerter haben, hat aber {avg}"

    def test_niedrige_passivrate(self) -> None:
        """Executive-Profil soll niedrige Passivrate haben (10-15%)."""
        profile = _load("executive_en")
        assert "10" in profile.passive_ratio or "15" in profile.passive_ratio

    def test_executive_phrasen(self) -> None:
        """Mindestens eine entscheidungsorientierte Phrase vorhanden."""
        profile = _load("executive_en")
        joined = " ".join(profile.typical_phrases).lower()
        assert any(
            term in joined
            for term in ["key takeaway", "bottom line", "action required", "evidence suggests"]
        )

    def test_english_description(self) -> None:
        """Executive-Profil ist auf Englisch — description enthaelt englische Woerter."""
        profile = _load("executive_en")
        assert any(word in profile.description.lower() for word in ["executive", "decision", "briefing", "summary"])


# --- Gemeinsame Konsistenz-Tests fuer alle 4 Profile ---


@pytest.mark.parametrize("name", ["konservativ_de", "progressiv_de", "b1_de", "executive_en"])
class TestAllProfiles:
    """Schema-Konsistenz fuer alle neuen Profile."""

    def test_is_voice_profile_instance(self, name: str) -> None:
        profile = _load(name)
        assert isinstance(profile, VoiceProfile)

    def test_name_matches_filename(self, name: str) -> None:
        profile = _load(name)
        assert profile.name == name

    def test_transition_patterns_non_empty(self, name: str) -> None:
        profile = _load(name)
        assert len(profile.transition_patterns) >= 3

    def test_sentence_length_has_range(self, name: str) -> None:
        profile = _load(name)
        assert "range" in profile.sentence_length

    def test_paragraph_length_has_avg_sentences(self, name: str) -> None:
        profile = _load(name)
        assert "avg_sentences" in profile.paragraph_length
