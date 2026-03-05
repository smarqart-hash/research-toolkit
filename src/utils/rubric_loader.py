"""Rubric Loader — Laedt Review-Rubrics und Policy-Context.

Verbindet Venue-Profile mit passenden Rubrics und optionalem Policy-Context.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class DimensionAnchor(BaseModel):
    """Ankerbeispiele fuer eine Dimension."""

    stark: str
    angemessen: str
    ausbaufaehig: str
    kritisch: str


class AutoDimension(BaseModel):
    """LLM-sicher bewertbare Dimension."""

    name: str
    description: str
    anchors: DimensionAnchor


class HumanDimension(BaseModel):
    """Dimension die menschliche Beurteilung erfordert."""

    name: str
    flag_when: str


class SeverityAnchors(BaseModel):
    """Ankerbeispiele pro Severity-Level."""

    CRITICAL: list[str] = Field(default_factory=list)
    HIGH: list[str] = Field(default_factory=list)
    MEDIUM: list[str] = Field(default_factory=list)
    LOW: list[str] = Field(default_factory=list)


class Rubric(BaseModel):
    """Komplette Review-Rubric mit Dimensionen und Ankern."""

    rubric_id: str
    name: str
    applies_to: list[str] = Field(default_factory=list)
    auto_dimensions: list[AutoDimension] = Field(default_factory=list)
    human_dimensions: list[HumanDimension] = Field(default_factory=list)
    severity_anchors: SeverityAnchors = Field(default_factory=SeverityAnchors)


class PolicyFramework(BaseModel):
    """Ein einzelnes Policy-Framework."""

    name: str
    status: str
    seit: str
    relevant_fuer: list[str] = Field(default_factory=list)


class PolicyContext(BaseModel):
    """Strukturierter politischer Kontext fuer ein Themenfeld."""

    domain: str
    level: str
    frameworks: list[PolicyFramework] = Field(default_factory=list)
    key_actors: list[str] = Field(default_factory=list)
    updated_at: str


def load_rubric(rubric_id: str, rubrics_dir: Path | None = None) -> Rubric:
    """Laedt eine Rubric anhand ihrer ID."""
    directory = rubrics_dir or DEFAULT_RUBRICS_DIR
    path = directory / f"{rubric_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Rubric nicht gefunden: {path}")
    return Rubric.model_validate_json(path.read_text(encoding="utf-8"))


def find_rubric_for_venue(venue_id: str, rubrics_dir: Path | None = None) -> Rubric:
    """Findet die passende Rubric fuer ein Venue-Profil."""
    directory = rubrics_dir or DEFAULT_RUBRICS_DIR
    for path in directory.glob("*.json"):
        rubric = Rubric.model_validate_json(path.read_text(encoding="utf-8"))
        if venue_id in rubric.applies_to:
            return rubric
    raise FileNotFoundError(f"Keine Rubric fuer Venue '{venue_id}' gefunden")


def load_policy_context(
    domain: str, context_dir: Path | None = None
) -> PolicyContext | None:
    """Laedt Policy-Context fuer eine Domain. None wenn nicht vorhanden."""
    directory = context_dir or DEFAULT_POLICY_DIR
    path = directory / f"{domain}.json"
    if not path.exists():
        return None
    return PolicyContext.model_validate_json(path.read_text(encoding="utf-8"))


def list_available_rubrics(rubrics_dir: Path | None = None) -> list[str]:
    """Gibt alle verfuegbaren Rubric-IDs zurueck."""
    directory = rubrics_dir or DEFAULT_RUBRICS_DIR
    if not directory.exists():
        return []
    return sorted(p.stem for p in directory.glob("*.json"))


DEFAULT_RUBRICS_DIR = Path("config/rubrics")
DEFAULT_POLICY_DIR = Path("config/policy_context")
