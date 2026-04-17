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
from typing import TYPE_CHECKING

import httpx
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.agents.bundestag_vocabulary import BundestagVocabulary
    from src.agents.paper_ranker import UnifiedPaper

logger = logging.getLogger(__name__)

BASE_URL = "https://search.dip.bundestag.de/api/v1"

# Anzahl Vorgaenge fuer Position-Enrichment bei include_positions=True
TOPIC_POSITIONS_TOP_N = 10

# Rate-Limit-Sleep zwischen Bulk-Calls (Positions-Loop)
TOPIC_RATE_LIMIT_SLEEP_S = 1.0

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


class Deskriptor(BaseModel):
    """Ein Deskriptor aus dem kontrollierten DIP-Vokabular.

    `typ` ist z.B. "Sachbegriffe", "Geograph. Begriffe", "Person".
    `fundstelle` flagged ob der Deskriptor aus einer expliziten Fundstelle
    stammt (selten, default False).
    """

    name: str = ""
    typ: str = ""
    fundstelle: bool = False


class DIPVorgang(BaseModel):
    """Ein Vorgang (Gesetzgebungsverfahren, Kleine Anfrage, ...) aus der DIP API.

    Ein Vorgang buendelt mehrere Dokumente (Vorgangspositionen + Drucksachen)
    zu einem Thema. Fuer die eigentlichen Dokumente: `get_vorgangspositionen()`.
    """

    id: str = ""
    typ: str = ""
    vorgangstyp: str = ""
    wahlperiode: int | None = None
    titel: str = ""
    datum: str = ""
    aktualisiert: str = ""
    initiative: list[str] = Field(default_factory=list)
    abstract: str | None = Field(default=None, alias="abstrakt")
    beratungsstand: str | None = None
    deskriptor: list[Deskriptor] = Field(default_factory=list)
    sachgebiet: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @property
    def year(self) -> int | None:
        if self.datum and len(self.datum) >= 4:
            try:
                return int(self.datum[:4])
            except ValueError:
                return None
        return None

    @property
    def url(self) -> str:
        return f"https://dip.bundestag.de/vorgang/{self.id}"


class DIPVorgangResponse(BaseModel):
    """Antwort der Vorgangs-Suche."""

    numFound: int = 0
    documents: list[DIPVorgang] = Field(default_factory=list)


class Fundstelle(BaseModel):
    """Fundstelle-Block einer Vorgangsposition (Drucksache-Referenz)."""

    dokumentnummer: str = ""
    pdf_url: str = ""
    drucksachetyp: str = ""
    urheber: list[str] = Field(default_factory=list)


class DIPVorgangsposition(BaseModel):
    """Einzelne Position innerhalb eines Vorgangs (Drucksache oder Debatten-Abschnitt).

    Enthaelt die PDF-URL und Dokument-Metadaten. Liefert das einzige
    verifiziert funktionierende Drucksache-Enrichment zu einem Vorgang:
    `/vorgangsposition?f.vorgang={id}`.
    """

    id: str = ""
    vorgang_id: str = ""
    vorgangsposition: str = ""
    dokumentart: str = ""
    titel: str = ""
    datum: str = ""
    fundstelle: Fundstelle | None = None

    @property
    def year(self) -> int | None:
        if self.datum and len(self.datum) >= 4:
            try:
                return int(self.datum[:4])
            except ValueError:
                return None
        return None


