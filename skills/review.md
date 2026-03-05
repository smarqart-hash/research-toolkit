# Review -- Structured Document Review

Reviews a document draft against a venue profile and rubric, producing dimension ratings, categorized issues with severity levels, and an actionable verdict.

## Input

```
research-toolkit review paper/draft.md
research-toolkit review paper/draft.md --venue policy_brief
research-toolkit review paper/draft.md --venue journal_article --section "Methodology"
```

## Steps

### 1. Load Document
- `.md` files: read directly
- `.docx` files: convert via `pandoc "$FILE" -t markdown --wrap=none`
- Check footnote count: warn if Pandoc loses footnotes

### 2. Determine Venue + Rubric
- Load venue profile from `config/venue_profiles/{venue}.json`
- Without venue: infer from document structure (e.g., recommendations present -> policy)
- Load rubric via `config/rubrics/{rubric_id}.json`

### 3. Splitting Decision
- Under 5000 words: single-pass (entire document at once)
- Over 5000 words: two-pass architecture:
  1. Chapter reviews: review each `##` section individually
  2. Synthesis pass: only chapter summaries as input, check overall structure

### 4. Perform Review

For EACH active dimension from the rubric:

**Rate with ordinal labels (NOT numbers):**
- `strong` -- No relevant deficiencies
- `adequate` -- Minor improvements possible
- `needs work` -- Significant gaps
- `critical` -- Fundamental problems

Use the anchor examples from the rubric for consistent rating.

**Human-required dimensions:** ONLY observe and flag, do NOT rate.
Output: `{dimension, confidence: "requires_human", observation, location}`

### 5. Identify Issues

Per issue, REQUIRED fields:
- **severity**: CRITICAL / HIGH / MEDIUM / LOW (use anchor examples from rubric)
- **category**: Structure / Evidence / Logic / Context / Clarity / Format
- **location**: Chapter + paragraph (e.g., "Ch. 3, Para. 2")
- **problem**: What is wrong (1 sentence)
- **suggestion**: Concrete, actionable fix (NOT "improve this")

### 6. Delta Comparison
- Check if previous reviews exist in `data/reviews/`
- If yes: load last review, compare issue IDs
- Show: "X of Y issues resolved, Z new"

### 7. Output

**Inline:** Dimensions table, human-required flags, issues grouped by severity, verdict.
**JSON export:** `data/reviews/review-YYYYMMDD-{docname}.json`

## Verdict Logic

- `READY`: 0 CRITICAL, max 2 HIGH
- `REVISION_NEEDED`: 1+ CRITICAL or 3+ HIGH
- `MAJOR_REWORK`: 3+ CRITICAL

## Rules

Do NOT rewrite -- only rate and suggest. Every issue needs a precise location and an actionable suggestion. If venue is missing: ASK, do not guess.

## Recommended Models

Review benefits from capable reasoning models. Use Claude Opus/Sonnet or GPT-4 for the main review pass. Lighter models (Claude Haiku, GPT-4o-mini) can handle structural checks and the splitting decision.
