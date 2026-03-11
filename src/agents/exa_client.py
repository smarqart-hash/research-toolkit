"""Exa API Client — Ergaenzende Paper-Suche.

Optional: Nur wenn EXA_API_KEY gesetzt. Findet neue/obskure Papers
die Semantic Scholar noch nicht indexiert hat.

API Docs: https://docs.exa.ai
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

BASE_URL = "https://api.exa.ai"


class ExaResult(BaseModel):
    """Ein Suchergebnis von Exa."""

    url: str
    title: str
    text: str | None = None
    published_date: str | None = None
    author: str | None = None
    score: float | None = None


class ExaSearchResponse(BaseModel):
    """Antwort der Exa-Suche."""

    results: list[ExaResult] = Field(default_factory=list)


class ExaClient:
    """Client fuer die Exa Search API. Nur aktiv wenn API Key vorhanden."""

    MAX_RETRIES = 1
    RETRY_DELAY_S = 2.0

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("EXA_API_KEY")

    @property
    def is_available(self) -> bool:
        """Prueft ob der Client nutzbar ist (API Key vorhanden)."""
        return self._api_key is not None and self._api_key != ""

    async def search_papers(
        self,
        query: str,
        *,
        num_results: int = 20,
        start_published_date: str | None = None,
    ) -> ExaSearchResponse:
        """Sucht nach akademischen Papers via Exa.

        Args:
            query: Suchbegriff.
            num_results: Max Ergebnisse.
            start_published_date: Fruehestes Datum (ISO, z.B. "2023-01-01").

        Raises:
            RuntimeError: Wenn kein API Key konfiguriert.
        """
        if not self.is_available:
            raise RuntimeError("EXA_API_KEY nicht gesetzt")

        payload: dict = {
            "query": query,
            "num_results": num_results,
            "type": "auto",
            "category": "research paper",
            "contents": {
                "text": {"max_characters": 500},
            },
            "include_domains": [
                "arxiv.org",
                "doi.org",
                "nature.com",
                "ieee.org",
                "sciencedirect.com",
                "springer.com",
                "mdpi.com",
                "wiley.com",
                "acm.org",
                "nih.gov",
                "nasa.gov",
                # DACH-Repositorien
                "gesis.org",
                "dnb.de",
                "zbw.eu",
            ],
        }
        if start_published_date:
            payload["start_published_date"] = start_published_date

        for attempt in range(self.MAX_RETRIES + 1):
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{BASE_URL}/search",
                    json=payload,
                    headers={
                        "x-api-key": self._api_key,
                        "Content-Type": "application/json",
                    },
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
