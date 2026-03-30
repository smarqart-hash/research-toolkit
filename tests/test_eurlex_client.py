"""Tests fuer den EUR-Lex CELLAR SPARQL Client."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.agents.eurlex_client import (
    EURLexClient,
    EURLexDocument,
    EURLexSearchResponse,
)
from src.agents.paper_ranker import from_eurlex


# --- Fixtures / Factories ---


def _eurlex_doc(
    celex: str = "32024R1689",
    title: str = "Regulation (EU) 2024/1689 - Artificial Intelligence Act",
    date: str = "2024-06-13",
    doc_type: str = "Regulation",
    subject: str = "artificial intelligence",
) -> EURLexDocument:
    """Factory fuer EURLexDocument Test-Objekte."""
    return EURLexDocument(
        celex=celex,
        title=title,
        date=date,
        doc_type=doc_type,
        subject=subject,
        url=f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}",
    )


def _mock_sparql_response(docs: list[EURLexDocument], status_code: int = 200) -> MagicMock:
    """Erstellt einen Mock-HTTP-Response im SPARQL-JSON-Format."""
    response = MagicMock()
    response.status_code = status_code
    response.request = httpx.Request("GET", "https://publications.europa.eu/webapi/rdf/sparql")
    bindings = []
    for doc in docs:
        bindings.append({
            "celex": {"type": "literal", "value": doc.celex},
            "title": {"type": "literal", "value": doc.title},
            "date": {"type": "literal", "value": doc.date},
            "docTypeLabel": {"type": "literal", "value": doc.doc_type},
            "subjectLabel": {"type": "literal", "value": doc.subject},
            "eurlex": {"type": "literal", "value": doc.url},
        })
    data = {
        "results": {
            "bindings": bindings,
        }
    }
    response.json.return_value = data
    response.raise_for_status = MagicMock()
    return response


# --- T1: Modell-Tests ---


class TestEURLexDocument:
    def test_year_extraction(self):
        doc = _eurlex_doc(date="2024-06-13")
        assert doc.year == 2024

    def test_year_none_for_empty(self):
        doc = _eurlex_doc(date="")
        assert doc.year is None

    def test_abstract_returns_title(self):
        """EUR-Lex hat keine Abstracts — Titel als Fallback."""
        doc = _eurlex_doc(title="AI Act Regulation")
        assert doc.abstract == "AI Act Regulation"

    def test_defaults(self):
        doc = EURLexDocument()
        assert doc.celex == ""
        assert doc.title == ""
        assert doc.date == ""
        assert doc.doc_type == ""

    def test_search_response_defaults(self):
        resp = EURLexSearchResponse()
        assert resp.total == 0
        assert resp.documents == []


# --- T2: Client HTTP ---


class TestEURLexClient:
    def test_search_success(self):
        """Erfolgreiche SPARQL-Suche gibt EURLexSearchResponse zurueck."""
        doc = _eurlex_doc()
        mock_resp = _mock_sparql_response([doc])

        async def run():
            client = EURLexClient()
            client._client = MagicMock()
            client._client.get = AsyncMock(return_value=mock_resp)
            client._client.aclose = AsyncMock()

            result = await client.search("artificial intelligence")

            assert isinstance(result, EURLexSearchResponse)
            assert result.total == 1
            assert "Artificial Intelligence Act" in result.documents[0].title

        asyncio.run(run())

    def test_sparql_query_contains_keyword(self):
        """SPARQL-Query enthaelt das Keyword im FILTER."""
        doc = _eurlex_doc()
        mock_resp = _mock_sparql_response([doc])
        captured_params: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured_params.append(params or {})
            return mock_resp

        async def run():
            client = EURLexClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()

            await client.search("artificial intelligence")

            query_param = captured_params[0]["query"]
            assert "artificial intelligence" in query_param

        asyncio.run(run())

    def test_language_parameter(self):
        """Sprach-Parameter wird in SPARQL-Query eingebaut."""
        doc = _eurlex_doc()
        mock_resp = _mock_sparql_response([doc])
        captured_params: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured_params.append(params or {})
            return mock_resp

        async def run():
            client = EURLexClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()

            await client.search("KI", language="de")

            query_param = captured_params[0]["query"]
            assert "DE" in query_param  # language.upper() im SPARQL

        asyncio.run(run())

    def test_empty_response(self):
        """Leere SPARQL-Response ergibt leere Dokumentenliste."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.request = httpx.Request("GET", "https://publications.europa.eu/")
        mock_resp.json.return_value = {"results": {"bindings": []}}
        mock_resp.raise_for_status = MagicMock()

        async def run():
            client = EURLexClient()
            client._client = MagicMock()
            client._client.get = AsyncMock(return_value=mock_resp)
            client._client.aclose = AsyncMock()

            result = await client.search("nonexistent topic")

            assert result.total == 0
            assert result.documents == []

        asyncio.run(run())

    def test_429_triggers_retry(self):
        """Bei 429-Response wird einmal retried."""
        doc = _eurlex_doc()
        success_resp = _mock_sparql_response([doc])

        rate_limit_resp = MagicMock()
        rate_limit_resp.status_code = 429
        rate_limit_resp.request = httpx.Request("GET", "https://publications.europa.eu/")

        call_count = [0]

        async def mock_get(url, params=None, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return rate_limit_resp
            return success_resp

        async def run():
            with patch("asyncio.sleep", new_callable=AsyncMock):
                client = EURLexClient()
                client._client = MagicMock()
                client._client.get = mock_get
                client._client.aclose = AsyncMock()

                result = await client.search("test")

            assert call_count[0] == 2
            assert isinstance(result, EURLexSearchResponse)

        asyncio.run(run())


# --- T3: Converter ---


class TestFromEurlex:
    def test_basic_conversion(self):
        doc = _eurlex_doc()
        paper = from_eurlex(doc)

        assert paper.source == "eurlex"
        assert paper.language == "de"
        assert paper.paper_id == "celex:32024R1689"
        assert "Artificial Intelligence Act" in paper.title
        assert paper.year == 2024
        assert paper.doi is None
        assert paper.citation_count is None

    def test_tags_contain_doc_type(self):
        doc = _eurlex_doc(doc_type="Directive")
        paper = from_eurlex(doc)
        assert "Directive" in paper.tags

    def test_tags_contain_subject(self):
        doc = _eurlex_doc(subject="data protection")
        paper = from_eurlex(doc)
        assert "data protection" in paper.tags

    def test_url_contains_celex(self):
        doc = _eurlex_doc(celex="32024R1689")
        paper = from_eurlex(doc)
        assert "32024R1689" in paper.url

    def test_abstract_equals_title(self):
        doc = _eurlex_doc(title="Test Title")
        paper = from_eurlex(doc)
        assert paper.abstract == "Test Title"
