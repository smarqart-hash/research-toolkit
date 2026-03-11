"""Claim Verification — prueft ob zitierte Claims inhaltlich korrekt sind.

FactScore-Pattern: LLM extrahiert atomare Claims, dann NLI-Prompt
prueft jeden Claim gegen Paper-Abstract.
Labels: SUPPORTS / REFUTES / NOT_ENOUGH_INFO / NO_ABSTRACT.
"""

from __future__ import annotations

import json
import logging
import re
from enum import Enum

import httpx

from pydantic import BaseModel, Field, computed_field

logger = logging.getLogger(__name__)


class VerificationLabel(str, Enum):
    """NLI-Label fuer Claim-Verification."""

    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    NOT_ENOUGH_INFO = "NOT_ENOUGH_INFO"
    NO_ABSTRACT = "NO_ABSTRACT"


class AtomicClaim(BaseModel):
    """Ein atomarer Claim aus dem Draft."""

    claim: str
    cited_paper_id: str
    source_sentence: str


class ClaimVerification(BaseModel):
    """Ergebnis der Verification eines Claims."""

    claim: AtomicClaim
    label: VerificationLabel
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
    abstract_used: str | None = None


class VerificationReport(BaseModel):
    """Gesamtbericht der Claim Verification."""

    document: str
    claims: list[ClaimVerification] = Field(default_factory=list)

    @computed_field
    @property
    def total_claims(self) -> int:
        return len(self.claims)

    @computed_field
    @property
    def supports_count(self) -> int:
        return sum(1 for c in self.claims if c.label == VerificationLabel.SUPPORTS)

    @computed_field
    @property
    def refutes_count(self) -> int:
        return sum(1 for c in self.claims if c.label == VerificationLabel.REFUTES)

    @computed_field
    @property
    def nei_count(self) -> int:
        return sum(1 for c in self.claims if c.label == VerificationLabel.NOT_ENOUGH_INFO)

    @computed_field
    @property
    def no_abstract_count(self) -> int:
        return sum(1 for c in self.claims if c.label == VerificationLabel.NO_ABSTRACT)


# --- Claim Extraction ---

from src.utils.llm_client import LLMConfig, llm_complete, load_llm_config

_MAX_SECTION_CHARS = 12_000  # ~3K Tokens — sicher unter Context-Limit
_EXTRACTION_MAX_TOKENS = 2048  # Extraction-Response braucht mehr als Default 1024

_EXTRACTION_SYSTEM_PROMPT = """\
Du bist ein wissenschaftlicher Claim-Analyst. Extrahiere alle atomaren \
faktuellen Claims aus dem Text die sich auf zitierte Papers beziehen.

Antworte AUSSCHLIESSLICH als JSON:
{
  "claims": [
    {
      "claim": "Der atomare Claim (eine pruefbare Aussage)",
      "cited_paper_id": "Paper-ID aus der Liste",
      "source_sentence": "Der Originalsatz aus dem Text"
    }
  ]
}

REGELN:
- Nur Claims die sich auf ein konkretes Paper beziehen
- Nur faktuell pruefbare Aussagen (keine Meinungen, keine Bewertungen)
- Ein Claim pro Eintrag (atomarisieren!)
- cited_paper_id MUSS aus der gegebenen Paper-Liste stammen
- Keine Markdown-Formatierung, nur reines JSON"""


def _split_draft_sections(draft_md: str) -> list[str]:
    """Splittet Draft an Markdown-Headings (## ...) fuer Batched Extraction.

    Kurze Drafts (<= _MAX_SECTION_CHARS) werden als einzelne Sektion zurueckgegeben.
    """
    if len(draft_md) <= _MAX_SECTION_CHARS:
        return [draft_md]

    parts = re.split(r"(?=^## )", draft_md, flags=re.MULTILINE)
    sections: list[str] = [p.strip() for p in parts if p.strip()]

    if not sections:
        return [draft_md]

    # Zu kurze Sektionen zusammenfassen
    merged: list[str] = []
    current = ""
    for section in sections:
        if current and len(current) + len(section) > _MAX_SECTION_CHARS:
            merged = [*merged, current]
            current = section
        else:
            current = f"{current}\n\n{section}" if current else section
    if current:
        merged = [*merged, current]

    return merged if merged else [draft_md]


def _build_extraction_prompt(draft_md: str, paper_map: dict[str, str]) -> str:
    """Baut User-Message fuer Claim-Extraktion."""
    papers_list = "\n".join(f"- {pid}: {title}" for pid, title in paper_map.items())
    return f"Paper-IDs:\n{papers_list}\n\n---\n\nText:\n{draft_md}"


