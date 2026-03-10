"""Tests fuer CLI Commands."""

from __future__ import annotations

from unittest.mock import patch

from src.agents.doctor import check_dependencies


class TestDoctor:
    """Testet den doctor-Command / check_dependencies."""

    def test_openalex_always_available(self):
        """OpenAlex braucht keinen Key — immer verfuegbar."""
        result = check_dependencies()
        openalex = [d for d in result if d.name == "OpenAlex Search"][0]
        assert openalex.available is True

    def test_ss_depends_on_key(self):
        """Semantic Scholar ohne Key: verfuegbar aber limited."""
        with patch.dict("os.environ", {}, clear=True):
            result = check_dependencies()
            ss = [d for d in result if d.name == "Semantic Scholar"][0]
            assert ss.available is True
            assert "rate limit" in ss.note.lower() or "limited" in ss.note.lower()

    def test_ss_with_key(self):
        """Semantic Scholar mit Key: voll verfuegbar."""
        with patch.dict("os.environ", {"S2_API_KEY": "test-key"}):
            result = check_dependencies()
            ss = [d for d in result if d.name == "Semantic Scholar"][0]
            assert ss.available is True
            assert ss.note == "" or "full" in ss.note.lower()

    def test_exa_depends_on_key(self):
        """Exa ohne Key: nicht verfuegbar."""
        with patch.dict("os.environ", {}, clear=True):
            result = check_dependencies()
            exa = [d for d in result if d.name == "Exa Search"][0]
            assert exa.available is False

    def test_specter2_check(self):
        """SPECTER2 Pruefung."""
        result = check_dependencies()
        specter2 = [d for d in result if d.name == "SPECTER2 Ranking"][0]
        # Entweder True oder False — beides ok, Hauptsache geprueft
        assert isinstance(specter2.available, bool)

    def test_all_dependencies_have_name(self):
        """Jede Dependency hat einen Namen."""
        result = check_dependencies()
        assert len(result) >= 5
        for dep in result:
            assert dep.name
            assert isinstance(dep.available, bool)
