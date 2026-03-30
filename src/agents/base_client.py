"""BASE (Bielefeld Academic Search Engine) API Client.

500M+ Dokumente aus 11.000+ Repositorien. Kostenlos, kein API Key noetig.
Gute Abdeckung deutschsprachiger Open-Access-Publikationen.

API Docs: https://www.base-search.net/about/en/about_api.php
"""

from __future__ import annotations

import asyncio
import logging

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

BASE_URL = "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi"


class BASEDocument(BaseModel):
    """Ein Dokument aus der BASE API."""

    dctitle: str = ""
    dcdescription: str | None = None
    dccreator: list[str] = Field(default_factory=list)
    dcyear: str | None = None
    dcidentifier: str | None = None  # URL zum Dokument
    dcdoi: str | None = None
    dclink: str | None = None  # Volltext-Link
    dclang: str | None = None  # Sprachcode (eng, deu, etc.)
    dctype: str | None = None  # article, report, thesis, etc.
    dcsubject: list[str] = Field(default_factory=list)
    dcoa: int | None = None  # 1 = Open Access, 0 = nicht

    @property
    def year(self) -> int | None:
        """Extrahiert Jahr als int."""
        if self.dcyear and self.dcyear.isdigit():
            return int(self.dcyear)
        return None

    @property
    def is_open_access(self) -> bool:
        return self.dcoa == 1

    @property
    def first_author(self) -> str:
        if self.dccreator:
            return self.dccreator[0]
        return "Unbekannt"


class BASESearchResponse(BaseModel):
    """Antwort der BASE API."""

    response: BASEResponseBody = Field(default_factory=lambda: BASEResponseBody())


class BASEResponseBody(BaseModel):
    """Response-Body mit numFound und docs."""

    numFound: int = 0
    docs: list[BASEDocument] = Field(default_factory=list)


class BASEClient:
    """Client fuer die BASE Search API.

    Kostenlos, kein API Key noetig. Rate Limit inoffiziell ~100 req/min.
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

    async def __aenter__(self) -> BASEClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def search(
        self,
        query: str,
        *,
        hits: int = 50,
        offset: int = 0,
        language: str | None = None,
        doc_type: str | None = None,
    ) -> BASESearchResponse:
        """Sucht Dokumente in BASE.

        Args:
            query: Suchbegriff (Freitext).
            hits: Max Ergebnisse (1-125).
            offset: Pagination.
            language: Sprachfilter (z.B. "eng", "deu").
            doc_type: Dokumenttyp-Filter (z.B. "article", "report").
        """
        # Solr-Query bauen
        fq_parts: list[str] = []
        if language:
            fq_parts.append(f"dclang:{language}")
        if doc_type:
            fq_parts.append(f"dctype:{doc_type}")

        params: dict[str, str | int] = {
            "func": "PerformSearch",
            "query": query,
            "format": "json",
            "hits": min(hits, 125),
            "offset": offset,
        }
        if fq_parts:
            params["filter"] = " AND ".join(fq_parts)

        for attempt in range(self.MAX_RETRIES + 1):
            response = await self._client.get(BASE_URL, params=params)
            if response.status_code == 429 and attempt < self.MAX_RETRIES:
                logger.warning(
                    "BASE Rate Limit (429), warte %.1fs (Versuch %d/%d)",
                    self.RETRY_DELAY_S,
                    attempt + 1,
                    self.MAX_RETRIES + 1,
                )
                await asyncio.sleep(self.RETRY_DELAY_S)
                continue
            response.raise_for_status()
            return BASESearchResponse.model_validate(response.json())

        raise httpx.HTTPStatusError(
            "BASE Rate Limit nach Retries",
            request=response.request,
            response=response,
        )
