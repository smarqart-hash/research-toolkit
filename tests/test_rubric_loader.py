"""Tests fuer den Rubric Loader."""

import json
from pathlib import Path

import pytest

from utils.rubric_loader import (
    PolicyContext,
    Rubric,
    find_rubric_for_venue,
    list_available_rubrics,
    load_policy_context,
    load_rubric,
)


@pytest.fixture
def rubrics_dir(tmp_path: Path) -> Path:
    """Erstellt ein temporaeres Rubrics-Verzeichnis mit Test-Daten."""
    rubrics = tmp_path / "rubrics"
    rubrics.mkdir()

    policy_rubric = {
        "rubric_id": "policy",
        "name": "Policy Test",
        "applies_to": ["policy_brief", "position_paper"],
        "auto_dimensions": [
            {
                "name": "Struktur",
                "description": "Test",
                "anchors": {
                    "stark": "Gut",
                    "angemessen": "OK",
                    "ausbaufaehig": "Maengel",
                    "kritisch": "Schlecht",
                },
            }
        ],
        "human_dimensions": [
            {"name": "Originalitaet", "flag_when": "Keine Abgrenzung"}
        ],
        "severity_anchors": {
            "CRITICAL": ["Beispiel C"],
            "HIGH": ["Beispiel H"],
            "MEDIUM": [],
            "LOW": [],
        },
    }
    (rubrics / "policy.json").write_text(json.dumps(policy_rubric), encoding="utf-8")

    akademisch_rubric = {
        "rubric_id": "akademisch",
        "name": "Akademisch Test",
        "applies_to": ["research_report"],
        "auto_dimensions": [],
        "human_dimensions": [],
        "severity_anchors": {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []},
    }
    (rubrics / "akademisch.json").write_text(
        json.dumps(akademisch_rubric), encoding="utf-8"
    )

    return rubrics


@pytest.fixture
def policy_dir(tmp_path: Path) -> Path:
    """Erstellt ein temporaeres Policy-Context-Verzeichnis."""
    policies = tmp_path / "policy_context"
    policies.mkdir()

    context = {
        "domain": "ki_allgemein",
        "level": "de+eu",
        "frameworks": [
            {
                "name": "AI Act",
                "status": "in_kraft",
                "seit": "2024-08",
                "relevant_fuer": ["alle KI-Themen"],
            }
        ],
        "key_actors": ["BMBF", "BMWK"],
        "updated_at": "2026-03-05",
    }
    (policies / "ki_allgemein.json").write_text(
        json.dumps(context), encoding="utf-8"
    )

    return policies


class TestLoadRubric:
    def test_load_existing_rubric(self, rubrics_dir: Path) -> None:
        rubric = load_rubric("policy", rubrics_dir)
        assert rubric.rubric_id == "policy"
        assert len(rubric.auto_dimensions) == 1
        assert rubric.auto_dimensions[0].name == "Struktur"

    def test_load_nonexistent_raises(self, rubrics_dir: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_rubric("nonexistent", rubrics_dir)

    def test_rubric_has_severity_anchors(self, rubrics_dir: Path) -> None:
        rubric = load_rubric("policy", rubrics_dir)
        assert len(rubric.severity_anchors.CRITICAL) == 1
        assert "Beispiel C" in rubric.severity_anchors.CRITICAL

    def test_rubric_has_human_dimensions(self, rubrics_dir: Path) -> None:
        rubric = load_rubric("policy", rubrics_dir)
        assert len(rubric.human_dimensions) == 1
        assert rubric.human_dimensions[0].name == "Originalitaet"


class TestFindRubricForVenue:
    def test_find_policy_for_policy_brief(self, rubrics_dir: Path) -> None:
        rubric = find_rubric_for_venue("policy_brief", rubrics_dir)
        assert rubric.rubric_id == "policy"

    def test_find_akademisch_for_research_report(self, rubrics_dir: Path) -> None:
        rubric = find_rubric_for_venue("research_report", rubrics_dir)
        assert rubric.rubric_id == "akademisch"

    def test_unknown_venue_raises(self, rubrics_dir: Path) -> None:
        with pytest.raises(FileNotFoundError):
            find_rubric_for_venue("unknown_venue", rubrics_dir)


class TestPolicyContext:
    def test_load_existing_context(self, policy_dir: Path) -> None:
        context = load_policy_context("ki_allgemein", policy_dir)
        assert context is not None
        assert context.domain == "ki_allgemein"
        assert len(context.frameworks) == 1
        assert context.frameworks[0].name == "AI Act"

    def test_load_nonexistent_returns_none(self, policy_dir: Path) -> None:
        result = load_policy_context("nonexistent", policy_dir)
        assert result is None

    def test_key_actors(self, policy_dir: Path) -> None:
        context = load_policy_context("ki_allgemein", policy_dir)
        assert context is not None
        assert "BMBF" in context.key_actors


class TestListRubrics:
    def test_list_available(self, rubrics_dir: Path) -> None:
        rubrics = list_available_rubrics(rubrics_dir)
        assert "policy" in rubrics
        assert "akademisch" in rubrics

    def test_list_empty_dir(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        assert list_available_rubrics(empty) == []
