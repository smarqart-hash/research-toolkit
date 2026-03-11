# Claim Verification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Erweitert den Check-Skill um LLM-basierte Claim Verification — prueft ob zitierte Claims inhaltlich korrekt sind (nicht nur ob Quellen existieren).

**Architecture:** FactScore-Pattern: LLM extrahiert atomare Claims aus Draft, dann NLI-Prompt prueft jeden Claim gegen Paper-Abstract. Pipeline: `extract_claims()` → `verify_claims()` → `VerificationReport`. Integriert in bestehenden `check`-Command via `--verify` Flag.

**Tech Stack:** Python 3.11+, Pydantic v2, httpx (async), bestehender `llm_client.py` (OpenRouter/Gemini Flash)

---

## Kontext

### Bestehende Dateien (lesen vor Implementation)
- `src/agents/quellen_checker.py` — Bestehender Check-Skill (Quellen-Existenz)
- `src/agents/reference_extractor.py` — Referenz-Extraktion aus Drafts
- `src/utils/llm_client.py` — LLM-Client (llm_complete, LLMConfig)
- `src/utils/evidence_card.py` — EvidenceCard Schema
- `src/agents/ranking_judge.py` — Referenz fuer LLM-JSON-Parsing Pattern
- `cli.py:282-343` — Bestehender `check`-Command

### Konventionen
- `from __future__ import annotations` in jeder Datei
- Immutability: `[*list, item]` statt `.append()`
- German Docstrings, English Code
- Error Handling: `try/except` mit `logger.warning()`
- Pydantic v2 BaseModel fuer alle Datenstrukturen
- JSON-Parsing: Markdown-Wrapper (```` ```json ... ``` ````) immer strippen

---

## Task 1: Datenmodelle

**Files:**
- Create: `src/agents/claim_verifier.py`
- Create: `tests/test_claim_verifier.py`

**Step 1: Write failing tests for models**

```python
"""Tests fuer Claim Verification (Sprint N)."""

from __future__ import annotations

import pytest

from src.agents.claim_verifier import (
    AtomicClaim,
    ClaimVerification,
    VerificationLabel,
    VerificationReport,
)


class TestAtomicClaim:
    def test_fields(self):
        claim = AtomicClaim(
            claim="X steigert Performance um 15%",
            cited_paper_id="10.1234/test",
            source_sentence="Smith (2024) zeigt, dass X die Performance um 15% steigert.",
        )
        assert claim.claim == "X steigert Performance um 15%"
        assert claim.cited_paper_id == "10.1234/test"

    def test_minimal(self):
        claim = AtomicClaim(claim="Test", cited_paper_id="p1", source_sentence="Test.")
        assert claim.claim == "Test"


class TestVerificationLabel:
    def test_all_labels(self):
        assert VerificationLabel.SUPPORTS == "SUPPORTS"
        assert VerificationLabel.REFUTES == "REFUTES"
        assert VerificationLabel.NOT_ENOUGH_INFO == "NOT_ENOUGH_INFO"
        assert VerificationLabel.NO_ABSTRACT == "NO_ABSTRACT"


class TestClaimVerification:
    def test_fields(self):
        cv = ClaimVerification(
            claim=AtomicClaim(claim="X", cited_paper_id="p1", source_sentence="S"),
            label=VerificationLabel.SUPPORTS,
            confidence=0.85,
            reasoning="Abstract bestaetigt den Claim",
            abstract_used="Ein Abstract...",
        )
        assert cv.label == VerificationLabel.SUPPORTS
        assert cv.confidence == 0.85

    def test_no_abstract(self):
        cv = ClaimVerification(
            claim=AtomicClaim(claim="X", cited_paper_id="p1", source_sentence="S"),
            label=VerificationLabel.NO_ABSTRACT,
            confidence=0.0,
            reasoning="Kein Abstract verfuegbar",
        )
        assert cv.abstract_used is None


class TestVerificationReport:
    def test_computed_stats(self):
        claims = [
            ClaimVerification(
                claim=AtomicClaim(claim="A", cited_paper_id="p1", source_sentence="S"),
                label=VerificationLabel.SUPPORTS, confidence=0.9, reasoning="",
            ),
            ClaimVerification(
                claim=AtomicClaim(claim="B", cited_paper_id="p2", source_sentence="S"),
                label=VerificationLabel.REFUTES, confidence=0.8, reasoning="",
            ),
            ClaimVerification(
                claim=AtomicClaim(claim="C", cited_paper_id="p3", source_sentence="S"),
                label=VerificationLabel.NOT_ENOUGH_INFO, confidence=0.5, reasoning="",
            ),
            ClaimVerification(
                claim=AtomicClaim(claim="D", cited_paper_id="p4", source_sentence="S"),
                label=VerificationLabel.NO_ABSTRACT, confidence=0.0, reasoning="",
            ),
        ]
        report = VerificationReport(document="test.md", claims=claims)
        assert report.supports_count == 1
        assert report.refutes_count == 1
        assert report.nei_count == 1
        assert report.no_abstract_count == 1
        assert report.total_claims == 4
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_claim_verifier.py -v`
Expected: `ModuleNotFoundError: No module named 'src.agents.claim_verifier'`

