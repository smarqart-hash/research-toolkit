"""Forschungsstand-Generator.

Orchestriert Paper-Suche, Deduplizierung, Clustering und generiert
eine strukturierte Uebersicht (3-5 Seiten), direkt nutzbar als Kapitelentwurf.

Drei Input-Modi:
1. Freitext-Thema → automatische Query-Generierung
2. Thema + Leitfragen → gezieltere Suche
3. Paper-Liste → direkte Analyse ohne Suche
"""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from pydantic import BaseModel, Field

from src.agents.exa_client import ExaClient
from src.agents.openalex_client import OpenAlexClient

logger = logging.getLogger(__name__)
from src.agents.paper_ranker import (
    UnifiedPaper,
    deduplicate,
    from_exa,
    from_openalex,
    from_semantic_scholar,
    rank_papers,
)
from src.agents.screener import PrismaFlow, ScreeningCriteria, screen_papers
from src.agents.semantic_scholar import SemanticScholarClient
from src.utils.bibtex_parser import parse_bibtex_file
from src.utils.evidence_card import EvidenceCard


# --- Datenmodelle ---


class ThemeCluster(BaseModel):
    """Ein thematisches Cluster von Papers."""

    theme: str  # z.B. "Deep Reinforcement Learning fuer Ampelsteuerung"
    description: str  # 2-3 Saetze Zusammenfassung
    papers: list[str] = Field(default_factory=list)  # Paper-IDs
    key_findings: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class ForschungsstandResult(BaseModel):
    """Ergebnis der Forschungsstand-Analyse."""

    topic: str
    leitfragen: list[str] = Field(default_factory=list)
    clusters: list[ThemeCluster] = Field(default_factory=list)
    papers: list[UnifiedPaper] = Field(default_factory=list)
    evidence_cards: list[EvidenceCard] = Field(default_factory=list)
    total_found: int = 0
    total_after_dedup: int = 0
    sources_used: list[str] = Field(default_factory=list)


@dataclass
class SearchConfig:
    """Konfiguration fuer die Paper-Suche."""

    max_results_per_query: int = 100
    year_filter: str | None = None  # z.B. "2020-2026"
    fields_of_study: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=lambda: ["ss", "openalex"])
    languages: list[str] = field(default_factory=lambda: ["en", "de"])
    top_k: int = 30  # Max Papers nach Ranking
    papers_file: Path | None = None  # BibTeX-Import


LOW_RECALL_THRESHOLD = 15


# --- Such-Orchestrierung ---


def _check_source_balance(stats: dict[str, int]) -> list[str]:
    """Prueft ob Quellen-Verteilung stark asymmetrisch ist.

    Warnt wenn eine aktive Quelle <10% des Gesamtpools liefert.
    """
    source_counts = {
        "Semantic Scholar": stats.get("ss_total", 0),
        "OpenAlex": stats.get("openalex_total", 0),
        "Exa": stats.get("exa_total", 0),
    }
    active = {k: v for k, v in source_counts.items() if v > 0}
    total = sum(active.values())
    if total == 0 or len(active) < 2:
        return []

    warnings: list[str] = []
    for source, count in active.items():
        ratio = count / total
        if ratio < 0.1:
            warnings = [
                *warnings,
                f"{source} lieferte nur {count}/{total} Papers ({ratio:.0%}). "
                f"Ergebnisse koennten asymmetrisch sein.",
            ]
    return warnings


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


async def _search_ss(
    queries: list[str],
    config: SearchConfig,
    stats: dict[str, int],
) -> list[UnifiedPaper]:
    """Sucht Papers via Semantic Scholar.

    Aktualisiert stats in-place fuer ss_total/ss_errors.
    """
    ss_client = SemanticScholarClient()
    papers: list[UnifiedPaper] = []
    for query in queries:
        try:
            response = await ss_client.search_papers(
                query,
                limit=config.max_results_per_query,
                year=config.year_filter,
                fields_of_study=config.fields_of_study or None,
            )
            batch = [from_semantic_scholar(p) for p in response.data]
            papers = [*papers, *batch]
            stats["ss_total"] += len(batch)
        except httpx.HTTPStatusError as e:
            stats["ss_errors"] += 1
            logger.warning(
                "Semantic Scholar HTTP %d fuer Query '%s': %s",
                e.response.status_code,
                query,
                e.response.text[:200],
            )
        except httpx.TimeoutException:
            stats["ss_errors"] += 1
            logger.warning("Semantic Scholar Timeout fuer Query '%s'", query)
    return papers