def _parse_extraction_response(raw: str, valid_ids: set[str]) -> list[AtomicClaim]:
    """Parst LLM-Antwort in AtomicClaim-Liste."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Claim-Extraction-JSON nicht parsbar: %s", raw[:80])
        return []

    result: list[AtomicClaim] = []
    for item in data.get("claims", []):
        pid = item.get("cited_paper_id", "")
        if pid not in valid_ids:
            continue
        result = [
            *result,
            AtomicClaim(
                claim=item.get("claim", ""),
                cited_paper_id=pid,
                source_sentence=item.get("source_sentence", ""),
            ),
        ]
    return result


async def extract_claims(
    draft_md: str,
    paper_map: dict[str, str],
    *,
    config: LLMConfig | None = None,
) -> list[AtomicClaim]:
    """Extrahiert atomare Claims aus Draft via LLM.

    Grosse Drafts werden an Markdown-Headings gesplittet
    und in Sektionen verarbeitet (je ein LLM-Call).

    Args:
        draft_md: Draft-Text (Markdown).
        paper_map: Dict von paper_id -> Titel (bekannte Papers).
        config: LLM-Konfiguration.

    Returns:
        Liste atomarer Claims.
    """
    if not paper_map:
        return []

    llm_config = config or load_llm_config()
    # Extraction braucht mehr Tokens als Default
    extraction_config = llm_config.model_copy(update={"max_tokens": _EXTRACTION_MAX_TOKENS})

    sections = _split_draft_sections(draft_md)
    valid_ids = set(paper_map.keys())
    all_claims: list[AtomicClaim] = []

    for section in sections:
        try:
            user_msg = _build_extraction_prompt(section, paper_map)
            raw = await llm_complete(
                _EXTRACTION_SYSTEM_PROMPT, user_msg, config=extraction_config
            )
            claims = _parse_extraction_response(raw, valid_ids)
            all_claims = [*all_claims, *claims]
        except (RuntimeError, httpx.HTTPError, json.JSONDecodeError, OSError) as e:
            logger.warning("Claim-Extraktion fehlgeschlagen fuer Sektion: %s", e)

    return all_claims


# --- Claim Verification (NLI) ---

_VERIFY_BATCH_SIZE = 5

_VERIFY_SYSTEM_PROMPT = """\
Du bist ein wissenschaftlicher Fakten-Pruefer. Pruefe ob der gegebene Abstract \
die Claims stuetzt, widerlegt, oder nicht genug Information enthaelt.

Antworte AUSSCHLIESSLICH als JSON:
{
  "verifications": [
    {
      "claim_index": 0,
      "label": "SUPPORTS|REFUTES|NOT_ENOUGH_INFO",
      "confidence": 0.0-1.0,
      "reasoning": "Kurze Begruendung"
    }
  ]
}

Labels:
- SUPPORTS: Abstract bestaetigt den Claim direkt oder implizit
- REFUTES: Abstract widerspricht dem Claim
- NOT_ENOUGH_INFO: Abstract behandelt das Thema nicht oder ist unklar

Keine Markdown-Formatierung, nur reines JSON."""


def _build_verify_prompt(
    claims: list[AtomicClaim],
    abstracts: dict[str, str],
) -> str:
    """Baut User-Message fuer Claim-Verification."""
    lines: list[str] = []
    for i, claim in enumerate(claims):
        abstract = abstracts.get(claim.cited_paper_id, "")
        lines = [
            *lines,
            f"--- Claim {i} ---",
            f"Claim: {claim.claim}",
            f"Abstract: {abstract}",
            "",
        ]
    return "\n".join(lines)


def _parse_verify_response(
    raw: str,
    claims: list[AtomicClaim],
    abstracts: dict[str, str],
) -> list[ClaimVerification]:
    """Parst LLM-NLI-Antwort in ClaimVerification-Liste."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Verify-JSON nicht parsbar: %s", raw[:80])
        return [
            ClaimVerification(
                claim=c,
                label=VerificationLabel.NOT_ENOUGH_INFO,
                confidence=0.0,
                reasoning="JSON-Parse-Fehler",
                abstract_used=abstracts.get(c.cited_paper_id),
            )
            for c in claims
        ]

    result: list[ClaimVerification] = []
    verified_indices: set[int] = set()
    for item in data.get("verifications", []):
        idx = item.get("claim_index", -1)
        if idx < 0 or idx >= len(claims):
            continue
        label_str = item.get("label", "NOT_ENOUGH_INFO").upper()
        if label_str not in ("SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO"):
            label_str = "NOT_ENOUGH_INFO"
        confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
        claim = claims[idx]
        result = [
            *result,
            ClaimVerification(
                claim=claim,
                label=VerificationLabel(label_str),
                confidence=confidence,
                reasoning=item.get("reasoning", ""),
                abstract_used=abstracts.get(claim.cited_paper_id),
            ),
        ]
        verified_indices.add(idx)

    # Claims ohne LLM-Antwort als NOT_ENOUGH_INFO
    for i, claim in enumerate(claims):
        if i not in verified_indices:
            result = [
                *result,
                ClaimVerification(
                    claim=claim,
                    label=VerificationLabel.NOT_ENOUGH_INFO,
                    confidence=0.0,
                    reasoning="Keine LLM-Antwort fuer diesen Claim",
                    abstract_used=abstracts.get(claim.cited_paper_id),
                ),
            ]

    return result


