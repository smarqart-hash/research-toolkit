"""Feature-Availability Check fuer das Research Toolkit.

Prueft welche optionalen Dependencies verfuegbar sind und zeigt
eine Feature-Matrix an. Hilft beim Onboarding und Debugging.
"""

from __future__ import annotations

import os

from pydantic import BaseModel


class DependencyStatus(BaseModel):
    """Status einer optionalen Abhaengigkeit."""

    name: str
    available: bool
    note: str = ""
    env_var: str | None = None


def check_dependencies() -> list[DependencyStatus]:
    """Prueft alle optionalen Dependencies und gibt Status-Liste zurueck."""
    deps: list[DependencyStatus] = []

    # OpenAlex — immer verfuegbar (kein Key noetig)
    mailto = os.environ.get("OPENALEX_MAILTO")
    deps = [
        *deps,
        DependencyStatus(
            name="OpenAlex Search",
            available=True,
            note="Polite Pool aktiv" if mailto else "Kein mailto — Standard Rate Limits",
            env_var="OPENALEX_MAILTO",
        ),
    ]

    # Semantic Scholar
    s2_key = os.environ.get("S2_API_KEY")
    deps = [
        *deps,
        DependencyStatus(
            name="Semantic Scholar",
            available=True,
            note="Full access" if s2_key else "Rate limited (kein API Key)",
            env_var="S2_API_KEY",
        ),
    ]

    # Exa
    exa_key = os.environ.get("EXA_API_KEY")
    deps = [
        *deps,
        DependencyStatus(
            name="Exa Search",
            available=bool(exa_key),
            note="" if exa_key else "EXA_API_KEY nicht gesetzt",
            env_var="EXA_API_KEY",
        ),
    ]

    # SPECTER2 — torch kann auf Python 3.14 mit AssertionError crashen
    try:
        import sentence_transformers  # noqa: F401

        specter2_available = True
        specter2_note = ""
    except ImportError:
        specter2_available = False
        specter2_note = "pip install sentence-transformers"
    except Exception as exc:
        specter2_available = False
        specter2_note = f"Import-Fehler: {type(exc).__name__}"
    deps = [
        *deps,
        DependencyStatus(
            name="SPECTER2 Ranking",
            available=specter2_available,
            note=specter2_note,
        ),
    ]

    # Smart Query Expansion (LLM)
    llm_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    deps = [
        *deps,
        DependencyStatus(
            name="Smart Query Expansion",
            available=bool(llm_key),
            note="" if llm_key else "OPENROUTER_API_KEY oder OPENAI_API_KEY nicht gesetzt",
            env_var="OPENROUTER_API_KEY",
        ),
    ]

    # Draft/Review/Revise (LLM)
    deps = [
        *deps,
        DependencyStatus(
            name="Draft/Review/Revise",
            available=bool(llm_key),
            note="" if llm_key else "LLM Key noetig (OPENROUTER_API_KEY)",
            env_var="OPENROUTER_API_KEY",
        ),
    ]

    return deps
