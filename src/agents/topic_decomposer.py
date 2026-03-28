"""Topic Decomposer — zerlegt ein Forschungsthema via LLM in recherchierbare Facetten.

Nutzt das Research-Brief Schema aus dem research-brief Skill.
Output ist ein TopicDecomposition-Objekt mit Facetten, Leitfragen, Scope und Exclusions.
"""

from __future__ import annotations

import json
import logging
import re

from pydantic import BaseModel, Field

from src.utils.llm_client import LLMConfig, llm_complete, load_llm_config

logger = logging.getLogger(__name__)

# Grenzen fuer Facetten-Anzahl
_MIN_FACETS = 2
_MAX_FACETS = 8

# System-Prompt fuer Topic-Zerlegung
_SYSTEM_PROMPT = """Du bist ein Forschungsassistent der komplexe Themen in recherchierbare Facetten zerlegt.
Antworte AUSSCHLIESSLICH mit einem validen JSON-Objekt — kein Markdown, kein Text davor oder danach.

Das JSON-Objekt muss exakt dieses Schema haben:
{
  "topic": "string — das originale Thema",
  "research_question": "string — praezise Forschungsfrage (auf Englisch)",
  "scope": "string — 2-3 Saetze was untersucht wird (auf Englisch)",
  "core_terms": ["string", ...],
  "exclusions": ["string", ...],
  "facets": [
    {
      "name": "string — Facetten-Name",
      "description": "string — was dieser Aspekt abdeckt",
      "search_query": "string — Search-Query fuer research-toolkit"
    }
  ],
  "suggested_leitfragen": ["string", ...]
}

Regeln:
- 2-8 Facetten (optimal: 3-6, jede Facette wird ein eigener Search-Lauf)
- Jede Facette deckt einen ANDEREN Aspekt ab (Overlap < 20%)
- core_terms: die 2-5 spezifischsten Begriffe (nicht generisch wie 'AI', 'research')
- exclusions: explizit benennen um Off-Topic-Drift zu verhindern
- search_query: auf Englisch, als Keywords (kein Boolean)
- research_question und scope: auf Englisch (Search-APIs sind EN-dominant)"""

_USER_PROMPT_DE = """Zerlege dieses Forschungsthema in {min}-{max} recherchierbare Facetten:

Thema: {topic}

Antworte nur mit dem JSON-Objekt."""

_USER_PROMPT_EN = """Decompose this research topic into {min}-{max} researchable facets:

Topic: {topic}

Reply with the JSON object only."""


class Facet(BaseModel):
    """Eine recherchierbare Facette eines Forschungsthemas."""

    name: str
    description: str
    search_query: str


class TopicDecomposition(BaseModel):
    """Strukturierte Zerlegung eines Forschungsthemas."""

    topic: str
    research_question: str
    scope: str
    core_terms: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    facets: list[Facet] = Field(default_factory=list)
    suggested_leitfragen: list[str] = Field(default_factory=list)


def _extract_json(text: str) -> str:
    """Extrahiert JSON aus einem LLM-Response-Text (entfernt Markdown-Bloecke etc.)."""
    # Markdown-Codeblock entfernen
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    # Erstes { ... } in der Antwort suchen
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return match.group(0)
    return text.strip()


def _validate_facet_count(decomposition: TopicDecomposition) -> None:
    """Prueft ob die Facetten-Anzahl im gueltigen Bereich liegt.

    Raises:
        ValueError: Wenn weniger als _MIN_FACETS oder mehr als _MAX_FACETS Facetten vorhanden.
    """
    count = len(decomposition.facets)
    if count < _MIN_FACETS:
        raise ValueError(
            f"Zu wenige Facetten: {count} (Minimum: {_MIN_FACETS}). "
            "LLM-Antwort war ungueltig oder das Thema zu eng gefasst."
        )
    if count > _MAX_FACETS:
        raise ValueError(
            f"Zu viele Facetten: {count} (Maximum: {_MAX_FACETS}). "
            "LLM-Antwort war ungueltig oder das Thema zu breit gefasst."
        )


async def decompose_topic(
    topic: str,
    language: str = "de",
    *,
    config: LLMConfig | None = None,
) -> TopicDecomposition:
    """Zerlegt ein Forschungsthema via LLM in recherchierbare Facetten.

    Args:
        topic: Das zu zerlegende Forschungsthema.
        language: Sprache des User-Prompts ('de' oder 'en'). Standardmaessig 'de'.
        config: LLM-Konfiguration (Default: aus Env-Vars).

    Returns:
        TopicDecomposition mit Facetten, Leitfragen, Scope und Exclusions.

    Raises:
        ValueError: Wenn LLM kein valides JSON liefert, Pflichtfelder fehlen,
                    oder die Facetten-Anzahl ausserhalb von 2-8 liegt.
        RuntimeError: Wenn kein API-Key konfiguriert ist.
        httpx.HTTPStatusError: Bei API-Fehlern.
    """
    if config is None:
        config = load_llm_config()

    user_template = _USER_PROMPT_DE if language == "de" else _USER_PROMPT_EN
    user_message = user_template.format(
        topic=topic,
        min=_MIN_FACETS,
        max=_MAX_FACETS,
    )

    raw_response = await llm_complete(
        system_prompt=_SYSTEM_PROMPT,
        user_message=user_message,
        config=config,
    )

    json_text = _extract_json(raw_response)

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM hat kein valides JSON geliefert: {exc}\n"
            f"Response (erste 500 Zeichen): {raw_response[:500]}"
        ) from exc

    try:
        decomposition = TopicDecomposition.model_validate(data)
    except Exception as exc:
        raise ValueError(
            f"JSON-Schema-Validierung fehlgeschlagen: {exc}\n"
            f"Data: {data!r}"
        ) from exc

    _validate_facet_count(decomposition)

    return decomposition
