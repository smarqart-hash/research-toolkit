"""Tests fuer die Review-Agent Schemas."""

from pathlib import Path

import pytest

from agents.reviewer import (
    Confidence,
    DimensionResult,
    HumanFlag,
    Rating,
    ReviewDelta,
    ReviewIssue,
    ReviewResult,
    Severity,
    Verdict,
    compute_delta,
    load_latest_review,
    save_review,
)


@pytest.fixture
def sample_issue() -> ReviewIssue:
    return ReviewIssue(
        severity=Severity.CRITICAL,
        category="Structure",
        location="Kap. 5 Handlungsempfehlungen",
        problem="Keine Adressaten angegeben",
        suggestion="An [Adressat]: [Verb] [konkrete Aktion]",
        dimension="Handlungsempfehlungen",
    )


@pytest.fixture
def sample_review(sample_issue: ReviewIssue) -> ReviewResult:
    return ReviewResult(
        document="draft-ki-mobilitaet.md",
        venue="policy_brief",
        rubric="policy",
        dimensions=[
            DimensionResult(name="Struktur", rating=Rating.STARK, comment="Vollstaendig"),
            DimensionResult(name="Klarheit", rating=Rating.AUSBAUFAEHIG, comment="Fachbegriffe"),
        ],
        human_flags=[
            HumanFlag(
                dimension="Originalitaet",
                observation="Keine Abgrenzung zum Forschungsstand",
                location="Kap. 2, Abs. 1",
            ),
        ],
        issues=[
            sample_issue,
            ReviewIssue(
                severity=Severity.HIGH,
                category="Evidence",
                location="Kap. 2, Abs. 3",
                problem="KI reduziert Emissionen um 30% — keine Quelle",
                suggestion="Beleg ergaenzen",
                dimension="Quellenangaben",
            ),
        ],
    )


class TestIssue:
    def test_issue_id_is_stable(self, sample_issue: ReviewIssue) -> None:
        """Gleicher Location + Problem ergibt gleiche ID."""
        duplicate = ReviewIssue(
            severity=Severity.HIGH,  # Andere Severity
            category="Format",  # Andere Category
            location=sample_issue.location,
            problem=sample_issue.problem,
            suggestion="Andere Suggestion",
            dimension="Andere Dimension",
        )
        assert sample_issue.issue_id == duplicate.issue_id

    def test_issue_id_differs_for_different_issues(self) -> None:
        issue_a = ReviewIssue(
            severity=Severity.HIGH,
            category="Evidence",
            location="Kap. 1",
            problem="Problem A",
            suggestion="Fix A",
            dimension="Quellenangaben",
        )
        issue_b = ReviewIssue(
            severity=Severity.HIGH,
            category="Evidence",
            location="Kap. 2",
            problem="Problem B",
            suggestion="Fix B",
            dimension="Quellenangaben",
        )
        assert issue_a.issue_id != issue_b.issue_id

    def test_issue_id_is_12_chars(self, sample_issue: ReviewIssue) -> None:
        assert len(sample_issue.issue_id) == 12


class TestVerdict:
    def test_ready_no_critical_few_high(self) -> None:
        result = ReviewResult(
            document="test.md",
            venue="test",
            rubric="policy",
            issues=[
                ReviewIssue(
                    severity=Severity.HIGH,
                    category="Clarity",
                    location="Kap. 1",
                    problem="P",
                    suggestion="S",
                    dimension="D",
                ),
            ],
        )
        assert result.verdict == Verdict.READY

    def test_revision_needed_one_critical(self) -> None:
        result = ReviewResult(
            document="test.md",
            venue="test",
            rubric="policy",
            issues=[
                ReviewIssue(
                    severity=Severity.CRITICAL,
                    category="Structure",
                    location="Kap. 1",
                    problem="P",
                    suggestion="S",
                    dimension="D",
                ),
            ],
        )
        assert result.verdict == Verdict.REVISION_NEEDED

    def test_revision_needed_three_high(self) -> None:
        issues = [
            ReviewIssue(
                severity=Severity.HIGH,
                category="Clarity",
                location=f"Kap. {i}",
                problem=f"Problem {i}",
                suggestion="S",
                dimension="D",
            )
            for i in range(3)
        ]
        result = ReviewResult(
            document="test.md", venue="test", rubric="policy", issues=issues
        )
        assert result.verdict == Verdict.REVISION_NEEDED

    def test_major_rework_three_critical(self) -> None:
        issues = [
            ReviewIssue(
                severity=Severity.CRITICAL,
                category="Structure",
                location=f"Kap. {i}",
                problem=f"Problem {i}",
                suggestion="S",
                dimension="D",
            )
            for i in range(3)
        ]
        result = ReviewResult(
            document="test.md", venue="test", rubric="policy", issues=issues
        )
        assert result.verdict == Verdict.MAJOR_REWORK

    def test_ready_no_issues(self) -> None:
        result = ReviewResult(document="test.md", venue="test", rubric="policy")
        assert result.verdict == Verdict.READY


class TestDelta:
    def test_compute_delta_resolved_issues(self) -> None:
        previous = ReviewResult(
            document="test.md",
            venue="test",
            rubric="policy",
            issues=[
                ReviewIssue(
                    severity=Severity.HIGH,
                    category="Evidence",
                    location="Kap. 1",
                    problem="Unbelegte Aussage",
                    suggestion="Quelle",
                    dimension="Quellenangaben",
                ),
            ],
        )
        current = ReviewResult(
            document="test.md", venue="test", rubric="policy", issues=[]
        )
        delta = compute_delta(current, previous)
        assert len(delta.resolved_ids) == 1
        assert len(delta.new_ids) == 0
        assert "1 von 1 Issues geloest" in delta.summary

    def test_compute_delta_new_issues(self) -> None:
        previous = ReviewResult(document="test.md", venue="test", rubric="policy")
        current = ReviewResult(
            document="test.md",
            venue="test",
            rubric="policy",
            issues=[
                ReviewIssue(
                    severity=Severity.MEDIUM,
                    category="Clarity",
                    location="Kap. 3",
                    problem="Neues Problem",
                    suggestion="Fix",
                    dimension="Klarheit",
                ),
            ],
        )
        delta = compute_delta(current, previous)
        assert len(delta.new_ids) == 1
        assert len(delta.resolved_ids) == 0


class TestPersistence:
    def test_save_and_load(self, sample_review: ReviewResult, tmp_path: Path) -> None:
        path = save_review(sample_review, tmp_path)
        assert path.exists()
        assert "review-" in path.name
        assert "draft-ki-mobilitaet" in path.name

    def test_load_latest_review(
        self, sample_review: ReviewResult, tmp_path: Path
    ) -> None:
        save_review(sample_review, tmp_path)
        loaded = load_latest_review("draft-ki-mobilitaet.md", tmp_path)
        assert loaded is not None
        assert loaded.document == "draft-ki-mobilitaet.md"
        assert len(loaded.issues) == 2

    def test_load_latest_review_not_found(self, tmp_path: Path) -> None:
        result = load_latest_review("nonexistent.md", tmp_path)
        assert result is None

    def test_human_flags_roundtrip(
        self, sample_review: ReviewResult, tmp_path: Path
    ) -> None:
        save_review(sample_review, tmp_path)
        loaded = load_latest_review("draft-ki-mobilitaet.md", tmp_path)
        assert loaded is not None
        assert len(loaded.human_flags) == 1
        assert loaded.human_flags[0].confidence == Confidence.REQUIRES_HUMAN
