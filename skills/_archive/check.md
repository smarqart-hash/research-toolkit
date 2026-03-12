# Check -- Citation Verification

Verifies references in a document against Semantic Scholar, checking existence, metadata accuracy, and optionally whether citations are used in the correct context.

## Input

```
research-toolkit check paper/draft.md
research-toolkit check paper/draft.md --context                # with context verification
research-toolkit check paper/draft.md --search data/search/search.json   # local lookup first
```

## Workflow

```
1. Load document (.docx -> Markdown via Pandoc)
2. Extract references (regex: inline citations + bibliography)
3. Merge: enrich inline citations with bibliography entries (title)
4. Unrecognized passages -> LLM fallback (identify missing references)
5. Local lookup against search.json (if provided)
6. API lookup via Semantic Scholar for non-local references
7. Metadata comparison (year, author, title)
8. Optional --context: check if citation is used in correct context
9. Generate report: Markdown + JSON
```

## Status Types

| Status | Icon | Meaning |
|--------|------|---------|
| VERIFIED | check | Source exists, metadata correct |
| NOT_FOUND | x | Source not findable |
| METADATA_MISMATCH | warning | Source exists, but discrepancies found |
| CONTEXT_MISMATCH | info | Source does not match its usage context (--context only) |

## LLM Fallback (Step 4)

After regex extraction, read the document and identify:
- Claims without source attribution ("X reduces Y by 30%")
- Informal references ("according to a recent study")
- Unrecognized citation formats

Create a ReferenceCandidate with `source_type="llm"` for each missing reference.

## Context Check (--context, Step 8)

For each VERIFIED / METADATA_MISMATCH entry:
- Read the paragraph around the citation
- Read the abstract of the found paper
- Check: is the paper accurately represented?
- On mismatch: status -> CONTEXT_MISMATCH with explanation

## Output

### Inline (Chat)
Summary + problem list with status icons.

### JSON
`data/check/check.json` -- machine-readable report for review integration.

## Code Modules

| Module | Purpose |
|--------|---------|
| `src/agents/reference_extractor.py` | Regex extraction (citation patterns) |
| `src/agents/quellen_checker.py` | Lookup + metadata comparison + report |
| `src/agents/semantic_scholar.py` | API client (retry on 429) |

## API Keys

Same keys as `search` -- see `.env.example`.
`S2_API_KEY` recommended for stable access.

## Recommended Models

Citation verification works best with capable models (Claude Sonnet/Opus, GPT-4, or similar) for the LLM fallback and context check steps. Lighter models (Claude Haiku, GPT-4o-mini) can handle the regex extraction and metadata comparison.
