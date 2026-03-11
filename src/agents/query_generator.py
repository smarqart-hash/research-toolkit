"""Smart Query Generator — 2-Stufen Query-Expansion fuer Paper-Suche.

Stufe 1 (lokal): Regelbasierte Synonym-Expansion, Boolean-Queries, immer verfuegbar.
Stufe 2 (LLM): OpenAI-kompatibles API (OpenRouter/Ollama), optional.

Ersetzt die einfache Heuristik in forschungsstand.generate_search_queries()
durch intelligente, API-spezifische Queries (SS: Boolean, Exa: Natural Language).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from pydantic import BaseModel, Field

from src.utils import CONFIG_DIR

logger = logging.getLogger(__name__)

# Pfad zu Config-Templates
_QUERY_TEMPLATES_DIR = CONFIG_DIR / "query_templates"


# --- Datenmodelle ---


class SearchScope(BaseModel):
    """Suchbereich-Eingrenzung."""

    year_range: tuple[int, int] | None = None
    languages: list[str] = Field(default_factory=lambda: ["en", "de"])
    fields_of_study: list[str] = Field(default_factory=list)


class QuerySet(BaseModel):
    """Generierte Suchqueries, getrennt nach API-Format."""

    research_question: str
    ss_queries: list[str] = Field(default_factory=list)
    exa_queries: list[str] = Field(default_factory=list)
    oa_queries: list[str] = Field(default_factory=list)
    scope: SearchScope = Field(default_factory=SearchScope)
    source: str = "local"  # "local" | "llm"


# --- Synonym-Map ---


def _load_synonyms() -> dict[str, list[str]]:
    """Laedt die Synonym-Map aus config/query_templates/synonyms.json."""
    path = _QUERY_TEMPLATES_DIR / "synonyms.json"
    if not path.exists():
        logger.warning("Synonym-Map nicht gefunden: %s", path)
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _find_synonyms(topic: str, synonym_map: dict[str, list[str]]) -> list[tuple[str, list[str]]]:
    """Findet passende Synonyme fuer Terme im Topic.

    Returns:
        Liste von (Term, [Synonyme]) Paaren.
    """
    topic_lower = topic.lower()
    matches: list[tuple[str, list[str]]] = []
    for term, synonyms in synonym_map.items():
        if term.lower() in topic_lower:
            matches = [*matches, (term, synonyms)]
    return matches


# --- Stufe 1: Lokale Expansion ---


def _extract_leitfragen_keywords(leitfragen: list[str]) -> list[str]:
    """Extrahiert Kern-Keywords aus Leitfragen (Fragewoerter entfernen)."""
    keywords: list[str] = []
    for frage in leitfragen:
        cleaned = frage.strip().rstrip("?")
        for prefix in [
            "Wie ", "Was ", "Welche ", "Warum ", "Inwieweit ",
            "How ", "What ", "Which ", "Why ", "To what extent ",
        ]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
                break
        if cleaned:
            keywords = [*keywords, cleaned]
    return keywords


def _build_boolean_query(topic: str, extra_terms: list[str]) -> str:
    """Baut eine Boolean-Query fuer Semantic Scholar."""
    if not extra_terms:
        return topic
    or_clause = " OR ".join(f'"{t}"' for t in extra_terms)
    return f"{topic} AND ({or_clause})"


def _expand_local(
    topic: str,
    leitfragen: list[str] | None = None,
    scope: SearchScope | None = None,
) -> QuerySet:
    """Regelbasierte Query-Expansion (Stufe 1, immer verfuegbar).

    Generiert min. 3 SS-Queries (Boolean) + min. 2 Exa-Queries (Natural Language).
    """
    synonym_map = _load_synonyms()
    matches = _find_synonyms(topic, synonym_map)
    keywords = _extract_leitfragen_keywords(leitfragen or [])

    # SS-Queries: Boolean-Format
    ss_queries: list[str] = [topic]

    # Synonym-basierte Queries
    for term, synonyms in matches:
        ss_queries = [*ss_queries, _build_boolean_query(topic, synonyms[:3])]

    # Leitfragen-basierte Queries
    for kw in keywords[:3]:
        ss_queries = [*ss_queries, f"{topic} AND {kw}"]

    # Garantie: min. 3 SS-Queries
    if len(ss_queries) < 3:
        ss_queries = [*ss_queries, f'"{topic}"']
    if len(ss_queries) < 3:
        ss_queries = [*ss_queries, f"{topic} survey OR review"]

    # Exa-Queries: Natural Language
    exa_queries: list[str] = [
        f"What are recent advances in {topic}?",
        f"Survey of {topic} methods and applications",
    ]
    for kw in keywords[:2]:
        exa_queries = [*exa_queries, f"How does {topic} relate to {kw}?"]

    # OA-Queries: Freitext ohne Boolean-Operatoren (OpenAlex nutzt eigene Relevanz-Engine)
    all_synonyms = [syn for _, syns in matches for syn in syns[:2]]
    oa_queries: list[str] = [
        topic,
        f"{topic} survey",
        *[f"{topic} {syn}" for syn in all_synonyms[:2]],
    ]

    return QuerySet(
        research_question=topic,
        ss_queries=ss_queries,
        exa_queries=exa_queries,
        oa_queries=oa_queries,
        scope=scope or SearchScope(),
        source="local",
    )


# --- Stufe 2: LLM-Enhanced Expansion ---


def _load_expand_prompt() -> str:
    """Laedt den System-Prompt fuer LLM-Expansion."""
    path = _QUERY_TEMPLATES_DIR / "expand_prompt.txt"
    if not path.exists():
        logger.warning("Expand-Prompt nicht gefunden: %s", path)
        return "Generate search queries for academic literature search. Respond in JSON."
    return path.read_text(encoding="utf-8")


async def _expand_llm(
    topic: str,
    leitfragen: list[str] | None = None,
    scope: SearchScope | None = None,
) -> QuerySet:
    """LLM-gestuetzte Query-Expansion (Stufe 2, braucht API-Key).

    Raises:
        RuntimeError: Wenn kein API-Key konfiguriert.
        httpx.HTTPStatusError: Bei API-Fehlern.
        httpx.TimeoutException: Bei Timeout.
        ValueError: Wenn LLM-Response nicht parsebar.
    """
    from src.utils.llm_client import llm_complete

    system_prompt = _load_expand_prompt()
    leitfragen_text = "\n".join(f"- {f}" for f in (leitfragen or []))
    user_message = f"Thema: {topic}"
    if leitfragen_text:
        user_message = f"{user_message}\nLeitfragen:\n{leitfragen_text}"

    raw_response = await llm_complete(system_prompt, user_message)

    # Markdown-JSON-Wrapper entfernen (```json ... ```)
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    # JSON parsen
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        preview = raw_response[:200] if raw_response else "(leer)"
        raise ValueError(
            f"LLM-Response ist kein valides JSON: {e}\nPreview: {preview}"
        ) from e

    # Validierung: min. 3 SS + 2 Exa
    ss_queries = data.get("ss_queries", [])
    exa_queries = data.get("exa_queries", [])
    research_question = data.get("research_question", topic)

    if not isinstance(ss_queries, list) or len(ss_queries) < 1:
        n = len(ss_queries) if isinstance(ss_queries, list) else 0
        raise ValueError(f"LLM gab {n} SS-Queries (min. 1)")
    if not isinstance(exa_queries, list) or len(exa_queries) < 1:
        n = len(exa_queries) if isinstance(exa_queries, list) else 0
        raise ValueError(f"LLM gab {n} Exa-Queries (min. 1)")

    # OA-Queries: Freitext ohne Boolean-Operatoren
    oa_queries = data.get("oa_queries", [])
    if not isinstance(oa_queries, list) or not oa_queries:
        # Fallback: Boolean-Operatoren + Klammern entfernen, Whitespace normalisieren
        oa_queries = [
            re.sub(r"\s+", " ", re.sub(r"\s*(AND|OR|NOT)\s*|[()]", " ", q)).strip()
            for q in ss_queries
        ]

    return QuerySet(
        research_question=research_question,
        ss_queries=ss_queries,
        exa_queries=exa_queries,
        oa_queries=oa_queries,
        scope=scope or SearchScope(),
        source="llm",
    )


# --- Public API ---


async def refine_topic(
    topic: str,
    leitfragen: list[str] | None = None,
) -> str:
    """Praezisiert ein vages Topic zu einer Forschungsfrage.

    Lokal: Gibt Topic unveraendert zurueck (kein Refinement ohne LLM).
    LLM: Nutzt PICO/SPIDER-Framework fuer kreative Umformulierung.
    """
    from src.utils.llm_client import load_llm_config

    config = load_llm_config()
    if not config.is_available:
        return topic

    try:
        query_set = await _expand_llm(topic, leitfragen)
        return query_set.research_question
    except Exception as e:
        logger.warning("LLM Topic-Refinement fehlgeschlagen: %s — nutze Original-Topic", e)
        return topic


async def expand_queries(
    topic: str,
    leitfragen: list[str] | None = None,
    scope: SearchScope | None = None,
) -> QuerySet:
    """Generiert optimierte Suchqueries (2-Stufen-Architektur).

    Stufe 1 (immer): Lokale regelbasierte Expansion.
    Stufe 2 (optional): LLM-Enhanced, wenn LLM_API_KEY gesetzt.
    Fallback: Bei LLM-Fehler → Stufe 1 mit Warning.
    """
    from src.utils.llm_client import load_llm_config

    config = load_llm_config()

    # Stufe 2: LLM-Enhanced (wenn verfuegbar)
    if config.is_available:
        try:
            return await _expand_llm(topic, leitfragen, scope)
        except Exception as e:
            logger.warning("LLM Query-Expansion fehlgeschlagen: %s — Fallback auf lokal", e)

    # Stufe 1: Lokal (immer verfuegbar)
    return _expand_local(topic, leitfragen, scope)


async def validate_queries(
    query_set: QuerySet,
    ss_client: object,
    exa_client: object | None = None,
) -> QuerySet:
    """Dry-Run: Prueft ob Queries Ergebnisse liefern.

    Entfernt Queries die 0 Ergebnisse liefern. Garantiert min. 1 SS-Query
    (Fallback auf research_question als Topic-Query).

    Args:
        query_set: Zu validierende Queries.
        ss_client: SemanticScholarClient-Instanz.
        exa_client: Optionaler ExaClient (wenn Exa-Queries validiert werden sollen).
    """
    import httpx as _httpx

    # SS-Queries validieren
    valid_ss: list[str] = []
    for query in query_set.ss_queries:
        try:
            response = await ss_client.search_papers(query, limit=1)  # type: ignore[attr-defined]
            if response.total > 0:
                valid_ss = [*valid_ss, query]
            else:
                logger.warning("SS-Query ohne Ergebnisse entfernt: '%s'", query)
        except (_httpx.HTTPStatusError, _httpx.TimeoutException) as e:
            logger.warning("SS-Query Validation fehlgeschlagen fuer '%s': %s", query, e)
            valid_ss = [*valid_ss, query]  # Bei Fehler behalten (benefit of the doubt)

    # Garantie: min. 1 SS-Query
    if not valid_ss:
        logger.warning("Alle SS-Queries entfernt — Fallback auf Topic-Query")
        valid_ss = [query_set.research_question]

    # Exa-Queries: nur validieren wenn Client vorhanden und verfuegbar
    valid_exa = query_set.exa_queries
    if exa_client is not None and getattr(exa_client, "is_available", False):
        validated_exa: list[str] = []
        for query in query_set.exa_queries:
            try:
                response = await exa_client.search_papers(query, num_results=1)  # type: ignore[attr-defined]
                if response.results:
                    validated_exa = [*validated_exa, query]
                else:
                    logger.warning("Exa-Query ohne Ergebnisse entfernt: '%s'", query)
            except (_httpx.HTTPStatusError, _httpx.TimeoutException) as e:
                logger.warning("Exa-Query Validation fehlgeschlagen fuer '%s': %s", query, e)
                validated_exa = [*validated_exa, query]
        valid_exa = validated_exa if validated_exa else query_set.exa_queries

    return QuerySet(
        research_question=query_set.research_question,
        ss_queries=valid_ss,
        exa_queries=valid_exa,
        oa_queries=query_set.oa_queries,  # OA-Queries nicht validiert — Freitext-Suche ist fehlertolerant
        scope=query_set.scope,
        source=query_set.source,
    )
