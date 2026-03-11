"""BibTeX-Import: Parst .bib-Dateien und konvertiert zu UnifiedPaper."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser

from src.agents.paper_ranker import UnifiedPaper

logger = logging.getLogger(__name__)


def _entry_to_paper(entry: dict) -> UnifiedPaper | None:
    """Konvertiert einen BibTeX-Eintrag zu UnifiedPaper. Gibt None bei fehlenden Pflichtfeldern."""
    title = entry.get("title", "").strip()
    if not title:
        logger.warning("BibTeX-Eintrag ohne Titel uebersprungen: %s", entry.get("ID", "?"))
        return None

    doi = entry.get("doi", "").strip() or None
    paper_id = doi if doi else f"import:{hashlib.sha256(title.encode()).hexdigest()[:16]}"

    # Autoren: BibTeX trennt mit " and "
    raw_authors = entry.get("author", "")
    authors = [a.strip() for a in raw_authors.split(" and ")] if raw_authors.strip() else []

    # Jahr parsen
    year_str = entry.get("year", "").strip()
    year = int(year_str) if year_str.isdigit() else None

    abstract = entry.get("abstract", "").strip() or None

    return UnifiedPaper(
        paper_id=paper_id,
        title=title,
        abstract=abstract,
        year=year,
        authors=authors,
        citation_count=None,
        source="import",
        doi=doi,
        url=entry.get("url", "").strip() or None,
    )


def parse_bibtex_string(bib_string: str) -> list[UnifiedPaper]:
    """Parst einen BibTeX-String und gibt eine Liste von UnifiedPaper zurueck."""
    if not bib_string.strip():
        return []

    parser = BibTexParser(common_strings=True)
    bib_db = bibtexparser.loads(bib_string, parser=parser)

    papers: list[UnifiedPaper] = []
    for entry in bib_db.entries:
        paper = _entry_to_paper(entry)
        if paper is not None:
            papers = [*papers, paper]

    return papers


def parse_bibtex_file(path: Path) -> list[UnifiedPaper]:
    """Parst eine .bib-Datei und gibt eine Liste von UnifiedPaper zurueck."""
    if not path.exists():
        raise FileNotFoundError(f"BibTeX-Datei nicht gefunden: {path}")

    bib_string = path.read_text(encoding="utf-8")
    return parse_bibtex_string(bib_string)
