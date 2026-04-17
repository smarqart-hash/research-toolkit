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
import os
import unicodedata
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
EMPTY_CACHE_RE_LEARN_AGE = timedelta(hours=1)

# Stopwords fuer Multi-Token Keyword-Fallback (learn-Methode).
_STOPWORDS_DE: frozenset[str] = frozenset({
    "der", "die", "das", "den", "dem", "des",
    "in", "im", "am", "an", "auf", "zu", "mit", "bei", "von", "vom",
    "und", "oder", "als", "fuer", "für", "aus", "nach", "vor", "ueber", "über",
    "ein", "eine", "einen", "einem", "einer", "eines",
})
_STOPWORDS_EN: frozenset[str] = frozenset({
    "the", "of", "in", "and", "on", "for", "to", "at", "is", "are", "with",
    "a", "an", "by", "from", "as", "or", "be", "this", "that", "it",
})
# Zusatz-Stopwords fuer generische Fach-Begriffe die zu vielen Fehl-Hits fuehren wuerden.
_STOPWORDS_DOMAIN: frozenset[str] = frozenset({
    "ai", "ki", "implications", "scalability", "applications",
    "challenges", "current", "status", "general", "novel",
})
_STOPWORDS_ALL: frozenset[str] = _STOPWORDS_DE | _STOPWORDS_EN | _STOPWORDS_DOMAIN

# Mapping Umlaut -> ASCII fuer _normalize_topic.
# Wird NACH .lower() angewendet, daher nur kleinbuchstaben-Eintraege noetig.
_UMLAUT_MAP: dict[str, str] = {
    "ü": "ue", "ä": "ae", "ö": "oe", "ß": "ss",
}


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
    """Normalisiert Topic-Keys (Unicode-NFC, lowercase, stripped, umlaut-translit).

    Umlaut-Transliteration sorgt dafuer, dass "Künstliche Intelligenz" und
    "Kuenstliche Intelligenz" auf den gleichen Cache-Key gemapped werden
    (beide -> "kuenstliche intelligenz"). Verhindert Legacy-Duplikate.

    NFC-Normalisierung VOR dem Umlaut-Mapping ist kritisch: ein NFD-kodiertes
    "ü" ist `u` + U+0308 (Combining Diaeresis) und wuerde sonst als zwei
    Zeichen das _UMLAUT_MAP verfehlen. Clipboard-Input oder macOS-Dateisysteme
    liefern NFD, JSON-Parser meist NFC — die Normalisierung garantiert
    konsistentes Verhalten unabhaengig von der Quelle.
    """
    normalized = unicodedata.normalize("NFC", topic)
    lowered = normalized.strip().lower()
    for ch, repl in _UMLAUT_MAP.items():
        lowered = lowered.replace(ch, repl)
    return lowered


