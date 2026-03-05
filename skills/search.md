# Search -- Literature Search & Evidence Extraction

Systematically searches academic databases, deduplicates and ranks results, clusters them by theme, and produces a structured literature overview with evidence cards.

## Input Modes

1. **Freetext**: `research-toolkit search "AI-based traffic control"`
2. **With questions**: `research-toolkit search --topic "AI traffic" --questions "Which DRL approaches exist?" "How does it scale?"`
3. **Paper list**: `research-toolkit search --papers doi:10.1234/... arxiv:2301.12345`

## Workflow

```
1. Parse input -> topic + guiding questions + optional paper IDs
2. Generate search queries (generate_search_queries)
3. Search Semantic Scholar (primary source)
4. Search Exa (if EXA_API_KEY is set)
5. Deduplicate (DOI > title hash)
6. Rank (citations, recency, open access)
7. Cluster top-K papers thematically (via LLM)
8. Extract evidence cards (key claims per paper)
9. Generate literature overview markdown (3-5 pages)
10. Output: Markdown + JSON + evidence cards
```

## Clustering (Step 7)

Cluster top-K papers into 3-6 thematic groups:
- Read abstract + title of each paper
- Identify shared themes/methods
- Create ThemeCluster with: theme, description, key_findings, open_questions
- Sort clusters by relevance to the main topic

## Output

### Markdown (Chapter Draft)
- Directly usable as "State of Research" chapter
- 3-5 pages, structured by theme clusters (each cluster = subsection)
- Source list at the end

### JSON (Machine-Readable)
- `data/search/{topic-slug}/search.json`
- Contains: clusters, papers, evidence_cards, statistics

### Evidence Cards
- `data/search/{topic-slug}/evidence_cards/`
- 1-3 cards per paper with key claims
- Schema: see `src/utils/evidence_card.py`

## API Keys

| Key | Env Variable | Cost | Sign Up |
|-----|-------------|------|---------|
| Semantic Scholar | `S2_API_KEY` | Free | https://www.semanticscholar.org/product/api#api-key-form |
| Exa | `EXA_API_KEY` | 1000 req/month free | https://dashboard.exa.ai |

**Without S2_API_KEY:** Strict rate limits (shared pool), 429 errors likely.
**Without EXA_API_KEY:** Exa is skipped, Semantic Scholar only.
Set keys in `.env` (see `.env.example`).

## Fallback on API Errors

If both Semantic Scholar and Exa return no results (rate limit, network):
1. Use parallel lightweight agents with web search as fallback
2. Per theme cluster: 1 agent with web search + `"research paper" site:arxiv.org OR site:doi.org`
3. Convert results into UnifiedPaper format manually
4. Check `ss_errors` / `exa_errors` stats fields for diagnostics

## Code Modules

| Module | Purpose |
|--------|---------|
| `src/agents/semantic_scholar.py` | Semantic Scholar API client (retry on 429) |
| `src/agents/exa_client.py` | Exa API client (optional, retry on 429) |
| `src/agents/paper_ranker.py` | Deduplication + ranking |
| `src/agents/forschungsstand.py` | Orchestration + generator |
| `src/utils/evidence_card.py` | Evidence card schema |

## Recommended Models

Works best with capable models (Claude Sonnet/Opus, GPT-4, or similar) for query generation, evidence extraction, and overview writing. For parallel sub-tasks like clustering, lighter models (Claude Haiku, GPT-4o-mini) suffice.