**Step 3: Write minimal implementation**

```python
"""Claim Verification — prueft ob zitierte Claims inhaltlich korrekt sind.

FactScore-Pattern: LLM extrahiert atomare Claims, dann NLI-Prompt
prueft jeden Claim gegen Paper-Abstract.
Labels: SUPPORTS / REFUTES / NOT_ENOUGH_INFO / NO_ABSTRACT.
"""

from __future__ import annotations

import json
import logging
from enum import Enum

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
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_claim_verifier.py -v`
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add src/agents/claim_verifier.py tests/test_claim_verifier.py
git commit -m "feat: add claim verification data models (Task 1)"
```

---

## Task 2: Claim Extraction (LLM)

**Files:**
- Modify: `src/agents/claim_verifier.py`
- Modify: `tests/test_claim_verifier.py`

**Step 1: Write failing tests for extraction**

```python
import json
from unittest.mock import AsyncMock, patch
from src.agents.claim_verifier import (
    AtomicClaim,
    _build_extraction_prompt,
    _parse_extraction_response,
    extract_claims,
)
from src.utils.llm_client import LLMConfig


def _llm_config() -> LLMConfig:
    return LLMConfig(api_key="test-key", model="test-model")


class TestBuildExtractionPrompt:
    def test_contains_draft(self):
        prompt = _build_extraction_prompt("Ein Draft mit Claims.", {"p1": "Paper A"})
        assert "Ein Draft mit Claims." in prompt

    def test_contains_paper_ids(self):
        prompt = _build_extraction_prompt("Draft.", {"p1": "Paper A", "p2": "Paper B"})
        assert "p1" in prompt
        assert "Paper A" in prompt


class TestParseExtractionResponse:
    def test_valid_json(self):
        response = json.dumps({
            "claims": [
                {
                    "claim": "X steigert Y um 15%",
                    "cited_paper_id": "p1",
                    "source_sentence": "Smith (2024) zeigt dass X Y um 15% steigert.",
                },
            ]
        })
        result = _parse_extraction_response(response, {"p1"})
        assert len(result) == 1
        assert result[0].claim == "X steigert Y um 15%"

    def test_markdown_wrapper(self):
        inner = json.dumps({"claims": [
            {"claim": "A", "cited_paper_id": "p1", "source_sentence": "S"}
        ]})
        response = f"```json\n{inner}\n```"
        result = _parse_extraction_response(response, {"p1"})
        assert len(result) == 1

    def test_invalid_json_returns_empty(self):
        result = _parse_extraction_response("kein json", {"p1"})
        assert result == []

    def test_unknown_paper_id_skipped(self):
        response = json.dumps({
            "claims": [
                {"claim": "A", "cited_paper_id": "unknown", "source_sentence": "S"},
            ]
        })
        result = _parse_extraction_response(response, {"p1"})
        assert result == []


class TestExtractClaims:
    @pytest.mark.asyncio
    async def test_basic_flow(self):
        llm_response = json.dumps({
            "claims": [
                {"claim": "X ist besser", "cited_paper_id": "p1", "source_sentence": "Laut S."},
            ]
        })
        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            mock.return_value = llm_response
            result = await extract_claims("Draft text.", {"p1": "Paper A"}, config=config)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty(self):
        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            mock.side_effect = RuntimeError("API down")
            result = await extract_claims("Draft.", {"p1": "A"}, config=config)
        assert result == []
