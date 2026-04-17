"""Paper-Deduplizierung und Ranking.

Nimmt Ergebnisse aus Semantic Scholar + Exa, entfernt Duplikate,
und rankt nach Relevanz fuer den Forschungsstand.

Ranking-Modi:
- Ohne query: Heuristische Score (Citations + Recency + OA + Abstract + Source)
- Mit query: SPECTER2-enhanced (semantische Aehnlichkeit + Heuristik)
"""

from __future__ import annotations

import functools
import hashlib
import logging
import math
from collections.abc import Sequence

from pydantic import BaseModel, Field, computed_field

from src.agents.base_client import BASEDocument
from src.agents.bundestag_client import DIPDrucksache, DIPVorgang, DIPVorgangsposition
from src.agents.dblp_client import DBLPHit
from src.agents.eurlex_client import EURLexDocument
from src.agents.exa_client import ExaResult
from src.agents.openalex_client import OpenAlexWork
from src.agents.semantic_scholar import PaperResult

logger = logging.getLogger(__name__)

# Source-spezifische Citation-Caps (Modul-Konstanten)
HEURISTIC_CITATION_CAPS = {"semantic_scholar": 0.4, "openalex": 0.15, "exa": 0.05, "base": 0.10, "bundestag": 0.0, "eurlex": 0.0, "dblp": 0.05}
ENHANCED_CITATION_CAPS = {"semantic_scholar": 0.25, "openalex": 0.10, "exa": 0.03, "base": 0.05, "bundestag": 0.0, "eurlex": 0.0, "dblp": 0.03}

# Recency-Berechnung: Papers vor RECENCY_BASELINE_YEAR bekommen 0 Punkte
RECENCY_BASELINE_YEAR = 2018
RECENCY_WINDOW_YEARS = 8

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
    pdf_url: str | None = None  # Open Access PDF URL (von SS oder OA)
    specter2_score: float | None = None  # None wenn nicht berechnet
    language: str | None = None  # ISO 639-1 Sprachcode, z.B. "de", "en"

    @computed_field
    @property
    def dedup_key(self) -> str:
        """Stabiler Key fuer Deduplizierung (DOI > Titel-Hash > ID-Fallback)."""
        if self.doi:
            return f"doi:{self.doi.lower()}"
        # Fallback bei leerem Titel: paper_id verwenden
        if not self.title or not self.title.strip():
            return f"id:{self.paper_id}"
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
        score = 0.0

        cite_cap = HEURISTIC_CITATION_CAPS.get(self.source, 0.2)

        # Zitationen (log-skaliert, source-capped)
        if self.citation_count and self.citation_count > 0:
            score += min(cite_cap, math.log10(self.citation_count + 1) / 10)

        # Aktualitaet (max 0.3)
        if self.year:
            recency = max(0, self.year - RECENCY_BASELINE_YEAR) / RECENCY_WINDOW_YEARS
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
        pdf_url=paper.openAccessPdf.url if paper.openAccessPdf else None,
        tags=paper.fieldsOfStudy or [],
    )


def from_exa(result: ExaResult) -> UnifiedPaper:
    """Konvertiert ein Exa-Ergebnis in UnifiedPaper.

    Exa liefert keine strukturierten Metadaten (Citations, DOI).
    Fallback: Aktuelles Jahr wenn publishedDate fehlt (Exa findet primaer aktuelle Inhalte).
    """
    import datetime

    year = _extract_year(result.published_date)
    if year is None:
        year = datetime.datetime.now(tz=datetime.timezone.utc).year

    # highlights (neu) bevorzugen, text als Fallback (Abwaertskompatibilitaet)
    abstract = None
    if result.highlights:
        abstract = " ".join(result.highlights)
    elif result.text:
        abstract = result.text

    return UnifiedPaper(
        paper_id=hashlib.sha256(result.url.encode()).hexdigest()[:16],
        title=result.title,
        abstract=abstract,
        year=year,
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
        pdf_url=work.open_access.oa_url,
        language=work.language,
    )


def from_base(doc: BASEDocument) -> UnifiedPaper:
    """Konvertiert ein BASE-Dokument in UnifiedPaper.

    BASE liefert keine Citations. DOI oft vorhanden.
    Sprache als 3-Letter-Code (eng, deu) → auf 2-Letter normalisieren.
    """
    # Sprache normalisieren: "eng" → "en", "deu" → "de"
    lang_map = {"eng": "en", "deu": "de", "fra": "fr", "spa": "es"}
    language = lang_map.get(doc.dclang or "", doc.dclang)

    return UnifiedPaper(
        paper_id=doc.dcdoi or hashlib.sha256((doc.dctitle or "").encode()).hexdigest()[:16],
        title=doc.dctitle,
        abstract=doc.dcdescription,
        year=doc.year,
        authors=doc.dccreator,
        citation_count=None,
        source="base",
        doi=doc.dcdoi,
        url=doc.dcidentifier,
        is_open_access=doc.is_open_access,
        pdf_url=doc.dclink,
        tags=doc.dcsubject,
        language=language,
    )


