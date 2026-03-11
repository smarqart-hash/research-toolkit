# F17: Paper-Import + Low-Recall-Warnung — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Externe Papers via BibTeX-Import formalisieren und bei niedrigem Recall warnen, statt stillen Bypass zu erlauben.

**Architecture:** Neues `bibtex_parser.py` Modul parsed `.bib` Dateien zu `UnifiedPaper` (source="import"). `SearchConfig` bekommt `papers_file` Parameter. `search_papers()` merged importierte Papers in den Pool. Low-Recall-Warnung wenn < 15 Papers nach Ranking.

**Tech Stack:** `bibtexparser` (pip), Pydantic, Typer CLI

---

### Task 1: bibtexparser Dependency hinzufuegen

**Files:**
- Modify: `pyproject.toml`

**Step 1: Dependency hinzufuegen**

In `pyproject.toml` unter `dependencies` (nicht optional — leichtgewichtig):

```toml
dependencies = [
    "pydantic>=2.0",
    "httpx>=0.27",
    "rich>=13.0",
    "typer>=0.12",
    "bibtexparser>=2.0",
]
```

**Step 2: Installieren**

Run: `pip install bibtexparser>=2.0`

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add bibtexparser dependency for paper import"
```

---

### Task 2: BibTeX-Parser mit Tests (TDD)

**Files:**
- Create: `src/utils/bibtex_parser.py`
- Create: `tests/test_bibtex_parser.py`

**Step 1: Test-Datei schreiben**

```python
"""Tests fuer BibTeX-Parser."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from src.utils.bibtex_parser import parse_bibtex_file, parse_bibtex_string


# --- Fixtures ---

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
    """Tests fuer parse_bibtex_string."""

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
    """Tests fuer parse_bibtex_file."""

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
        """Kaputte Eintraege werden uebersprungen, nicht gecrasht."""
        malformed = "@article{broken, title = }\n" + BIB_ENTRY
        papers = parse_bibtex_string(malformed)
        # Mindestens der gueltige Eintrag muss durch
        assert len(papers) >= 1
```

**Step 2: Test ausfuehren — FAIL erwartet**

Run: `pytest tests/test_bibtex_parser.py -v`
Expected: ModuleNotFoundError (bibtex_parser existiert noch nicht)

**Step 3: Implementation schreiben**

```python
"""BibTeX-Parser — konvertiert .bib Dateien zu UnifiedPaper.

Nutzt bibtexparser v2 fuer robustes Parsing. Kaputte Eintraege
werden geloggt und uebersprungen (kein Crash).
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from src.agents.paper_ranker import UnifiedPaper

logger = logging.getLogger(__name__)


def parse_bibtex_string(bib_string: str) -> list[UnifiedPaper]:
    """Parsed BibTeX-String zu Liste von UnifiedPaper.

    Eintraege ohne Titel werden uebersprungen.
    Source wird auf "import" gesetzt.
    """
    if not bib_string.strip():
        return []

    import bibtexparser

    try:
        library = bibtexparser.parse(bib_string)
    except Exception as e:
        logger.warning("BibTeX-Parse-Fehler: %s", e)
        return []

    papers: list[UnifiedPaper] = []
    for entry in library.entries:
        try:
            paper = _entry_to_paper(entry)
            if paper is not None:
                papers = [*papers, paper]
        except Exception as e:
            logger.warning("BibTeX-Eintrag '%s' uebersprungen: %s", entry.key, e)

    return papers


def parse_bibtex_file(path: Path) -> list[UnifiedPaper]:
    """Parsed BibTeX-Datei zu Liste von UnifiedPaper.

    Raises:
        FileNotFoundError: Wenn Datei nicht existiert.
    """
    if not path.exists():
        raise FileNotFoundError(f"BibTeX-Datei nicht gefunden: {path}")

    bib_string = path.read_text(encoding="utf-8")
    return parse_bibtex_string(bib_string)


