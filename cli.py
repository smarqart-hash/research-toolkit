"""Research Toolkit CLI — Modular AI toolkit for academic research.

Commands:
    search  — Literature search via Semantic Scholar + Exa
    draft   — Generate venue-formatted drafts
    review  — Structured 7-dimension feedback
    check   — Verify citations against databases
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="research-toolkit",
    help="Modular AI toolkit for academic research — from literature search to polished draft.",
    no_args_is_help=True,
)
console = Console()


def _load_env() -> None:
    """Lade .env Datei falls vorhanden."""
    env_path = Path(".env")
    if not env_path.exists():
        return
    import os

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def _setup_logging(verbose: bool) -> None:
    """Konfiguriere Logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler()],
    )


def _check_output_dir() -> Path:
    """Erstelle Output-Verzeichnis falls noetig."""
    import os

    output_dir = Path(os.getenv("OUTPUT_DIR", "./output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _available_venues() -> list[str]:
    """Liste verfuegbare Venue-Profile."""
    profiles_dir = Path("config/venue_profiles")
    if not profiles_dir.exists():
        return []
    return sorted(p.stem for p in profiles_dir.glob("*.json"))


@app.command()
def search(
    topic: str = typer.Argument(..., help="Research topic to search for"),
    max_results: int = typer.Option(30, "--max", "-m", help="Max papers after ranking"),
    use_exa: bool = typer.Option(True, "--exa/--no-exa", help="Include Exa search"),
    year_filter: str = typer.Option(None, "--years", "-y", help="Year range, e.g. 2020-2026"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Search academic literature via Semantic Scholar + Exa."""
    _load_env()
    _setup_logging(verbose)
    output_dir = _check_output_dir()

    from src.agents.forschungsstand import (
        ForschungsstandResult,
        SearchConfig,
        format_as_markdown,
        save_forschungsstand,
        search_papers,
    )

    config = SearchConfig(
        top_k=max_results,
        use_exa=use_exa,
        year_filter=year_filter,
    )

    console.print(Panel(f"Searching: [bold]{topic}[/bold]", style="blue"))

    try:
        papers, stats = asyncio.run(search_papers(topic, config=config))
    except Exception as e:
        console.print(f"[red]Search failed:[/red] {e}")
        raise typer.Exit(1)

    result = ForschungsstandResult(
        topic=topic,
        papers=papers,
        total_found=sum(stats.values()),
        total_after_dedup=len(papers),
        sources_used=list(stats.keys()),
    )

    # Ergebnisse speichern
    output_path = output_dir / "search_results.json"
    save_forschungsstand(result, output_path)

    md_path = output_dir / "search_results.md"
    md_path.write_text(format_as_markdown(result), encoding="utf-8")

    # Zusammenfassung anzeigen
    table = Table(title=f"Results: {topic}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Total found", str(result.total_found))
    table.add_row("After dedup", str(result.total_after_dedup))
    table.add_row("Sources", ", ".join(result.sources_used))
    table.add_row("Top papers", str(len(papers)))
    console.print(table)
    console.print(f"\nSaved to: [green]{output_path}[/green]")
    console.print(f"Markdown: [green]{md_path}[/green]")


@app.command()
def draft(
    topic: str = typer.Argument(..., help="Topic for the draft"),
    venue: str = typer.Option(..., "--venue", "-V", help="Venue profile ID"),
    voice: str = typer.Option("academic_en", "--voice", help="Voice profile name"),
    forschungsstand: Path = typer.Option(
        None, "--input", "-i", help="Path to search_results.json from search command"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Generate a venue-formatted draft based on research."""
    _load_env()
    _setup_logging(verbose)
    output_dir = _check_output_dir()

    if venue not in _available_venues():
        console.print(f"[red]Unknown venue:[/red] {venue}")
        console.print(f"Available: {', '.join(_available_venues())}")
        raise typer.Exit(1)

    from src.agents.drafting import DraftingConfig, DraftingMode, load_venue_profile

    config = DraftingConfig(
        mode=DraftingMode.QUICK,
        venue_id=venue,
        topic=topic,
        voice_profile_name=voice,
        forschungsstand_path=forschungsstand,
    )

    venue_profile = load_venue_profile(config.venue_id)

    console.print(Panel(f"Drafting: [bold]{topic}[/bold]\nVenue: {venue_profile.name}", style="blue"))
    console.print(f"Sections: {', '.join(venue_profile.sections)}")
    console.print(f"\n[yellow]Note:[/yellow] Draft generation requires an LLM backend (not included).")
    console.print("The toolkit provides structure, prompts, and quality checks.")
    console.print(f"\nVenue profile loaded: [green]{venue}[/green]")
    console.print(f"Voice profile: [green]{voice}[/green]")
    console.print(f"Output directory: [green]{output_dir}[/green]")


@app.command()
def review(
    document: Path = typer.Argument(..., help="Path to markdown document to review"),
    venue: str = typer.Option(None, "--venue", "-V", help="Venue profile for rubric matching"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run structured 7-dimension review on a document."""
    _load_env()
    _setup_logging(verbose)
    output_dir = _check_output_dir()

    if not document.exists():
        console.print(f"[red]File not found:[/red] {document}")
        raise typer.Exit(1)

    from src.agents.reviewer import ReviewConfig
    from src.utils.rubric_loader import find_rubric_for_venue, load_all_rubrics

    console.print(Panel(f"Reviewing: [bold]{document.name}[/bold]", style="blue"))

    text = document.read_text(encoding="utf-8")
    word_count = len(text.split())
    console.print(f"Document: {word_count} words")

    if venue:
        rubrics = load_all_rubrics()
        matched = find_rubric_for_venue(venue, rubrics=rubrics)
        if matched:
            console.print(f"Rubric: [green]{matched.name}[/green]")
        else:
            console.print(f"[yellow]No rubric found for venue '{venue}'[/yellow]")

    console.print(f"\n[yellow]Note:[/yellow] Full review requires an LLM backend (not included).")
    console.print("The toolkit provides rubrics, dimension scoring, and issue tracking.")


@app.command()
def check(
    document: Path = typer.Argument(..., help="Path to document with citations to verify"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Verify citations against Semantic Scholar."""
    _load_env()
    _setup_logging(verbose)
    output_dir = _check_output_dir()

    if not document.exists():
        console.print(f"[red]File not found:[/red] {document}")
        raise typer.Exit(1)

    from src.agents.reference_extractor import extract_references

    console.print(Panel(f"Checking citations: [bold]{document.name}[/bold]", style="blue"))

    text = document.read_text(encoding="utf-8")
    references = extract_references(text)

    console.print(f"Found [cyan]{len(references)}[/cyan] citation candidates")

    if not references:
        console.print("[yellow]No citations found in document.[/yellow]")
        raise typer.Exit(0)

    # Zeige gefundene Referenzen
    table = Table(title="Extracted References")
    table.add_column("#", style="dim")
    table.add_column("Author(s)", style="cyan")
    table.add_column("Year", style="green")
    table.add_column("Title", style="white")
    for i, ref in enumerate(references[:20], 1):
        table.add_row(
            str(i),
            ref.authors[0] if ref.authors else "?",
            str(ref.year) if ref.year else "?",
            (ref.title[:60] + "...") if ref.title and len(ref.title) > 60 else (ref.title or "?"),
        )
    console.print(table)

    if len(references) > 20:
        console.print(f"... and {len(references) - 20} more")

    console.print(f"\n[yellow]Note:[/yellow] Full verification requires API access.")
    console.print("Run with S2_API_KEY set for best results (see .env.example).")

    # Ergebnisse speichern
    output_path = output_dir / "extracted_references.json"
    refs_data = [
        {
            "authors": ref.authors,
            "year": ref.year,
            "title": ref.title,
            "raw_text": ref.raw_text,
        }
        for ref in references
    ]
    output_path.write_text(json.dumps(refs_data, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"\nSaved to: [green]{output_path}[/green]")


@app.command()
def venues() -> None:
    """List all available venue profiles."""
    table = Table(title="Available Venue Profiles")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Type", style="green")
    table.add_column("Pages", style="dim")

    for venue_id in _available_venues():
        try:
            profile_path = Path("config/venue_profiles") / f"{venue_id}.json"
            data = json.loads(profile_path.read_text(encoding="utf-8"))
            pages = data.get("page_range", data.get("page_limit", "?"))
            if isinstance(pages, list):
                pages = f"{pages[0]}-{pages[1]}"
            table.add_row(venue_id, data.get("name", "?"), data.get("type", "?"), str(pages))
        except Exception:
            table.add_row(venue_id, "?", "?", "?")

    console.print(table)


if __name__ == "__main__":
    app()
