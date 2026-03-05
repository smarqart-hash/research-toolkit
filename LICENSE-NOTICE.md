# Legal Notice

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

## Code Origin

All code in this repository is original work. No code was copied from, derived from,
or based on existing open-source projects (STORM, PaperQA2, OpenScholar, or others).

The architecture was informed by published research on automated research tools,
but the implementation is entirely independent.

## Third-Party APIs

- **Semantic Scholar API** by the Allen Institute for AI — used for paper search and metadata.
  Terms of Service: https://www.semanticscholar.org/product/api/license
  Attribution: "This toolkit uses the Semantic Scholar API."

- **Exa API** (optional) — used for complementary neural search.
  Terms of Service: https://exa.ai/terms

## Dependencies with Non-Permissive Licenses

- **PyMuPDF** (optional `[parsing]` extra) — AGPL-3.0 licensed.
  This dependency is isolated as an optional extra. The core toolkit does not
  include or require PyMuPDF. If AGPL is incompatible with your use case,
  use `pypdf` or `pdfplumber` (both MIT-licensed) as alternatives.

- **marker-pdf** (optional `[parsing]` extra) — GPL-3.0 licensed.
  Same isolation as PyMuPDF. Not imported by core code. Only pulled in
  if you explicitly install `pip install research-toolkit[parsing]`.

## AI Disclosure

This toolkit was developed with AI assistance (Claude Code by Anthropic).
The example output in `examples/` was generated using the toolkit's own pipeline
with real Semantic Scholar API data.
