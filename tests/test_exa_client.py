"""Tests fuer den Exa Client (Unit-Tests, kein API-Call)."""

from src.agents.exa_client import ExaClient, ExaResult, ExaSearchResponse


class TestExaResult:
    def test_minimal(self):
        result = ExaResult(url="https://example.com", title="Test")
        assert result.text is None
        assert result.author is None
        assert result.score is None

    def test_full(self):
        result = ExaResult(
            url="https://example.com",
            title="Test Paper",
            text="Abstract text.",
            published_date="2024-03-15",
            author="Max Mueller",
            score=0.95,
        )
        assert result.published_date == "2024-03-15"
        assert result.score == 0.95


class TestExaSearchResponse:
    def test_empty(self):
        response = ExaSearchResponse()
        assert response.results == []

    def test_with_results(self):
        response = ExaSearchResponse(
            results=[ExaResult(url="https://example.com", title="Test")]
        )
        assert len(response.results) == 1


class TestExaClient:
    def test_not_available_without_key(self):
        client = ExaClient(api_key=None)
        # Sicherstellen dass auch Env-Variable nicht gesetzt ist
        client._api_key = None
        assert client.is_available is False

    def test_not_available_with_empty_key(self):
        client = ExaClient(api_key="")
        assert client.is_available is False

    def test_available_with_key(self):
        client = ExaClient(api_key="test-key-123")
        assert client.is_available is True

    def test_dach_domains_in_payload(self):
        """Prueft dass DACH-Repositorien in include_domains enthalten sind."""
        import asyncio
        import unittest.mock as mock

        client = ExaClient(api_key="test-key-123")

        # Mock-Response vorbereiten
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = mock.MagicMock()

        captured_payload: dict = {}

        async def fake_post(url, **kwargs):
            captured_payload.update(kwargs.get("json", {}))
            return mock_response

        # Internes _client-Objekt mocken (Connection Pooling)
        client._client = mock.MagicMock()
        client._client.post = fake_post
        client._client.aclose = mock.AsyncMock()

        asyncio.run(client.search_papers("test query"))

        domains = captured_payload.get("include_domains", [])
        assert "gesis.org" in domains
        assert "dnb.de" in domains
        assert "zbw.eu" in domains
