"""Tests fuer den Semantic Scholar Client (Unit-Tests, kein API-Call)."""

import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.agents.semantic_scholar import (
    Author,
    ExternalIds,
    OpenAccessPdf,
    PaperResult,
    SearchResponse,
    SemanticScholarClient,
)


class TestPaperResult:
    def test_doi_property(self):
        paper = PaperResult(
            paperId="abc",
            title="Test",
            externalIds=ExternalIds(DOI="10.1234/test"),
        )
        assert paper.doi == "10.1234/test"

    def test_doi_none_without_external_ids(self):
        paper = PaperResult(paperId="abc", title="Test")
        assert paper.doi is None

    def test_arxiv_id_property(self):
        paper = PaperResult(
            paperId="abc",
            title="Test",
            externalIds=ExternalIds(ArXiv="2301.12345"),
        )
        assert paper.arxiv_id == "2301.12345"

    def test_first_author(self):
        paper = PaperResult(
            paperId="abc",
            title="Test",
            authors=[
                Author(authorId="1", name="Max Mueller"),
                Author(authorId="2", name="Anna Schmidt"),
            ],
        )
        assert paper.first_author == "Max Mueller"

    def test_first_author_empty(self):
        paper = PaperResult(paperId="abc", title="Test", authors=[])
        assert paper.first_author == "Unbekannt"


class TestSearchResponse:
    def test_empty_response(self):
        response = SearchResponse()
        assert response.total == 0
        assert response.data == []

    def test_with_data(self):
        response = SearchResponse(
            total=1,
            data=[PaperResult(paperId="abc", title="Test Paper")],
        )
        assert len(response.data) == 1
        assert response.data[0].title == "Test Paper"


class TestSemanticScholarClient:
    def test_no_api_key(self):
        client = SemanticScholarClient(api_key=None)
        # Ohne Key: kein x-api-key Header (Warnung wird geloggt)
        assert "x-api-key" not in client._headers

    def test_with_api_key(self):
        client = SemanticScholarClient(api_key="test-key")
        assert client._headers["x-api-key"] == "test-key"


class TestSemanticScholarRetry:
    """Tests fuer Retry-Logik bei 429 Rate Limit."""

    def test_retry_on_429_then_success(self):
        """429 beim ersten Versuch, Erfolg beim zweiten."""
        client = SemanticScholarClient(api_key="test-key")
        client.RETRY_DELAY_S = 0.01  # Schnell fuer Tests

        # Mock: Erster Call 429, zweiter Call 200
        response_429 = httpx.Response(
            429,
            request=httpx.Request("GET", "https://test.com"),
            content=b'{"message": "Too Many Requests"}',
        )
        response_200 = httpx.Response(
            200,
            request=httpx.Request("GET", "https://test.com"),
            content=b'{"total": 0, "offset": 0, "data": []}',
        )

        call_count = 0

        async def mock_request(method, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return response_429
            return response_200

        async def run():
            with patch.object(
                httpx.AsyncClient, "request", side_effect=mock_request
            ):
                result = await client.search_papers("test query")
                assert result.total == 0
                assert call_count == 2

        asyncio.run(run())

    def test_429_after_retries_raises(self):
        """429 bei allen Versuchen wirft HTTPStatusError."""
        client = SemanticScholarClient(api_key="test-key")
        client.RETRY_DELAY_S = 0.01

        response_429 = httpx.Response(
            429,
            request=httpx.Request("GET", "https://test.com"),
            content=b'{"message": "Too Many Requests"}',
        )

        async def mock_request(method, url, **kwargs):
            return response_429

        async def run():
            with patch.object(
                httpx.AsyncClient, "request", side_effect=mock_request
            ):
                with pytest.raises(httpx.HTTPStatusError):
                    await client.search_papers("test query")

        asyncio.run(run())
