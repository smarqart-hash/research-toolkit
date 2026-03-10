"""Tests fuer den Citation Tracker."""

import logging

import pytest

from utils.citation_tracker import track_citations
from utils.evidence_card import EvidenceCard


def _card(
    paper_id: str,
    title: str = "Test Paper",
    authors: list[str] | None = None,
    year: int | None = None,
) -> EvidenceCard:
    """Helfer-Factory fuer Evidence Cards."""
    return EvidenceCard(
        card_id=f"ec-{paper_id}",
        paper_id=paper_id,
        paper_title=title,
        authors=authors or [],
        year=year,
        claim="Test claim",
        method="Test method",
    )


class TestCitationTracking:
    def test_title_match(self) -> None:
        cards = [_card("p1", title="Deep Learning for Traffic Control")]
        draft = "Recent work on Deep Learning for Traffic Control shows..."
        cited = track_citations(draft, cards)
        assert cited == ["p1"]

    def test_title_match_case_insensitive(self) -> None:
        cards = [_card("p1", title="BERT: Pre-training")]
        draft = "We build upon bert: pre-training approaches..."
        cited = track_citations(draft, cards)
        assert cited == ["p1"]

    def test_author_year_match(self) -> None:
        cards = [_card("p1", authors=["Smith, J."], year=2024)]
        draft = "As demonstrated by Smith (2024), the approach..."
        cited = track_citations(draft, cards)
        assert cited == ["p1"]

    def test_author_et_al_year_match(self) -> None:
        cards = [_card("p1", authors=["Mueller, K.", "Schmidt, A."], year=2023)]
        draft = "Mueller et al. 2023 found significant improvements."
        cited = track_citations(draft, cards)
        assert cited == ["p1"]

    def test_no_match(self) -> None:
        cards = [_card("p1", title="Unrelated Paper", authors=["Nobody, X."], year=2020)]
        draft = "This draft discusses something completely different."
        cited = track_citations(draft, cards)
        assert cited == []

    def test_multiple_matches(self) -> None:
        cards = [
            _card("p1", title="Paper Alpha"),
            _card("p2", title="Paper Beta"),
            _card("p3", title="Paper Gamma"),
        ]
        draft = "We reference Paper Alpha and Paper Gamma in our analysis."
        cited = track_citations(draft, cards)
        assert cited == ["p1", "p3"]

    def test_empty_draft(self, caplog: pytest.LogCaptureFixture) -> None:
        cards = [_card("p1", title="Test")]
        with caplog.at_level(logging.WARNING):
            cited = track_citations("", cards)
        assert cited == []
        assert "Leerer Draft" in caplog.text

    def test_empty_cards(self) -> None:
        cited = track_citations("Some draft text", [])
        assert cited == []

    def test_card_without_title_and_authors(self) -> None:
        card = EvidenceCard(
            card_id="ec-bare",
            paper_id="bare",
            paper_title="",
            claim="C",
            method="M",
        )
        cited = track_citations("Some draft mentioning nothing relevant.", [card])
        assert cited == []

    def test_card_with_authors_but_no_year(self) -> None:
        cards = [_card("p1", authors=["Smith, J."])]
        draft = "Smith discusses several approaches."
        cited = track_citations(draft, cards)
        assert cited == []

    def test_no_citations_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        cards = [_card("p1", title="Irrelevant")]
        with caplog.at_level(logging.WARNING):
            track_citations("Draft without any relevant references.", cards)
        assert "Keine Zitationen" in caplog.text

    def test_special_chars_in_author_name(self) -> None:
        cards = [_card("p1", authors=["O'Brien, S."], year=2024)]
        draft = "O'Brien (2024) demonstrated the effectiveness."
        cited = track_citations(draft, cards)
        assert cited == ["p1"]
