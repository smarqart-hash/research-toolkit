"""Tests fuer den OpenAlex API Client."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.agents.openalex_client import (
    OpenAlexAuthorship,
    OpenAlexClient,
    OpenAlexOpenAccess,
    OpenAlexSearchResponse,
    OpenAlexWork,
)


# --- Fixtures / Factories ---


_SENTINEL = object()  # Sentinel fuer "nicht gesetzt" vs. explizit None


def _openalex_work(
    work_id: str = "https://openalex.org/W123",
    doi: str | None = "https://doi.org/10.1234/test",
    display_name: str = "Test Paper OpenAlex",
    publication_year: int | None = 2024,
    cited_by_count: int = 42,
    abstract_inverted_index: dict | None = _SENTINEL,  # type: ignore[assignment]
    is_oa: bool = True,
    language: str | None = "en",
    authors: list[str] | None = None,
) -> OpenAlexWork:
    """Factory fuer OpenAlexWork Test-Objekte."""
    if abstract_inverted_index is _SENTINEL:
        abstract_inverted_index = {"This": [0], "is": [1], "an": [2], "abstract": [3]}
    authorship_list = []
    for name in authors or ["Max Mustermann"]:
        authorship_list.append(
            OpenAlexAuthorship.model_validate({"author": {"display_name": name}})
        )
    return OpenAlexWork(
        id=work_id,
        doi=doi,
        display_name=display_name,
        publication_year=publication_year,
        cited_by_count=cited_by_count,
        abstract_inverted_index=abstract_inverted_index,
        open_access=OpenAlexOpenAccess(is_oa=is_oa),
        language=language,
        authorships=authorship_list,
    )


def _mock_response(works: list[OpenAlexWork], status_code: int = 200) -> MagicMock:
    """Erstellt einen Mock-HTTP-Response mit OpenAlexSearchResponse."""
    response = MagicMock()
    response.status_code = status_code
    response.request = httpx.Request("GET", "https://api.openalex.org/works")
    data = {
        "meta": {"count": len(works), "per_page": len(works)},
        "results": [w.model_dump() for w in works],
    }
    response.json.return_value = data
    response.raise_for_status = MagicMock()
    return response


# --- T1: Abstract-Rekonstruktion ---


class TestAbstractReconstruction:
    def test_basic_reconstruction(self):
        """Inverted Index wird korrekt zu Klartext rekonstruiert."""
        work = _openalex_work(
            abstract_inverted_index={
                "Machine": [0],
                "learning": [1],
                "is": [2],
                "powerful": [3],
            }
        )
        assert work.abstract == "Machine learning is powerful"

    def test_multiposition_word(self):
        """Ein Wort kann an mehreren Positionen stehen."""
        work = _openalex_work(
            abstract_inverted_index={
                "cat": [0, 4],
                "sat": [1],
                "on": [2],
                "the": [3],
            }
        )
        result = work.abstract
        assert result is not None
        words = result.split()
        assert words[0] == "cat"
        assert words[4] == "cat"

    def test_empty_inverted_index_returns_none(self):
        """Leerer Abstract-Index ergibt None."""
        work = _openalex_work(abstract_inverted_index=None)
        assert work.abstract is None

    def test_empty_dict_returns_none(self):
        """Leeres Dict ergibt None."""
        work = OpenAlexWork(
            id="https://openalex.org/W1",
            display_name="Test",
            abstract_inverted_index=None,
        )
        assert work.abstract is None

    def test_word_order_by_position(self):
        """Woerter werden nach Position sortiert, nicht Eingabe-Reihenfolge."""
        work = _openalex_work(
            abstract_inverted_index={
                "second": [1],
                "first": [0],
                "third": [2],
            }
        )
        assert work.abstract == "first second third"


# --- T1: first_author Property ---


class TestFirstAuthor:
    def test_returns_first_author_name(self):
        work = _openalex_work(authors=["Anna Mueller", "Ben Schmidt"])
        assert work.first_author == "Anna Mueller"

    def test_no_authors_returns_unbekannt(self):
        work = OpenAlexWork(id="https://openalex.org/W1", display_name="Test", authorships=[])
        assert work.first_author == "Unbekannt"


# --- T1: Pydantic-Modell Validierung ---


class TestOpenAlexWorkModel:
    def test_basic_model_creation(self):
        work = _openalex_work()
        assert work.id == "https://openalex.org/W123"
        assert work.doi == "https://doi.org/10.1234/test"
        assert work.display_name == "Test Paper OpenAlex"
        assert work.publication_year == 2024
        assert work.cited_by_count == 42

    def test_defaults(self):
        work = OpenAlexWork(id="https://openalex.org/W1", display_name="Minimal Work")
        assert work.doi is None
        assert work.publication_year is None
        assert work.cited_by_count == 0
        assert work.authorships == []
        assert work.abstract_inverted_index is None
        assert work.open_access.is_oa is False

    def test_open_access_default(self):
        work = OpenAlexWork(id="W1", display_name="Test")
        assert work.open_access.is_oa is False
        assert work.open_access.oa_url is None

    def test_search_response_model(self):
        works = [_openalex_work()]
        response = OpenAlexSearchResponse(
            meta={"count": 1, "per_page": 1},
            results=works,
        )
        assert len(response.results) == 1
        assert response.meta["count"] == 1

    def test_search_response_defaults(self):
        response = OpenAlexSearchResponse()
        assert response.results == []
        assert response.meta == {}


# --- T2: OpenAlexClient HTTP ---


class TestOpenAlexClient:
    def test_init_without_mailto(self):
        client = OpenAlexClient()
        assert client._mailto is None

    def test_init_with_mailto(self):
        client = OpenAlexClient(mailto="test@example.com")
        assert client._mailto == "test@example.com"

    def test_init_reads_env_variable(self, monkeypatch):
        monkeypatch.setenv("OPENALEX_MAILTO", "env@example.com")
        client = OpenAlexClient()
        assert client._mailto == "env@example.com"

    def test_search_works_success(self):
        """Erfolgreiche Suche gibt OpenAlexSearchResponse zurueck."""
        work = _openalex_work()
        mock_resp = _mock_response([work])

        async def run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_cm = AsyncMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
                mock_cm.__aexit__ = AsyncMock(return_value=None)
                mock_cm.get = AsyncMock(return_value=mock_resp)
                mock_client_cls.return_value = mock_cm

                client = OpenAlexClient()
                result = await client.search_works("machine learning")

            assert isinstance(result, OpenAlexSearchResponse)
            assert len(result.results) == 1
            assert result.results[0].display_name == "Test Paper OpenAlex"

        asyncio.run(run())

    def test_search_works_with_year_range(self):
        """Jahr-Filter wird korrekt als Filter-Parameter uebergeben."""
        work = _openalex_work()
        mock_resp = _mock_response([work])
        captured_params: list[dict] = []

        async def run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_cm = AsyncMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
                mock_cm.__aexit__ = AsyncMock(return_value=None)

                async def mock_get(url, params=None, **kwargs):
                    captured_params.append(params or {})
                    return mock_resp

                mock_cm.get = mock_get
                mock_client_cls.return_value = mock_cm

                client = OpenAlexClient()
                await client.search_works("test", year_range="2020-2026")

            assert "filter" in captured_params[0]
            assert "publication_year:2020-2026" in captured_params[0]["filter"]

        asyncio.run(run())

    def test_search_works_with_languages(self):
        """Sprach-Filter wird korrekt als Filter-Parameter uebergeben."""
        work = _openalex_work()
        mock_resp = _mock_response([work])
        captured_params: list[dict] = []

        async def run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_cm = AsyncMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
                mock_cm.__aexit__ = AsyncMock(return_value=None)

                async def mock_get(url, params=None, **kwargs):
                    captured_params.append(params or {})
                    return mock_resp

                mock_cm.get = mock_get
                mock_client_cls.return_value = mock_cm

                client = OpenAlexClient()
                await client.search_works("test", languages=["en", "de"])

            assert "language:en|de" in captured_params[0]["filter"]

        asyncio.run(run())

    def test_search_works_combined_filters(self):
        """Jahr + Sprach-Filter werden kombiniert."""
        work = _openalex_work()
        mock_resp = _mock_response([work])
        captured_params: list[dict] = []

        async def run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_cm = AsyncMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
                mock_cm.__aexit__ = AsyncMock(return_value=None)

                async def mock_get(url, params=None, **kwargs):
                    captured_params.append(params or {})
                    return mock_resp

                mock_cm.get = mock_get
                mock_client_cls.return_value = mock_cm

                client = OpenAlexClient()
                await client.search_works(
                    "test", year_range="2020-2026", languages=["en", "de"]
                )

            filter_val = captured_params[0]["filter"]
            assert "publication_year:2020-2026" in filter_val
            assert "language:en|de" in filter_val

        asyncio.run(run())

    def test_mailto_added_to_params(self):
        """mailto-Parameter wird hinzugefuegt wenn gesetzt."""
        work = _openalex_work()
        mock_resp = _mock_response([work])
        captured_params: list[dict] = []

        async def run():
            with (
                patch("httpx.AsyncClient") as mock_client_cls,
                patch.dict("os.environ", {}, clear=False),
            ):
                # Env-Var entfernen damit mailto genutzt wird
                import os
                os.environ.pop("OPENALEX_API_KEY", None)

                mock_cm = AsyncMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
                mock_cm.__aexit__ = AsyncMock(return_value=None)

                async def mock_get(url, params=None, **kwargs):
                    captured_params.append(params or {})
                    return mock_resp

                mock_cm.get = mock_get
                mock_client_cls.return_value = mock_cm

                client = OpenAlexClient(mailto="user@example.com")
                await client.search_works("test")

            assert captured_params[0]["mailto"] == "user@example.com"

        asyncio.run(run())

    def test_per_page_capped_at_200(self):
        """per_page wird auf max 200 begrenzt."""
        work = _openalex_work()
        mock_resp = _mock_response([work])
        captured_params: list[dict] = []

        async def run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_cm = AsyncMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
                mock_cm.__aexit__ = AsyncMock(return_value=None)

                async def mock_get(url, params=None, **kwargs):
                    captured_params.append(params or {})
                    return mock_resp

                mock_cm.get = mock_get
                mock_client_cls.return_value = mock_cm

                client = OpenAlexClient()
                await client.search_works("test", per_page=999)

            assert captured_params[0]["per_page"] == 200

        asyncio.run(run())

    def test_429_triggers_retry(self):
        """Bei 429-Response wird einmal retried."""
        work = _openalex_work()
        success_resp = _mock_response([work])

        rate_limit_resp = MagicMock()
        rate_limit_resp.status_code = 429
        rate_limit_resp.request = httpx.Request("GET", "https://api.openalex.org/works")
        rate_limit_resp.raise_for_status = MagicMock()

        call_count = [0]

        async def run():
            with (
                patch("httpx.AsyncClient") as mock_client_cls,
                patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            ):
                mock_cm = AsyncMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
                mock_cm.__aexit__ = AsyncMock(return_value=None)

                async def mock_get(url, params=None, **kwargs):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        return rate_limit_resp
                    return success_resp

                mock_cm.get = mock_get
                mock_client_cls.return_value = mock_cm

                client = OpenAlexClient()
                result = await client.search_works("test")

            assert call_count[0] == 2  # Erster Versuch + 1 Retry
            mock_sleep.assert_called_once()
            assert isinstance(result, OpenAlexSearchResponse)

        asyncio.run(run())

    def test_http_error_raises(self):
        """HTTP-Fehler (nicht 429) werden als Exception weitergegeben."""
        error_resp = MagicMock()
        error_resp.status_code = 500
        error_resp.request = httpx.Request("GET", "https://api.openalex.org/works")
        error_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=error_resp.request,
            response=error_resp,
        )

        async def run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_cm = AsyncMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
                mock_cm.__aexit__ = AsyncMock(return_value=None)
                mock_cm.get = AsyncMock(return_value=error_resp)
                mock_client_cls.return_value = mock_cm

                client = OpenAlexClient()
                with pytest.raises(httpx.HTTPStatusError):
                    await client.search_works("test")

        asyncio.run(run())

    def test_no_filter_params_when_not_specified(self):
        """Ohne year_range und languages wird kein filter-Parameter gesetzt."""
        work = _openalex_work()
        mock_resp = _mock_response([work])
        captured_params: list[dict] = []

        async def run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_cm = AsyncMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_cm)
                mock_cm.__aexit__ = AsyncMock(return_value=None)

                async def mock_get(url, params=None, **kwargs):
                    captured_params.append(params or {})
                    return mock_resp

                mock_cm.get = mock_get
                mock_client_cls.return_value = mock_cm

                client = OpenAlexClient()
                await client.search_works("test")

            assert "filter" not in captured_params[0]

        asyncio.run(run())


# --- T2: Relevanz-Score Feld ---


class TestOpenAlexRelevanceFilter:
    """Testet Relevanz-Score Feld."""

    def test_work_has_relevance_score(self):
        """OpenAlexWork hat relevance_score Feld."""
        work = OpenAlexWork(
            id="W1",
            display_name="Test",
            relevance_score=0.85,
        )
        assert work.relevance_score == 0.85

    def test_work_default_relevance_zero(self):
        """Ohne Score: Default 0.0."""
        work = OpenAlexWork(id="W2", display_name="Test")
        assert work.relevance_score == 0.0
