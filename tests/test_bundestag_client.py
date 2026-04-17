"""Tests fuer den Bundestag DIP API Client."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.agents.bundestag_client import (
    BundestagClient,
    Deskriptor,
    DIPDrucksache,
    DIPSearchResponse,
    DIPVorgang,
    DIPVorgangResponse,
    DIPVorgangsposition,
    DIPVorgangspositionResponse,
    Fundstelle,
    PUBLIC_API_KEY,
)
from src.agents.paper_ranker import from_bundestag, from_dip_vorgang, from_dip_vorgangsposition


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

    def test_drucksachetyp_filter_uses_correct_param(self):
        """Dokumenttyp-Filter wird als `f.drucksachetyp` (nicht `f.typ`) gesendet.

        Regression-Test fuer V3-Fix: OpenAPI spezifiziert `f.drucksachetyp`,
        Pre-V3-Code sendete faelschlich `f.typ` das DIP ignorierte.
        """
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

            assert captured_params[0]["f.drucksachetyp"] == "Gesetzentwurf"
            assert "f.typ" not in captured_params[0], (
                "Legacy f.typ Parameter darf nicht mehr gesendet werden"
            )

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


# --- T4: V3 Regression + Neue Methoden ---


def _mock_vorgang_response(vorgaenge: list[DIPVorgang]) -> MagicMock:
    """Mock-Response fuer /vorgang-Listen."""
    response = MagicMock()
    response.status_code = 200
    response.request = httpx.Request("GET", "https://search.dip.bundestag.de/api/v1/vorgang")
    response.json.return_value = {
        "numFound": len(vorgaenge),
        "documents": [v.model_dump(by_alias=True) for v in vorgaenge],
    }
    response.raise_for_status = MagicMock()
    return response


def _mock_vorgang_detail_response(vorgang: DIPVorgang) -> MagicMock:
    """Mock-Response fuer /vorgang/{id}."""
    response = MagicMock()
    response.status_code = 200
    response.request = httpx.Request(
        "GET", f"https://search.dip.bundestag.de/api/v1/vorgang/{vorgang.id}"
    )
    response.json.return_value = vorgang.model_dump(by_alias=True)
    response.raise_for_status = MagicMock()
    return response


def _mock_positions_response(positions: list[DIPVorgangsposition]) -> MagicMock:
    """Mock-Response fuer /vorgangsposition."""
    response = MagicMock()
    response.status_code = 200
    response.request = httpx.Request(
        "GET", "https://search.dip.bundestag.de/api/v1/vorgangsposition"
    )
    response.json.return_value = {
        "numFound": len(positions),
        "documents": [p.model_dump(by_alias=True) for p in positions],
    }
    response.raise_for_status = MagicMock()
    return response


class TestLegacyBugRegression:
    """Regression-Tests fuer V1-Bug (search= ignoriert) + V3-Fix (f.titel)."""

    def test_search_drucksachen_uses_f_titel_not_search(self):
        ds = _drucksache()
        mock_resp = _mock_response([ds])
        captured: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured.append(params or {})
            return mock_resp

        async def run():
            client = BundestagClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()
            await client.search_drucksachen("Klimaschutz")

        asyncio.run(run())
        params = captured[0]
        assert params.get("f.titel") == "Klimaschutz"
        assert "search" not in params, "Legacy search= Parameter darf nicht gesetzt sein"

    def test_search_drucksachen_empty_query_omits_titel(self):
        """Leere Query laesst f.titel weg (Browse-Modus)."""
        ds = _drucksache()
        mock_resp = _mock_response([ds])
        captured: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured.append(params or {})
            return mock_resp

        async def run():
            client = BundestagClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()
            await client.search_drucksachen("")
            await client.search_drucksachen("   ")

        asyncio.run(run())
        for params in captured:
            assert "f.titel" not in params
            assert "search" not in params

    def test_search_vorgaenge_uses_f_titel_not_search(self):
        mock_resp = _mock_vorgang_response([])
        captured: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured.append(params or {})
            return mock_resp

        async def run():
            client = BundestagClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()
            await client.search_vorgaenge("Energiewende")

        asyncio.run(run())
        assert captured[0].get("f.titel") == "Energiewende"
        assert "search" not in captured[0]


class TestGetVorgang:
    """Tests fuer get_vorgang (Detail-Abruf mit Deskriptoren)."""

    def test_parses_deskriptoren_and_sachgebiete(self):
        vorgang = DIPVorgang(
            id="333085",
            typ="Vorgang",
            vorgangstyp="Kleine Anfrage",
            wahlperiode=21,
            titel="Test-Titel",
            datum="2026-04-15",
            initiative=["Fraktion der AfD"],
            sachgebiet=["Umwelt", "Landwirtschaft"],
            deskriptor=[
                Deskriptor(name="Klimaschutz", typ="Sachbegriffe"),
                Deskriptor(name="Harz", typ="Geograph. Begriffe", fundstelle=False),
            ],
        )
        mock_resp = _mock_vorgang_detail_response(vorgang)

        async def run():
            client = BundestagClient()
            client._client = MagicMock()
            client._client.get = AsyncMock(return_value=mock_resp)
            client._client.aclose = AsyncMock()
            result = await client.get_vorgang("333085")
            return result

        result = asyncio.run(run())
        assert result.id == "333085"
        assert result.vorgangstyp == "Kleine Anfrage"
        assert result.wahlperiode == 21
        assert len(result.deskriptor) == 2
        assert result.deskriptor[0].name == "Klimaschutz"
        assert "Umwelt" in result.sachgebiet
        assert result.url == "https://dip.bundestag.de/vorgang/333085"

    def test_hits_correct_endpoint(self):
        vorgang = DIPVorgang(id="V1", titel="T", datum="2026-01-01")
        mock_resp = _mock_vorgang_detail_response(vorgang)
        captured_urls: list[str] = []

        async def mock_get(url, params=None, **kwargs):
            captured_urls.append(url)
            return mock_resp

        async def run():
            client = BundestagClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()
            await client.get_vorgang("333085")

        asyncio.run(run())
        assert captured_urls[0].endswith("/vorgang/333085")


class TestGetVorgangspositionen:
    """Tests fuer get_vorgangspositionen (verifizierter Join-Pfad)."""

    def test_uses_f_vorgang_filter(self):
        mock_resp = _mock_positions_response([])
        captured: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured.append(params or {})
            return mock_resp

        async def run():
            client = BundestagClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()
            await client.get_vorgangspositionen("333578")

        asyncio.run(run())
        assert captured[0]["f.vorgang"] == "333578"

    def test_parses_fundstelle(self):
        vp = DIPVorgangsposition(
            id="690420",
            vorgang_id="333578",
            vorgangsposition="Antwort",
            dokumentart="Drucksache",
            titel="Kleine Anfrage + Antwort",
            datum="2026-04-15",
            fundstelle=Fundstelle(
                dokumentnummer="21/5250",
                drucksachetyp="Fragen",
                pdf_url="https://dserver.bundestag.de/btd/21/052/2105250.pdf",
                urheber=["Bundesregierung"],
            ),
        )
        mock_resp = _mock_positions_response([vp])

        async def run():
            client = BundestagClient()
            client._client = MagicMock()
            client._client.get = AsyncMock(return_value=mock_resp)
            client._client.aclose = AsyncMock()
            return await client.get_vorgangspositionen("333578")

        result = asyncio.run(run())
        assert result.numFound == 1
        pos = result.documents[0]
        assert pos.fundstelle is not None
        assert pos.fundstelle.dokumentnummer == "21/5250"
        assert "Bundesregierung" in pos.fundstelle.urheber


class TestSearchTopic:
    """Tests fuer search_topic High-Level-API."""

    def _make_vocab(self, tmp_path, cached_descriptors=None):
        """Helper: BundestagVocabulary mit optional gecachtem Eintrag."""
        from datetime import datetime, timezone
        from src.agents.bundestag_vocabulary import (
            BundestagVocabulary,
            DescriptorEntry,
            TopicVocab,
        )

        vocab = BundestagVocabulary(cache_path=tmp_path / "vocab.json")
        if cached_descriptors is not None:
            tv = TopicVocab(
                topic="klimaschutz",
                descriptors=[
                    DescriptorEntry(name=name, freq=freq, typ="Sachbegriffe")
                    for name, freq in cached_descriptors
                ],
                sample_size=50,
                learned_at=datetime.now(tz=timezone.utc),
            )
            vocab.set(tv)
        return vocab

    def test_with_vocabulary_uses_f_deskriptor(self, tmp_path):
        """Mit Cache-Hit wird f.deskriptor statt f.titel gesendet."""
        vocab = self._make_vocab(tmp_path, cached_descriptors=[("Klimaschutz", 37)])
        mock_resp = _mock_vorgang_response([])
        captured: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured.append(params or {})
            return mock_resp

        async def run():
            client = BundestagClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()
            await client.search_topic("Klimaschutz", vocabulary=vocab)

        asyncio.run(run())
        assert captured[0]["f.deskriptor"] == "Klimaschutz"
        assert "f.titel" not in captured[0]

    def test_without_vocabulary_falls_back_to_f_titel(self, tmp_path):
        """Ohne Vocabulary-Instanz laeuft search_topic auf f.titel-Fallback."""
        mock_resp = _mock_vorgang_response([])
        captured: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured.append(params or {})
            return mock_resp

        async def run():
            client = BundestagClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()
            await client.search_topic("Klimaschutz", vocabulary=None)

        asyncio.run(run())
        assert captured[0].get("f.titel") == "Klimaschutz"
        assert "f.deskriptor" not in captured[0]

    def test_dedupes_vorgang_ids(self, tmp_path):
        """Duplizierte Vorgang-IDs in Response werden in Dedup gefiltert."""
        vocab = self._make_vocab(tmp_path, cached_descriptors=[("Klimaschutz", 37)])
        v1 = DIPVorgang(id="V1", titel="T1", datum="2026-04-01")
        v2 = DIPVorgang(id="V2", titel="T2", datum="2026-03-01")
        v1_dup = DIPVorgang(id="V1", titel="T1 (dup)", datum="2026-04-01")
        mock_resp = _mock_vorgang_response([v1, v2, v1_dup])

        async def run():
            client = BundestagClient()
            client._client = MagicMock()
            client._client.get = AsyncMock(return_value=mock_resp)
            client._client.aclose = AsyncMock()
            return await client.search_topic("Klimaschutz", vocabulary=vocab)

        papers = asyncio.run(run())
        paper_ids = {p.paper_id for p in papers}
        assert paper_ids == {"dip-vorgang:V1", "dip-vorgang:V2"}

    def test_ranking_is_recency_desc(self, tmp_path):
        """Ergebnisse werden nach Jahr absteigend sortiert."""
        vocab = self._make_vocab(tmp_path, cached_descriptors=[("Klimaschutz", 37)])
        old = DIPVorgang(id="V1", titel="Alt", datum="2020-01-01")
        new = DIPVorgang(id="V2", titel="Neu", datum="2026-01-01")
        mid = DIPVorgang(id="V3", titel="Mittel", datum="2023-01-01")
        mock_resp = _mock_vorgang_response([old, new, mid])

        async def run():
            client = BundestagClient()
            client._client = MagicMock()
            client._client.get = AsyncMock(return_value=mock_resp)
            client._client.aclose = AsyncMock()
            return await client.search_topic("Klimaschutz", vocabulary=vocab)

        papers = asyncio.run(run())
        years = [p.year for p in papers]
        assert years == [2026, 2023, 2020]

    def test_wahlperiode_filter_passed(self, tmp_path):
        """wahlperiode wird als f.wahlperiode weitergereicht."""
        vocab = self._make_vocab(tmp_path, cached_descriptors=[("Klimaschutz", 37)])
        mock_resp = _mock_vorgang_response([])
        captured: list[dict] = []

        async def mock_get(url, params=None, **kwargs):
            captured.append(params or {})
            return mock_resp

        async def run():
            client = BundestagClient()
            client._client = MagicMock()
            client._client.get = mock_get
            client._client.aclose = AsyncMock()
            await client.search_topic("Klimaschutz", vocabulary=vocab, wahlperiode=20)

        asyncio.run(run())
        assert captured[0]["f.wahlperiode"] == 20


class TestFromDipVorgang:
    def test_basic_conversion(self):
        v = DIPVorgang(
            id="333085",
            typ="Vorgang",
            vorgangstyp="Kleine Anfrage",
            titel="Test",
            datum="2026-04-15",
            initiative=["Fraktion der AfD"],
            deskriptor=[Deskriptor(name="Klimaschutz", typ="Sachbegriffe")],
            sachgebiet=["Umwelt"],
        )
        p = from_dip_vorgang(v)
        assert p.source == "bundestag"
        assert p.paper_id == "dip-vorgang:333085"
        assert p.authors == ["Fraktion der AfD"]
        assert "Klimaschutz" in p.tags
        assert "Umwelt" in p.tags
        assert "Kleine Anfrage" in p.tags
        assert p.url == "https://dip.bundestag.de/vorgang/333085"


class TestFromDipVorgangsposition:
    def test_uses_dokumentnummer_as_id(self):
        vp = DIPVorgangsposition(
            id="690420",
            vorgang_id="333578",
            titel="Antwort",
            datum="2026-04-15",
            dokumentart="Drucksache",
            fundstelle=Fundstelle(
                dokumentnummer="21/5250",
                drucksachetyp="Fragen",
                pdf_url="https://example.org/pdf",
                urheber=["Bundesregierung"],
            ),
        )
        p = from_dip_vorgangsposition(vp)
        assert p.paper_id == "dip:21/5250"
        assert p.pdf_url == "https://example.org/pdf"
        assert p.authors == ["Bundesregierung"]

    def test_fallback_id_when_no_dokumentnummer(self):
        vp = DIPVorgangsposition(id="X", vorgang_id="Y", titel="T", datum="2026-01-01")
        p = from_dip_vorgangsposition(vp)
        assert p.paper_id == "dip-vp:X"
        assert p.pdf_url is None
