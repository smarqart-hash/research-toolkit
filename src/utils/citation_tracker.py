"""Citation Tracker — Implizites Feedback via Zitationsabgleich.

Prueft welche Evidence-Card-Papers im Draft tatsaechlich zitiert werden.
Loggt CITATION_USED Events in provenance.jsonl.
"""

from __future__ import annotations

import logging
import re

from src.utils.evidence_card import EvidenceCard

logger = logging.getLogger(__name__)


def track_citations(
    draft_md: str,
    cards: list[EvidenceCard],
) -> list[str]:
    """Findet welche Evidence-Card-Papers im Draft zitiert werden.

    Matching-Strategie:
    - Titel-Substring im Markdown (case-insensitive)
    - Autor-Nachname + Jahr Pattern (z.B. "Smith 2024", "Smith et al. 2024")

    Gibt Liste der zitierten paper_ids zurueck.
    """
    if not draft_md or not cards:
        if not cards:
            return []
        logger.warning("Leerer Draft — keine Zitationen moeglich")
        return []

    cited_ids: list[str] = []
    draft_lower = draft_md.lower()

    for card in cards:
        title_match = (
            card.paper_title.lower() in draft_lower if card.paper_title else False
        )

        author_year_match = False
        if card.authors and card.year:
            # Format "Nachname, Vorname" oder "Nachname"
            raw = card.authors[0]
            first_author = raw.split(",")[0].strip() if "," in raw else raw.split()[-1]
            pattern = rf"{re.escape(first_author)}.*?{card.year}"
            author_year_match = bool(re.search(pattern, draft_md, re.IGNORECASE))

        if title_match or author_year_match:
            cited_ids = [*cited_ids, card.paper_id]

    if not cited_ids:
        logger.warning("Keine Zitationen im Draft gefunden — 0 CITATION_USED Events")

    return cited_ids
