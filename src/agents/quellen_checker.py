"""Quellen-Checker — verifiziert Referenzen gegen Semantic Scholar + lokale Daten.

Lookup-Reihenfolge:
1. Lokale forschungsstand.json (falls vorhanden)
2. Semantic Scholar get_paper per DOI
3. Semantic Scholar search_papers per Titel+Autor
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path

import httpx
from pydantic import BaseModel, Field

from src.agents.paper_ranker import UnifiedPaper, from_semantic_scholar
from src.agents.reference_extractor import ReferenceCandidate
from src.agents.semantic_scholar import SemanticScholarClient

logger = logging.getLogger(__name__)


class CheckStatus(str, Enum):
    """Ergebnis-Status einer Quellen-Pruefung."""

    VERIFIED = "VERIFIED"
    NOT_FOUND = "NOT_FOUND"
    METADATA_MISMATCH = "METADATA_MISMATCH"
    CONTEXT_MISMATCH = "CONTEXT_MISMATCH"


class ReferenceCheckResult(BaseModel):
    """Ergebnis der Pruefung einer einzelnen Referenz."""

    status: CheckStatus
    candidate: ReferenceCandidate
    matched_paper: UnifiedPaper | None = None
    mismatches: list[str] = Field(default_factory=list)
    context_note: str | None = None  # Nur bei --context Flag


class QuellenCheckReport(BaseModel):
    """Gesamtbericht der Quellen-Pruefung."""

    document: str
    results: list[ReferenceCheckResult] = Field(default_factory=list)
    total_references: int = 0
    verified: int = 0
    not_found: int = 0
    metadata_mismatch: int = 0
    context_mismatch: int = 0
    lookup_errors: int = 0

    def compute_stats(self) -> None:
        """Berechnet Statistiken aus den Ergebnissen."""
        self.total_references = len(self.results)
        self.verified = sum(1 for r in self.results if r.status == CheckStatus.VERIFIED)
        self.not_found = sum(1 for r in self.results if r.status == CheckStatus.NOT_FOUND)
        self.metadata_mismatch = sum(
            1 for r in self.results if r.status == CheckStatus.METADATA_MISMATCH
        )
        self.context_mismatch = sum(
            1 for r in self.results if r.status == CheckStatus.CONTEXT_MISMATCH
        )


# --- Lokaler Lookup ---


def load_local_papers(forschungsstand_path: Path) -> dict[str, UnifiedPaper]:
    """Laedt Papers aus forschungsstand.json als Lookup-Dict.

    Keys: Titel (lowercase, normalisiert) und DOI (falls vorhanden).
    """
    if not forschungsstand_path.exists():
        return {}

    try:
        data = json.loads(forschungsstand_path.read_text(encoding="utf-8"))
        papers = [UnifiedPaper.model_validate(p) for p in data.get("papers", [])]
    except Exception:
        logger.warning("Konnte forschungsstand.json nicht laden: %s", forschungsstand_path)
        return {}

    lookup: dict[str, UnifiedPaper] = {}
    for paper in papers:
        # Titel-Key
        title_key = _normalize_title(paper.title)
        lookup[title_key] = paper
        # DOI-Key
        if paper.doi:
            lookup[f"doi:{paper.doi.lower()}"] = paper

    return lookup


def _normalize_title(title: str) -> str:
    """Normalisiert Titel fuer Matching."""
    normalized = "".join(c for c in title.lower() if c.isalnum() or c == " ")
    return " ".join(normalized.split())


# --- Metadaten-Vergleich ---


def compare_metadata(
    candidate: ReferenceCandidate, paper: UnifiedPaper
) -> list[str]:
    """Vergleicht Metadaten zwischen Zitat und gefundenem Paper."""
    mismatches: list[str] = []

    # Jahr pruefen
    if candidate.year and paper.year and candidate.year != paper.year:
        mismatches = [*mismatches, f"Jahr: {candidate.year} vs. {paper.year}"]

    # Autoren pruefen (erster Autor muss matchen)
    if candidate.authors and paper.authors:
        first_cited = candidate.authors[0].lower()
        paper_authors_lower = [a.lower() for a in paper.authors]
        if not any(first_cited in a for a in paper_authors_lower):
            mismatches = [
                *mismatches,
                f"Autor '{candidate.authors[0]}' nicht in {paper.authors[:3]}",
            ]

    # Titel pruefen (nur wenn Kandidat einen Titel hat)
    if candidate.title and paper.title:
        cand_title = _normalize_title(candidate.title)
        paper_title = _normalize_title(paper.title)
        # Fuzzy: mindestens 60% der Woerter muessen uebereinstimmen
        cand_words = set(cand_title.split())
        paper_words = set(paper_title.split())
        if cand_words and paper_words:
            overlap = len(cand_words & paper_words) / max(len(cand_words), 1)
            if overlap < 0.6:
                mismatches = [
                    *mismatches,
                    f"Titel weicht ab: '{candidate.title[:50]}' vs. '{paper.title[:50]}'",
                ]

    return mismatches


# --- Lookup-Logik ---


def check_against_local(
    candidate: ReferenceCandidate, local_papers: dict[str, UnifiedPaper]
) -> ReferenceCheckResult | None:
    """Prueft eine Referenz gegen lokale Paper-Daten.

    Returns None wenn nicht gefunden (weiter mit API-Lookup).
    """
    # Titel-Match
    if candidate.title:
        title_key = _normalize_title(candidate.title)
        if title_key in local_papers:
            paper = local_papers[title_key]
            mismatches = compare_metadata(candidate, paper)
            status = CheckStatus.METADATA_MISMATCH if mismatches else CheckStatus.VERIFIED
            return ReferenceCheckResult(
                status=status,
                candidate=candidate,
                matched_paper=paper,
                mismatches=mismatches,
            )

    # Autor+Jahr Match (durchsuche alle, tolerant: +/- 1 Jahr)
    if candidate.authors and candidate.year:
        for paper in local_papers.values():
            if paper.year and abs(paper.year - candidate.year) <= 1 and paper.authors:
                first_cited = candidate.authors[0].lower()
                if any(first_cited in a.lower() for a in paper.authors):
                    mismatches = compare_metadata(candidate, paper)
                    status = (
                        CheckStatus.METADATA_MISMATCH if mismatches else CheckStatus.VERIFIED
                    )
                    return ReferenceCheckResult(
                        status=status,
                        candidate=candidate,
                        matched_paper=paper,
                        mismatches=mismatches,
                    )

    return None


async def check_against_api(
    candidate: ReferenceCandidate,
    ss_client: SemanticScholarClient,
) -> ReferenceCheckResult:
    """Prueft eine Referenz gegen Semantic Scholar API."""
    # Versuch 1: Titel-Suche
    search_query = ""
    if candidate.title:
        search_query = candidate.title
    elif candidate.authors and candidate.year:
        search_query = f"{candidate.authors[0]} {candidate.year}"
    else:
        return ReferenceCheckResult(
            status=CheckStatus.NOT_FOUND,
            candidate=candidate,
            mismatches=["Zu wenig Informationen fuer API-Suche"],
        )

    try:
        response = await ss_client.search_papers(search_query, limit=5)
        if not response.data:
            return ReferenceCheckResult(
                status=CheckStatus.NOT_FOUND,
                candidate=candidate,
            )

        # Bestes Match finden
        best_match = _find_best_match(candidate, response.data)
        if best_match is None:
            return ReferenceCheckResult(
                status=CheckStatus.NOT_FOUND,
                candidate=candidate,
            )

        paper = from_semantic_scholar(best_match)
        mismatches = compare_metadata(candidate, paper)
        status = CheckStatus.METADATA_MISMATCH if mismatches else CheckStatus.VERIFIED
        return ReferenceCheckResult(
            status=status,
            candidate=candidate,
            matched_paper=paper,
            mismatches=mismatches,
        )

    except httpx.HTTPStatusError as e:
        logger.warning(
            "SS HTTP %d bei Quellen-Check fuer '%s'",
            e.response.status_code,
            search_query[:50],
        )
        return ReferenceCheckResult(
            status=CheckStatus.NOT_FOUND,
            candidate=candidate,
            mismatches=[f"API-Fehler: HTTP {e.response.status_code}"],
        )
    except httpx.TimeoutException:
        logger.warning("SS Timeout bei Quellen-Check fuer '%s'", search_query[:50])
        return ReferenceCheckResult(
            status=CheckStatus.NOT_FOUND,
            candidate=candidate,
            mismatches=["API-Timeout"],
        )


def _find_best_match(candidate: ReferenceCandidate, papers: list) -> object | None:
    """Findet das beste Match aus SS-Ergebnissen."""
    from src.agents.semantic_scholar import PaperResult

    for paper in papers:
        if not isinstance(paper, PaperResult):
            continue

        # Autor-Match
        if candidate.authors and paper.authors:
            first_cited = candidate.authors[0].lower()
            if any(first_cited in a.name.lower() for a in paper.authors):
                # Jahr-Match (tolerant: +/- 1 Jahr)
                if candidate.year and paper.year:
                    if abs(candidate.year - paper.year) <= 1:
                        return paper
                elif not candidate.year:
                    return paper

        # Titel-Match als Fallback
        if candidate.title and paper.title:
            cand_norm = _normalize_title(candidate.title)
            paper_norm = _normalize_title(paper.title)
            cand_words = set(cand_norm.split())
            paper_words = set(paper_norm.split())
            if cand_words and paper_words:
                overlap = len(cand_words & paper_words) / max(len(cand_words), 1)
                if overlap >= 0.6:
                    return paper

    return None


# --- Orchestrierung ---


async def check_references(
    candidates: list[ReferenceCandidate],
    *,
    forschungsstand_path: Path | None = None,
    document_name: str = "unknown",
) -> QuellenCheckReport:
    """Prueft alle Referenzen: erst lokal, dann API.

    Args:
        candidates: Extrahierte Referenzen.
        forschungsstand_path: Pfad zu forschungsstand.json (optional).
        document_name: Name des geprueften Dokuments.

    Returns:
        QuellenCheckReport mit allen Ergebnissen.
    """
    report = QuellenCheckReport(document=document_name)
    local_papers: dict[str, UnifiedPaper] = {}

    # Lokale Papers laden
    if forschungsstand_path:
        local_papers = load_local_papers(forschungsstand_path)
        if local_papers:
            logger.info(
                "%d Papers aus forschungsstand.json geladen", len(local_papers)
            )

    ss_client = SemanticScholarClient()
    results: list[ReferenceCheckResult] = []

    for candidate in candidates:
        # Schritt 1: Lokaler Lookup
        local_result = check_against_local(candidate, local_papers)
        if local_result is not None:
            results = [*results, local_result]
            continue

        # Schritt 2: API-Lookup
        api_result = await check_against_api(candidate, ss_client)
        results = [*results, api_result]

    report.results = results
    report.compute_stats()
    return report


# --- Output-Formatierung ---


def format_report_as_markdown(report: QuellenCheckReport) -> str:
    """Formatiert den Report als Markdown."""
    lines: list[str] = []

    lines.append(f"## Quellen-Check: {report.document}")
    lines.append("")
    lines.append(
        f"**{report.total_references} Referenzen** geprueft: "
        f"{report.verified} verifiziert, "
        f"{report.not_found} nicht gefunden, "
        f"{report.metadata_mismatch} mit Abweichungen"
    )
    lines.append("")

    # Probleme zuerst
    problems = [
        r for r in report.results if r.status != CheckStatus.VERIFIED
    ]
    if problems:
        lines.append("### Probleme")
        lines.append("")
        for result in problems:
            icon = "❌" if result.status == CheckStatus.NOT_FOUND else "⚠️"
            lines.append(f"- {icon} **{result.candidate.raw_text}** ({result.candidate.location})")
            lines.append(f"  Status: {result.status.value}")
            for m in result.mismatches:
                lines.append(f"  - {m}")
            lines.append("")

    # Verifizierte
    verified = [r for r in report.results if r.status == CheckStatus.VERIFIED]
    if verified:
        lines.append("### Verifiziert")
        lines.append("")
        for result in verified:
            lines.append(f"- ✅ {result.candidate.raw_text}")

    lines.append("")
    return "\n".join(lines)


def save_report(report: QuellenCheckReport, output_dir: Path) -> Path:
    """Speichert den Report als JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "quellen-check.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path