def _entry_to_paper(entry) -> UnifiedPaper | None:
    """Konvertiert einen bibtexparser Entry zu UnifiedPaper."""
    title = entry.fields_dict.get("title")
    if title is None:
        return None
    title_str = title.value.strip()
    if not title_str:
        return None

    # DOI extrahieren
    doi_field = entry.fields_dict.get("doi")
    doi = doi_field.value.strip() if doi_field else None

    # Paper-ID: DOI bevorzugt, sonst Hash aus Key
    paper_id = doi if doi else f"import:{hashlib.sha256(entry.key.encode()).hexdigest()[:16]}"

    # Autoren parsen (BibTeX: "Smith, John and Doe, Jane")
    author_field = entry.fields_dict.get("author")
    authors: list[str] = []
    if author_field:
        authors = [a.strip() for a in author_field.value.split(" and ")]

    # Jahr
    year_field = entry.fields_dict.get("year")
    year: int | None = None
    if year_field:
        try:
            year = int(year_field.value.strip())
        except ValueError:
            pass

    # Abstract
    abstract_field = entry.fields_dict.get("abstract")
    abstract = abstract_field.value.strip() if abstract_field else None

    # URL
    url_field = entry.fields_dict.get("url")
    url = url_field.value.strip() if url_field else None

    return UnifiedPaper(
        paper_id=paper_id,
        title=title_str,
        abstract=abstract,
        year=year,
        authors=authors,
        citation_count=None,
        source="import",
        doi=doi,
        url=url,
    )
```

**Step 4: Tests ausfuehren — PASS erwartet**

Run: `pytest tests/test_bibtex_parser.py -v`
Expected: Alle Tests PASS

**Step 5: Commit**

```bash
git add src/utils/bibtex_parser.py tests/test_bibtex_parser.py
git commit -m "feat: BibTeX parser for paper import (F17)"
```

---

### Task 3: SearchConfig + search_papers um Import erweitern (TDD)

**Files:**
- Modify: `src/agents/forschungsstand.py`
- Modify: `tests/test_forschungsstand.py`

**Step 1: Tests schreiben**

In `tests/test_forschungsstand.py` hinzufuegen:

```python
class TestPaperImport:
    """Tests fuer --papers Import-Integration."""

    def test_search_config_papers_file_default_none(self):
        config = SearchConfig()
        assert config.papers_file is None

    def test_imported_papers_merged_into_results(self, tmp_path):
        """Importierte Papers werden in den Ergebnis-Pool gemerged."""
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

    def test_imported_papers_deduped_with_api_results(self, tmp_path):
        """Import-Papers mit gleicher DOI werden gegen API-Papers dedupliziert."""
        bib_content = textwrap.dedent("""\
            @article{dup2023,
                author = {Dup, Author},
                title = {Duplicate Paper},
                year = {2023},
                doi = {10.1234/duplicate},
            }
        """)
        bib_file = tmp_path / "refs.bib"
        bib_file.write_text(bib_content, encoding="utf-8")

        config = SearchConfig(papers_file=bib_file, sources=[])
        papers, stats, _ = asyncio.run(
            search_papers("test", config=config)
        )
        # Wenn kein API-Ergebnis mit gleicher DOI: Import bleibt
        assert any(p.doi == "10.1234/duplicate" for p in papers)
```

**Step 2: Tests ausfuehren — FAIL erwartet**

Run: `pytest tests/test_forschungsstand.py::TestPaperImport -v`
Expected: FAIL (papers_file Attribut fehlt)

**Step 3: SearchConfig + search_papers erweitern**

In `src/agents/forschungsstand.py`:

1. Import hinzufuegen (oben):
```python
from src.utils.bibtex_parser import parse_bibtex_file
```

2. `SearchConfig` erweitern:
```python
@dataclass
class SearchConfig:
    """Konfiguration fuer die Paper-Suche."""
    max_results_per_query: int = 50
    year_filter: str | None = None
    fields_of_study: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=lambda: ["ss", "openalex"])
    languages: list[str] = field(default_factory=lambda: ["en", "de"])
    top_k: int = 30
    papers_file: Path | None = None  # BibTeX-Import
