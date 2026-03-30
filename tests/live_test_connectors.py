"""Live-Tests fuer die 3 neuen API Connectors.

ACHTUNG: Diese Tests machen echte HTTP-Requests!
Nur manuell ausfuehren: python tests/live_test_connectors.py
"""

from __future__ import annotations

import asyncio
import sys

from src.agents.base_client import BASEClient
from src.agents.bundestag_client import BundestagClient
from src.agents.eurlex_client import EURLexClient
from src.agents.paper_ranker import from_base, from_bundestag, from_eurlex


async def test_base():
    """Live-Test BASE API."""
    print("\n=== BASE API ===")
    async with BASEClient() as client:
        result = await client.search("artificial intelligence", hits=5)
        print(f"Gefunden: {result.response.numFound} Dokumente")
        for doc in result.response.docs[:3]:
            paper = from_base(doc)
            print(f"  [{paper.year}] {paper.title[:80]}...")
            print(f"    DOI: {paper.doi or 'N/A'} | Lang: {paper.language} | OA: {paper.is_open_access}")
        return len(result.response.docs) > 0


async def test_bundestag():
    """Live-Test Bundestag DIP API."""
    print("\n=== BUNDESTAG DIP API ===")
    async with BundestagClient() as client:
        result = await client.search_drucksachen(
            "Kuenstliche Intelligenz",
            rows=5,
        )
        print(f"Gefunden: {result.numFound} Drucksachen")
        for ds in result.documents[:3]:
            paper = from_bundestag(ds)
            print(f"  [{paper.year}] {paper.title[:80]}...")
            print(f"    Typ: {ds.typ} | URL: {paper.url}")
        return len(result.documents) > 0


async def test_eurlex():
    """Live-Test EUR-Lex SPARQL API."""
    print("\n=== EUR-LEX SPARQL API ===")
    async with EURLexClient() as client:
        result = await client.search(
            "artificial intelligence",
            language="en",
            limit=5,
        )
        print(f"Gefunden: {result.total} Dokumente")
        for doc in result.documents[:3]:
            paper = from_eurlex(doc)
            print(f"  [{paper.year}] {paper.title[:80]}...")
            print(f"    CELEX: {doc.celex} | Typ: {doc.doc_type}")
        return len(result.documents) > 0


async def main():
    results = {}
    for name, test_fn in [("BASE", test_base), ("Bundestag", test_bundestag), ("EUR-Lex", test_eurlex)]:
        try:
            success = await test_fn()
            results[name] = "PASS" if success else "FAIL (0 Ergebnisse)"
        except Exception as e:
            results[name] = f"ERROR: {e}"
            print(f"  FEHLER: {e}")

    print("\n=== ZUSAMMENFASSUNG ===")
    for name, status in results.items():
        icon = "[OK]" if status == "PASS" else "[FAIL]"
        print(f"  {icon} {name}: {status}")

    all_pass = all(s == "PASS" for s in results.values())
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    asyncio.run(main())
