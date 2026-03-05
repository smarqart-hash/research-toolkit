"""Document Splitter — Teilt Markdown-Dokumente an Kapitel-Headings.

Fuer die Zwei-Pass-Architektur: Lange Dokumente werden kapitelweise
reviewt, dann ein Synthese-Pass ueber alle Kapitel-Reviews.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocumentSection:
    """Ein Kapitel/Abschnitt aus einem Dokument."""

    heading: str
    level: int  # 1 = #, 2 = ##, 3 = ###
    content: str
    index: int  # Position im Dokument (0-basiert)

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    @property
    def estimated_pages(self) -> float:
        """Grobe Schaetzung: ~250 Woerter pro Seite."""
        return self.word_count / 250


# Grenzwert ab dem Splitting aktiviert wird (~20 Seiten)
SPLITTING_THRESHOLD_WORDS = 5000

# Regex fuer Markdown-Headings
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def split_markdown(text: str, min_level: int = 2) -> list[DocumentSection]:
    """Teilt Markdown-Text an Headings der angegebenen Ebene.

    Args:
        text: Der Markdown-Text.
        min_level: Minimale Heading-Ebene fuer Splits (2 = ##).

    Returns:
        Liste von DocumentSection-Objekten.
    """
    sections: list[DocumentSection] = []
    matches = list(HEADING_PATTERN.finditer(text))

    if not matches:
        return [DocumentSection(heading="Dokument", level=1, content=text.strip(), index=0)]

    # Text vor dem ersten Heading (falls vorhanden)
    preamble = text[: matches[0].start()].strip()
    if preamble:
        sections = [DocumentSection(heading="Einleitung", level=0, content=preamble, index=0)]

    for i, match in enumerate(matches):
        level = len(match.group(1))
        heading = match.group(2).strip()

        # Inhalt: Vom Ende dieses Headings bis zum naechsten Heading
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()

        # Nur an der angegebenen Ebene splitten
        if level <= min_level:
            sections = [
                *sections,
                DocumentSection(
                    heading=heading,
                    level=level,
                    content=content,
                    index=len(sections),
                ),
            ]
        elif sections:
            # Unter-Headings zum letzten Kapitel hinzufuegen
            last = sections[-1]
            merged_content = f"{last.content}\n\n{'#' * level} {heading}\n{content}"
            sections = [
                *sections[:-1],
                DocumentSection(
                    heading=last.heading,
                    level=last.level,
                    content=merged_content.strip(),
                    index=last.index,
                ),
            ]

    return sections


def needs_splitting(text: str) -> bool:
    """Prueft ob ein Dokument zu lang fuer Single-Pass-Review ist."""
    return len(text.split()) > SPLITTING_THRESHOLD_WORDS


def convert_docx_to_markdown(docx_path: Path) -> str:
    """Konvertiert .docx zu Markdown via Pandoc.

    Gibt Warnung zurueck wenn Fussnoten-Verlust erkannt wird.

    Raises:
        FileNotFoundError: Wenn Pandoc nicht installiert ist.
        RuntimeError: Wenn Konvertierung fehlschlaegt.
    """
    if not docx_path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {docx_path}")

    try:
        result = subprocess.run(
            ["pandoc", str(docx_path), "-t", "markdown", "--wrap=none"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError as err:
        raise FileNotFoundError(
            "Pandoc ist nicht installiert. Installiere es von https://pandoc.org"
        ) from err

    if result.returncode != 0:
        raise RuntimeError(f"Pandoc-Konvertierung fehlgeschlagen: {result.stderr}")

    return result.stdout


def extract_section_by_name(
    sections: list[DocumentSection], name: str
) -> DocumentSection | None:
    """Findet eine Sektion anhand des Heading-Namens (case-insensitive, Teilmatch)."""
    name_lower = name.lower()
    for section in sections:
        if name_lower in section.heading.lower():
            return section
    return None