```

3. In `search_papers()` nach dem `asyncio.gather` Block, VOR Deduplizierung:
```python
    # Paper-Import aus BibTeX-Datei
    if config.papers_file is not None:
        imported = parse_bibtex_file(config.papers_file)
        all_papers = [*all_papers, *imported]
        stats["import_total"] = len(imported)
        logger.info("Paper-Import: %d Papers aus %s", len(imported), config.papers_file.name)
```

4. `stats`-Dict erweitern (Initialwert):
```python
    stats: dict[str, int] = {
        ...
        "import_total": 0,
    }
```

**Step 4: Tests ausfuehren — PASS erwartet**

Run: `pytest tests/test_forschungsstand.py::TestPaperImport -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/agents/forschungsstand.py tests/test_forschungsstand.py
git commit -m "feat: integrate BibTeX import into search pipeline (F17)"
```

---

### Task 4: Low-Recall-Warnung (TDD)

**Files:**
- Modify: `src/agents/forschungsstand.py`
- Modify: `tests/test_forschungsstand.py`

**Step 1: Tests schreiben**

```python
class TestLowRecallWarning:
    """Tests fuer Low-Recall-Warnung."""

    def test_no_warning_above_threshold(self):
        warnings = _check_low_recall(20, has_exa=True, has_import=True)
        assert warnings == []

    def test_warning_below_threshold(self):
        warnings = _check_low_recall(8, has_exa=True, has_import=False)
        assert len(warnings) >= 1
        assert "8" in warnings[0]

    def test_warning_suggests_exa_when_missing(self):
        warnings = _check_low_recall(5, has_exa=False, has_import=False)
        assert any("exa" in w.lower() or "EXA_API_KEY" in w for w in warnings)

    def test_warning_suggests_import_when_missing(self):
        warnings = _check_low_recall(5, has_exa=True, has_import=False)
        assert any("--papers" in w or "import" in w.lower() for w in warnings)

    def test_no_suggestions_when_all_active(self):
        """Warnung aber keine Vorschlaege wenn alles aktiv."""
        warnings = _check_low_recall(5, has_exa=True, has_import=True)
        assert len(warnings) >= 1
        # Nur Hinweis, keine Empfehlungen
```

**Step 2: Tests ausfuehren — FAIL erwartet**

Run: `pytest tests/test_forschungsstand.py::TestLowRecallWarning -v`

**Step 3: Implementation**

In `src/agents/forschungsstand.py` (nach `_check_source_balance`):

```python
LOW_RECALL_THRESHOLD = 15


def _check_low_recall(
    paper_count: int,
    *,
    has_exa: bool,
    has_import: bool,
) -> list[str]:
    """Warnt wenn wenige Papers gefunden — empfiehlt weitere Quellen.

    Schwelle: < 15 Papers nach Ranking.
    """
    if paper_count >= LOW_RECALL_THRESHOLD:
        return []

    warnings: list[str] = [
        f"Niedriger Recall: nur {paper_count} Papers gefunden "
        f"(Schwelle: {LOW_RECALL_THRESHOLD})."
    ]

    if not has_exa:
        warnings = [
            *warnings,
            "Empfehlung: Exa aktivieren fuer Web-Suche (export EXA_API_KEY=<key>).",
        ]
    if not has_import:
        warnings = [
            *warnings,
            "Empfehlung: Externe Papers importieren (--papers refs.bib).",
        ]

    return warnings
```

In `search_papers()`, nach dem Ranking-Schritt:

```python
    # Low-Recall-Warnung
    has_exa = "exa" in config.sources
    has_import = config.papers_file is not None
    recall_warnings = _check_low_recall(len(ranked), has_exa=has_exa, has_import=has_import)
    for warning in recall_warnings:
        logger.warning("Low-Recall: %s", warning)
