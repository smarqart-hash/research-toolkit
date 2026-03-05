# Draft -- Venue-Aware Document Drafting

Writes structured document drafts that match a target venue's format and voice profile, with built-in self-check against quality dimensions.

## Input

```
research-toolkit draft                                        # Interactive (asks topic + venue)
research-toolkit draft --topic "AI in Public Admin" --venue policy_brief
research-toolkit draft --topic "..." --venue journal_article --search data/search/ai-admin/search.json
research-toolkit draft --topic "..." --mode detail            # Chapter-by-chapter with feedback
```

## Two Modes

### Quick (Default)
1. Ask 5-8 scoping questions (scope, focus, audience, depth)
2. Load venue profile + voice profile + search results
3. Generate chapter structure from venue profile
4. Write all chapters autonomously
5. Self-check against quality dimensions (clarity, argumentation, evidence, completeness)
6. Fix flagged findings
7. Show draft + self-check report

### Detail
Same as Quick, but step 4 happens chapter by chapter:
- Show chapter -> user gives feedback -> revise -> next chapter

## Workflow

```
1. Load venue profile (config/venue_profiles/{venue_id}.json)
2. Load voice profile (config/voice_profiles/{voice_id}.json)
3. Load search results (if --search provided)
4. Generate chapter structure (from venue sections)
5. Per chapter: write draft (voice profile as style constraint)
6. Run self-check (4 automatable quality dimensions)
7. Fix findings (CRITICAL + WARNING auto, INFO as hint)
8. Create provenance log
9. Save output: Markdown + self-check JSON + provenance JSON
```

## Self-Check Dimensions

| Dimension | Check | Automatable |
|-----------|-------|-------------|
| Clarity | Sentence length, jargon density | Yes |
| Argumentation | Structure patterns, bullet-point misuse | Yes |
| Evidence | Source citations per section | Yes |
| Completeness | Minimum length, AI disclosure | Yes |
| Originality | -- | No (human via review) |
| Methodology | -- | No (human via review) |
| Practical relevance | -- | No (human via review) |

## Voice Profile

Voice profiles (`config/voice_profiles/{voice_id}.json`) define:
- Sentence length (avg, range)
- Passive voice ratio
- Typical phrases and transitions
- Dos and don'ts
- Structure patterns (opening, body, closing)

Create custom voice profiles by analyzing existing publications from your target venue.

## Output

```
paper/draft-{topic}/draft.md           -- Markdown draft
paper/draft-{topic}/selfcheck.json     -- Self-check findings
paper/draft-{topic}/provenance.json    -- Provenance (source per section)
```

## Code Modules

| Module | Purpose |
|--------|---------|
| `src/agents/drafting.py` | Data models, self-check, voice/venue loader |
| `config/venue_profiles/` | Venue profiles (sections, recommendation format) |
| `config/voice_profiles/` | Voice profiles (writing style) |

## Tips

- Providing search results as input yields better evidence integration
- After drafting: run `review` for the 3 human-required dimensions
- After review: run `check` for citation verification

## Recommended Models

Works best with capable models (Claude Sonnet/Opus, GPT-4, or similar) for drafting and self-check. Lighter models (Claude Haiku, GPT-4o-mini) can handle individual chapter outlines or structural validation.
