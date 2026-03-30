"""DBLP API Client — Computer Science Bibliographie.

6M+ Eintraege, spezialisiert auf CS/Informatik. Kostenlos, kein API Key noetig.
Gute Abdeckung deutscher Autoren, Konferenzen (GI, INFORMATIK) und Venues.

API Docs: https://dblp.org/faq/How+to+use+the+dblp+search+API.html
"""

from __future__ import annotations

import asyncio
import logging

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

BASE_URL = "https://dblp.org/search/publ/api"


class DBLPAuthor(BaseModel):
    """Autor aus DBLP."""

    text: str = ""  # Name des Autors


class DBLPInfo(BaseModel):
    """Info-Block eines DBLP-Eintrags."""

    authors: dict = Field(default_factory=dict)  # {"author": [{"text": "..."}] oder {"text": "..."}}
    title: str = ""
    venue: str = ""
    year: str = ""
    type: str = ""  # Conference and Workshop Papers, Journal Articles, etc.
    doi: str | None = None
    url: str = ""  # DBLP URL
    ee: str | None = None  # Electronic Edition URL (oft Publisher-Link)

    @property
    def year_int(self) -> int | None:
        if self.year and self.year.isdigit():
            return int(self.year)
        return None

    @property
    def author_names(self) -> list[str]:
        """Extrahiert Autorennamen aus dem verschachtelten Format."""
        raw = self.authors.get("author", [])
        if isinstance(raw, dict):
            return [raw.get("text", "")]
        if isinstance(raw, list):
            return [a.get("text", "") if isinstance(a, dict) else str(a) for a in raw]
        return []


class DBLPHit(BaseModel):
    """Ein Treffer aus der DBLP-Suche."""

    score: str = ""  # Relevanz-Score als String
    info: DBLPInfo = Field(default_factory=DBLPInfo)

    @property
    def relevance_score(self) -> float:
        try:
            return float(self.score)
        except (ValueError, TypeError):
            return 0.0


class DBLPResult(BaseModel):
    """Wrapper fuer die hits-Struktur."""

    hit: list[DBLPHit] = Field(default_factory=list)
    total: str = "0"  # DBLP liefert total als String

    @property
    def total_int(self) -> int:
        try:
            return int(self.total)
        except (ValueError, TypeError):
            return 0


class DBLPSearchResponse(BaseModel):
    """Antwort der DBLP API."""

    result: dict = Field(default_factory=dict)

    @property
    def hits(self) -> DBLPResult:
        raw = self.result.get("hits", {})
        return DBLPResult.model_validate(raw)


class DBLPClient:
    """Client fuer die DBLP Publication Search API.

    Kostenlos, kein API Key noetig. Rate Limit inoffiziell ~1 req/s.
    Unterstuetzt async Context Manager.
    """

    MAX_RETRIES = 1
    RETRY_DELAY_S = 2.0

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=30,
            headers={"User-Agent": "auguri.us/1.0 (research briefing platform)"},
        )

    async def close(self) -> None:
        """Schliesst den HTTP-Client und gibt Verbindungen frei."""
        await self._client.aclose()

    async def __aenter__(self) -> DBLPClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def search(
        self,
        query: str,
        *,
        hits: int = 30,
        offset: int = 0,
    ) -> DBLPSearchResponse:
        """Sucht Publikationen in DBLP.

        Args:
            query: Suchbegriff (Freitext, Autor, Venue).
            hits: Max Ergebnisse (1-1000).
            offset: Pagination (first result index).
        """
        params: dict[str, str | int] = {
            "q": query,
            "format": "json",
            "h": min(hits, 1000),
            "f": offset,
        }

        for attempt in range(self.MAX_RETRIES + 1):
            response = await self._client.get(BASE_URL, params=params)
            if response.status_code == 429 and attempt < self.MAX_RETRIES:
                logger.warning(
                    "DBLP Rate Limit (429), warte %.1fs (Versuch %d/%d)",
                    self.RETRY_DELAY_S,
                    attempt + 1,
                    self.MAX_RETRIES + 1,
                )
                await asyncio.sleep(self.RETRY_DELAY_S)
                continue
            response.raise_for_status()
            return DBLPSearchResponse.model_validate(response.json())

        raise httpx.HTTPStatusError(
            "DBLP Rate Limit nach Retries",
            request=response.request,
            response=response,
        )