def _tokenize_for_fallback(topic: str) -> list[str]:
    """Zerlegt Topic in Content-Tokens fuer Keyword-Fallback.

    Pipeline: whitespace-split -> lowercase -> stopword-filter -> len>=3.
    Sortiert absteigend nach Laenge (laengste Tokens zuerst = typischerweise
    spezifischer). Gibt max 3 Tokens zurueck, um API-Calls zu begrenzen.
    """
    words = topic.replace("-", " ").replace("/", " ").split()
    content = [
        w.lower().strip(".,;:!?()[]{}\"'")
        for w in words
    ]
    content = [w for w in content if len(w) >= 3 and w not in _STOPWORDS_ALL]
    # Dedup unter Erhaltung der Reihenfolge
    seen: set[str] = set()
    unique: list[str] = []
    for w in content:
        if w not in seen:
            seen = {*seen, w}
            unique = [*unique, w]
    # Nach Laenge absteigend sortieren (immutable), max 3
    return sorted(unique, key=len, reverse=True)[:3]


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
        """Persistiert Cache nach Disk (atomic via Temp-File + os.replace).

        Verhindert dass ein Crash mittendrin den Cache korrumpiert. Bei Fehler
        bleibt der alte Cache intakt.
        """
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": CACHE_VERSION,
            "updated": _utcnow().isoformat(),
            "topics": {
                key: json.loads(tv.model_dump_json())
                for key, tv in self._topics.items()
            },
        }
        tmp_path = self._cache_path.with_suffix(self._cache_path.suffix + ".tmp")
        try:
            tmp_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            os.replace(tmp_path, self._cache_path)
        except OSError:
            # Aufraeumen wenn Temp-File liegen geblieben ist
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise
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

    async def _sample_titel(
        self,
        client: BundestagClient,
        query: str,
        sample_size: int,
    ) -> tuple[Counter[tuple[str, str]], Counter[str], int]:
        """Fuehrt einen /vorgang?f.titel=<query> Sample aus und aggregiert Counter.

        Returns:
            (desc_counter, sach_counter, n_documents). Leere Counter bei HTTP-Fehler.
        """
        desc_counter: Counter[tuple[str, str]] = Counter()
        sach_counter: Counter[str] = Counter()
        try:
            response = await client.search_vorgaenge(query, rows=min(sample_size, 100))
        except httpx.HTTPError as exc:
            logger.warning("Sample '%s' fehlgeschlagen: %s", query, exc)
            return desc_counter, sach_counter, 0

        for vorgang in response.documents:
            for desc in vorgang.deskriptor:
                if desc.name:
                    desc_counter[(desc.name, desc.typ)] += 1
            for sach in vorgang.sachgebiet:
                if sach:
                    sach_counter[sach] += 1
        return desc_counter, sach_counter, len(response.documents)

    async def learn(
        self,
        topic: str,
        *,
        sample_size: int = 50,
        min_freq: int = 3,
    ) -> TopicVocab:
        """Lernt Vokabular fuer ein Topic via /vorgang?f.titel={topic} Sampling.

        Algorithmus:
        1. Primary-Sample: ganzer Topic-String als f.titel-Query.
        2. Wenn 0 Treffer: Multi-Token-Fallback — Topic tokenisieren (stopword-filter),
           bis zu 3 laengste Content-Tokens einzeln sampeln (rows=20 je Token).
           Deskriptoren aus allen Sub-Samples aggregieren.
        3. Filter auf min_freq, sortieren, in Cache ablegen.

        Das `min_freq` wird bei kleinen Samples (< 10 Docs) automatisch auf 1 gesenkt,
        damit spaerliche Topics nicht leer persistiert werden.

        Edge-Cases:
        - 0 Treffer in Primary UND allen Fallback-Tokens → leerer Vokabular-Eintrag.
        - Keine Rekursion: Fallback laeuft genau 1x, dann Ende.
        - Rate-Limit: 1s Sleep vor jedem Request, 429-Retry durch _request() des Clients.

        Args:
            topic: Topic-String (case-insensitive, wird normalisiert).
            sample_size: Max Vorgaenge fuer Primary-Sample. API cap 100.
            min_freq: Minimale Frequenz fuer Aufnahme.

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
            # Primary-Sample: ganzer Topic-String
            await asyncio.sleep(RATE_LIMIT_SLEEP_S)
            desc_counter, sach_counter, n_primary = await self._sample_titel(
                client, topic, sample_size
            )
            total_n = n_primary
            broadened = False

            # Fallback: Multi-Token-Sampling bei 0 Treffern
            if n_primary == 0:
                tokens = _tokenize_for_fallback(topic)
                if tokens:
                    logger.info(
                        "Learn '%s': primary 0 hits, broadening via tokens %s",
                        topic, tokens,
                    )
                    broadened = True
                    for token in tokens:
                        await asyncio.sleep(RATE_LIMIT_SLEEP_S)
                        td, ts, n_token = await self._sample_titel(
                            client, token, sample_size=20
                        )
                        desc_counter.update(td)
                        sach_counter.update(ts)
                        total_n += n_token

            # Adaptive min_freq: nur bei Broadening-Branch senken.
            # Grund: Primary-Sample soll Caller-kontrolliert sein (Tests erwarten strikte
            # min_freq-Filter), aber Fallback-Samples (kleine n_token-Sub-Samples) haben
            # natuerlich wenig Wiederholung und brauchen min_freq=1.
            effective_min_freq = 1 if broadened else min_freq

            descriptors = [
                DescriptorEntry(name=name, typ=typ, freq=freq)
                for (name, typ), freq in desc_counter.most_common()
                if freq >= effective_min_freq
            ]
            sachgebiete = [
                SachgebietEntry(name=name, freq=freq)
                for name, freq in sach_counter.most_common()
                if freq >= effective_min_freq
            ]

            vocab = TopicVocab(
                topic=key,
                descriptors=descriptors,
                sachgebiete=sachgebiete,
                sample_size=total_n,
                learned_at=_utcnow(),
            )
            self.set(vocab)
            logger.info(
                "Learned '%s': %d descriptors, %d sachgebiete (sample=%d%s)",
                key,
                len(descriptors),
                len(sachgebiete),
                total_n,
                ", broadened" if broadened else "",
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
        """Cache-first Lookup: lernt nur wenn Miss, Stale oder leer-und-alt.

        Ein Cache-Eintrag mit 0 Deskriptoren blockiert nicht dauerhaft — wenn er
        aelter als EMPTY_CACHE_RE_LEARN_AGE (1h) ist, wird er neu gelernt.
        Verhindert dass einmalige Fehl-Samples (z.B. Umlaut-Bug) persistent blocken.
        """
        key = _normalize_topic(topic)
        entry = self._topics.get(key)
        if entry is not None:
            # Stale-Check (normales TTL)
            if entry.is_stale(self._stale_days):
                pass  # faellt durch zu learn()
            elif not entry.descriptors:
                # Leer-Eintrag: re-learn wenn > 1h alt, sonst zurueckgeben
                age = _utcnow() - entry.learned_at
                if age > EMPTY_CACHE_RE_LEARN_AGE:
                    logger.debug(
                        "Cache-Eintrag '%s' leer und > %s alt, re-learning",
                        key, EMPTY_CACHE_RE_LEARN_AGE,
                    )
                else:
                    return entry
            else:
                return entry
        return await self.learn(topic, sample_size=sample_size, min_freq=min_freq)