async def _search_openalex(
    queries: list[str],
    config: SearchConfig,
    stats: dict[str, int],
) -> list[UnifiedPaper]:
    """Sucht Papers via OpenAlex.

    Aktualisiert stats in-place fuer openalex_total/openalex_errors.
    """
    oa_client = OpenAlexClient()
    papers: list[UnifiedPaper] = []
    for query in queries:
        try:
            response = await oa_client.search_works(
                query,
                per_page=config.max_results_per_query,
                year_range=config.year_filter,
                languages=config.languages or None,
            )
            # Pre-Filter: OpenAlex-Papers unter Relevanz-Schwelle entfernen
            min_oa_relevance = 0.3
            relevant = [w for w in response.results if w.relevance_score >= min_oa_relevance]
            filtered_count = len(response.results) - len(relevant)
            if filtered_count > 0:
                logger.info(
                    "OpenAlex Pre-Filter: %d/%d Papers unter Relevanz-Schwelle %.1f entfernt",
                    filtered_count,
                    len(response.results),
                    min_oa_relevance,
                )
            batch = [from_openalex(w) for w in relevant]
            papers = [*papers, *batch]
            stats["openalex_total"] += len(batch)
        except httpx.HTTPStatusError as e:
            stats["openalex_errors"] += 1
            logger.warning(
                "OpenAlex HTTP %d fuer Query '%s': %s",
                e.response.status_code,
                query,
                e.response.text[:200],
            )
        except httpx.TimeoutException:
            stats["openalex_errors"] += 1
            logger.warning("OpenAlex Timeout fuer Query '%s'", query)
    return papers


async def _search_exa(
    queries: list[str],
    config: SearchConfig,
    stats: dict[str, int],
) -> list[UnifiedPaper]:
    """Sucht Papers via Exa (nur wenn API Key vorhanden).

    Aktualisiert stats in-place fuer exa_total/exa_errors.
    """
    exa_client = ExaClient()
    if not exa_client.is_available:
        logger.info("Exa nicht verfuegbar (EXA_API_KEY nicht gesetzt)")
        return []
    papers: list[UnifiedPaper] = []
    for query in queries:
        try:
            exa_response = await exa_client.search_papers(
                query, num_results=min(config.max_results_per_query, 50),
            )
            batch = [from_exa(r) for r in exa_response.results]
            papers = [*papers, *batch]
            stats["exa_total"] += len(batch)
        except httpx.HTTPStatusError as e:
            stats["exa_errors"] += 1
            logger.warning(
                "Exa HTTP %d fuer Query '%s': %s",
                e.response.status_code,
                query,
                e.response.text[:200],
            )
        except httpx.TimeoutException:
            stats["exa_errors"] += 1
            logger.warning("Exa Timeout fuer Query '%s'", query)
    return papers


