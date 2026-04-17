"""Live-Tests gegen die echte Bundestag DIP API.

Gates:
    - `@pytest.mark.live` — ueberspringbar via `pytest -m "not live"`
    - `BUNDESTAG_API_KEY` oder oeffentlicher Demo-Key als Default

Ausfuehrung:
    pytest tests/test_bundestag_live.py -m live -v

Kalibrierung (exploration 2026-04-17):
    - "Klimaschutz" → 3.644 Vorgaenge
    - "Kuenstliche Intelligenz" → 109 Vorgaenge
    - "Digitalisierung" → 21 Vorgaenge
    - Vollbestand: 285.331 Drucksachen (Regression-Grenze: kein Topic > 50k)
"""

from __future__ import annotations

import asyncio
import os
from statistics import median

import pytest

from src.agents.bundestag_client import BundestagClient
from src.agents.bundestag_vocabulary import BundestagVocabulary

pytestmark = pytest.mark.live

# Realistische Policy-Topics aus briefing-app Benchmark-Runs
LIVE_TOPICS = [
    "Klimaschutz",
    "Kuenstliche Intelligenz",
    "Digitalisierung",
    "Energiewende",
    "Gesundheitspolitik",
    "Cybersicherheit",
    "Migration",
    "Bundeswehr",
    "EU-Regulierung",
    "Buerokratieabbau",
]

REGRESSION_CAP = 50_000  # Kein Topic darf Vollbestand liefern (V1-Bug)
MIN_RELEVANT_HITS = 5  # Unter 5 Hits = Topic zu speziell
MIN_SUCCESS_RATE = 0.7  # 7/10 muessen Hits zwischen MIN und REGRESSION_CAP liefern
MEDIAN_LOWER = 10
MEDIAN_UPPER = 10_000


def _run(coro):
    """Helper fuer sync-Test-Run von async-Code (lifecycle isoliert pro Call)."""
    return asyncio.run(coro)


@pytest.fixture
def live_vocab(tmp_path):
    """Frische Vocabulary-Instanz im tmp_path (kein Cache-Leakage)."""
    return BundestagVocabulary(cache_path=tmp_path / "vocab.json")


class TestLiveSearchTopic:
    """End-to-End-Tests: search_topic liefert relevante, topic-spezifische Hits."""

    def test_no_topic_returns_full_inventory(self, live_vocab):
        """Regression-Test: kein Topic liefert > REGRESSION_CAP Hits (V1-Bug)."""
        hits_per_topic: dict[str, int] = {}

        async def run():
            async with BundestagClient() as client:
                for topic in LIVE_TOPICS:
                    try:
                        papers = await client.search_topic(
                            topic,
                            rows=100,
                            vocabulary=live_vocab,
                            include_positions=False,
                        )
                    except Exception as exc:  # noqa: BLE001 — Live-API-Fehler tolerant
                        pytest.fail(f"Topic '{topic}' crashte mit {type(exc).__name__}: {exc}")
                    hits_per_topic[topic] = len(papers)

        _run(run())

        # Regression: Kein Topic liefert Vollbestand
        over_cap = {t: n for t, n in hits_per_topic.items() if n > REGRESSION_CAP}
        assert not over_cap, (
            f"Topics ueber Regression-Cap {REGRESSION_CAP}: {over_cap}"
        )

        # Success-Rate: Mindestens 70% der Topics liefern relevante Hits
        relevant = [
            t for t, n in hits_per_topic.items()
            if MIN_RELEVANT_HITS <= n <= REGRESSION_CAP
        ]
        success_rate = len(relevant) / len(LIVE_TOPICS)
        assert success_rate >= MIN_SUCCESS_RATE, (
            f"Nur {len(relevant)}/{len(LIVE_TOPICS)} Topics im Zielkorridor "
            f"({MIN_RELEVANT_HITS}-{REGRESSION_CAP}). Details: {hits_per_topic}"
        )

        # Median im realistischen Korridor
        med = median(hits_per_topic.values())
        assert MEDIAN_LOWER <= med <= MEDIAN_UPPER, (
            f"Median {med} ausserhalb [{MEDIAN_LOWER}, {MEDIAN_UPPER}]. "
            f"Details: {hits_per_topic}"
        )

    def test_klimaschutz_is_topic_specific(self, live_vocab):
        """Baseline-Topic 'Klimaschutz' liefert topic-spezifische Vorgaenge."""

        async def run():
            async with BundestagClient() as client:
                return await client.search_topic(
                    "Klimaschutz",
                    rows=50,
                    vocabulary=live_vocab,
                    include_positions=False,
                )

        papers = _run(run())

        # Mindestens 10 Hits (war in Exploration 3.644)
        assert len(papers) >= 10, f"Klimaschutz lieferte nur {len(papers)} Hits"
        # Kein Vollbestand
        assert len(papers) < REGRESSION_CAP

        # Mindestens 30% der Titles sollten Topic-relevante Begriffe enthalten
        topic_keywords = ["klima", "emission", "co2", "treibhaus", "energie", "erneuerbar"]
        hits = [
            p for p in papers
            if any(kw in (p.title or "").lower() for kw in topic_keywords)
        ]
        relevance = len(hits) / max(1, len(papers))
        assert relevance >= 0.3, (
            f"Nur {relevance:.0%} der Hits enthalten Klima-Keywords. "
            f"Sample: {[p.title[:80] for p in papers[:5]]}"
        )

    def test_graceful_degradation_for_rare_topic(self, live_vocab):
        """Seltenes/spezifisches Topic crasht nicht, auch wenn 0 Deskriptoren."""
        rare_topic = "Quantensensorik-Regulierung"

        async def run():
            async with BundestagClient() as client:
                return await client.search_topic(
                    rare_topic,
                    rows=20,
                    vocabulary=live_vocab,
                    include_positions=False,
                )

        papers = _run(run())
        assert isinstance(papers, list)

    def test_include_positions_returns_pdf_urls(self, live_vocab):
        """include_positions=True liefert pdf_urls aus /vorgangsposition."""

        async def run():
            async with BundestagClient() as client:
                return await client.search_topic(
                    "Klimaschutz",
                    rows=5,
                    vocabulary=live_vocab,
                    include_positions=True,
                )

        papers = _run(run())
        assert len(papers) > 0, "Mindestens 1 Position erwartet fuer Klimaschutz"
        # Mindestens 30% haben eine pdf_url
        with_pdf = [p for p in papers if p.pdf_url]
        ratio = len(with_pdf) / max(1, len(papers))
        assert ratio >= 0.3, (
            f"Nur {ratio:.0%} der Positionen haben pdf_url (erwartet >=30%). "
            f"Sample-IDs: {[p.paper_id for p in papers[:5]]}"
        )


class TestLiveRegressionLegacy:
    """Regression: search_drucksachen mit f.titel liefert keine 285k Drucksachen."""

    def test_search_drucksachen_no_full_inventory(self):
        """V3-Fix: f.titel filtert — kein Vollbestand trotz Legacy-API-Call."""

        async def run():
            async with BundestagClient() as client:
                return await client.search_drucksachen("Klimaschutz", rows=5)

        result = _run(run())
        assert result.numFound < REGRESSION_CAP, (
            f"Legacy search_drucksachen liefert {result.numFound} Hits — "
            f"Vollbestand-Regression (V1-Bug)"
        )
