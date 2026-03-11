"""Tests fuer CLI Commands."""

from __future__ import annotations

from unittest.mock import patch

from src.agents.doctor import check_dependencies


class TestDoctor:
    """Testet den doctor-Command / check_dependencies."""

    def test_openalex_always_available(self):
        """OpenAlex braucht keinen Key — immer verfuegbar."""
        with patch.dict("os.environ", {}, clear=True):
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


class TestPapersImportFlag:
    """Tests fuer --papers CLI Flag."""

    def test_papers_flag_file_not_found(self):
        """CLI gibt Fehler bei nicht-existenter .bib Datei."""
        from typer.testing import CliRunner

        from cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["search", "test", "--papers", "/nonexistent.bib"])
        assert result.exit_code != 0
        assert "nicht gefunden" in result.output or "not found" in result.output.lower()

    def test_papers_flag_passes_to_config(self, tmp_path, monkeypatch):
        """--papers wird korrekt an SearchConfig weitergegeben."""
        bib = tmp_path / "refs.bib"
        bib.write_text("@article{x, author={A}, title={Test}, year={2024}}", encoding="utf-8")

        captured_config = {}

        async def mock_search(topic, *, config=None, **kwargs):
            captured_config["papers_file"] = config.papers_file if config else None
            return [], {"ss_total": 0, "openalex_total": 0, "exa_total": 0, "import_total": 0}, None

        monkeypatch.setattr("src.agents.forschungsstand.search_papers", mock_search)

        from typer.testing import CliRunner

        from cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["search", "test", "--papers", str(bib)])
        assert captured_config.get("papers_file") == bib
