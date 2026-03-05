"""Integrationstests fuer den Review-Workflow.

Testet das Zusammenspiel von Document-Splitter, Rubric-Loader und Review-Schemas.
"""

from pathlib import Path

import pytest

from agents.reviewer import (
    DimensionResult,
    HumanFlag,
    Rating,
    ReviewIssue,
    ReviewResult,
    Severity,
    Verdict,
    compute_delta,
    save_review,
)
from utils.document_splitter import (
    extract_section_by_name,
    needs_splitting,
    split_markdown,
)
from utils.rubric_loader import find_rubric_for_venue, load_rubric


FIXTURES_DIR = Path(__file__).parent / "fixtures"
RUBRICS_DIR = Path(__file__).parent.parent / "config" / "rubrics"


@pytest.fixture
def sample_draft() -> str:
    path = FIXTURES_DIR / "sample-draft-impuls.md"
    return path.read_text(encoding="utf-8")


class TestFullReviewWorkflow:
    """Testet den kompletten Workflow: Laden → Splitten → Rubric → Review → Export."""

    def test_load_and_split_sample_draft(self, sample_draft: str) -> None:
        """Sample-Draft ist kurz genug fuer Single-Pass."""
        assert not needs_splitting(sample_draft)
        sections = split_markdown(sample_draft)
        assert len(sections) >= 5

    def test_extract_handlungsempfehlungen(self, sample_draft: str) -> None:
        sections = split_markdown(sample_draft)
        empfehlungen = extract_section_by_name(sections, "Handlungsempfehlungen")
        assert empfehlungen is not None
        assert "Pilotprojekte" in empfehlungen.content

    def test_rubric_matches_venue(self) -> None:
        """Policy-Rubric wird fuer working_paper gefunden."""
        rubric = find_rubric_for_venue("policy_brief", RUBRICS_DIR)
        assert rubric.rubric_id == "policy"
        assert len(rubric.auto_dimensions) == 6
        assert len(rubric.human_dimensions) == 3

    def test_rubric_has_severity_anchors(self) -> None:
        rubric = load_rubric("policy", RUBRICS_DIR)
        assert len(rubric.severity_anchors.CRITICAL) >= 2
        assert len(rubric.severity_anchors.HIGH) >= 2

    def test_simulate_review_result(self, sample_draft: str, tmp_path: Path) -> None:
        """Simuliert ein komplettes Review-Ergebnis."""
        rubric = find_rubric_for_venue("policy_brief", RUBRICS_DIR)

        # Simuliere Dimension-Bewertungen
        dimensions = [
            DimensionResult(
                name="Struktur & Vollstaendigkeit",
                rating=Rating.ANGEMESSEN,
                comment="Kernsektionen vorhanden, Impressum fehlt",
            ),
            DimensionResult(
                name="Klarheit & Verstaendlichkeit",
                rating=Rating.ANGEMESSEN,
                comment="Ueberwiegend verstaendlich, DRL nicht erklaert",
            ),
            DimensionResult(
                name="Quellenangaben",
                rating=Rating.AUSBAUFAEHIG,
                comment="Emissionsreduktion 30% ohne Quelle, nur 3 Quellen gesamt",
            ),
            DimensionResult(
                name="Handlungsempfehlungen",
                rating=Rating.AUSBAUFAEHIG,
                comment="Empfehlungen vorhanden aber ohne Adressaten",
            ),
        ]

        issues = [
            ReviewIssue(
                severity=Severity.HIGH,
                category="Evidence",
                location="Kap. 1, Abs. 1",
                problem="Emissionsreduktion um 30% ohne Quellenangabe",
                suggestion="Quelle ergaenzen oder als Potenzialschaetzung kennzeichnen",
                dimension="Quellenangaben",
            ),
            ReviewIssue(
                severity=Severity.HIGH,
                category="Structure",
                location="Kap. 5 Handlungsempfehlungen",
                problem="Keine Adressaten bei Empfehlungen",
                suggestion="Format: An [Bundesregierung/Kommunen/...]: [Aktion]",
                dimension="Handlungsempfehlungen",
            ),
            ReviewIssue(
                severity=Severity.HIGH,
                category="Context",
                location="Kap. 1 Einleitung",
                problem="Regulatorischer Rahmen nicht erwaehnt",
                suggestion="AI Act und BMDV-Digitalstrategie referenzieren",
                dimension="Regulatorik-Referenzen",
            ),
            ReviewIssue(
                severity=Severity.MEDIUM,
                category="Clarity",
                location="Kap. 2, Abs. 1",
                problem="DRL (Deep Reinforcement Learning) nicht erklaert",
                suggestion="Abkuerzung beim ersten Vorkommen ausschreiben und erklaeren",
                dimension="Klarheit & Verstaendlichkeit",
            ),
        ]

        human_flags = [
            HumanFlag(
                dimension="Originalitaet",
                observation="Keine Abgrenzung zu bestehenden Publikationen zum Thema",
                location="Kap. 2",
            ),
        ]

        result = ReviewResult(
            document="sample-draft-impuls.md",
            venue="policy_brief",
            rubric="policy",
            dimensions=dimensions,
            human_flags=human_flags,
            issues=issues,
        )

        # Verdict pruefen: 3 HIGH → REVISION_NEEDED
        assert result.verdict == Verdict.REVISION_NEEDED

        # Export
        path = save_review(result, tmp_path)
        assert path.exists()
        assert "sample-draft-impuls" in path.name

    def test_iteration_delta(self, tmp_path: Path) -> None:
        """Simuliert zwei Review-Iterationen mit Delta."""
        # Iteration 1
        v1 = ReviewResult(
            document="draft.md",
            venue="policy_brief",
            rubric="policy",
            iteration=1,
            issues=[
                ReviewIssue(
                    severity=Severity.HIGH,
                    category="Evidence",
                    location="Kap. 1",
                    problem="Keine Quelle",
                    suggestion="Ergaenzen",
                    dimension="Quellenangaben",
                ),
                ReviewIssue(
                    severity=Severity.HIGH,
                    category="Structure",
                    location="Kap. 5",
                    problem="Keine Adressaten",
                    suggestion="Ergaenzen",
                    dimension="Handlungsempfehlungen",
                ),
                ReviewIssue(
                    severity=Severity.HIGH,
                    category="Context",
                    location="Kap. 1",
                    problem="Regulatorik fehlt",
                    suggestion="AI Act",
                    dimension="Regulatorik",
                ),
            ],
        )

        # Iteration 2: 1 Issue geloest, 2 offen
        v2 = ReviewResult(
            document="draft.md",
            venue="policy_brief",
            rubric="policy",
            iteration=2,
            issues=[
                ReviewIssue(
                    severity=Severity.HIGH,
                    category="Structure",
                    location="Kap. 5",
                    problem="Keine Adressaten",
                    suggestion="Ergaenzen",
                    dimension="Handlungsempfehlungen",
                ),
                ReviewIssue(
                    severity=Severity.HIGH,
                    category="Context",
                    location="Kap. 1",
                    problem="Regulatorik fehlt",
                    suggestion="AI Act",
                    dimension="Regulatorik",
                ),
            ],
        )

        delta = compute_delta(v2, v1)
        assert len(delta.resolved_ids) == 1
        assert len(delta.open_ids) == 2
        assert len(delta.new_ids) == 0
        assert "1 von 3 Issues geloest" in delta.summary