class DIPVorgangspositionResponse(BaseModel):
    """Antwort der Vorgangspositions-Suche."""

    numFound: int = 0
    documents: list[DIPVorgangsposition] = Field(default_factory=list)


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
        """Sucht Drucksachen im Bundestag via Titel-Match.

        Args:
            query: Titel-Phrase (Freitext, mehrere Woerter = Phrase-Match).
                   Leerer/Whitespace-String laesst Parameter weg (Browse-Modus).
            typ: Drucksachentyp (Antrag, Gesetzentwurf, Kleine Anfrage, ...).
            datum_start: Startdatum (YYYY-MM-DD).
            datum_end: Enddatum (YYYY-MM-DD).
            rows: Max Ergebnisse.

        Note:
            Fuer Topic-Research besser `search_topic()` nutzen — diese Methode
            filtert nur auf `f.titel` (keine semantische Vokabular-Expansion).
            DIP ignoriert `search=`/`q=`/`f.volltext=` am `/drucksache` Endpunkt
            (empirisch verifiziert 2026-04-17, siehe docs/guides/bundestag-dip-api.md).
        """
        params: dict[str, str | int] = {
            "rows": min(rows, 100),
        }
        if query and query.strip():
            params["f.titel"] = query.strip()
        if typ:
            params["f.drucksachetyp"] = typ
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
        """Sucht Vorgaenge (Gesetzgebungsverfahren) im Bundestag via Titel-Match.

        Args:
            query: Titel-Phrase (Freitext, mehrere Woerter = Phrase-Match).
                   Leerer/Whitespace-String laesst Parameter weg (Browse-Modus).
            datum_start: Startdatum (YYYY-MM-DD).
            rows: Max Ergebnisse.

        Note:
            Fuer Topic-Research besser `search_topic()` nutzen — diese Methode
            filtert nur auf `f.titel` (keine Deskriptor-Vokabular-Expansion).
            `/vorgang` unterstuetzt zusaetzlich `f.deskriptor` (semantisch wirksam),
            aber diese Methode ist bewusst schlicht fuer Titel-Suche.
        """
        params: dict[str, str | int] = {
            "rows": min(rows, 100),
        }
        if query and query.strip():
            params["f.titel"] = query.strip()
        if datum_start:
            params["f.datum.start"] = datum_start

        response = await self._request("vorgang", params)
        return DIPVorgangResponse.model_validate(response.json())

    async def get_vorgang(self, vorgang_id: str) -> DIPVorgang:
        """Detail-Abruf eines Vorgangs (inkl. Deskriptoren + Sachgebiete).

        Args:
            vorgang_id: Vorgangs-ID aus DIP (z.B. "333085").

        Returns:
            DIPVorgang mit allen Metadaten-Feldern.

        Note:
            `/vorgang/{id}` liefert KEINE Drucksachen-Links (empirisch verifiziert
            2026-04-17). Fuer assoziierte Dokumente: `get_vorgangspositionen()`.
        """
        response = await self._request(f"vorgang/{vorgang_id}", {})
        return DIPVorgang.model_validate(response.json())

    async def get_vorgangspositionen(
        self,
        vorgang_id: str,
        *,
        rows: int = 20,
    ) -> DIPVorgangspositionResponse:
        """Dokumente (Drucksachen + Plenarprotokolle) zu einem Vorgang.

        VERIFIZIERTER Join-Pfad (2026-04-17):
        `/vorgangsposition?f.vorgang={id}` liefert 2-N Positionen mit
        `fundstelle.pdf_url` + `dokumentnummer` + `drucksachetyp`.

        Achtung: `/drucksache?f.vorgang=` wird von der DIP ignoriert und
        liefert den Vollbestand. Nur dieser Endpunkt funktioniert.

        Args:
            vorgang_id: Vorgangs-ID aus DIP.
            rows: Max Ergebnisse (Cap 100).
        """
        params: dict[str, str | int] = {
            "f.vorgang": vorgang_id,
            "rows": min(rows, 100),
        }
        response = await self._request("vorgangsposition", params)
        return DIPVorgangspositionResponse.model_validate(response.json())

    async def search_topic(
        self,
        topic: str,
        *,
        rows: int = 50,
        include_positions: bool = False,
        vocabulary: BundestagVocabulary | None = None,
        wahlperiode: int | None = None,
    ) -> list[UnifiedPaper]:
        """Topic-zentrierte Suche ueber Deskriptor-Vokabular.

        Algorithmus:
        1. Vocabulary-Lookup (cache-first). Falls Miss/Stale: learn().
        2. Wenn Top-1-Deskriptor verfuegbar: `/vorgang?f.deskriptor=<top-1>`.
           Sonst: Fallback auf `/vorgang?f.titel=<topic>` (graceful degradation).
        3. Dedup via Vorgang-ID.
        4. Wenn include_positions: `/vorgangsposition?f.vorgang={id}` fuer Top-N.
        5. Ranking: Recency desc, Ties aufgeloest via Deskriptor-Frequenz-Score.

        Args:
            topic: Topic-String (z.B. "Klimaschutz").
            rows: Max Vorgaenge (Cap 100 per Request).
            include_positions: Wenn True, zusaetzlich Top-10 Vorgaenge auf
                Positionen expandieren (liefert Drucksachen mit pdf_url).
            vocabulary: BundestagVocabulary-Instanz (cached Deskriptoren).
                Wenn None: Fallback auf f.titel-Suche (ohne Learning).
            wahlperiode: Optional Filter auf Legislaturperiode.

        Returns:
            list[UnifiedPaper] mit source="bundestag", gerankt nach Recency.
        """
        from src.agents.paper_ranker import (
            UnifiedPaper as _UP,
            from_dip_vorgang,
            from_dip_vorgangsposition,
        )

        top_descriptor: str | None = None
        desc_freq_map: dict[str, int] = {}
        if vocabulary is not None:
            tv = await vocabulary.get_or_learn(topic)
            top_descriptor = tv.top_descriptor()
            desc_freq_map = {d.name: d.freq for d in tv.descriptors}

        # Vorgang-Suche: Deskriptor bevorzugt, Titel als Fallback
        params: dict[str, str | int] = {"rows": min(rows, 100)}
        if top_descriptor:
            params["f.deskriptor"] = top_descriptor
            used_filter = f"f.deskriptor={top_descriptor}"
        else:
            if topic and topic.strip():
                params["f.titel"] = topic.strip()
            used_filter = f"f.titel={topic} (kein Deskriptor)"
        if wahlperiode is not None:
            params["f.wahlperiode"] = wahlperiode

        logger.debug("search_topic '%s' via %s", topic, used_filter)
        response = await self._request("vorgang", params)
        vorgang_response = DIPVorgangResponse.model_validate(response.json())
        vorgaenge = vorgang_response.documents

        # Dedup pro Vorgang-ID
        seen_ids: set[str] = set()
        unique_vorgaenge: list[DIPVorgang] = []
        for v in vorgaenge:
            if v.id and v.id not in seen_ids:
                seen_ids.add(v.id)
                unique_vorgaenge.append(v)

        # Ranking: Recency desc, Deskriptor-Freq-Score als Tiebreaker
        def _rank_key(v: DIPVorgang) -> tuple[int, int]:
            year = v.year or 0
            freq_score = sum(desc_freq_map.get(d.name, 0) for d in v.deskriptor)
            return (year, freq_score)

        unique_vorgaenge.sort(key=_rank_key, reverse=True)

        # Bei include_positions: Top-N expandieren zu Drucksachen
        papers: list[_UP] = []
        if include_positions:
            top_n = unique_vorgaenge[:TOPIC_POSITIONS_TOP_N]
            seen_doknrs: set[str] = set()
            for idx, vorgang in enumerate(top_n):
                if idx > 0:
                    await asyncio.sleep(TOPIC_RATE_LIMIT_SLEEP_S)
                try:
                    vp_response = await self.get_vorgangspositionen(vorgang.id, rows=50)
                except httpx.HTTPError as exc:
                    logger.warning(
                        "Positions-Fetch fuer %s fehlgeschlagen: %s",
                        vorgang.id,
                        exc,
                    )
                    continue
                for vp in vp_response.documents:
                    key = (
                        vp.fundstelle.dokumentnummer
                        if vp.fundstelle and vp.fundstelle.dokumentnummer
                        else f"vp:{vp.id}"
                    )
                    if key in seen_doknrs:
                        continue
                    seen_doknrs.add(key)
                    papers.append(from_dip_vorgangsposition(vp))
        else:
            papers = [from_dip_vorgang(v) for v in unique_vorgaenge]

        logger.info(
            "search_topic('%s'): %d Vorgaenge, %d UnifiedPaper (positions=%s)",
            topic,
            len(unique_vorgaenge),
            len(papers),
            include_positions,
        )
        return papers
