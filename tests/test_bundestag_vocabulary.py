"""Unit-Tests fuer BundestagVocabulary (Cache-Round-Trip, Learning, Stale-Check)."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.bundestag_client import (
    Deskriptor,
    DIPVorgang,
    DIPVorgangResponse,
)
from src.agents.bundestag_vocabulary import (
    BundestagVocabulary,
    DescriptorEntry,
    SachgebietEntry,
    TopicVocab,
)


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _make_topic_vocab(
    topic: str = "klimaschutz",
    descriptors: list[tuple[str, int]] | None = None,
    age_days: int = 0,
) -> TopicVocab:
    """Factory fuer TopicVocab-Fixtures mit optionalem Alter."""
    descriptors = descriptors or [("Klimaschutz", 37)]
    return TopicVocab(
        topic=topic,
        descriptors=[
            DescriptorEntry(name=name, freq=freq, typ="Sachbegriffe")
            for name, freq in descriptors
        ],
        sample_size=50,
        learned_at=_utcnow() - timedelta(days=age_days),
    )


class TestCacheRoundTrip:
    def test_save_and_load(self, tmp_path):
        """Cache persistiert Topics ueber save()/neuer Instanz load()."""
        cache_path = tmp_path / "vocab.json"
        vocab = BundestagVocabulary(cache_path=cache_path)
        vocab.set(_make_topic_vocab(descriptors=[("Klimaschutz", 37), ("Energiewende", 14)]))
        vocab.save()

        # Neue Instanz laedt denselben Cache
        reloaded = BundestagVocabulary(cache_path=cache_path)
        tv = reloaded.get("klimaschutz")
        assert tv is not None
        assert [d.name for d in tv.descriptors] == ["Klimaschutz", "Energiewende"]

    def test_save_creates_parent_dirs(self, tmp_path):
        nested = tmp_path / "a" / "b" / "vocab.json"
        vocab = BundestagVocabulary(cache_path=nested)
        vocab.set(_make_topic_vocab())
        vocab.save()
        assert nested.exists()

    def test_save_format_is_v1_schema(self, tmp_path):
        cache_path = tmp_path / "vocab.json"
        vocab = BundestagVocabulary(cache_path=cache_path)
        vocab.set(_make_topic_vocab())
        vocab.save()
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert "updated" in data
        assert "klimaschutz" in data["topics"]

    def test_missing_cache_starts_empty(self, tmp_path):
        vocab = BundestagVocabulary(cache_path=tmp_path / "nonexistent.json")
        assert vocab.all_topics() == []

    def test_corrupt_cache_does_not_crash(self, tmp_path):
        cache_path = tmp_path / "vocab.json"
        cache_path.write_text("{not json]", encoding="utf-8")
        vocab = BundestagVocabulary(cache_path=cache_path)
        assert vocab.all_topics() == []

    def test_wrong_version_starts_empty(self, tmp_path):
        cache_path = tmp_path / "vocab.json"
        cache_path.write_text(
            json.dumps({"version": 99, "topics": {"x": {}}}),
            encoding="utf-8",
        )
        vocab = BundestagVocabulary(cache_path=cache_path)
        assert vocab.all_topics() == []


class TestNormalization:
    def test_topic_key_normalized_lowercase(self, tmp_path):
        vocab = BundestagVocabulary(cache_path=tmp_path / "vocab.json")
        vocab.set(_make_topic_vocab(topic="KlimaSchutz"))
        assert vocab.get("klimaschutz") is not None
        assert vocab.get("KLIMASCHUTZ") is not None
        assert vocab.get("  klimaschutz  ") is not None


class TestStaleCheck:
    def test_fresh_entry_returned(self, tmp_path):
        vocab = BundestagVocabulary(cache_path=tmp_path / "vocab.json", stale_days=30)
        vocab.set(_make_topic_vocab(age_days=10))
        assert vocab.get("klimaschutz") is not None

    def test_stale_entry_returns_none(self, tmp_path):
        vocab = BundestagVocabulary(cache_path=tmp_path / "vocab.json", stale_days=30)
        vocab.set(_make_topic_vocab(age_days=45))
        assert vocab.get("klimaschutz") is None

    def test_stale_boundary_at_configured_days(self, tmp_path):
        vocab = BundestagVocabulary(cache_path=tmp_path / "vocab.json", stale_days=7)
        vocab.set(_make_topic_vocab(age_days=10))
        assert vocab.get("klimaschutz") is None


class TestTopDescriptor:
    def test_returns_first_entry(self):
        tv = _make_topic_vocab(
            descriptors=[("Klimaschutz", 37), ("Windenergie", 12)],
        )
        assert tv.top_descriptor() == "Klimaschutz"

    def test_empty_returns_none(self):
        tv = TopicVocab(topic="rare", learned_at=_utcnow())
        assert tv.top_descriptor() is None


class TestLearning:
    """Tests fuer learn() — Aggregation + Frequenz-Filter + 0-Deskriptor-Fall."""

    def _make_client_with_response(self, vorgaenge: list[DIPVorgang]) -> MagicMock:
        """Mock-Client dessen search_vorgaenge Return-Value fixiert ist."""
        client = MagicMock()
        response = DIPVorgangResponse(numFound=len(vorgaenge), documents=vorgaenge)
        client.search_vorgaenge = AsyncMock(return_value=response)
        client.close = AsyncMock()
        return client

    def test_aggregates_descriptors_and_sorts_by_freq(self, tmp_path, monkeypatch):
        # Beschleunige Tests: kein Rate-Limit-Sleep
        import src.agents.bundestag_vocabulary as bv_module
        monkeypatch.setattr(bv_module, "RATE_LIMIT_SLEEP_S", 0.0)

        v1 = DIPVorgang(
            id="V1", titel="T1", datum="2026-01-01",
            deskriptor=[
                Deskriptor(name="Klimaschutz", typ="Sachbegriffe"),
                Deskriptor(name="Windenergie", typ="Sachbegriffe"),
            ],
            sachgebiet=["Umwelt"],
        )
        v2 = DIPVorgang(
            id="V2", titel="T2", datum="2026-02-01",
            deskriptor=[
                Deskriptor(name="Klimaschutz", typ="Sachbegriffe"),
                Deskriptor(name="Rare-Desc", typ="Sachbegriffe"),
            ],
            sachgebiet=["Umwelt"],
        )
        v3 = DIPVorgang(
            id="V3", titel="T3", datum="2026-03-01",
            deskriptor=[Deskriptor(name="Klimaschutz", typ="Sachbegriffe")],
            sachgebiet=["Energie"],
        )
        client = self._make_client_with_response([v1, v2, v3])
        vocab = BundestagVocabulary(cache_path=tmp_path / "vocab.json", client=client)

        tv = asyncio.run(vocab.learn("Klimaschutz", min_freq=2, sample_size=50))

        # "Klimaschutz" freq=3, "Windenergie" freq=1 (below min_freq), "Rare" freq=1
        desc_names = [d.name for d in tv.descriptors]
        assert "Klimaschutz" in desc_names
        assert "Windenergie" not in desc_names
        assert "Rare-Desc" not in desc_names
        assert tv.descriptors[0].name == "Klimaschutz"
        assert tv.descriptors[0].freq == 3

    def test_zero_descriptors_cached_as_empty(self, tmp_path, monkeypatch):
        """Topic ohne brauchbare Deskriptoren wird trotzdem gecached."""
        import src.agents.bundestag_vocabulary as bv_module
        monkeypatch.setattr(bv_module, "RATE_LIMIT_SLEEP_S", 0.0)

        # Nur Vorgaenge ohne Deskriptoren
        v = DIPVorgang(id="V", titel="T", datum="2026-01-01")
        client = self._make_client_with_response([v, v, v])
        vocab = BundestagVocabulary(cache_path=tmp_path / "vocab.json", client=client)

        tv = asyncio.run(vocab.learn("obskures-topic", min_freq=3, sample_size=50))

        assert tv.descriptors == []
        assert tv.sachgebiete == []
        # Trotzdem cached
        assert vocab.get("obskures-topic") is not None

    def test_min_freq_filters(self, tmp_path, monkeypatch):
        import src.agents.bundestag_vocabulary as bv_module
        monkeypatch.setattr(bv_module, "RATE_LIMIT_SLEEP_S", 0.0)

        v1 = DIPVorgang(
            id="V1", titel="T", datum="2026-01-01",
            deskriptor=[Deskriptor(name="A", typ="Sachbegriffe")],
        )
        v2 = DIPVorgang(
            id="V2", titel="T", datum="2026-01-01",
            deskriptor=[Deskriptor(name="A", typ="Sachbegriffe")],
        )
        client = self._make_client_with_response([v1, v2])
        vocab = BundestagVocabulary(cache_path=tmp_path / "vocab.json", client=client)

        # min_freq=3 → "A" freq=2 fliegt raus
        tv = asyncio.run(vocab.learn("topic-a", min_freq=3, sample_size=50))
        assert tv.descriptors == []

    def test_http_error_caches_empty_entry(self, tmp_path, monkeypatch):
        """Learn-Fehler (HTTP) cached einen leeren TopicVocab (graceful degradation)."""
        import httpx
        import src.agents.bundestag_vocabulary as bv_module
        monkeypatch.setattr(bv_module, "RATE_LIMIT_SLEEP_S", 0.0)

        client = MagicMock()
        client.search_vorgaenge = AsyncMock(
            side_effect=httpx.ConnectError("network down")
        )
        client.close = AsyncMock()
        vocab = BundestagVocabulary(cache_path=tmp_path / "vocab.json", client=client)

        tv = asyncio.run(vocab.learn("broken-topic"))
        assert tv.descriptors == []
        assert vocab.get("broken-topic") is not None

    def test_get_or_learn_uses_cache(self, tmp_path, monkeypatch):
        """Cache-Hit vermeidet Learn-Call."""
        import src.agents.bundestag_vocabulary as bv_module
        monkeypatch.setattr(bv_module, "RATE_LIMIT_SLEEP_S", 0.0)

        client = MagicMock()
        client.search_vorgaenge = AsyncMock(return_value=DIPVorgangResponse())
        client.close = AsyncMock()
        vocab = BundestagVocabulary(cache_path=tmp_path / "vocab.json", client=client)
        vocab.set(_make_topic_vocab())

        asyncio.run(vocab.get_or_learn("klimaschutz"))
        client.search_vorgaenge.assert_not_called()

    def test_get_or_learn_fetches_on_miss(self, tmp_path, monkeypatch):
        import src.agents.bundestag_vocabulary as bv_module
        monkeypatch.setattr(bv_module, "RATE_LIMIT_SLEEP_S", 0.0)

        client = MagicMock()
        client.search_vorgaenge = AsyncMock(return_value=DIPVorgangResponse())
        client.close = AsyncMock()
        vocab = BundestagVocabulary(cache_path=tmp_path / "vocab.json", client=client)

        asyncio.run(vocab.get_or_learn("unknown-topic"))
        client.search_vorgaenge.assert_called_once()
