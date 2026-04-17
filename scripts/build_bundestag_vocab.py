"""Seed-Script fuer BundestagVocabulary.

Laedt `data/seed_topics.json`, lernt jedes Topic via DIP-API und persistiert
den Cache unter `data/vocabularies/bundestag_deskriptoren.json`.

Usage:
    python scripts/build_bundestag_vocab.py
    python scripts/build_bundestag_vocab.py --sample-size 100 --min-freq 3
    python scripts/build_bundestag_vocab.py --force  # Re-Learn auch bei Cache-Hit

Rate-Limit: 1s Sleep zwischen Topics (30 req/min konservativ).
Laufzeit: ~1 Minute fuer 20-30 Topics.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Projekt-Root fuer src/ Import
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from agents.bundestag_client import BundestagClient  # noqa: E402
from agents.bundestag_vocabulary import BundestagVocabulary  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("seed")

DEFAULT_SEED_PATH = PROJECT_ROOT / "data" / "seed_topics.json"
DEFAULT_CACHE_PATH = PROJECT_ROOT / "data" / "vocabularies" / "bundestag_deskriptoren.json"


def _load_seed(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Seed-Datei nicht gefunden: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    topics = data.get("topics")
    if not isinstance(topics, list) or not topics:
        raise ValueError(f"Seed-Datei '{path}' hat kein 'topics' Array")
    return list(topics)


async def seed_vocabulary(
    *,
    seed_path: Path,
    cache_path: Path,
    sample_size: int,
    min_freq: int,
    force: bool,
) -> None:
    topics = _load_seed(seed_path)
    logger.info("Seed-Topics: %d aus %s", len(topics), seed_path)

    async with BundestagClient() as client:
        # Client ueber Init-Parameter wiederverwenden (kein private-attr-access)
        vocab = BundestagVocabulary(cache_path=cache_path, client=client)

        learned = 0
        skipped = 0
        failed: list[str] = []

        for idx, topic in enumerate(topics, 1):
            logger.info("[%d/%d] Topic: %s", idx, len(topics), topic)
            if not force and vocab.get(topic) is not None:
                logger.info("  -> Cache-Hit (skip, --force fuer Re-Learn)")
                skipped += 1
                continue
            try:
                tv = await vocab.learn(
                    topic, sample_size=sample_size, min_freq=min_freq
                )
                logger.info(
                    "  -> %d descriptors, %d sachgebiete (sample=%d)",
                    len(tv.descriptors),
                    len(tv.sachgebiete),
                    tv.sample_size,
                )
                learned = learned + 1
            except Exception as exc:  # noqa: BLE001 — Netzwerk-tolerant
                logger.exception("  -> FEHLER: %s", exc)
                failed = [*failed, topic]

        vocab.save()
        logger.info(
            "Done: %d gelernt, %d cache-hit, %d fehlgeschlagen. Cache: %s",
            learned,
            skipped,
            len(failed),
            cache_path,
        )
        if failed:
            logger.warning("Fehlgeschlagene Topics: %s", failed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed", type=Path, default=DEFAULT_SEED_PATH, help="Seed-Topics JSON"
    )
    parser.add_argument(
        "--cache", type=Path, default=DEFAULT_CACHE_PATH, help="Cache-Output-Pfad"
    )
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--min-freq", type=int, default=3)
    parser.add_argument(
        "--force", action="store_true", help="Re-Learn auch bei Cache-Hit"
    )
    args = parser.parse_args()

    asyncio.run(
        seed_vocabulary(
            seed_path=args.seed,
            cache_path=args.cache,
            sample_size=args.sample_size,
            min_freq=args.min_freq,
            force=args.force,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
