"""Referenz-Extraktor — extrahiert Quellenangaben aus Dokumenten.

Zwei Stufen:
1. Regex: Harvard-Pattern (Autor Jahr), Literaturverzeichnis-Eintraege
2. LLM-Fallback: Fuer nicht-erkannte Referenzen (via Skill-Prompt)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pydantic import BaseModel, Field


class ReferenceCandidate(BaseModel):
    """Eine extrahierte Quellenangabe aus dem Dokument."""

    raw_text: str  # Originaltext wie im Dokument
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    title: str | None = None
    location: str = ""  # z.B. "Kap. 2, Abs. 3"
    page_ref: str | None = None  # z.B. "S. 15"
    source_type: str = "regex"  # "regex" oder "llm"
    from_bibliography: bool = False  # Aus dem Literaturverzeichnis


# --- Harvard-Patterns ---

# Inline-Zitate: (Mueller 2024), (Mueller et al. 2024), (Mueller/Schmidt 2024, S. 15)
INLINE_CITE_PATTERN = re.compile(
    r"\("
    r"(?P<authors>[A-ZÄÖÜ][a-zäöüß]+(?:\s+et\s+al\.)?(?:\s*[/,]\s*[A-ZÄÖÜ][a-zäöüß]+)*)"
    r"\s+"
    r"(?P<year>\d{4})"
    r"(?:,?\s*S\.\s*(?P<page>\d+(?:\s*[–-]\s*\d+)?))?"
    r"\)",
)

# Narrative Zitate: Mueller (2024), Mueller et al. (2024)
NARRATIVE_CITE_PATTERN = re.compile(
    r"(?P<authors>[A-ZÄÖÜ][a-zäöüß]+(?:\s+et\s+al\.)?)"
    r"\s+\((?P<year>\d{4})"
    r"(?:,?\s*S\.\s*(?P<page>\d+(?:\s*[–-]\s*\d+)?))?"
    r"\)",
)

# Literaturverzeichnis-Eintrag: - Autor et al. (Jahr): Titel. Journal.
BIBLIO_ENTRY_PATTERN = re.compile(
    r"^[-–•]\s*"
    r"(?P<authors>[A-ZÄÖÜ][^(]+?)"
    r"\((?P<year>\d{4})\)"
    r":\s*"
    r"(?P<title>[^\n.]+)"
    r"\.",
    re.MULTILINE,
)


def _parse_authors(author_str: str) -> list[str]:
    """Parst Autor-String in Liste."""
    author_str = author_str.strip().rstrip(",")
    # "Mueller et al." → ["Mueller"]
    if "et al" in author_str:
        base = author_str.split("et al")[0].strip()
        return [base]
    # "Mueller/Schmidt" oder "Mueller, Schmidt"
    if "/" in author_str:
        return [a.strip() for a in author_str.split("/")]
    if "," in author_str:
        return [a.strip() for a in author_str.split(",")]
    return [author_str.strip()]


def _find_section_for_position(text: str, pos: int) -> str:
    """Findet die Kapitel-Ueberschrift fuer eine Textposition."""
    # Suche rueckwaerts nach ## Heading
    section_pattern = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)
    last_section = "Dokument"
    for match in section_pattern.finditer(text):
        if match.start() <= pos:
            last_section = match.group(1).strip()
        else:
            break
    return last_section


def extract_inline_citations(text: str) -> list[ReferenceCandidate]:
    """Extrahiert Inline-Zitate (Klammer- und Narrativ-Stil).

    Sucht nur VOR dem Literaturverzeichnis, nicht darin.
    """
    # Nur Text vor dem Literaturverzeichnis durchsuchen
    biblio_start = _find_bibliography_section(text)
    search_text = text[:biblio_start] if biblio_start >= 0 else text

    candidates: list[ReferenceCandidate] = []
    seen_keys: set[str] = set()

    for pattern in [INLINE_CITE_PATTERN, NARRATIVE_CITE_PATTERN]:
        for match in pattern.finditer(search_text):
            authors = _parse_authors(match.group("authors"))
            year = int(match.group("year"))
            page = match.group("page") if "page" in match.groupdict() else None
            key = f"{','.join(authors)}_{year}"

            if key not in seen_keys:
                seen_keys.add(key)
                candidates = [
                    *candidates,
                    ReferenceCandidate(
                        raw_text=match.group(0),
                        authors=authors,
                        year=year,
                        location=_find_section_for_position(text, match.start()),
                        page_ref=f"S. {page}" if page else None,
                    ),
                ]

    return candidates


def extract_bibliography(text: str) -> list[ReferenceCandidate]:
    """Extrahiert Eintraege aus dem Literaturverzeichnis."""
    candidates: list[ReferenceCandidate] = []

    # Finde den Literaturverzeichnis-Abschnitt
    biblio_start = _find_bibliography_section(text)
    if biblio_start < 0:
        return []

    biblio_text = text[biblio_start:]

    for match in BIBLIO_ENTRY_PATTERN.finditer(biblio_text):
        authors = _parse_authors(match.group("authors"))
        year = int(match.group("year"))
        title = match.group("title").strip()

        candidates = [
            *candidates,
            ReferenceCandidate(
                raw_text=match.group(0).strip(),
                authors=authors,
                year=year,
                title=title,
                location="Literaturverzeichnis",
                from_bibliography=True,
            ),
        ]

    return candidates


def _find_bibliography_section(text: str) -> int:
    """Findet den Start des Literaturverzeichnisses."""
    patterns = [
        r"^#{1,3}\s*Literaturverzeichnis",
        r"^#{1,3}\s*Literatur\b",
        r"^#{1,3}\s*Quellen\b",
        r"^#{1,3}\s*Referenzen\b",
        r"^#{1,3}\s*References\b",
        r"^#{1,3}\s*Bibliography\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if match:
            return match.start()
    return -1


def extract_all_references(text: str) -> list[ReferenceCandidate]:
    """Extrahiert alle Referenzen (Inline + Literaturverzeichnis).

    Merge-Logik: Inline-Zitate werden mit Literaturverzeichnis-Eintraegen
    angereichert (Titel ergaenzen wenn gleicher Autor+Jahr).
    """
    inline = extract_inline_citations(text)
    biblio = extract_bibliography(text)

    # Biblio-Lookup nach Autor+Jahr
    biblio_lookup: dict[str, ReferenceCandidate] = {}
    for entry in biblio:
        if entry.authors and entry.year:
            key = f"{entry.authors[0]}_{entry.year}"
            biblio_lookup[key] = entry

    # Inline-Zitate mit Biblio-Titeln anreichern
    merged: list[ReferenceCandidate] = []
    matched_biblio_keys: set[str] = set()

    for cite in inline:
        key = f"{cite.authors[0]}_{cite.year}" if cite.authors and cite.year else ""
        if key in biblio_lookup:
            # Titel aus Biblio uebernehmen
            biblio_entry = biblio_lookup[key]
            enriched = cite.model_copy(
                update={"title": biblio_entry.title}
            )
            merged = [*merged, enriched]
            matched_biblio_keys.add(key)
        else:
            merged = [*merged, cite]

    # Biblio-Eintraege ohne Inline-Match separat hinzufuegen
    for entry in biblio:
        if entry.authors and entry.year:
            key = f"{entry.authors[0]}_{entry.year}"
            if key not in matched_biblio_keys:
                merged = [*merged, entry]

    return merged