async def search_papers(
    topic: str,
    *,
    queries: list[str] | None = None,
    config: SearchConfig | None = None,
    screening: ScreeningCriteria | None = None,
    refine: bool = False,
    no_validate: bool = True,
) -> tuple[list[UnifiedPaper], dict[str, int], PrismaFlow | None]:
    """Sucht Papers parallel via konfigurierten Quellen (SS, OpenAlex, Exa).

    Args:
        topic: Hauptthema.
        queries: Optionale zusaetzliche Suchqueries (aus Leitfragen).
        config: Such-Konfiguration.
        screening: Optionale Screening-Kriterien (PRISMA-Flow).
        refine: Smart Query Expansion aktivieren (lokal + optional LLM).
        no_validate: Dry-Run-Validierung ueberspringen.

    Returns:
        Tuple aus (Papers, Statistiken, PrismaFlow oder None).
    """
    if config is None:
        config = SearchConfig()

    stats: dict[str, int] = {
        "ss_total": 0,
        "exa_total": 0,
        "ss_errors": 0,
        "exa_errors": 0,
        "openalex_total": 0,
        "openalex_errors": 0,
        "import_total": 0,
    }

    # Queries zusammenstellen — mit oder ohne Smart Expansion
    if refine:
        from src.agents.query_generator import expand_queries, validate_queries

        query_set = await expand_queries(topic, queries)
        ss_queries = query_set.ss_queries
        exa_queries = query_set.exa_queries
        oa_queries = query_set.oa_queries
        stats["query_source"] = 1 if query_set.source == "llm" else 0

        # Optionale Dry-Run-Validierung
        if not no_validate:
            ss_client_for_validate = SemanticScholarClient()
            exa_client_for_validate = ExaClient() if "exa" in config.sources else None
            query_set = await validate_queries(
                query_set, ss_client_for_validate, exa_client_for_validate
            )
            ss_queries = query_set.ss_queries
            exa_queries = query_set.exa_queries
            oa_queries = query_set.oa_queries

        logger.info(
            "Smart Query Expansion (%s): %d SS, %d OA, %d Exa Queries",
            query_set.source,
            len(ss_queries),
            len(oa_queries),
            len(exa_queries),
        )
    else:
        ss_queries = [topic]
        if queries:
            ss_queries = [*ss_queries, *queries]
        exa_queries = ss_queries[:2]
        oa_queries = ss_queries  # Ohne --refine: gleiche Queries (kein Boolean)

    # Parallele Suche ueber alle konfigurierten Quellen
    search_tasks = []
    sources_used: list[str] = []

    if "ss" in config.sources:
        search_tasks.append(_search_ss(ss_queries, config, stats))
        sources_used.append("Semantic Scholar")
    if "openalex" in config.sources:
        # OA-Queries bevorzugen (Freitext ohne Boolean), Fallback auf SS-Queries
        openalex_queries = oa_queries if oa_queries else ss_queries
        search_tasks.append(_search_openalex(openalex_queries, config, stats))
        sources_used.append("OpenAlex")
    if "exa" in config.sources:
        search_tasks.append(_search_exa(exa_queries, config, stats))
        sources_used.append("Exa")

    results = await asyncio.gather(*search_tasks, return_exceptions=True)

    all_papers: list[UnifiedPaper] = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning("Quelle fehlgeschlagen: %s", result)
            continue
        all_papers = [*all_papers, *result]

    # Paper-Import aus BibTeX-Datei
    if config.papers_file is not None:
        imported = parse_bibtex_file(config.papers_file)
        all_papers = [*all_papers, *imported]
        stats["import_total"] = len(imported)
        logger.info("Paper-Import: %d Papers aus %s", len(imported), config.papers_file.name)

    # Warnung wenn alle Quellen leer
    total_found = stats["ss_total"] + stats["openalex_total"] + stats["exa_total"]

    # Source-Balance pruefen
    balance_warnings = _check_source_balance(stats)
    for warning in balance_warnings:
        logger.warning("Source-Balance: %s", warning)

    if total_found == 0:
        logger.warning(
            "Keine Papers gefunden! SS-Fehler: %d, OpenAlex-Fehler: %d, Exa-Fehler: %d. "
            "Pruefen: S2_API_KEY gesetzt? Netzwerk erreichbar?",
            stats["ss_errors"],
            stats["openalex_errors"],
            stats["exa_errors"],
        )

    # Deduplizierung + Ranking (mit SPECTER2 wenn Topic als Query)
    deduped = deduplicate(all_papers)
    ranked = rank_papers(deduped, top_k=config.top_k, query=topic)

    stats["before_dedup"] = len(all_papers)
    stats["after_dedup"] = len(deduped)
    stats["after_ranking"] = len(ranked)

    # Low-Recall-Warnung
    has_exa = "exa" in config.sources
    has_import = config.papers_file is not None
    recall_warnings = _check_low_recall(len(ranked), has_exa=has_exa, has_import=has_import)
    for warning in recall_warnings:
        logger.warning("Low-Recall: %s", warning)

    # Optionales Screening
    prisma_flow: PrismaFlow | None = None
    if screening is not None:
        screening_result = screen_papers(ranked, screening)
        prisma_flow = screening_result.prisma_flow
        prisma_flow.identified = len(all_papers)
        prisma_flow.after_dedup = len(deduped)
        prisma_flow.after_ranking = len(ranked)
        ranked = screening_result.included
        stats["after_screening"] = len(ranked)

    return ranked, stats, prisma_flow