def from_bundestag(drucksache: DIPDrucksache) -> UnifiedPaper:
    """Konvertiert eine Bundestag-Drucksache in UnifiedPaper.

    Bundestag-Dokumente haben keine DOI oder Citations.
    Dokumentnummer als ID, Titel als Abstract-Ersatz.
    """
    return UnifiedPaper(
        paper_id=f"dip:{drucksache.dokumentnummer}" if drucksache.dokumentnummer else f"dip:{drucksache.id}",
        title=drucksache.titel,
        abstract=drucksache.abstract or drucksache.titel,
        year=drucksache.year,
        authors=[],
        citation_count=None,
        source="bundestag",
        url=drucksache.url,
        tags=[drucksache.typ] if drucksache.typ else [],
        language="de",
    )


def from_dip_vorgang(vorgang: DIPVorgang) -> UnifiedPaper:
    """Konvertiert einen DIP-Vorgang in UnifiedPaper.

    Vorgaenge buendeln Dokumente zu einem Thema (Gesetzgebungsverfahren,
    Kleine Anfrage, ...). Ideal fuer Topic-Research auf der buendelnden Ebene.

    Tags-Struktur: [typ, vorgangstyp, ...deskriptor.name, ...sachgebiet]
    → breites Signal fuer Filterung + LLM-Context.
    """
    tags: list[str] = []
    if vorgang.typ:
        tags.append(vorgang.typ)
    if vorgang.vorgangstyp and vorgang.vorgangstyp != vorgang.typ:
        tags.append(vorgang.vorgangstyp)
    tags.extend(d.name for d in vorgang.deskriptor if d.name)
    tags.extend(s for s in vorgang.sachgebiet if s)

    return UnifiedPaper(
        paper_id=f"dip-vorgang:{vorgang.id}",
        title=vorgang.titel,
        abstract=vorgang.abstract or vorgang.titel,
        year=vorgang.year,
        authors=list(vorgang.initiative),
        citation_count=None,
        source="bundestag",
        url=vorgang.url,
        tags=tags,
        language="de",
    )


def from_dip_vorgangsposition(vp: DIPVorgangsposition) -> UnifiedPaper:
    """Konvertiert eine DIP-Vorgangsposition (Drucksache o. Debatten-Abschnitt).

    Paper-ID bevorzugt Dokumentnummer (stabil fuer Dedup ueber Drucksachen),
    fallback auf Vorgangsposition-ID.
    """
    fundstelle = vp.fundstelle
    doknr = fundstelle.dokumentnummer if fundstelle else ""
    paper_id = f"dip:{doknr}" if doknr else f"dip-vp:{vp.id}"
    url = (
        f"https://dip.bundestag.de/vorgang/{vp.vorgang_id}"
        if vp.vorgang_id
        else f"https://dip.bundestag.de/vorgangsposition/{vp.id}"
    )
    tags: list[str] = []
    if vp.dokumentart:
        tags.append(vp.dokumentart)
    if fundstelle and fundstelle.drucksachetyp:
        tags.append(fundstelle.drucksachetyp)
    if vp.vorgangsposition:
        tags.append(vp.vorgangsposition)

    authors = list(fundstelle.urheber) if fundstelle else []

    return UnifiedPaper(
        paper_id=paper_id,
        title=vp.titel,
        abstract=vp.titel,
        year=vp.year,
        authors=authors,
        citation_count=None,
        source="bundestag",
        url=url,
        pdf_url=fundstelle.pdf_url if fundstelle and fundstelle.pdf_url else None,
        tags=tags,
        language="de",
    )


def from_eurlex(doc: EURLexDocument) -> UnifiedPaper:
    """Konvertiert ein EUR-Lex-Dokument in UnifiedPaper.

    EU-Rechtsakte: CELEX-Nummer als ID, kein DOI, kein Abstract.
    """
    return UnifiedPaper(
        paper_id=f"celex:{doc.celex}" if doc.celex else hashlib.sha256(doc.title.encode()).hexdigest()[:16],
        title=doc.title,
        abstract=doc.title,  # EUR-Lex hat keine Abstracts
        year=doc.year,
        authors=[],
        citation_count=None,
        source="eurlex",
        url=doc.url,
        tags=[doc.doc_type, doc.subject] if doc.doc_type else [doc.subject] if doc.subject else [],
        language="de",
    )