async def verify_claims(
    claims: list[AtomicClaim],
    abstracts: dict[str, str],
    *,
    config: LLMConfig | None = None,
) -> list[ClaimVerification]:
    """Verifiziert Claims gegen Paper-Abstracts via LLM-NLI.

    Claims ohne verfuegbaren Abstract bekommen NO_ABSTRACT.
    Restliche Claims werden in Batches an LLM geschickt.
    """
    if not claims:
        return []

    llm_config = config or load_llm_config()

    # Phase 1: Claims ohne Abstract sofort als NO_ABSTRACT markieren
    to_verify: list[AtomicClaim] = []
    no_abstract_results: list[ClaimVerification] = []
    for claim in claims:
        if claim.cited_paper_id not in abstracts or not abstracts[claim.cited_paper_id]:
            no_abstract_results = [
                *no_abstract_results,
                ClaimVerification(
                    claim=claim,
                    label=VerificationLabel.NO_ABSTRACT,
                    confidence=0.0,
                    reasoning="Kein Abstract verfuegbar",
                ),
            ]
        else:
            to_verify = [*to_verify, claim]

    if not to_verify:
        return no_abstract_results

    # Phase 2: Batched LLM-Verification
    all_verified: list[ClaimVerification] = []
    for i in range(0, len(to_verify), _VERIFY_BATCH_SIZE):
        batch = to_verify[i : i + _VERIFY_BATCH_SIZE]
        try:
            user_msg = _build_verify_prompt(batch, abstracts)
            raw = await llm_complete(_VERIFY_SYSTEM_PROMPT, user_msg, config=llm_config)
            verified = _parse_verify_response(raw, batch, abstracts)
            all_verified = [*all_verified, *verified]
        except (RuntimeError, httpx.HTTPError, json.JSONDecodeError, OSError) as e:
            logger.warning("Verify-Batch-Fehler: %s", e)
            all_verified = [
                *all_verified,
                *[
                    ClaimVerification(
                        claim=claim,
                        label=VerificationLabel.NOT_ENOUGH_INFO,
                        confidence=0.0,
                        reasoning=f"LLM-Fehler: {e}",
                        abstract_used=abstracts.get(claim.cited_paper_id),
                    )
                    for claim in batch
                ],
            ]

    return [*no_abstract_results, *all_verified]


# --- Report Formatting ---


def format_verification_report(report: VerificationReport) -> str:
    """Formatiert VerificationReport als Markdown."""
    lines: list[str] = [
        f"## Claim Verification: {report.document}",
        "",
        f"**{report.total_claims} Claims** geprueft: "
        f"{report.supports_count} bestaetigt, "
        f"{report.refutes_count} widerlegt, "
        f"{report.nei_count} unklar, "
        f"{report.no_abstract_count} ohne Abstract",
        "",
    ]

    # Probleme zuerst (REFUTES)
    refuted = [c for c in report.claims if c.label == VerificationLabel.REFUTES]
    if refuted:
        lines = [*lines, "### Widerlegte Claims", ""]
        for cv in refuted:
            lines = [
                *lines,
                f"- **{cv.claim.claim}**",
                f"  Paper: {cv.claim.cited_paper_id} | Confidence: {cv.confidence:.0%}",
                f"  Begruendung: {cv.reasoning}",
                "",
            ]

    # NOT_ENOUGH_INFO
    nei = [c for c in report.claims if c.label == VerificationLabel.NOT_ENOUGH_INFO]
    if nei:
        lines = [*lines, "### Unklare Claims", ""]
        for cv in nei:
            lines = [
                *lines,
                f"- **{cv.claim.claim}**",
                f"  Paper: {cv.claim.cited_paper_id} | Confidence: {cv.confidence:.0%}",
                "",
            ]

    # SUPPORTS (kompakt)
    supported = [c for c in report.claims if c.label == VerificationLabel.SUPPORTS]
    if supported:
        lines = [*lines, "### Bestaetigte Claims", ""]
        for cv in supported:
            lines = [*lines, f"- {cv.claim.claim} (Paper: {cv.claim.cited_paper_id})"]

    lines = [*lines, ""]
    return "\n".join(lines)


# --- Orchestration ---


async def run_verification(
    draft_md: str,
    paper_map: dict[str, str],
    abstracts: dict[str, str],
    *,
    document_name: str = "unknown",
    config: LLMConfig | None = None,
) -> VerificationReport:
    """Orchestriert Claim-Extraktion und -Verification.

    Args:
        draft_md: Draft-Text.
        paper_map: Dict paper_id -> Titel.
        abstracts: Dict paper_id -> Abstract-Text.
        document_name: Name des Dokuments fuer Report.
        config: LLM-Konfiguration.

    Returns:
        VerificationReport.
    """
    llm_config = config or load_llm_config()

    # Phase 1: Claims extrahieren
    claims = await extract_claims(draft_md, paper_map, config=llm_config)
    if not claims:
        return VerificationReport(document=document_name)

    # Phase 2: Claims verifizieren
    verifications = await verify_claims(claims, abstracts, config=llm_config)

    return VerificationReport(document=document_name, claims=verifications)
