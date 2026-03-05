# Contributing

Thanks for your interest in contributing to Research Toolkit! This is a working prototype — contributions that improve quality, coverage, or usability are very welcome.

## Quickest Contribution: Add a Venue Profile

Venue profiles are ~20 lines of JSON. To add one:

1. Copy an existing profile from `config/venue_profiles/`
2. Rename to `your_venue.json`
3. Adjust: `name`, `type`, `page_range`, `sections`, `citation_style`
4. Add the venue ID to the appropriate rubric's `applies_to` list in `config/rubrics/`
5. Open a PR

Example — adding a journal profile:
```json
{
  "id": "plos_one",
  "name": "PLOS ONE",
  "type": "journal",
  "page_range": null,
  "word_limit": 6000,
  "sections": ["Introduction", "Methods", "Results", "Discussion"],
  "citation_style": "numeric",
  "review_criteria": ["reproducibility", "statistical_rigor"]
}
```

## Add a Voice Profile

Voice profiles define writing style. Copy `config/voice_profiles/academic_en_voice.json` and adjust:
- `sentence_length` (average and range)
- `typical_phrases` and `transitions`
- `dos` and `donts`

## Add a Database Connector

The toolkit currently searches Semantic Scholar and Exa. To add a new source:

1. Create `src/agents/your_source.py` following the pattern in `exa_client.py`
2. Return `UnifiedPaper` objects (see `src/agents/paper_ranker.py`)
3. Add tests in `tests/test_your_source.py`
4. Update `skills/search.md` to mention the new source

High-value additions: PubMed, LIVIVO, BASE, OpenAlex, Crossref.

## Development Setup

```bash
git clone https://github.com/smarqart-hash/research-toolkit.git
cd research-toolkit
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e ".[dev]"
pytest  # 207 tests should pass
```

## Code Standards

- **Python 3.11+**, formatted with Black, linted with Ruff
- **Immutable patterns** — no object/array mutation
- **Functions < 50 lines**, files < 800 lines
- **Tests required** for new features (pytest, aim for 80%+ coverage)
- Comments in English, commit messages in English (Conventional Commits)

## Pull Requests

- Keep PRs focused — one feature or fix per PR
- Include tests for new functionality
- Update relevant skill documentation in `skills/` if behavior changes
- Reference any related issues

## What We Need Most

1. **Database connectors** — PubMed, OpenAlex, LIVIVO, BASE
2. **Citation format support** — APA, numeric, Vancouver (currently Harvard only)
3. **Validation studies** — compare Search output against manual expert search
4. **Voice profiles** — domain-specific writing styles (medical, legal, engineering)
5. **Bug reports** — especially around citation extraction edge cases
