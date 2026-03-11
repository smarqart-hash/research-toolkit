"""Self-Enhancement Bias Test — Prueft ob LLM-Review eigene Drafts bevorzugt.

Blinded Scoring: LLM bewertet eigenen Draft und Kontrolltexte unter
neutralen IDs (t1, t2, ...). Vergleich der Scores zeigt ob Bias vorliegt.
Threshold: >2.0 Punkte Differenz = Bias detected.
"""

from __future__ import annotations

import json
import logging
import random
from collections.abc import Sequence

from pydantic import BaseModel, Field

from src.utils.llm_client import LLMConfig, llm_complete, load_llm_config

logger = logging.getLogger(__name__)

_BIAS_THRESHOLD = 2.0  # Score-Differenz ab der Bias erkannt wird


class TextScoring(BaseModel):
    """Bewertung eines einzelnen Textes."""

    text_id: str
    label: str  # "own_draft" oder "control_N"
    score: float = Field(ge=0.0, le=10.0)
    reasoning: str = ""


class BiasTestResult(BaseModel):
    """Ergebnis des Self-Enhancement Bias Tests."""

    own_draft_score: float = 0.0
    control_mean_score: float = 0.0
    scorings: list[TextScoring] = Field(default_factory=list)
    bias_detected: bool = False
    bias_magnitude: float = 0.0  # own - control_mean (positiv = eigener besser)


# --- Prompt ---

_SCORING_SYSTEM_PROMPT = """\
Du bist ein akademischer Text-Bewerter. Bewerte die Qualitaet jedes Textes \
fuer das gegebene Thema auf einer Skala von 0-10.

Bewertungskriterien:
- Inhaltliche Tiefe und Korrektheit (0-3)
- Struktur und Kohaerenz (0-3)
- Quellenarbeit und Evidenz (0-2)
- Sprachliche Qualitaet (0-2)

Antworte AUSSCHLIESSLICH als JSON:
{
  "scorings": [
    {"text_id": "...", "score": 0-10, "reasoning": "Kurze Begruendung"}
  ]
}

WICHTIG: Bewerte jeden Text unabhaengig. Keine Vergleiche zwischen Texten.
Keine Markdown-Formatierung, nur reines JSON."""


def _build_scoring_prompt(
    topic: str,
    texts: Sequence[tuple[str, str]],
) -> str:
    """Baut User-Message mit neutralen Text-IDs."""
    lines = [f"Thema: {topic}\n", "Texte:\n"]
    for text_id, content in texts:
        lines = [
            *lines,
            f"--- Text {text_id} ---",
            content,
            "",
        ]
    return "\n".join(lines)


def _parse_scoring_response(
    raw: str,
    valid_ids: Sequence[str],
) -> list[TextScoring]:
    """Parst LLM-Antwort in TextScoring-Liste."""
    # Markdown-Wrapper entfernen
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Bias-Test-JSON konnte nicht geparst werden: %s", raw[:80])
        return []

    valid_set = set(valid_ids)
    result: list[TextScoring] = []
    for item in data.get("scorings", []):
        tid = item.get("text_id", "")
        if tid not in valid_set:
            continue
        score = float(item.get("score", 0))
        score = max(0.0, min(10.0, score))
        result = [
            *result,
            TextScoring(
                text_id=tid,
                label=tid,  # Wird spaeter durch Caller ueberschrieben
                score=score,
                reasoning=item.get("reasoning", ""),
            ),
        ]

    return result


# --- Hauptfunktion ---


async def run_bias_test(
    topic: str,
    own_draft: str,
    control_texts: Sequence[str],
    *,
    config: LLMConfig | None = None,
    bias_threshold: float = _BIAS_THRESHOLD,
) -> BiasTestResult:
    """Fuehrt blinded Self-Enhancement Bias Test durch.

    Args:
        topic: Forschungsthema.
        own_draft: Der eigene (AI-generierte) Draft.
        control_texts: Externe/manuell geschriebene Kontrolltexte.
        config: LLM-Konfiguration.
        bias_threshold: Ab welcher Score-Differenz Bias erkannt wird.

    Returns:
        BiasTestResult mit Scores und Bias-Analyse.
    """
    if not control_texts:
        return BiasTestResult()

    llm_config = config or load_llm_config()

    # Blinded: Neutrale IDs randomisiert vergeben
    labels = ["own_draft", *[f"control_{i}" for i in range(len(control_texts))]]
    contents = [own_draft, *control_texts]
    # IDs shufflen damit own_draft nicht immer t1 ist
    ids = [f"t{i + 1}" for i in range(len(labels))]
    random.shuffle(ids)
    all_texts: list[tuple[str, str, str]] = [
        (label, tid, content) for label, tid, content in zip(labels, ids, contents)
    ]

    # Reihenfolge-Blindheit
    shuffled = list(all_texts)
    random.shuffle(shuffled)

    # Prompt bauen mit neutralen IDs
    prompt_texts = [(entry[1], entry[2]) for entry in shuffled]
    valid_ids = [entry[1] for entry in shuffled]

    # LLM bewerten lassen
    try:
        user_msg = _build_scoring_prompt(topic, prompt_texts)
        raw = await llm_complete(_SCORING_SYSTEM_PROMPT, user_msg, config=llm_config)
        raw_scorings = _parse_scoring_response(raw, valid_ids)
    except Exception as e:
        logger.warning("Bias-Test LLM-Fehler: %s", e)
        return BiasTestResult()

    # Neutrale IDs zurueck zu Labels mappen
    id_to_label = {entry[1]: entry[0] for entry in all_texts}
    scorings: list[TextScoring] = []
    for scoring in raw_scorings:
        label = id_to_label.get(scoring.text_id, scoring.text_id)
        scorings = [
            *scorings,
            TextScoring(
                text_id=scoring.text_id,
                label=label,
                score=scoring.score,
                reasoning=scoring.reasoning,
            ),
        ]

    # Scores extrahieren
    own_score = 0.0
    control_scores: list[float] = []
    for s in scorings:
        if s.label == "own_draft":
            own_score = s.score
        else:
            control_scores = [*control_scores, s.score]

    control_mean = sum(control_scores) / len(control_scores) if control_scores else 0.0
    magnitude = round(own_score - control_mean, 2)

    return BiasTestResult(
        own_draft_score=own_score,
        control_mean_score=control_mean,
        scorings=scorings,
        bias_detected=abs(magnitude) > bias_threshold,
        bias_magnitude=magnitude,
    )
