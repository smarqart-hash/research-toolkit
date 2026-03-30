"""Bundestag DIP (Dokumentations- und Informationssystem) API Client.

Drucksachen, Plenarprotokolle, Anfragen, Gesetzentwuerfe des Deutschen Bundestags.
REST API mit kostenlosem API Key. Moderne Swagger-dokumentierte API.

API Docs: https://dip.bundestag.de/über-dip/hilfe/api
Swagger: https://search.dip.bundestag.de/api/v1/swagger-ui/
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

BASE_URL = "https://search.dip.bundestag.de/api/v1"

# Oeffentlicher Demo-Key aus der DIP API-Dokumentation
# Oeffentlicher API-Key (gueltig bis Ende Mai 2026)
# Quelle: https://dip.bundestag.de/ueber-dip/hilfe/api
PUBLIC_API_KEY = "OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw"


class DIPDrucksache(BaseModel):
    """Eine Drucksache aus der DIP API."""

    id: str = ""
    typ: str = ""  # Antrag, Gesetzentwurf, Kleine Anfrage, etc.
    dokumentnummer: str = ""
    titel: str = ""
    datum: str = ""  # ISO-Datum (YYYY-MM-DD)
    autoren_anzahl: int = 0
    fundstelle: dict = Field(default_factory=dict)
    abstract: str | None = Field(default=None, alias="abstrakt")

    model_config = {"populate_by_name": True}

    @property
    def year(self) -> int | None:
        """Extrahiert Jahr aus Datum."""
        if self.datum and len(self.datum) >= 4:
            try:
                return int(self.datum[:4])
            except ValueError:
                return None
        return None

    @property
    def url(self) -> str:
        return f"https://dip.bundestag.de/drucksache/{self.dokumentnummer}"


class DIPSearchResponse(BaseModel):
    """Antwort der DIP API."""

    numFound: int = 0
    documents: list[DIPDrucksache] = Field(default_factory=list)


class DIPVorgang(BaseModel):
    """Ein Vorgang (Gesetzgebungsverfahren) aus der DIP API."""

    id: str = ""
    typ: str = ""
    titel: str = ""
    datum: str = ""
    initiative: list[str] = Field(default_factory=list)
    abstract: str | None = Field(default=None, alias="abstrakt")
    beratungsstand: str | None = None

    model_config = {"populate_by_name": True}

    @property
    def year(self) -> int | None:
        if self.datum and len(self.datum) >= 4:
            try:
                return int(self.datum[:4])
            except ValueError:
                return None
        return None


class DIPVorgangResponse(BaseModel):
    """Antwort der Vorgangs-Suche."""

    numFound: int = 0
    documents: list[DIPVorgang] = Field(default_factory=list)


class BundestagClient:
    """Client fuer die Bundestag DIP API.

    Kostenloser API Key (oeffentlicher Demo-Key verfuegbar).
    Rate Limit: 25 req/s.
    Unterstuetzt async Context Manager.
    """

    MAX_RETRIES = 1
    RETRY_DELAY_S = 2.0

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("BUNDESTAG_API_KEY") or PUBLIC_API_KEY
        self._client = httpx.AsyncClient(
            timeout=30,
            headers={"User-Agent": "auguri.us/1.0 (research briefing platform)"},
        )

    async def close(self) -> None:
        """Schliesst den HTTP-Client und gibt Verbindungen frei."""
        await self._client.aclose()

    async def __aenter__(self) -> BundestagClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def _request(self, endpoint: str, params: dict) -> httpx.Response:
        """HTTP-Request mit API Key und Retry bei 429."""
        params["apikey"] = self._api_key
        params["format"] = "json"

        for attempt in range(self.MAX_RETRIES + 1):
            response = await self._client.get(
                f"{BASE_URL}/{endpoint}", params=params
            )
            if response.status_code == 429 and attempt < self.MAX_RETRIES:
                logger.warning(
                    "DIP Rate Limit (429), warte %.1fs (Versuch %d/%d)",
                    self.RETRY_DELAY_S,
                    attempt + 1,
                    self.MAX_RETRIES + 1,
                )
                await asyncio.sleep(self.RETRY_DELAY_S)
                continue
            response.raise_for_status()
            return response

        raise httpx.HTTPStatusError(
            "DIP Rate Limit nach Retries",
            request=response.request,
            response=response,
        )

    async def search_drucksachen(
        self,
        query: str,
        *,
        typ: str | None = None,
        datum_start: str | None = None,
        datum_end: str | None = None,
        rows: int = 20,
    ) -> DIPSearchResponse:
        """Sucht Drucksachen im Bundestag.

        Args:
            query: Suchbegriff (Freitext).
            typ: Dokumenttyp (Antrag, Gesetzentwurf, Kleine Anfrage, etc.).
            datum_start: Startdatum (YYYY-MM-DD).
            datum_end: Enddatum (YYYY-MM-DD).
            rows: Max Ergebnisse.
        """
        params: dict[str, str | int] = {
            "search": query,
            "rows": min(rows, 100),
        }
        if typ:
            params["f.typ"] = typ
        if datum_start:
            params["f.datum.start"] = datum_start
        if datum_end:
            params["f.datum.end"] = datum_end

        response = await self._request("drucksache", params)
        return DIPSearchResponse.model_validate(response.json())

    async def search_vorgaenge(
        self,
        query: str,
        *,
        datum_start: str | None = None,
        rows: int = 20,
    ) -> DIPVorgangResponse:
        """Sucht Vorgaenge (Gesetzgebungsverfahren) im Bundestag.

        Args:
            query: Suchbegriff (Freitext).
            datum_start: Startdatum (YYYY-MM-DD).
            rows: Max Ergebnisse.
        """
        params: dict[str, str | int] = {
            "search": query,
            "rows": min(rows, 100),
        }
        if datum_start:
            params["f.datum.start"] = datum_start

        response = await self._request("vorgang", params)
        return DIPVorgangResponse.model_validate(response.json())