def from_dblp(hit: DBLPHit) -> UnifiedPaper:
    """Konvertiert einen DBLP-Treffer in UnifiedPaper.

    DBLP liefert keine Abstracts und keine Citations.
    Venue als Tag, DOI oft vorhanden.
    """
    info = hit.info
    doi = info.doi
    # DBLP-URL als Fallback-ID
    paper_id = doi or hashlib.sha256(info.url.encode()).hexdigest()[:16] if info.url else hashlib.sha256(info.title.encode()).hexdigest()[:16]

    return UnifiedPaper(
        paper_id=paper_id,
        title=info.title,
        abstract=None,  # DBLP hat keine Abstracts
        year=info.year_int,
        authors=info.author_names,
        citation_count=None,
        source="dblp",
        doi=doi,
        url=info.ee or info.url,
        tags=[info.venue] if info.venue else [],
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


@functools.lru_cache(maxsize=1)
def _load_specter2_model():
    """Laedt SPECTER2 Model (Lazy, gecacht via lru_cache).

    Raises:
        ImportError: Wenn sentence-transformers nicht installiert.
    """
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("allenai/specter2_base")


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
    except Exception as e:
        # torch kann auf Python 3.14 mit AssertionError crashen
        logger.info("SPECTER2 Import-Fehler: %s", e)
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

    Source-aware Citation-Caps (konsistent mit relevance_score):
    - SS: 0.25, OA: 0.10, Exa: 0.03

    Gewichtung wenn SPECTER2 verfuegbar:
    - 40% SPECTER2 Similarity (Semantic Match dominiert)
    - 15% Citations (log-skaliert, source-capped, reduziert gg. Survey-Bias)
    - 25% Recency
    - 10% Open Access
    - 10% Abstract vorhanden
    """
    s2_score = specter2_scores.get(paper.paper_id, 0.0)
    score = 0.4 * s2_score

    cite_cap = ENHANCED_CITATION_CAPS.get(paper.source, 0.15)

    # Zitationen (log-skaliert, source-capped)
    if paper.citation_count and paper.citation_count > 0:
        score += min(cite_cap, math.log10(paper.citation_count + 1) / 10 * 0.375)

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


def _apply_source_quota(
    ranked: list[UnifiedPaper],
    top_k: int,
    *,
    min_per_source: int = 3,
    scores: dict[str, float] | None = None,
) -> list[UnifiedPaper]:
    """Wendet Source-Quota an: reserviert Mindestplaetze pro aktiver Quelle.

    Phase 1: Reserviert min(effective_min, verfuegbare) Plaetze pro Quelle.
    Phase 2: Fuellt restliche Plaetze nach Score auf.
    Ergebnis wird nach Score neu sortiert und auf top_k beschnitten.

    Args:
        ranked: Nach Score absteigend sortierte Papers.
        top_k: Maximale Anzahl zurueckzugebender Papers.
        min_per_source: Mindestanzahl reservierter Plaetze pro Quelle.
        scores: Optionales Score-Dict (z.B. enhanced_scores bei SPECTER2).
            Falls None, wird relevance_score verwendet.
    """
    # Quellen sammeln
    sources = list(dict.fromkeys(p.source for p in ranked))
    if len(sources) <= 1:
        return ranked[:top_k]

    # Effektives Minimum: bei kleinem top_k anteilig reduzieren
    effective_min = min(min_per_source, max(1, top_k // len(sources)))

    # Score-Funktion: SPECTER2-enhanced oder heuristisch
    sort_key = (
        (lambda p: scores.get(p.paper_id, 0.0))
        if scores is not None
        else (lambda p: p.relevance_score)
    )

    # Phase 1: Top-N pro Quelle reservieren
    reserved: list[UnifiedPaper] = []
    reserved_ids: set[str] = set()
    for source in sources:
        source_papers = [p for p in ranked if p.source == source]
        quota = min(effective_min, len(source_papers))
        for paper in source_papers[:quota]:
            if paper.paper_id not in reserved_ids:
                reserved.append(paper)
                reserved_ids.add(paper.paper_id)

    # Phase 2: Restliche Plaetze nach Score auffuellen
    remaining_slots = max(0, top_k - len(reserved))
    fill = [p for p in ranked if p.paper_id not in reserved_ids][:remaining_slots]

    # Zusammenfuehren, nach Score sortieren, auf top_k beschneiden
    result = sorted([*reserved, *fill], key=sort_key, reverse=True)
    return result[:top_k]


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
            updated = [
                paper.model_copy(update={"specter2_score": specter2_scores.get(paper.paper_id)})
                for paper in papers
            ]
            enhanced_scores = {
                p.paper_id: _compute_enhanced_score(p, specter2_scores) for p in updated
            }
            ranked = sorted(updated, key=lambda p: enhanced_scores[p.paper_id], reverse=True)
            if top_k:
                return _apply_source_quota(ranked, top_k, scores=enhanced_scores)
            return ranked

    # Fallback: heuristisches Ranking
    ranked = sorted(papers, key=lambda p: p.relevance_score, reverse=True)
    if top_k:
        return _apply_source_quota(ranked, top_k)
    return ranked
