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

    def test_camel_case_alias(self):
        """Exa API gibt publishedDate als camelCase zurueck."""
        result = ExaResult.model_validate({
            "url": "https://example.com",
            "title": "CamelCase Paper",
            "publishedDate": "2025-01-15T00:00:00.000Z",
        })
        assert result.published_date == "2025-01-15T00:00:00.000Z"

    def test_camel_case_null(self):
        """publishedDate: null wird korrekt als None gemappt."""
        result = ExaResult.model_validate({
            "url": "https://example.com",
            "title": "No Date",
            "publishedDate": None,
        })
        assert result.published_date is None

    def test_highlights_from_api(self):
        """Exa API gibt highlights als Liste von Strings zurueck."""
        result = ExaResult.model_validate({
            "url": "https://arxiv.org/abs/2401.00001",
            "title": "Highlight Paper",
            "highlights": ["Key finding 1.", "Key finding 2."],
            "highlightScores": [0.95, 0.87],
        })
        assert len(result.highlights) == 2
        assert result.highlight_scores == [0.95, 0.87]

    def test_highlights_default_empty(self):
        """Ohne highlights: leere Liste als Default."""
        result = ExaResult(url="https://example.com", title="No Highlights")
        assert result.highlights == []
        assert result.highlight_scores == []


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

    def test_highlights_mode_in_payload(self):
        """Prueft dass highlights statt text als Content-Mode genutzt wird."""
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

        contents = captured_payload.get("contents", {})
        assert "highlights" in contents, "Muss highlights statt text nutzen"
        assert "text" not in contents, "text-Mode entfernt zugunsten highlights"
        assert contents["highlights"]["query"] == "test query"
        assert contents["highlights"]["highlightsPerUrl"] == 3
        assert contents["highlights"]["highlightsNumSentences"] == 3
        assert captured_payload.get("category") == "research paper"
        assert captured_payload.get("type") == "deep"
        assert captured_payload.get("num_results") == 30
        assert "include_domains" not in captured_payload

    def test_additional_queries_in_payload(self):
        """Prueft dass additionalQueries korrekt im Payload landen."""
        import asyncio
        import unittest.mock as mock

        client = ExaClient(api_key="test-key-123")

        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = mock.MagicMock()

        captured_payload: dict = {}

        async def fake_post(url, **kwargs):
            captured_payload.update(kwargs.get("json", {}))
            return mock_response

        client._client = mock.MagicMock()
        client._client.post = fake_post
        client._client.aclose = mock.AsyncMock()

        asyncio.run(client.search_papers(
            "main query",
            additional_queries=["variant 1", "variant 2"],
        ))

        assert captured_payload.get("additionalQueries") == ["variant 1", "variant 2"]
        assert captured_payload.get("query") == "main query"

    def test_additional_queries_max_four(self):
        """additionalQueries wird auf max 4 Eintraege begrenzt."""
        import asyncio
        import unittest.mock as mock

        client = ExaClient(api_key="test-key-123")

        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = mock.MagicMock()

        captured_payload: dict = {}

        async def fake_post(url, **kwargs):
            captured_payload.update(kwargs.get("json", {}))
            return mock_response

        client._client = mock.MagicMock()
        client._client.post = fake_post
        client._client.aclose = mock.AsyncMock()

        asyncio.run(client.search_papers(
            "main query",
            additional_queries=["q1", "q2", "q3", "q4", "q5", "q6"],
        ))

        assert len(captured_payload.get("additionalQueries", [])) == 4
