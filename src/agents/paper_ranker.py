"""Paper-Deduplizierung und Ranking.

Nimmt Ergebnisse aus Semantic Scholar + Exa, entfernt Duplikate,
und rankt nach Relevanz fuer den Forschungsstand.

Ranking-Modi:
- Ohne query: Heuristische Score (Citations + Recency + OA + Abstract + Source)
- Mit query: SPECTER2-enhanced (semantische Aehnlichkeit + Heuristik)
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Sequence

from pydantic import BaseModel, Field, computed_field

from src.agents.exa_client import ExaResult
from src.agents.openalex_client import OpenAlexWork
from src.agents.semantic_scholar import PaperResult

logger = logging.getLogger(__name__)

# SPECTER2 Model-Cache (Lazy Loading)
_specter2_model = None


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
    specter2_score: float | None = None  # None wenn nicht berechnet

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

        Source-aware: OpenAlex Citation-Cap bei 0.15 (statt 0.4),
        weil breite Queries hochzitierte aber irrelevante Papers liefern.
        Max-Scores: SS ~1.0, OA ~0.75, Exa ~0.6.
        """
        import math

        score = 0.0

        # Source-spezifische Citation-Caps
        _citation_caps = {
            "semantic_scholar": 0.4,
            "openalex": 0.15,
            "exa": 0.05,
        }
        cite_cap = _citation_caps.get(self.source, 0.2)

        # Zitationen (log-skaliert, source-capped)
        if self.citation_count and self.citation_count > 0:
            score += min(cite_cap, math.log10(self.citation_count + 1) / 10)

        # Aktualitaet (max 0.3)
        if self.year:
            recency = max(0, self.year - 2018) / 8
            score += min(0.3, recency * 0.3)

        # Open Access Bonus (0.1)
        if self.is_open_access:
            score += 0.1

        # Abstract vorhanden (0.15 — aufgewertet, staerkstes Qualitaetssignal)
        if self.abstract:
            score += 0.15

        # Strukturierte Metadaten: SS bevorzugt (0.1), OA neutral (0.05)
        if self.source == "semantic_scholar":
            score += 0.1
        elif self.source == "openalex":
            score += 0.05

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


def from_openalex(work: OpenAlexWork) -> UnifiedPaper:
    """Konvertiert ein OpenAlex Work in UnifiedPaper.

    DOI-Normalisierung: OpenAlex liefert DOIs als vollstaendige URL
    ("https://doi.org/10.xxx") — wir extrahieren nur den DOI-Teil.
    """
    # DOI aus URL extrahieren: "https://doi.org/10.xxx" → "10.xxx"
    doi: str | None = None
    if work.doi:
        doi = work.doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/")

    return UnifiedPaper(
        paper_id=doi or work.id,
        title=work.display_name,
        abstract=work.abstract,  # via @property aus inverted_index
        year=work.publication_year,
        authors=[a.author.display_name for a in work.authorships],
        citation_count=work.cited_by_count,
        source="openalex",
        doi=doi,
        url=work.id,  # OpenAlex URL als Referenz
        is_open_access=work.open_access.is_oa,
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


# --- SPECTER2 ---


def _load_specter2_model():
    """Laedt SPECTER2 Model (Lazy, gecacht).

    Raises:
        ImportError: Wenn sentence-transformers nicht installiert.
    """
    global _specter2_model
    if _specter2_model is not None:
        return _specter2_model
    from sentence_transformers import SentenceTransformer
    _specter2_model = SentenceTransformer("allenai/specter2_base")
    return _specter2_model


def compute_specter2_similarity(
    query: str,
    papers: Sequence[UnifiedPaper],
) -> dict[str, float]:
    """Berechnet SPECTER2-Cosine-Similarity zwischen Query und Paper-Abstracts.

    Returns:
        Dict von paper_id -> similarity_score (0-1).
        Leeres Dict wenn sentence-transformers nicht installiert.
    """
    try:
        model = _load_specter2_model()
    except (ImportError, OSError) as e:
        logger.info("SPECTER2 nicht verfuegbar: %s", e)
        return {}

    import numpy as np

    # Papers mit Abstract sammeln
    papers_with_abstract = [p for p in papers if p.abstract and p.abstract.strip()]
    if not papers_with_abstract:
        return {p.paper_id: 0.0 for p in papers}

    # Embeddings berechnen
    texts = [query, *[p.abstract for p in papers_with_abstract]]
    embeddings = model.encode(texts, normalize_embeddings=True)

    query_emb = embeddings[0]
    paper_embs = embeddings[1:]

    # Cosine Similarity (bereits normalisiert -> Dot Product)
    similarities = np.dot(paper_embs, query_emb)

    # Score-Dict aufbauen
    scores: dict[str, float] = {}
    for paper in papers:
        scores[paper.paper_id] = 0.0  # Default fuer Papers ohne Abstract

    for i, paper in enumerate(papers_with_abstract):
        scores[paper.paper_id] = float(max(0.0, min(1.0, similarities[i])))

    return scores


# --- Ranking ---


def _compute_enhanced_score(
    paper: UnifiedPaper,
    specter2_scores: dict[str, float],
) -> float:
    """Berechnet kombinierten Score mit SPECTER2-Gewichtung.

    Gewichtung wenn SPECTER2 verfuegbar:
    - 30% SPECTER2 Similarity
    - 25% Citations (log-skaliert)
    - 25% Recency
    - 10% Open Access
    - 10% Abstract vorhanden
    """
    import math

    s2_score = specter2_scores.get(paper.paper_id, 0.0)
    score = 0.3 * s2_score

    # Zitationen (max 0.25)
    if paper.citation_count and paper.citation_count > 0:
        score += min(0.25, math.log10(paper.citation_count + 1) / 10 * 0.625)

    # Aktualitaet (max 0.25)
    if paper.year:
        recency = max(0, paper.year - 2018) / 8
        score += min(0.25, recency * 0.25)

    # Open Access (0.1)
    if paper.is_open_access:
        score += 0.1

    # Abstract vorhanden (0.1)
    if paper.abstract:
        score += 0.1

    return round(min(1.0, score), 3)


def rank_papers(
    papers: Sequence[UnifiedPaper],
    *,
    top_k: int | None = None,
    query: str | None = None,
) -> list[UnifiedPaper]:
    """Rankt Papers nach Relevanz.

    Mit query: SPECTER2-enhanced Ranking (semantische Aehnlichkeit + Heuristik).
    Ohne query: Heuristisches Ranking (relevance_score).
    """
    if query is not None:
        specter2_scores = compute_specter2_similarity(query, papers)
        if specter2_scores:
            # SPECTER2-Scores auf Papers speichern
            updated = []
            for paper in papers:
                s2_score = specter2_scores.get(paper.paper_id)
                updated = [
                    *updated,
                    paper.model_copy(update={"specter2_score": s2_score}),
                ]
            enhanced_scores = {
                p.paper_id: _compute_enhanced_score(p, specter2_scores) for p in updated
            }
            ranked = sorted(updated, key=lambda p: enhanced_scores[p.paper_id], reverse=True)
            if top_k:
                return ranked[:top_k]
            return ranked

    # Fallback: heuristisches Ranking
    ranked = sorted(papers, key=lambda p: p.relevance_score, reverse=True)
    if top_k:
        return ranked[:top_k]
    return ranked
