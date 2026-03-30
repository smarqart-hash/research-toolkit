"""EUR-Lex CELLAR SPARQL Client.

EU-Gesetzgebung: Verordnungen, Richtlinien, Entscheidungen (AI Act, DSA, DMA, DSGVO).
SPARQL-Endpoint auf dem CELLAR Triplestore. Kostenlos, kein API Key noetig.

API Docs: https://eur-lex.europa.eu/content/tools/webservices/
SPARQL Endpoint: https://publications.europa.eu/webapi/rdf/sparql
"""

from __future__ import annotations

import asyncio
import logging

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

SPARQL_ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"


class EURLexDocument(BaseModel):
    """Ein Dokument aus EUR-Lex via SPARQL."""

    celex: str = ""  # CELEX-Nummer (z.B. 32024R1689)
    title: str = ""
    date: str = ""  # ISO-Datum
    doc_type: str = ""  # Regulation, Directive, Decision, etc.
    subject: str = ""  # EuroVoc-Thema
    url: str = ""  # EUR-Lex URL

    @property
    def year(self) -> int | None:
        """Extrahiert Jahr aus Datum."""
        if self.date and len(self.date) >= 4:
            try:
                return int(self.date[:4])
            except ValueError:
                return None
        return None

    @property
    def abstract(self) -> str:
        """Titel als Pseudo-Abstract (EUR-Lex liefert keine Abstracts)."""
        return self.title


class EURLexSearchResponse(BaseModel):
    """Antwort der SPARQL-Suche."""

    total: int = 0
    documents: list[EURLexDocument] = Field(default_factory=list)


class EURLexClient:
    """Client fuer den EUR-Lex CELLAR SPARQL Endpoint.

    Kostenlos, kein API Key noetig. Rate Limit: empfohlen max 1 req/s.
    Unterstuetzt async Context Manager.
    """

    MAX_RETRIES = 1
    RETRY_DELAY_S = 3.0

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=90,  # SPARQL-Queries koennen langsam sein (besonders DE-Suche)
            headers={
                "User-Agent": "auguri.us/1.0 (research briefing platform)",
                "Accept": "application/sparql-results+json",
            },
        )

    async def close(self) -> None:
        """Schliesst den HTTP-Client und gibt Verbindungen frei."""
        await self._client.aclose()

    async def __aenter__(self) -> EURLexClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def search(
        self,
        keyword: str,
        *,
        language: str = "en",
        doc_types: list[str] | None = None,
        limit: int = 20,
    ) -> EURLexSearchResponse:
        """Sucht EU-Rechtsdokumente via EuroVoc-Themen und Freitext.

        Args:
            keyword: Suchbegriff (wird in EuroVoc-Labels gesucht).
            language: Sprache fuer Titel und Labels (en, de, fr).
            doc_types: Filter nach Dokumenttyp (Regulation, Directive, etc.).
            limit: Max Ergebnisse.
        """
        # Einfache, performante SPARQL-Query (Titel-Suche).
        # EuroVoc-Joins sind zu langsam und liefern oft 0 Ergebnisse.
        # CELLAR nutzt 3-Letter ISO 639-2 Codes (ENG, DEU, FRA)
        lang_map = {"en": "ENG", "de": "DEU", "fr": "FRA", "es": "SPA", "it": "ITA"}
        lang_uri = lang_map.get(language.lower(), language.upper())

        query = f"""
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>

SELECT DISTINCT ?celex ?title ?date ?eurlex WHERE {{
  ?work cdm:resource_legal_id_celex ?celex ;
        cdm:work_date_document ?date .
  ?exp cdm:expression_belongs_to_work ?work ;
       cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/{lang_uri}> ;
       cdm:expression_title ?title .
  BIND(CONCAT("https://eur-lex.europa.eu/legal-content/{lang_uri}/TXT/?uri=CELEX:", ?celex) AS ?eurlex)
  FILTER(CONTAINS(LCASE(STR(?title)), LCASE("{keyword}")))
}}
ORDER BY DESC(?date)
LIMIT {min(limit, 50)}
"""

        for attempt in range(self.MAX_RETRIES + 1):
            response = await self._client.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "application/sparql-results+json"},
            )
            if response.status_code == 429 and attempt < self.MAX_RETRIES:
                logger.warning(
                    "EUR-Lex Rate Limit (429), warte %.1fs (Versuch %d/%d)",
                    self.RETRY_DELAY_S,
                    attempt + 1,
                    self.MAX_RETRIES + 1,
                )
                await asyncio.sleep(self.RETRY_DELAY_S)
                continue
            response.raise_for_status()
            return self._parse_sparql_response(response.json())

        raise httpx.HTTPStatusError(
            "EUR-Lex Rate Limit nach Retries",
            request=response.request,
            response=response,
        )

    def _parse_sparql_response(self, data: dict) -> EURLexSearchResponse:
        """Parst SPARQL JSON-Response in EURLexSearchResponse."""
        bindings = data.get("results", {}).get("bindings", [])
        documents: list[EURLexDocument] = []

        for binding in bindings:
            celex = binding.get("celex", {}).get("value", "")
            # Dokumenttyp aus CELEX-Nummer ableiten (R=Regulation, L=Directive, D=Decision)
            doc_type = ""
            if celex:
                # Format: 3YYYYXNNNN — X ist der Typ-Buchstabe
                type_char = celex[5:6] if len(celex) > 5 else ""
                doc_type = {"R": "Regulation", "L": "Directive", "D": "Decision",
                            "C": "Communication"}.get(type_char, "")

            doc = EURLexDocument(
                celex=celex,
                title=binding.get("title", {}).get("value", ""),
                date=binding.get("date", {}).get("value", ""),
                doc_type=doc_type,
                subject=binding.get("subjectLabel", {}).get("value", ""),
                url=binding.get("eurlex", {}).get("value", ""),
            )
            documents.append(doc)

        return EURLexSearchResponse(
            total=len(documents),
            documents=documents,
        )
