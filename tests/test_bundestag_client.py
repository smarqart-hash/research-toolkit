"""Tests fuer den Bundestag DIP API Client."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.agents.bundestag_client import (
    BundestagClient,
    DIPDrucksache,
    DIPSearchResponse,
    DIPVorgang,
    DIPVorgangResponse,
    PUBLIC_API_KEY,
)
from src.agents.paper_ranker import from_bundestag


# --- Fixtures / Factories ---


def _drucksache(
    titel: str = "Entwurf eines Gesetzes zur Regulierung von KI-Systemen",
    typ: str = "Gesetzentwurf",
    dokumentnummer: str = "20/12345",
    datum: str = "2025-03-15",
    abstrakt: str | None = "Dieser Gesetzentwurf regelt den Einsatz von KI.",
) -> DIPDrucksache:
    """Factory fuer DIPDrucksache Test-Objekte."""
    return DIPDrucksache(
        id="BT-123",
        typ=typ,
        dokumentnummer=dokumentnummer,
        titel=titel,
        datum=datum,
        abstrakt=abstrakt,
    )


def _mock_response(docs: list[DIPDrucksache], status_code: int = 200) -> MagicMock:
    """Erstellt einen Mock-HTTP-Response mit DIPSearchResponse."""
    response = MagicMock()
    response.status_code = status_code
    response.request = httpx.Request("GET", "https://search.dip.bundestag.de/api/v1/drucksache")
    data = {
        "numFound": len(docs),
        "documents": [d.model_dump(by_alias=True) for d in docs],
    }
    response.json.return_value = data
    response.raise_for_status = MagicMock()
    return response


# --- T1: Modell-Tests ---


class TestDIPDrucksache:
    def test_year_extraction(self):
        ds = _drucksache(datum="2025-03-15")
        assert ds.year == 2025

    def test_year_none_for_empty(self):
        ds = _drucksache(datum="")
        assert ds.year is None

    def test_url_construction(self):
        ds = _drucksache(dokumentnummer="20/12345")
        assert ds.url == "https://dip.bundestag.de/drucksache/20/12345"

    def test_defaults(self):
        ds = DIPDrucksache()
        assert ds.id == ""
        assert ds.typ == ""
        assert ds.titel == ""

    def test_abstract_via_alias(self):
        """Abstract wird ueber 'abstrakt' Alias befuellt."""
        ds = DIPDrucksache(abstrakt="Test Abstract")
        assert ds.abstract == "Test Abstract"


class TestDIPVorgang:
    def test_year_extraction(self):
        v = DIPVorgang(id="V-1", titel="Test", datum="2024-06-01")
        assert v.year == 2024

    def test_initiative_list(self):
        v = DIPVorgang(
            id="V-2",
            titel="Test",
            datum="2024-01-01",
            initiative=["Bundesregierung"],
        )
        assert v.initiative == ["Bundesregierung"]


# --- T2: Client HTTP ---


class TestBundestagClient:
    def test_init_uses_public_key(self):
        """Ohne API Key wird der oeffentliche Demo-Key verwendet."""
        client = BundestagClient()
        assert client._api_key == PUBLIC_API_KEY

    def test_init_custom_key(self):
        client = BundestagClient(api_key="custom-key")
        assert client._api_key == "custom-key"

    def test_init_reads_env_variable(self, monkeypatch):
        monkeypatch.setenv("BUNDESTAG_API_KEY", "env-key")
        client = BundestagClient()
        assert client._api_key == "env-key"

    def test_search_drucksachen_success(self):
        """Erfolgreiche Suche gibt DIPSearchResponse zurueck."""
        ds = _drucksache()
        mock_resp = _mock_response([ds])

        async def run():
            client = BundestagClient()
            client._client = MagicMock()
            client._client.get = AsyncMock(return_value=mock_resp)
            client._client.aclose = AsyncMock()

            result = await client.search_drucksachen("Kuenstliche Intelligenz")

            assert isinstance(result, DIPSearchResponse)
            assert result.numFound == 1
            assert "KI-Systemen" in result.documents[0].titel

        asyncio.run(run())

    def test_api_key_added_to_params(self):
        """API Key wird als Parameter mitgesendet."""
        ds = _drucksache()
        mock_resp = _mock_response([ds])
        captured_params: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured_params.append(params or {})
            return mock_resp

        async def run():
            client = BundestagClient(api_key="test-key")
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()

            await client.search_drucksachen("test")

            assert captured_params[0]["apikey"] == "test-key"
            assert captured_params[0]["format"] == "json"

        asyncio.run(run())

    def test_typ_filter(self):
        """Dokumenttyp-Filter wird uebergeben."""
        ds = _drucksache()
        mock_resp = _mock_response([ds])
        captured_params: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured_params.append(params or {})
            return mock_resp

        async def run():
            client = BundestagClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()

            await client.search_drucksachen("KI", typ="Gesetzentwurf")

            assert captured_params[0]["f.typ"] == "Gesetzentwurf"

        asyncio.run(run())

    def test_rows_capped_at_100(self):
        """rows wird auf max 100 begrenzt."""
        ds = _drucksache()
        mock_resp = _mock_response([ds])
        captured_params: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured_params.append(params or {})
            return mock_resp

        async def run():
            client = BundestagClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()

            await client.search_drucksachen("test", rows=500)

            assert captured_params[0]["rows"] == 100

        asyncio.run(run())


# --- T3: Converter ---


class TestFromBundestag:
    def test_basic_conversion(self):
        ds = _drucksache()
        paper = from_bundestag(ds)

        assert paper.source == "bundestag"
        assert paper.language == "de"
        assert paper.paper_id == "dip:20/12345"
        assert "KI-Systemen" in paper.title
        assert paper.year == 2025
        assert paper.doi is None
        assert paper.citation_count is None

    def test_tags_contain_typ(self):
        ds = _drucksache(typ="Kleine Anfrage")
        paper = from_bundestag(ds)
        assert "Kleine Anfrage" in paper.tags

    def test_abstract_fallback_to_title(self):
        ds = _drucksache(abstrakt=None)
        paper = from_bundestag(ds)
        assert paper.abstract == ds.titel

    def test_url_matches_drucksache(self):
        ds = _drucksache(dokumentnummer="20/99999")
        paper = from_bundestag(ds)
        assert "20/99999" in paper.url
