"""OpenAlex API Client — Breite akademische Suche.

Kostenlos, kein API Key noetig. Polite Pool mit mailto-Header
fuer hoehere Rate Limits. 200M+ Works indexiert.

API Docs: https://developers.openalex.org/
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openalex.org"


class OpenAlexAuthor(BaseModel):
    """Autor aus Authorship."""

    display_name: str
    orcid: str | None = None


class OpenAlexAuthorship(BaseModel):
    """Authorship-Eintrag."""

    author: OpenAlexAuthor


class OpenAlexOpenAccess(BaseModel):
    """Open Access Info."""

    is_oa: bool = False
    oa_url: str | None = None


class OpenAlexWork(BaseModel):
    """Ein Work aus der OpenAlex API."""

    id: str
    doi: str | None = None
    display_name: str  # = Titel
    publication_year: int | None = None
    authorships: list[OpenAlexAuthorship] = Field(default_factory=list)
    cited_by_count: int = 0
    abstract_inverted_index: dict[str, list[int]] | None = None
    open_access: OpenAlexOpenAccess = Field(default_factory=OpenAlexOpenAccess)
    language: str | None = None
    type: str | None = None
    relevance_score: float = 0.0  # Von OpenAlex API geliefert (0-1)

    @property
    def abstract(self) -> str | None:
        """Rekonstruiert Abstract aus Inverted Index.

        OpenAlex speichert Abstracts als Inverted Index: {"Wort": [pos1, pos2]}.
        Wir sortieren nach Position und verbinden die Woerter.
        """
        if not self.abstract_inverted_index:
            return None
        # Inverted Index: {"word": [pos1, pos2]} → sortiert nach Position
        positions: list[tuple[int, str]] = []
        for word, idxs in self.abstract_inverted_index.items():
            for idx in idxs:
                positions.append((idx, word))
        positions.sort(key=lambda x: x[0])
        return " ".join(w for _, w in positions)

    @property
    def first_author(self) -> str:
        """Gibt den Erstautor zurueck, oder 'Unbekannt' wenn kein Autor."""
        if self.authorships:
            return self.authorships[0].author.display_name
        return "Unbekannt"


class OpenAlexSearchResponse(BaseModel):
    """Antwort der Works-Suche."""

    meta: dict = Field(default_factory=dict)  # count, per_page, next_cursor
    results: list[OpenAlexWork] = Field(default_factory=list)


class OpenAlexClient:
    """Client fuer die OpenAlex Works API.

    Immer verfuegbar (kein API Key noetig).
    Polite Pool: mailto-Parameter fuer hoehere Rate Limits.
    """

    MAX_RETRIES = 1
    RETRY_DELAY_S = 2.0

    def __init__(self, mailto: str | None = None) -> None:
        self._mailto = mailto or os.environ.get("OPENALEX_MAILTO")

    async def search_works(
        self,
        query: str,
        *,
        per_page: int = 50,
        year_range: str | None = None,
        languages: list[str] | None = None,
    ) -> OpenAlexSearchResponse:
        """Sucht Works nach Freitext-Query.

        Args:
            query: Suchbegriff.
            per_page: Max Ergebnisse (1-200).
            year_range: z.B. "2020-2026" → filter=publication_year:2020-2026
            languages: z.B. ["en", "de"] → filter=language:en|de
        """
        params: dict[str, str | int] = {
            "search": query,
            "per_page": min(per_page, 200),
        }
        if self._mailto:
            params["mailto"] = self._mailto

        # Filter zusammenbauen
        filters: list[str] = []
        if year_range:
            filters.append(f"publication_year:{year_range}")
        if languages:
            lang_filter = "|".join(languages)
            filters.append(f"language:{lang_filter}")
        if filters:
            params["filter"] = ",".join(filters)

        response: httpx.Response | None = None
        for attempt in range(self.MAX_RETRIES + 1):
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{BASE_URL}/works",
                    params=params,
                )
            if response.status_code == 429 and attempt < self.MAX_RETRIES:
                logger.warning(
                    "OpenAlex Rate Limit (429), warte %.1fs (Versuch %d/%d)",
                    self.RETRY_DELAY_S,
                    attempt + 1,
                    self.MAX_RETRIES + 1,
                )
                await asyncio.sleep(self.RETRY_DELAY_S)
                continue
            response.raise_for_status()
            return OpenAlexSearchResponse.model_validate(response.json())

        # Sollte nur bei MAX_RETRIES=0 mit 429 erreicht werden
        if response is not None:
            raise httpx.HTTPStatusError(
                "OpenAlex Rate Limit nach Retries",
                request=response.request,
                response=response,
            )
        raise RuntimeError("OpenAlex: Kein Response erhalten")
