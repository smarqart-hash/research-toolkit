"""Exa API Client — Ergaenzende Paper-Suche.

Optional: Nur wenn EXA_API_KEY gesetzt. Findet neue/obskure Papers
die Semantic Scholar noch nicht indexiert hat.

API Docs: https://docs.exa.ai
Best Practices (Stand Maerz 2026):
- highlights statt text fuer Agent-Workflows (10x weniger Tokens)
- category "research paper" statt include_domains (weniger restriktiv)
- highlights.query fuer topic-relevante Excerpts
- type "deep" fuer bessere Research-Qualitaet
- additionalQueries fuer breitere Abdeckung
- highlightsPerUrl + highlightsNumSentences fuer kontrollierte Excerpts
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

BASE_URL = "https://api.exa.ai"


class ExaResult(BaseModel):
    """Ein Suchergebnis von Exa."""

    model_config = ConfigDict(populate_by_name=True)

    url: str
    title: str
    text: str | None = None
    highlights: list[str] = Field(default_factory=list)
    highlight_scores: list[float] = Field(
        default_factory=list, alias="highlightScores"
    )
    published_date: str | None = Field(default=None, alias="publishedDate")
    author: str | None = None
    score: float | None = None


class ExaSearchResponse(BaseModel):
    """Antwort der Exa-Suche."""

    results: list[ExaResult] = Field(default_factory=list)


class ExaClient:
    """Client fuer die Exa Search API. Nur aktiv wenn API Key vorhanden.

    Nutzt Connection Pooling: ein httpx.AsyncClient wird wiederverwendet.
    Unterstuetzt async Context Manager (async with ExaClient() as client).
    """

    MAX_RETRIES = 1
    RETRY_DELAY_S = 2.0

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("EXA_API_KEY")
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["x-api-key"] = self._api_key
        self._client = httpx.AsyncClient(timeout=30, headers=headers)

    async def close(self) -> None:
        """Schliesst den HTTP-Client und gibt Verbindungen frei."""
        await self._client.aclose()

    async def __aenter__(self) -> ExaClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    @property
    def is_available(self) -> bool:
        """Prueft ob der Client nutzbar ist (API Key vorhanden)."""
        return self._api_key is not None and self._api_key != ""

    async def search_papers(
        self,
        query: str,
        *,
        num_results: int = 30,
        start_published_date: str | None = None,
        additional_queries: list[str] | None = None,
        search_type: str = "deep",
    ) -> ExaSearchResponse:
        """Sucht nach akademischen Papers via Exa.

        Args:
            query: Suchbegriff.
            num_results: Max Ergebnisse (default 30, max 50).
            start_published_date: Fruehestes Datum (ISO, z.B. "2023-01-01").
            additional_queries: Zusaetzliche Query-Varianten fuer breitere Abdeckung.
            search_type: Suchtyp ("deep" fuer Qualitaet, "auto" fuer Speed).

        Raises:
            RuntimeError: Wenn kein API Key konfiguriert.
        """
        if not self.is_available:
            raise RuntimeError("EXA_API_KEY nicht gesetzt")

        # type "deep": bessere Qualitaet fuer Research (vs "auto")
        # category "research paper": breiter als include_domains, weniger Noise
        # highlights: 10x weniger Tokens, topic-relevante Excerpts
        # highlightsPerUrl + highlightsNumSentences: kontrollierte Excerpt-Menge
        payload: dict = {
            "query": query,
            "num_results": min(num_results, 50),
            "type": search_type,
            "category": "research paper",
            "contents": {
                "highlights": {
                    "max_characters": 4000,
                    "query": query,
                    "highlightsPerUrl": 3,
                    "highlightsNumSentences": 3,
                },
            },
        }
        if start_published_date:
            payload["start_published_date"] = start_published_date
        if additional_queries:
            payload["additionalQueries"] = additional_queries[:4]

        for attempt in range(self.MAX_RETRIES + 1):
            response = await self._client.post(
                f"{BASE_URL}/search",
                json=payload,
            )
            if response.status_code == 429 and attempt < self.MAX_RETRIES:
                logger.warning(
                    "Exa Rate Limit (429), warte %.1fs (Versuch %d/%d)",
                    self.RETRY_DELAY_S,
                    attempt + 1,
                    self.MAX_RETRIES + 1,
                )
                await asyncio.sleep(self.RETRY_DELAY_S)
                continue
            response.raise_for_status()
            return ExaSearchResponse.model_validate(response.json())

        raise httpx.HTTPStatusError(
            "Exa Rate Limit nach Retries",
            request=response.request,
            response=response,
        )