def generate_search_queries(topic: str, leitfragen: list[str]) -> list[str]:
    """Generiert Suchqueries aus Thema und Leitfragen.

    Einfache Heuristik — kein LLM noetig fuer Basis-Queries.
    """
    queries = [topic]
    for frage in leitfragen:
        # Fragewoerter entfernen, Kern extrahieren
        cleaned = frage.strip().rstrip("?")
        for prefix in ["Wie ", "Was ", "Welche ", "Warum ", "Inwieweit "]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break
        queries = [*queries, f"{topic} {cleaned}"]
    return queries


# --- Hilfsfunktionen ---


def slugify(text: str, max_length: int = 60) -> str:
    """Erzeugt einen URL/Ordner-sicheren Slug aus beliebigem Text.

    Beispiel: "KI-basierte Verkehrssteuerung" → "ki-basierte-verkehrssteuerung"
    """
    # Unicode normalisieren, Akzente entfernen
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_length].rstrip("-")


# --- Ergebnis-Persistenz ---


def save_forschungsstand(
    result: ForschungsstandResult,
    output_dir: Path,
    *,
    slug: str | None = None,
) -> Path:
    """Speichert das Forschungsstand-Ergebnis als JSON.

    Legt Dateien in output_dir/{slug}/ ab. Slug wird aus dem Topic generiert
    falls nicht explizit angegeben.
    """
    if slug is None:
        slug = slugify(result.topic)
    topic_dir = output_dir / slug
    topic_dir.mkdir(parents=True, exist_ok=True)
    path = topic_dir / "forschungsstand.json"
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_forschungsstand(path: Path) -> ForschungsstandResult:
    """Laedt ein gespeichertes Forschungsstand-Ergebnis."""
    return ForschungsstandResult.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def merge_results(
    existing: ForschungsstandResult,
    new: ForschungsstandResult,
) -> ForschungsstandResult:
    """Mergt neue Suchergebnisse in bestehenden Pool.

    Dedupliziert ueber dedup_key. Bei Konflikten: SS > OA > Exa.
    Akkumuliert total_found und vereinigt sources_used.
    """
    all_papers = [*existing.papers, *new.papers]
    merged_papers = deduplicate(all_papers)

    merged_sources = list(dict.fromkeys([*existing.sources_used, *new.sources_used]))

    merged_leitfragen = list(dict.fromkeys([*existing.leitfragen, *new.leitfragen]))

    return ForschungsstandResult(
        topic=existing.topic,
        papers=merged_papers,
        total_found=existing.total_found + new.total_found,
        total_after_dedup=len(merged_papers),
        sources_used=merged_sources,
        leitfragen=merged_leitfragen,
    )


def format_as_markdown(result: ForschungsstandResult) -> str:
    """Formatiert das Ergebnis als Markdown-Kapitelentwurf.

    Ziel: 3-5 Seiten, direkt nutzbar als Kapitel "Stand der Forschung".
    """
    lines: list[str] = []

    lines.append(f"## Stand der Forschung: {result.topic}")
    lines.append("")

    # Einleitung
    lines.append(
        f"Die folgende Uebersicht basiert auf der Analyse von "
        f"{result.total_after_dedup} wissenschaftlichen Arbeiten "
        f"({', '.join(result.sources_used)})."
    )
    if result.leitfragen:
        lines.append("")
        lines.append("**Leitfragen:**")
        for frage in result.leitfragen:
            lines.append(f"- {frage}")
    lines.append("")

    # Cluster als Unterkapitel
    for i, cluster in enumerate(result.clusters, 1):
        lines.append(f"### {i}. {cluster.theme}")
        lines.append("")
        lines.append(cluster.description)
        lines.append("")

        if cluster.key_findings:
            lines.append("**Zentrale Befunde:**")
            for finding in cluster.key_findings:
                lines.append(f"- {finding}")
            lines.append("")

        if cluster.open_questions:
            lines.append("**Offene Fragen:**")
            for question in cluster.open_questions:
                lines.append(f"- {question}")
            lines.append("")

    # Quellen-Uebersicht
    lines.append("### Quellenverzeichnis")
    lines.append("")
    for paper in result.papers:
        author_str = paper.authors[0] if paper.authors else "Unbekannt"
        if len(paper.authors) > 1:
            author_str += " et al."
        year_str = f" ({paper.year})" if paper.year else ""
        cite_str = f" [{paper.citation_count} Zitationen]" if paper.citation_count else ""
        lines.append(f"- {author_str}{year_str}: {paper.title}{cite_str}")

    lines.append("")
    return "\n".join(lines)
