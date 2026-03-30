"""Tests fuer den BASE (Bielefeld Academic Search Engine) API Client."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.agents.base_client import (
    BASEClient,
    BASEDocument,
    BASEResponseBody,
    BASESearchResponse,
)
from src.agents.paper_ranker import from_base


# --- Fixtures / Factories ---


def _base_doc(
    title: str = "AI in der Verwaltung",
    description: str | None = "Eine Studie ueber KI-Einsatz in deutschen Behoerden.",
    creators: list[str] | None = None,
    year: str = "2024",
    doi: str | None = "10.1234/base-test",
    lang: str = "deu",
    oa: int = 1,
) -> BASEDocument:
    """Factory fuer BASEDocument Test-Objekte."""
    return BASEDocument(
        dctitle=title,
        dcdescription=description,
        dccreator=creators or ["Mueller, Anna", "Schmidt, Ben"],
        dcyear=year,
        dcdoi=doi,
        dcidentifier="https://example.edu/pub/ai-verwaltung.pdf",
        dclink="https://example.edu/pub/ai-verwaltung.pdf",
        dclang=lang,
        dctype="article",
        dcsubject=["artificial intelligence", "public administration"],
        dcoa=oa,
    )


def _mock_response(docs: list[BASEDocument], status_code: int = 200) -> MagicMock:
    """Erstellt einen Mock-HTTP-Response mit BASESearchResponse."""
    response = MagicMock()
    response.status_code = status_code
    response.request = httpx.Request("GET", "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi")
    data = {
        "response": {
            "numFound": len(docs),
            "docs": [d.model_dump() for d in docs],
        }
    }
    response.json.return_value = data
    response.raise_for_status = MagicMock()
    return response


# --- T1: Modell-Tests ---


class TestBASEDocument:
    def test_year_extraction(self):
        doc = _base_doc(year="2024")
        assert doc.year == 2024

    def test_year_none_for_invalid(self):
        doc = _base_doc(year="unknown")
        assert doc.year is None

    def test_is_open_access(self):
        doc = _base_doc(oa=1)
        assert doc.is_open_access is True

    def test_not_open_access(self):
        doc = _base_doc(oa=0)
        assert doc.is_open_access is False

    def test_first_author(self):
        doc = _base_doc(creators=["Mueller, Anna", "Schmidt, Ben"])
        assert doc.first_author == "Mueller, Anna"

    def test_first_author_unknown(self):
        doc = BASEDocument(dctitle="Test", dccreator=[])
        assert doc.first_author == "Unbekannt"

    def test_defaults(self):
        doc = BASEDocument()
        assert doc.dctitle == ""
        assert doc.dcdescription is None
        assert doc.dccreator == []
        assert doc.dcsubject == []


# --- T2: Client HTTP ---


class TestBASEClient:
    def test_search_success(self):
        """Erfolgreiche Suche gibt BASESearchResponse zurueck."""
        doc = _base_doc()
        mock_resp = _mock_response([doc])

        async def run():
            client = BASEClient()
            client._client = MagicMock()
            client._client.get = AsyncMock(return_value=mock_resp)
            client._client.aclose = AsyncMock()

            result = await client.search("artificial intelligence")

            assert isinstance(result, BASESearchResponse)
            assert result.response.numFound == 1
            assert result.response.docs[0].dctitle == "AI in der Verwaltung"

        asyncio.run(run())

    def test_search_with_language_filter(self):
        """Sprach-Filter wird als Parameter uebergeben."""
        doc = _base_doc()
        mock_resp = _mock_response([doc])
        captured_params: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured_params.append(params or {})
            return mock_resp

        async def run():
            client = BASEClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()

            await client.search("test", language="deu")

            assert "filter" in captured_params[0]
            assert "dclang:deu" in captured_params[0]["filter"]

        asyncio.run(run())

    def test_hits_capped_at_125(self):
        """hits wird auf max 125 begrenzt."""
        doc = _base_doc()
        mock_resp = _mock_response([doc])
        captured_params: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured_params.append(params or {})
            return mock_resp

        async def run():
            client = BASEClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()

            await client.search("test", hits=999)

            assert captured_params[0]["hits"] == 125

        asyncio.run(run())

    def test_429_triggers_retry(self):
        """Bei 429-Response wird einmal retried."""
        doc = _base_doc()
        success_resp = _mock_response([doc])

        rate_limit_resp = MagicMock()
        rate_limit_resp.status_code = 429
        rate_limit_resp.request = httpx.Request("GET", "https://api.base-search.net/")

        call_count = [0]

        async def mock_get(url, params=None, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return rate_limit_resp
            return success_resp

        async def run():
            from unittest.mock import patch

            with patch("asyncio.sleep", new_callable=AsyncMock):
                client = BASEClient()
                client._client = MagicMock()
                client._client.get = mock_get
                client._client.aclose = AsyncMock()

                result = await client.search("test")

            assert call_count[0] == 2
            assert isinstance(result, BASESearchResponse)

        asyncio.run(run())


# --- T3: Converter ---


class TestFromBase:
    def test_basic_conversion(self):
        doc = _base_doc()
        paper = from_base(doc)

        assert paper.title == "AI in der Verwaltung"
        assert paper.source == "base"
        assert paper.doi == "10.1234/base-test"
        assert paper.year == 2024
        assert paper.is_open_access is True
        assert paper.language == "de"
        assert len(paper.authors) == 2

    def test_language_normalization(self):
        doc = _base_doc(lang="eng")
        paper = from_base(doc)
        assert paper.language == "en"

    def test_no_doi_uses_title_hash(self):
        doc = _base_doc(doi=None)
        paper = from_base(doc)
        assert paper.paper_id != ""
        assert paper.doi is None

    def test_no_abstract(self):
        doc = _base_doc(description=None)
        paper = from_base(doc)
        assert paper.abstract is None
