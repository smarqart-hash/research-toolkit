"""Paper-Deduplizierung und Ranking.

Nimmt Ergebnisse aus Semantic Scholar + Exa, entfernt Duplikate,
und rankt nach Relevanz fuer den Forschungsstand.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from pydantic import BaseModel, Field, computed_field

from src.agents.exa_client import ExaResult
from src.agents.semantic_scholar import PaperResult


class UnifiedPaper(BaseModel):
    """Vereinheitlichtes Paper-Format nach Deduplizierung."""

    paper_id: str  # DOI bevorzugt, sonst SS-ID oder URL-Hash
    title: str
    abstract: str | None = None
    year: int | None = None
    authors: list[str] = Field(default_factory=list)
    citation_count: int | None = None
    source: str  # "semantic_scholar" oder "exa"
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    is_open_access: bool = False
    tags: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def dedup_key(self) -> str:
        """Stabiler Key fuer Deduplizierung (DOI > Titel-Hash)."""
        if self.doi:
            return f"doi:{self.doi.lower()}"
        # Titel normalisieren: lowercase, keine Sonderzeichen
        normalized = "".join(c for c in self.title.lower() if c.isalnum() or c == " ")
        normalized = " ".join(normalized.split())
        return f"title:{hashlib.sha256(normalized.encode()).hexdigest()[:16]}"

    @computed_field
    @property
    def relevance_score(self) -> float:
        """Heuristischer Relevanz-Score (0-1) fuer Ranking.

        Faktoren: Zitationen, Aktualitaet, Open Access.
        """
        score = 0.0

        # Zitationen (log-skaliert, max 0.4)
        if self.citation_count and self.citation_count > 0:
            import math
            score += min(0.4, math.log10(self.citation_count + 1) / 10)

        # Aktualitaet (max 0.3)
        if self.year:
            recency = max(0, self.year - 2018) / 8  # 2018-2026 normiert
            score += min(0.3, recency * 0.3)

        # Open Access Bonus (0.1)
        if self.is_open_access:
            score += 0.1

        # Abstract vorhanden (0.1)
        if self.abstract:
            score += 0.1

        # Semantic Scholar bevorzugt (zuverlaessigere Metadaten) (0.1)
        if self.source == "semantic_scholar":
            score += 0.1

        return round(min(1.0, score), 3)


def from_semantic_scholar(paper: PaperResult) -> UnifiedPaper:
    """Konvertiert ein Semantic Scholar Paper in UnifiedPaper."""
    return UnifiedPaper(
        paper_id=paper.doi or paper.paperId,
        title=paper.title,
        abstract=paper.abstract,
        year=paper.year,
        authors=[a.name for a in paper.authors],
        citation_count=paper.citationCount,
        source="semantic_scholar",
        doi=paper.doi,
        arxiv_id=paper.arxiv_id,
        url=f"https://www.semanticscholar.org/paper/{paper.paperId}",
        is_open_access=paper.isOpenAccess or False,
        tags=paper.fieldsOfStudy or [],
    )


def from_exa(result: ExaResult) -> UnifiedPaper:
    """Konvertiert ein Exa-Ergebnis in UnifiedPaper."""
    # Exa liefert keine strukturierten Metadaten — nur Basics
    return UnifiedPaper(
        paper_id=hashlib.sha256(result.url.encode()).hexdigest()[:16],
        title=result.title,
        abstract=result.text,
        year=_extract_year(result.published_date),
        authors=[result.author] if result.author else [],
        citation_count=None,
        source="exa",
        url=result.url,
    )


def _extract_year(date_str: str | None) -> int | None:
    """Extrahiert Jahr aus ISO-Datum oder Year-String."""
    if not date_str:
        return None
    try:
        return int(date_str[:4])
    except (ValueError, IndexError):
        return None


def deduplicate(papers: Sequence[UnifiedPaper]) -> list[UnifiedPaper]:
    """Entfernt Duplikate. Bevorzugt Semantic Scholar bei Konflikten."""
    seen: dict[str, UnifiedPaper] = {}
    for paper in papers:
        key = paper.dedup_key
        if key not in seen:
            seen[key] = paper
        elif paper.source == "semantic_scholar" and seen[key].source != "semantic_scholar":
            # SS hat bessere Metadaten — ueberschreiben
            seen[key] = paper
    return list(seen.values())


def rank_papers(papers: Sequence[UnifiedPaper], *, top_k: int | None = None) -> list[UnifiedPaper]:
    """Rankt Papers nach relevance_score (absteigend)."""
    ranked = sorted(papers, key=lambda p: p.relevance_score, reverse=True)
    if top_k:
        return ranked[:top_k]
    return ranked