```

**Step 2: Run to verify fail**

Run: `pytest tests/test_claim_verifier.py::TestBuildExtractionPrompt -v`
Expected: `ImportError` (Funktionen existieren noch nicht)

**Step 3: Implement extraction**

Add to `claim_verifier.py`:

```python
from src.utils.llm_client import LLMConfig, llm_complete, load_llm_config

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

    try:
        user_msg = _build_extraction_prompt(draft_md, paper_map)
        raw = await llm_complete(_EXTRACTION_SYSTEM_PROMPT, user_msg, config=llm_config)
        return _parse_extraction_response(raw, set(paper_map.keys()))
    except Exception as e:
        logger.warning("Claim-Extraktion fehlgeschlagen: %s", e)
        return []
```

**Step 4: Run tests**

Run: `pytest tests/test_claim_verifier.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/agents/claim_verifier.py tests/test_claim_verifier.py
git commit -m "feat: add LLM-based atomic claim extraction (Task 2)"
```

---

## Task 3: Claim Verification (NLI)

**Files:**
- Modify: `src/agents/claim_verifier.py`
- Modify: `tests/test_claim_verifier.py`

**Step 1: Write failing tests for verification**

```python
class TestVerifyClaims:
    @pytest.mark.asyncio
    async def test_supports(self):
        claims = [AtomicClaim(claim="X ist effektiv", cited_paper_id="p1", source_sentence="S")]
        abstracts = {"p1": "Unsere Studie zeigt dass X effektiv ist."}
        llm_response = json.dumps({
            "verifications": [
                {"claim_index": 0, "label": "SUPPORTS", "confidence": 0.9, "reasoning": "Bestaetigt"}
            ]
        })
        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            mock.return_value = llm_response
            result = await verify_claims(claims, abstracts, config=config)
        assert len(result) == 1
        assert result[0].label == VerificationLabel.SUPPORTS
        assert result[0].abstract_used == "Unsere Studie zeigt dass X effektiv ist."

    @pytest.mark.asyncio
    async def test_no_abstract(self):
        """Paper ohne Abstract → NO_ABSTRACT Label, kein LLM-Call."""
        claims = [AtomicClaim(claim="X", cited_paper_id="p1", source_sentence="S")]
        abstracts = {}  # Kein Abstract fuer p1
        config = _llm_config()
        result = await verify_claims(claims, abstracts, config=config)
        assert len(result) == 1
        assert result[0].label == VerificationLabel.NO_ABSTRACT

    @pytest.mark.asyncio
    async def test_batching(self):
        """Claims werden in Batches von 5 verarbeitet."""
        claims = [
            AtomicClaim(claim=f"Claim {i}", cited_paper_id="p1", source_sentence="S")
            for i in range(8)
        ]
        abstracts = {"p1": "Abstract."}
        batch1 = json.dumps({"verifications": [
            {"claim_index": i, "label": "SUPPORTS", "confidence": 0.8, "reasoning": ""}
            for i in range(5)
        ]})
        batch2 = json.dumps({"verifications": [
            {"claim_index": i, "label": "SUPPORTS", "confidence": 0.8, "reasoning": ""}
            for i in range(3)
        ]})
        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            mock.side_effect = [batch1, batch2]
            result = await verify_claims(claims, abstracts, config=config)
        assert mock.call_count == 2
        assert len(result) == 8

    @pytest.mark.asyncio
    async def test_llm_error_graceful(self):
        claims = [AtomicClaim(claim="X", cited_paper_id="p1", source_sentence="S")]
        abstracts = {"p1": "Abstract."}
        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            mock.side_effect = RuntimeError("API")
            result = await verify_claims(claims, abstracts, config=config)
        assert len(result) == 1
        assert result[0].label == VerificationLabel.NOT_ENOUGH_INFO
```

**Step 2: Run to verify fail**

**Step 3: Implement verification**

Add to `claim_verifier.py`:

```python
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
        # Fallback: alle als NOT_ENOUGH_INFO
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
        except Exception as e:
            logger.warning("Verify-Batch-Fehler: %s", e)
            for claim in batch:
                all_verified = [
                    *all_verified,
                    ClaimVerification(
                        claim=claim,
                        label=VerificationLabel.NOT_ENOUGH_INFO,
                        confidence=0.0,
                        reasoning=f"LLM-Fehler: {e}",
                        abstract_used=abstracts.get(claim.cited_paper_id),
                    ),
                ]

    return [*no_abstract_results, *all_verified]
