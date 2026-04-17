"""BundestagVocabulary — Deskriptor-Vokabular-Cache fuer Topic-Queries.

DIP liefert ein kontrolliertes Vokabular (Deskriptoren + Sachgebiete) nur als
Felder in `/vorgang` Responses, nicht als separaten Catalog-Endpunkt.

Dieses Modul lernt das Vokabular pro Topic via Sampling und cached die
Ergebnisse in JSON fuer Pipeline-Reuse + Cross-Project-Portabilitaet.

Usage:
    vocab = BundestagVocabulary()  # liest data/vocabularies/...
    tv = await vocab.learn("klimaschutz", sample_size=50)
    vocab.save()

Cache-Schema (JSON):
    {
      "version": 1,
      "updated": "2026-04-17T10:00:00Z",
      "topics": {
        "klimaschutz": {
          "topic": "klimaschutz",
          "descriptors": [{"name": "Klimaschutz", "freq": 37, "typ": "Sachbegriffe"}, ...],
          "sachgebiete": [{"name": "Umwelt", "freq": 14}, ...],
          "sample_size": 50,
          "learned_at": "2026-04-17T10:00:00Z"
        }
      }
    }
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from pydantic import BaseModel, Field

from src.agents.bundestag_client import BundestagClient

logger = logging.getLogger(__name__)

CACHE_VERSION = 1
DEFAULT_CACHE_PATH = Path("data/vocabularies/bundestag_deskriptoren.json")
DEFAULT_STALE_DAYS = 30
RATE_LIMIT_SLEEP_S = 1.0


class DescriptorEntry(BaseModel):
    """Ein Deskriptor mit Frequenz im Sample."""

    name: str
    freq: int
    typ: str = ""


class SachgebietEntry(BaseModel):
    """Ein Sachgebiet mit Frequenz im Sample."""

    name: str
    freq: int


class TopicVocab(BaseModel):
    """Gelerntes Vokabular fuer ein Topic."""

    topic: str
    descriptors: list[DescriptorEntry] = Field(default_factory=list)
    sachgebiete: list[SachgebietEntry] = Field(default_factory=list)
    sample_size: int = 0
    learned_at: datetime

    model_config = {"arbitrary_types_allowed": True}

    def is_stale(self, max_age_days: int = DEFAULT_STALE_DAYS) -> bool:
        """Prueft ob der Cache-Eintrag aelter als max_age_days ist."""
        age = _utcnow() - self.learned_at
        return age > timedelta(days=max_age_days)

    def top_descriptor(self) -> str | None:
        """Top-1 Deskriptor nach Frequenz (fuer f.deskriptor-Query)."""
        return self.descriptors[0].name if self.descriptors else None


def _utcnow() -> datetime:
    """UTC-Zeit mit tz-awareness (Python >= 3.11)."""
    return datetime.now(timezone.utc)


def _normalize_topic(topic: str) -> str:
    """Normalisiert Topic-Keys (lowercase, stripped) fuer Cache-Lookup."""
    return topic.strip().lower()


class BundestagVocabulary:
    """Cache fuer gelernte Topic → Deskriptor-Mappings.

    Persistiert als JSON im Repo, damit Pipeline-Reuse ohne Re-Learning funktioniert.
    """

    def __init__(
        self,
        cache_path: Path | None = None,
        client: BundestagClient | None = None,
        *,
        stale_days: int = DEFAULT_STALE_DAYS,
    ) -> None:
        self._cache_path = cache_path or DEFAULT_CACHE_PATH
        self._client = client
        self._stale_days = stale_days
        self._topics: dict[str, TopicVocab] = {}
        self._load()

    def _load(self) -> None:
        """Laed Cache von Disk, falls vorhanden."""
        if not self._cache_path.exists():
            logger.debug("Cache %s existiert nicht, starte leer", self._cache_path)
            return
        try:
            data = json.loads(self._cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Cache %s nicht lesbar (%s), starte leer", self._cache_path, exc
            )
            return
        if data.get("version") != CACHE_VERSION:
            logger.warning(
                "Cache-Version %s != erwartete %d, starte leer",
                data.get("version"),
                CACHE_VERSION,
            )
            return
        for key, tv_dict in (data.get("topics") or {}).items():
            try:
                self._topics[key] = TopicVocab.model_validate(tv_dict)
            except (ValueError, TypeError) as exc:
                logger.warning("Cache-Eintrag '%s' invalid: %s", key, exc)

    def save(self) -> None:
        """Persistiert Cache nach Disk (erzeugt Parent-Dirs)."""
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": CACHE_VERSION,
            "updated": _utcnow().isoformat(),
            "topics": {
                key: json.loads(tv.model_dump_json())
                for key, tv in self._topics.items()
            },
        }
        self._cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        logger.info(
            "Vocabulary gespeichert nach %s (%d Topics)",
            self._cache_path,
            len(self._topics),
        )

    def get(self, topic: str) -> TopicVocab | None:
        """Gibt den Cache-Eintrag fuer Topic zurueck, None bei Miss oder Stale."""
        key = _normalize_topic(topic)
        entry = self._topics.get(key)
        if entry is None:
            return None
        if entry.is_stale(self._stale_days):
            logger.debug("Cache-Eintrag '%s' stale (> %dd)", key, self._stale_days)
            return None
        return entry

    def set(self, vocab: TopicVocab) -> None:
        """Fuegt/ueberschreibt einen Cache-Eintrag (ohne save)."""
        self._topics[_normalize_topic(vocab.topic)] = vocab

    def all_topics(self) -> list[str]:
        """Alle gelernten Topic-Keys (unabhaengig von Stale-Status)."""
        return sorted(self._topics.keys())

    async def learn(
        self,
        topic: str,
        *,
        sample_size: int = 50,
        min_freq: int = 3,
    ) -> TopicVocab:
        """Lernt Vokabular fuer ein Topic via /vorgang?f.titel={topic} Sampling.

        Extrahiert alle `deskriptor[].name` + `sachgebiet[]` aus den Sample-Vorgaengen,
        zaehlt Frequenzen, filtert auf min_freq, sortiert absteigend.

        Edge-Cases:
        - 0 Treffer oder 0 Deskriptoren → TopicVocab mit leeren Listen (trotzdem cached).
          Caller kann bei `top_descriptor() is None` auf f.titel-Fallback gehen.
        - Rate-Limit: 1s Sleep vor Request, 429-Retry durch _request() des Clients.

        Args:
            topic: Topic-String (case-insensitive, wird normalisiert).
            sample_size: Max Vorgaenge zum Sampling (rows). API cap 100.
            min_freq: Minimale Frequenz fuer Aufnahme in den Cache.

        Returns:
            TopicVocab mit absteigend sortierten Deskriptoren/Sachgebieten.
        """
        key = _normalize_topic(topic)
        client = self._client
        owns_client = False
        if client is None:
            client = BundestagClient()
            owns_client = True
        try:
            await asyncio.sleep(RATE_LIMIT_SLEEP_S)
            try:
                response = await client.search_vorgaenge(
                    topic, rows=min(sample_size, 100)
                )
            except httpx.HTTPError as exc:
                logger.warning("Learn '%s' fehlgeschlagen: %s — cache leere Liste", topic, exc)
                vocab = TopicVocab(topic=key, learned_at=_utcnow(), sample_size=0)
                self.set(vocab)
                return vocab

            desc_counter: Counter[tuple[str, str]] = Counter()
            sach_counter: Counter[str] = Counter()

            for vorgang in response.documents:
                for desc in vorgang.deskriptor:
                    if desc.name:
                        desc_counter[(desc.name, desc.typ)] += 1
                for sach in vorgang.sachgebiet:
                    if sach:
                        sach_counter[sach] += 1

            descriptors = [
                DescriptorEntry(name=name, typ=typ, freq=freq)
                for (name, typ), freq in desc_counter.most_common()
                if freq >= min_freq
            ]
            sachgebiete = [
                SachgebietEntry(name=name, freq=freq)
                for name, freq in sach_counter.most_common()
                if freq >= min_freq
            ]

            vocab = TopicVocab(
                topic=key,
                descriptors=descriptors,
                sachgebiete=sachgebiete,
                sample_size=len(response.documents),
                learned_at=_utcnow(),
            )
            self.set(vocab)
            logger.info(
                "Learned '%s': %d descriptors, %d sachgebiete (sample=%d)",
                key,
                len(descriptors),
                len(sachgebiete),
                len(response.documents),
            )
            return vocab
        finally:
            if owns_client:
                await client.close()

    async def get_or_learn(
        self,
        topic: str,
        *,
        sample_size: int = 50,
        min_freq: int = 3,
    ) -> TopicVocab:
        """Cache-first Lookup: lernt nur wenn Miss oder Stale."""
        cached = self.get(topic)
        if cached is not None:
            return cached
        return await self.learn(topic, sample_size=sample_size, min_freq=min_freq)
