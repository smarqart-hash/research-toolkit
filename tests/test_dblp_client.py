"""Tests fuer den DBLP API Client."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.agents.dblp_client import (
    DBLPClient,
    DBLPHit,
    DBLPInfo,
    DBLPResult,
    DBLPSearchResponse,
)
from src.agents.paper_ranker import from_dblp


# --- Fixtures / Factories ---


def _dblp_hit(
    title: str = "Attention Is All You Need",
    authors: list[str] | None = None,
    year: str = "2017",
    venue: str = "NeurIPS",
    doi: str | None = "10.5555/3295222.3295349",
    url: str = "https://dblp.org/rec/conf/nips/VaswaniSPUJGKP17",
    ee: str | None = "https://papers.nips.cc/paper/7181",
    score: str = "5",
) -> DBLPHit:
    """Factory fuer DBLPHit Test-Objekte."""
    author_list = [{"text": a} for a in (authors or ["Vaswani, Ashish", "Shazeer, Noam"])]
    return DBLPHit(
        score=score,
        info=DBLPInfo(
            authors={"author": author_list},
            title=title,
            venue=venue,
            year=year,
            type="Conference and Workshop Papers",
            doi=doi,
            url=url,
            ee=ee,
        ),
    )


def _mock_response(hits: list[DBLPHit], total: int = 0, status_code: int = 200) -> MagicMock:
    """Erstellt einen Mock-HTTP-Response mit DBLPSearchResponse."""
    response = MagicMock()
    response.status_code = status_code
    response.request = httpx.Request("GET", "https://dblp.org/search/publ/api")
    data = {
        "result": {
            "hits": {
                "total": str(total or len(hits)),
                "hit": [h.model_dump() for h in hits],
            }
        }
    }
    response.json.return_value = data
    response.raise_for_status = MagicMock()
    return response


# --- T1: Modell-Tests ---


class TestDBLPInfo:
    def test_year_int(self):
        info = DBLPInfo(year="2024")
        assert info.year_int == 2024

    def test_year_int_invalid(self):
        info = DBLPInfo(year="unknown")
        assert info.year_int is None

    def test_author_names_list(self):
        info = DBLPInfo(authors={"author": [{"text": "Alice"}, {"text": "Bob"}]})
        assert info.author_names == ["Alice", "Bob"]

    def test_author_names_single(self):
        """Einzelner Autor kommt als Dict statt Liste."""
        info = DBLPInfo(authors={"author": {"text": "Alice"}})
        assert info.author_names == ["Alice"]

    def test_author_names_empty(self):
        info = DBLPInfo(authors={})
        assert info.author_names == []

    def test_defaults(self):
        info = DBLPInfo()
        assert info.title == ""
        assert info.venue == ""
        assert info.doi is None


class TestDBLPHit:
    def test_relevance_score(self):
        hit = _dblp_hit(score="7.5")
        assert hit.relevance_score == 7.5

    def test_relevance_score_invalid(self):
        hit = _dblp_hit(score="")
        assert hit.relevance_score == 0.0


class TestDBLPResult:
    def test_total_int(self):
        result = DBLPResult(total="12345")
        assert result.total_int == 12345

    def test_total_int_invalid(self):
        result = DBLPResult(total="")
        assert result.total_int == 0


# --- T2: Client HTTP ---


class TestDBLPClient:
    def test_search_success(self):
        """Erfolgreiche Suche gibt DBLPSearchResponse zurueck."""
        hit = _dblp_hit()
        mock_resp = _mock_response([hit])

        async def run():
            client = DBLPClient()
            client._client = MagicMock()
            client._client.get = AsyncMock(return_value=mock_resp)
            client._client.aclose = AsyncMock()

            result = await client.search("attention is all you need")

            assert isinstance(result, DBLPSearchResponse)
            assert result.hits.total_int == 1
            assert result.hits.hit[0].info.title == "Attention Is All You Need"

        asyncio.run(run())

    def test_search_params(self):
        """Query-Parameter werden korrekt uebergeben."""
        hit = _dblp_hit()
        mock_resp = _mock_response([hit])
        captured_params: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured_params.append(params or {})
            return mock_resp

        async def run():
            client = DBLPClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()

            await client.search("test query", hits=20, offset=10)

            assert captured_params[0]["q"] == "test query"
            assert captured_params[0]["format"] == "json"
            assert captured_params[0]["h"] == 20
            assert captured_params[0]["f"] == 10

        asyncio.run(run())

    def test_hits_capped_at_1000(self):
        """hits wird auf max 1000 begrenzt."""
        hit = _dblp_hit()
        mock_resp = _mock_response([hit])
        captured_params: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured_params.append(params or {})
            return mock_resp

        async def run():
            client = DBLPClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()

            await client.search("test", hits=5000)

            assert captured_params[0]["h"] == 1000

        asyncio.run(run())

    def test_429_triggers_retry(self):
        """Bei 429-Response wird einmal retried."""
        hit = _dblp_hit()
        success_resp = _mock_response([hit])

        rate_limit_resp = MagicMock()
        rate_limit_resp.status_code = 429
        rate_limit_resp.request = httpx.Request("GET", "https://dblp.org/")

        call_count = [0]

        async def mock_get(url, params=None, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return rate_limit_resp
            return success_resp

        async def run():
            from unittest.mock import patch

            with patch("asyncio.sleep", new_callable=AsyncMock):
                client = DBLPClient()
                client._client = MagicMock()
                client._client.get = mock_get
                client._client.aclose = AsyncMock()

                result = await client.search("test")

            assert call_count[0] == 2
            assert isinstance(result, DBLPSearchResponse)

        asyncio.run(run())


# --- T3: Converter ---


class TestFromDblp:
    def test_basic_conversion(self):
        hit = _dblp_hit()
        paper = from_dblp(hit)

        assert paper.title == "Attention Is All You Need"
        assert paper.source == "dblp"
        assert paper.doi == "10.5555/3295222.3295349"
        assert paper.year == 2017
        assert paper.abstract is None  # DBLP hat keine Abstracts
        assert len(paper.authors) == 2
        assert "NeurIPS" in paper.tags

    def test_no_doi_uses_url_hash(self):
        hit = _dblp_hit(doi=None)
        paper = from_dblp(hit)
        assert paper.paper_id != ""
        assert paper.doi is None

    def test_ee_preferred_over_url(self):
        """Electronic Edition URL wird bevorzugt."""
        hit = _dblp_hit(
            url="https://dblp.org/rec/xyz",
            ee="https://publisher.com/paper/123",
        )
        paper = from_dblp(hit)
        assert paper.url == "https://publisher.com/paper/123"

    def test_single_author(self):
        hit = _dblp_hit(authors=["Solo Author"])
        paper = from_dblp(hit)
        assert paper.authors == ["Solo Author"]

    def test_venue_as_tag(self):
        hit = _dblp_hit(venue="ICML")
        paper = from_dblp(hit)
        assert "ICML" in paper.tags
