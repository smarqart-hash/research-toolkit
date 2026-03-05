# Example: AI-Assisted Automated Research

A meta-example: this toolkit researching the field of automated research tools.

## Files

| File | Skill | Description |
|------|-------|-------------|
| `search_results.json` | Search | 20 top-ranked papers from Semantic Scholar (120 found, deduplicated and ranked) |
| `draft.md` | Draft | ~2900-word literature review following the `literature_review` venue profile |

## How This Was Generated

```bash
# Step 1: Search (real Semantic Scholar API data)
research-toolkit search "AI-assisted automated research tools"

# Step 2: Draft (literature review format, academic English voice)
research-toolkit draft "AI-Assisted Automated Research" \
    --venue literature_review --voice academic_en \
    --input search_results.json
```

## What Makes This Meta

The literature review examines tools and methods for automated academic research — and was itself produced by one such tool. Section 6.3 of the draft explicitly reflects on this recursive quality.