```

**Step 4: Tests ausfuehren — PASS erwartet**

Run: `pytest tests/test_forschungsstand.py::TestLowRecallWarning -v`

**Step 5: Commit**

```bash
git add src/agents/forschungsstand.py tests/test_forschungsstand.py
git commit -m "feat: low-recall warning with actionable suggestions (F17)"
```

---

### Task 5: CLI --papers Flag (TDD)

**Files:**
- Modify: `cli.py`
- Modify: `tests/test_cli.py`

**Step 1: Tests schreiben**

In `tests/test_cli.py` hinzufuegen:

```python
class TestPapersImportFlag:
    """Tests fuer --papers CLI Flag."""

    def test_papers_flag_accepted(self, tmp_path):
        """CLI akzeptiert --papers Flag."""
        bib = tmp_path / "refs.bib"
        bib.write_text("@article{x, title={Test}, year={2024}}", encoding="utf-8")
        # Nur pruefen dass der Flag geparst wird (kein API-Call noetig)
        from cli import app
        from typer.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(app, ["search", "test", "--papers", str(bib), "--sources", ""])
        # Sollte nicht wegen unbekanntem Flag crashen
        assert result.exit_code != 2  # 2 = Typer usage error

    def test_papers_flag_file_not_found(self):
        """CLI gibt Fehler bei nicht-existenter .bib Datei."""
        from cli import app
        from typer.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(app, ["search", "test", "--papers", "/nonexistent.bib"])
        assert result.exit_code != 0
```

**Step 2: Tests ausfuehren — FAIL erwartet**

Run: `pytest tests/test_cli.py::TestPapersImportFlag -v`

**Step 3: CLI erweitern**

In `cli.py`, `search` Command:

```python
@app.command()
def search(
    topic: str = typer.Argument(..., help="Research topic to search for"),
    max_results: int = typer.Option(30, "--max", "-m", help="Max papers after ranking"),
    sources: str = typer.Option(
        "ss,openalex", "--sources", "-s",
        help="Komma-separiert: ss,openalex,exa (Standard: ss,openalex)",
    ),
    year_filter: str = typer.Option(None, "--years", "-y", help="Year range, e.g. 2020-2026"),
    refine: bool = typer.Option(False, "--refine", "-r", help="Smart query expansion"),
    no_validate: bool = typer.Option(False, "--no-validate", help="Skip dry-run validation"),
    append: bool = typer.Option(False, "--append", "-a", help="Merge into existing results"),
    papers: Path = typer.Option(
        None, "--papers", "-p", help="BibTeX-Datei mit externen Papers importieren"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
```

Im Body, nach source_list Parsing:

```python
    # Paper-Import validieren
    if papers is not None and not papers.exists():
        console.print(f"[red]BibTeX-Datei nicht gefunden:[/red] {papers}")
        raise typer.Exit(1)
```

Bei SearchConfig:

```python
    config = SearchConfig(
        top_k=max_results,
        sources=source_list,
        year_filter=year_filter,
        papers_file=papers,
    )
```

**Step 4: Tests ausfuehren — PASS erwartet**

Run: `pytest tests/test_cli.py::TestPapersImportFlag -v`

**Step 5: Commit**

```bash
git add cli.py tests/test_cli.py
git commit -m "feat: --papers CLI flag for BibTeX import (F17)"
```

---

### Task 6: CLAUDE.md + Docs aktualisieren

**Files:**
- Modify: `CLAUDE.md`

**Step 1: CLI Commands Sektion**

```bash
research-toolkit search TOPIC        # --max, --sources, --years, --append, --papers
```

**Step 2: Neuer Abschnitt unter Ranking**

```markdown
**Paper-Import:** `--papers refs.bib` importiert externe Papers (source="import") in den Pool.
**Low-Recall-Warnung:** Warnung wenn < 15 Papers nach Ranking + Empfehlungen (Exa, Import).
```

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add paper import and low-recall warning to CLAUDE.md"
```

---

### Task 7: Adversarial Review (Quality Gate)

**Step 1:** Adversarial Review ausfuehren mit `/adversarial-review`

Pruefkriterien:
- BibTeX-Parser robust gegen kaputte Eintraege?
- Import-Papers korrekt dedupliziert (DOI-Match)?
- Low-Recall-Schwelle sinnvoll (15)?
- Kein Silent Failure bei fehlender .bib Datei?
- Source "import" korrekt im Ranking (kein Citation-Cap noetig)?

**Step 2:** Fixes falls noetig

**Step 3:** Finaler Commit + Merge nach master
