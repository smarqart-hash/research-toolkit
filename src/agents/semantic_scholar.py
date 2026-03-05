"""Semantic Scholar API Client.

Primaere Quelle fuer Paper-Suche. Kostenlos, kein API Key noetig fuer Basis-Zugriff.
Mit API Key: hoehere Rate Limits.

API Docs: https://api.semanticscholar.org/api-docs/
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

BASE_URL = "https://api.semanticscholar.org/graph/v1"

# Felder die wir pro Paper abfragen
PAPER_FIELDS = (
    "paperId,title,abstract,year,authors,citationCount,"
    "referenceCount,isOpenAccess,openAccessPdf,externalIds,"
    "publicationTypes,journal,fieldsOfStudy"
)


class Author(BaseModel):
    """Paper-Autor."""

    authorId: str | None = None
    name: str


class ExternalIds(BaseModel):
    """Externe Identifier (DOI, arXiv, etc.)."""

    DOI: str | None = None
    ArXiv: str | None = None
    PubMed: str | None = None
    CorpusId: int | None = None


class OpenAccessPdf(BaseModel):
    """Open Access PDF Info."""

    url: str
    status: str | None = None


class Journal(BaseModel):
    """Journal-Info."""

    name: str | None = None
    volume: str | None = None
    pages: str | None = None


class PaperResult(BaseModel):
    """Ein Paper aus der Semantic Scholar API."""

    paperId: str
    title: str
    abstract: str | None = None
    year: int | None = None
    authors: list[Author] = Field(default_factory=list)
    citationCount: int | None = None
    referenceCount: int | None = None
    isOpenAccess: bool | None = None
    openAccessPdf: OpenAccessPdf | None = None
    externalIds: ExternalIds | None = None
    publicationTypes: list[str] | None = None
    journal: Journal | None = None
    fieldsOfStudy: list[str] | None = None

    @property
    def doi(self) -> str | None:
        if self.externalIds:
            return self.externalIds.DOI
        return None

    @property
    def arxiv_id(self) -> str | None:
        if self.externalIds:
            return self.externalIds.ArXiv
        return None

    @property
    def first_author(self) -> str:
        if self.authors:
            return self.authors[0].name
        return "Unbekannt"


class SearchResponse(BaseModel):
    """Antwort der Paper-Suche."""

    total: int = 0
    offset: int = 0
    data: list[PaperResult] = Field(default_factory=list)


class SemanticScholarClient:
    """Client fuer die Semantic Scholar Academic Graph API."""

    MAX_RETRIES = 1
    RETRY_DELAY_S = 2.0

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("S2_API_KEY")
        self._headers: dict[str, str] = {}
        if self._api_key:
            self._headers["x-api-key"] = self._api_key
        else:
            logger.warning("S2_API_KEY nicht gesetzt — Rate Limits sind strenger")

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
    ) -> httpx.Response:
        """HTTP-Request mit Retry bei 429 Rate Limit."""
        for attempt in range(self.MAX_RETRIES + 1):
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.request(
                    method, url, params=params, headers=self._headers
                )
            if response.status_code == 429 and attempt < self.MAX_RETRIES:
                logger.warning(
                    "S2 Rate Limit (429), warte %.1fs (Versuch %d/%d)",
                    self.RETRY_DELAY_S,
                    attempt + 1,
                    self.MAX_RETRIES + 1,
                )
                await asyncio.sleep(self.RETRY_DELAY_S)
                continue
            response.raise_for_status()
            return response
        # Sollte nicht erreicht werden, aber fuer Typsicherheit
        raise httpx.HTTPStatusError(
            "Rate Limit nach Retries",
            request=response.request,
            response=response,
        )

    async def search_papers(
        self,
        query: str,
        *,
        limit: int = 50,
        offset: int = 0,
        year: str | None = None,
        fields_of_study: list[str] | None = None,
    ) -> SearchResponse:
        """Sucht Papers nach Freitext-Query.

        Args:
            query: Suchbegriff.
            limit: Max Ergebnisse (1-100).
            offset: Pagination.
            year: Jahrfilter, z.B. "2020-2026" oder "2024-".
            fields_of_study: Filter nach Fachgebiet.
        """
        params: dict[str, str | int] = {
            "query": query,
            "limit": min(limit, 100),
            "offset": offset,
            "fields": PAPER_FIELDS,
        }
        if year:
            params["year"] = year
        if fields_of_study:
            params["fieldsOfStudy"] = ",".join(fields_of_study)

        response = await self._request(
            "GET", f"{BASE_URL}/paper/search", params=params
        )
        return SearchResponse.model_validate(response.json())

    async def get_paper(self, paper_id: str) -> PaperResult:
        """Holt Details zu einem einzelnen Paper (via DOI, arXiv ID, oder SS ID).

        Args:
            paper_id: DOI (z.B. "10.1234/..."), arXiv ID, oder SS Paper ID.
        """
        response = await self._request(
            "GET",
            f"{BASE_URL}/paper/{paper_id}",
            params={"fields": PAPER_FIELDS},
        )
        return PaperResult.model_validate(response.json())

    async def get_citations(
        self, paper_id: str, *, limit: int = 50
    ) -> list[PaperResult]:
        """Holt Papers die dieses Paper zitieren (Forward Citations)."""
        response = await self._request(
            "GET",
            f"{BASE_URL}/paper/{paper_id}/citations",
            params={"fields": PAPER_FIELDS, "limit": min(limit, 100)},
        )
        data = response.json().get("data", [])
        return [
            PaperResult.model_validate(item["citingPaper"])
            for item in data
            if item.get("citingPaper")
        ]

    async def get_references(
        self, paper_id: str, *, limit: int = 50
    ) -> list[PaperResult]:
        """Holt Papers die von diesem Paper zitiert werden (Backward References)."""
        response = await self._request(
            "GET",
            f"{BASE_URL}/paper/{paper_id}/references",
            params={"fields": PAPER_FIELDS, "limit": min(limit, 100)},
        )
        data = response.json().get("data", [])
        return [
            PaperResult.model_validate(item["citedPaper"])
            for item in data
            if item.get("citedPaper")
        ]
