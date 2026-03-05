# Architecture

## Overview

Research Toolkit is built around four independent modules that share a common data format (Evidence Cards) and can be used standalone or chained into a pipeline.

```
Search → Draft → Review → Check
  ↓        ↑
Evidence Cards
```

## Module Independence

Each module has its own entry point and can run without the others:

- **Search** (`src/agents/forschungsstand.py`) — Orchestrates Semantic Scholar + Exa, deduplicates, ranks, generates evidence cards
- **Draft** (`src/agents/drafting.py`) — Loads venue/voice profiles, generates chapter structure, runs self-check
- **Review** (`src/agents/reviewer.py`) — Loads rubrics, evaluates across 7 dimensions, tracks issues with severity
- **Check** (`src/agents/quellen_checker.py`) — Extracts references, verifies against S2 API, reports mismatches

## Key Design Decisions

### Evidence Cards over Full Text

Papers are compressed into structured JSON extracts (claim, method, metrics, limitations, confidence). This prevents token waste in downstream LLM processing and enables systematic comparison.

### Venue/Voice Profiles as JSON Config

Publication formats and writing styles are externalized as JSON files, not hardcoded. Adding a new venue is a 20-line JSON file, not a code change.

### Provenance Tracking

Every agent action is logged to an append-only JSONL file (`provenance.jsonl`). Each entry records: timestamp, phase, agent, action, source, claim, and evidence card ID. This enables full traceability from output back to source.

### Ordinal Labels over Numeric Scores

Review dimensions use ordinal labels (strong / adequate / needs work / critical) instead of numeric scores. This matches how human reviewers think and avoids false precision.

### Two-Pass Review for Long Documents

Documents over ~3000 words are split into chapters, reviewed individually, then synthesized in a second pass. This prevents context window overflow and improves consistency.

## Data Flow

```
Input (topic/document)
    ↓
[Search] → Semantic Scholar API → Exa API
    ↓
UnifiedPaper[] → deduplicate → rank (SPECTER2)
    ↓
EvidenceCard[] → stored as JSON
    ↓
[Draft] → VenueProfile + VoiceProfile → chapter structure
    ↓
Markdown draft → self-check → fixes
    ↓
[Review] → Rubric matching → 7-dimension scoring
    ↓
ReviewReport (issues with severity + suggestions)
    ↓
[Check] → Reference extraction → S2 lookup → metadata comparison
    ↓
QuellenCheckReport (verified / not found / mismatch)
```

## File Structure

```
src/
├── agents/           # Module logic
│   ├── forschungsstand.py   # Search orchestration
│   ├── drafting.py          # Draft generation
│   ├── quellen_checker.py   # Citation verification
│   ├── reference_extractor.py  # Citation parsing (Harvard-style)
│   ├── semantic_scholar.py  # S2 API client
│   ├── exa_client.py        # Exa API client
│   ├── paper_ranker.py      # SPECTER2 ranking + deduplication
│   └── reviewer.py          # Review schemas
├── pipeline/         # Orchestration
│   ├── state.py             # State machine (6 phases, checkpoint/resume)
│   └── provenance.py        # Append-only audit log
└── utils/            # Shared utilities
    ├── evidence_card.py     # Evidence card schema
    ├── document_splitter.py # Markdown chapter splitting
    └── rubric_loader.py     # Rubric + venue matching
```