```

**Step 4: Run tests**

Run: `pytest tests/test_claim_verifier.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/agents/claim_verifier.py tests/test_claim_verifier.py
git commit -m "feat: add LLM-based claim verification / NLI (Task 3)"
```

---

## Task 4: Report + Markdown Output

**Files:**
- Modify: `src/agents/claim_verifier.py`
- Modify: `tests/test_claim_verifier.py`

**Step 1: Write failing tests**

```python
class TestFormatVerificationReport:
    def test_basic_markdown(self):
        from src.agents.claim_verifier import format_verification_report
        report = VerificationReport(
            document="test.md",
            claims=[
                ClaimVerification(
                    claim=AtomicClaim(claim="X ist gut", cited_paper_id="p1", source_sentence="S"),
                    label=VerificationLabel.SUPPORTS, confidence=0.9, reasoning="Bestaetigt",
                ),
                ClaimVerification(
                    claim=AtomicClaim(claim="Y ist schlecht", cited_paper_id="p2", source_sentence="S"),
                    label=VerificationLabel.REFUTES, confidence=0.8, reasoning="Widerlegt",
                ),
            ],
        )
        md = format_verification_report(report)
        assert "test.md" in md
        assert "SUPPORTS" in md or "Bestaetigt" in md
        assert "REFUTES" in md or "Widerlegt" in md
        assert "1" in md  # supports count
        assert "2" in md  # total claims

    def test_empty_report(self):
        from src.agents.claim_verifier import format_verification_report
        report = VerificationReport(document="test.md")
        md = format_verification_report(report)
        assert "0" in md  # 0 claims
```

**Step 2: Run to verify fail**

**Step 3: Implement**

Add to `claim_verifier.py`:

```python
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
```

**Step 4: Run tests**

**Step 5: Commit**

```bash
git add src/agents/claim_verifier.py tests/test_claim_verifier.py
git commit -m "feat: add verification report markdown formatting (Task 4)"
```

---

## Task 5: CLI Integration (`--verify` Flag)

**Files:**
- Modify: `cli.py:282-343`
- Modify: `tests/test_claim_verifier.py`

**Step 1: Write failing test for CLI integration**

```python
class TestRunVerification:
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """End-to-End: Draft → Extract Claims → Verify → Report."""
        from src.agents.claim_verifier import run_verification

        draft = "Smith (2024) zeigt dass X die Performance um 15% steigert."
        abstracts = {"p1": "Wir zeigen dass X Performance um 15% verbessert."}
        paper_map = {"p1": "Smith et al. 2024"}

        extract_response = json.dumps({"claims": [
            {"claim": "X steigert Performance um 15%", "cited_paper_id": "p1",
             "source_sentence": "Smith (2024) zeigt dass X die Performance um 15% steigert."}
        ]})
        verify_response = json.dumps({"verifications": [
            {"claim_index": 0, "label": "SUPPORTS", "confidence": 0.9, "reasoning": "Bestaetigt"}
        ]})

        config = _llm_config()
        with patch("src.agents.claim_verifier.llm_complete", new_callable=AsyncMock) as mock:
            mock.side_effect = [extract_response, verify_response]
            report = await run_verification(
                draft_md=draft,
                paper_map=paper_map,
                abstracts=abstracts,
                document_name="test.md",
                config=config,
            )

        assert report.total_claims == 1
        assert report.supports_count == 1
```

**Step 2: Run to verify fail**

**Step 3: Implement orchestration**

Add to `claim_verifier.py`:

```python
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
```

**Step 4: Modify CLI** — Add `--verify` flag to `check` command in `cli.py`:

Add parameter:
```python
verify: bool = typer.Option(
    False, "--verify", help="Verify claims against paper abstracts (requires LLM_API_KEY)"
),
```

After existing reference check, add verification block:
```python
if verify:
    from src.agents.claim_verifier import run_verification, format_verification_report
    # ... load abstracts from forschungsstand.json, run verification
    console.print(format_verification_report(report))
```

**Step 5: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/agents/claim_verifier.py tests/test_claim_verifier.py cli.py
git commit -m "feat: integrate claim verification into check command (--verify)"
```

---

## Summary

| Task | Tests | Dateien |
|------|-------|---------|
| 1: Datenmodelle | 8 | claim_verifier.py, test_claim_verifier.py |
| 2: Claim-Extraktion | 7 | claim_verifier.py |
| 3: Claim-Verification | 4 | claim_verifier.py |
| 4: Report-Formatting | 2 | claim_verifier.py |
| 5: CLI-Integration | 1 | claim_verifier.py, cli.py |
| **Total** | **~22** | **2 neue, 1 modifiziert** |

**Nach Implementation:** Adversarial Review dispatchen.
