"""Tests fuer den Drafting-Agent."""

import json
from pathlib import Path

from src.agents.drafting import (
    DraftingConfig,
    DraftingMode,
    DraftResult,
    DraftSection,
    ProvenanceSource,
    ReflexiveMetadata,
    SelfCheckFinding,
    SelfCheckSeverity,
    VenueProfile,
    VoiceProfile,
    create_provenance_entry,
    format_draft_as_markdown,
    format_self_check_as_markdown,
    generate_chapter_structure,
    generate_reflexive_section,
    load_venue_profile,
    load_voice_profile,
    save_draft,
    self_check_draft,
    self_check_section,
)


# --- Fixtures ---


def _voice() -> VoiceProfile:
    return VoiceProfile(
        name="academic_en",
        sentence_length={"avg": 18, "range": [8, 35]},
        formality="hochformell",
        passive_ratio="35-40%",
        typical_phrases=["Es ist erforderlich, dass"],
        dos=["Zahlen kontextualisieren"],
        donts=["Keine Bullet-Point-Listen fuer Fliesstext-Argumente nutzen"],
    )


def _venue() -> VenueProfile:
    return VenueProfile(
        venue_id="working_paper",
        name="Working Paper",
        type="policy_brief",
        page_range=[20, 50],
        sections=[
            "Kurzzusammenfassung",
            "Einleitung / Problemstellung",
            "Analyse / Handlungsfelder",
            "Handlungsempfehlungen",
            "Literaturverzeichnis",
            "Impressum",
        ],
        handlungsempfehlungen={
            "adressaten": ["Bundesregierung", "Wirtschaft"],
            "count_range": [5, 8],
            "style": "An [Adressat]: [Verb] [konkrete Aktion]",
        },
        ai_disclosure_required=True,
    )


def _section(
    heading: str = "Analyse",
    content: str = "",
    citations: list[str] | None = None,
) -> DraftSection:
    return DraftSection(
        heading=heading,
        content=content,
        word_count=len(content.split()) if content else 0,
        citations=citations or [],
    )


# --- Voice/Venue Loader ---


class TestLoadVenueProfile:
    def test_load_existing(self, tmp_path: Path):
        data = {
            "venue_id": "test_venue",
            "name": "Test Venue",
            "sections": ["Einleitung", "Fazit"],
        }
        path = tmp_path / "test_venue.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        result = load_venue_profile("test_venue", profiles_dir=tmp_path)
        assert result.venue_id == "test_venue"
        assert len(result.sections) == 2

    def test_load_nonexistent(self, tmp_path: Path):
        result = load_venue_profile("nope", profiles_dir=tmp_path)
        assert result.venue_id == "nope"
        assert result.sections == []

    def test_load_real_working_paper(self):
        """Testet Laden des echten Working Paper Profils."""
        profiles_dir = Path("config/venue_profiles")
        if not profiles_dir.exists():
            return  # Skip wenn nicht vorhanden
        result = load_venue_profile("working_paper", profiles_dir=profiles_dir)
        assert result.venue_id == "working_paper"
        assert len(result.sections) > 0


class TestLoadVoiceProfile:
    def test_load_existing(self, tmp_path: Path):
        data = {"name": "test", "dos": ["Klar schreiben"], "donts": ["Nicht emotional"]}
        path = tmp_path / "test_voice.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        result = load_voice_profile("test", profiles_dir=tmp_path)
        assert result.name == "test"
        assert len(result.dos) == 1

    def test_load_nonexistent(self, tmp_path: Path):
        result = load_voice_profile("nope", profiles_dir=tmp_path)
        assert result.name == "nope"
        assert result.dos == []

    def test_load_real_academic_en_voice(self):
        """Testet Laden des echten Academic EN Voice Profils."""
        profiles_dir = Path("config/voice_profiles")
        if not profiles_dir.exists():
            return
        result = load_voice_profile("academic_en", profiles_dir=profiles_dir)
        assert result.name == "academic_en"
        assert len(result.dos) > 0
        assert len(result.donts) > 0


# --- Kapitelstruktur ---


class TestChapterStructure:
    def test_generates_sections_from_venue(self):
        venue = _venue()
        sections = generate_chapter_structure(venue, "KI in der Verwaltung")
        assert len(sections) == len(venue.sections)
        assert sections[0].heading == "Kurzzusammenfassung"

    def test_einleitung_has_topic_note(self):
        venue = _venue()
        sections = generate_chapter_structure(venue, "Mobilität")
        einleitung = [s for s in sections if "einleitung" in s.heading.lower()][0]
        assert "Mobilität" in einleitung.notes

    def test_einleitung_has_leitfragen(self):
        venue = _venue()
        sections = generate_chapter_structure(
            venue, "Mobilität", leitfragen=["Wie effektiv ist X?"]
        )
        einleitung = [s for s in sections if "einleitung" in s.heading.lower()][0]
        assert "Wie effektiv ist X?" in einleitung.notes

    def test_handlungsempfehlungen_has_adressaten(self):
        venue = _venue()
        sections = generate_chapter_structure(venue, "KI")
        empf = [s for s in sections if "handlungsempfehlungen" in s.heading.lower()][0]
        assert "Bundesregierung" in empf.notes
        assert "5-8" in empf.notes


# --- Self-Check ---


class TestSelfCheckSection:
    def test_empty_section_no_findings(self):
        section = _section(content="")
        findings = self_check_section(section, _voice(), _venue())
        assert findings == []

    def test_long_sentences_warning(self):
        # Ein Satz mit 40+ Woertern
        long_text = " ".join(["Wort"] * 40) + ". Noch ein kurzer Satz hier."
        section = _section(content=long_text)
        findings = self_check_section(section, _voice(), _venue())
        severity_types = [f.dimension for f in findings]
        assert "Klarheit" in severity_types

    def test_no_citations_warning(self):
        # Langer Abschnitt ohne Quellen
        text = " ".join(["Dies ist ein Analysesatz."] * 50)
        section = _section(heading="Analyse", content=text, citations=[])
        findings = self_check_section(section, _voice(), _venue())
        evidenz_findings = [f for f in findings if f.dimension == "Evidenz"]
        assert len(evidenz_findings) >= 1

    def test_citations_suppress_warning(self):
        text = " ".join(["Dies ist ein Analysesatz."] * 50)
        section = _section(heading="Analyse", content=text, citations=["Mueller 2024"])
        findings = self_check_section(section, _voice(), _venue())
        evidenz_findings = [f for f in findings if f.dimension == "Evidenz"]
        assert len(evidenz_findings) == 0

    def test_short_section_info(self):
        section = _section(heading="Methodik", content="Kurzer Text.")
        findings = self_check_section(section, _voice(), _venue())
        vollst_findings = [f for f in findings if f.dimension == "Vollstaendigkeit"]
        assert len(vollst_findings) >= 1

    def test_short_section_ok_for_impressum(self):
        section = _section(heading="Impressum", content="Kurzer Text.")
        findings = self_check_section(section, _voice(), _venue())
        vollst_findings = [f for f in findings if f.dimension == "Vollstaendigkeit"]
        assert len(vollst_findings) == 0

    def test_bullet_point_warning(self):
        text = "Einleitung.\n" + "\n".join(f"- Punkt {i}" for i in range(8))
        section = _section(heading="Analyse", content=text)
        findings = self_check_section(section, _voice(), _venue())
        arg_findings = [f for f in findings if f.dimension == "Argumentation"]
        assert len(arg_findings) >= 1

    def test_non_evidence_section_no_citation_warning(self):
        text = " ".join(["Zusammenfassung."] * 50)
        section = _section(heading="Kurzzusammenfassung", content=text, citations=[])
        findings = self_check_section(section, _voice(), _venue())
        evidenz_findings = [f for f in findings if f.dimension == "Evidenz"]
        assert len(evidenz_findings) == 0


class TestSelfCheckDraft:
    def test_ai_disclosure_missing(self):
        venue = _venue()  # ai_disclosure_required=True
        sections = [
            _section(heading="Einleitung", content="Einleitung Text " * 20),
            _section(heading="Analyse", content="Analyse Text " * 20),
        ]
        findings = self_check_draft(sections, _voice(), venue)
        disclosure_findings = [
            f for f in findings if "AI-Disclosure" in f.message
        ]
        assert len(disclosure_findings) == 1
        assert disclosure_findings[0].severity == SelfCheckSeverity.CRITICAL

    def test_ai_disclosure_present(self):
        venue = _venue()
        sections = [
            _section(heading="Einleitung", content="Text " * 20),
            _section(heading="Impressum", content="Impressum Text."),
        ]
        findings = self_check_draft(sections, _voice(), venue)
        disclosure_findings = [
            f for f in findings if "AI-Disclosure" in f.message
        ]
        assert len(disclosure_findings) == 0

    def test_page_count_warning(self):
        venue = _venue()  # page_range [20, 50]
        # Sehr wenig Text (~1 Seite)
        sections = [_section(heading="Einleitung", content="Kurz. " * 30)]
        findings = self_check_draft(sections, _voice(), venue)
        page_findings = [f for f in findings if "Seitenzahl" in f.message]
        assert len(page_findings) >= 1


# --- Provenance ---


class TestProvenance:
    def test_create_entry(self):
        entry = create_provenance_entry(
            "Einleitung",
            ProvenanceSource.GENERATED,
            confidence="high",
        )
        assert entry["section"] == "Einleitung"
        assert entry["source"] == "generated"
        assert entry["confidence"] == "high"
        assert "timestamp" in entry

    def test_forschungsstand_source(self):
        entry = create_provenance_entry(
            "Analyse",
            ProvenanceSource.FORSCHUNGSSTAND,
            evidence_card_ids=["card_001"],
        )
        assert entry["source"] == "forschungsstand"
        assert entry["evidence_card_ids"] == ["card_001"]


# --- Output-Formatierung ---


class TestFormatting:
    def test_draft_markdown(self):
        config = DraftingConfig(topic="KI-Mobilität", venue_id="working_paper")
        result = DraftResult(
            config=config,
            sections=[
                DraftSection(heading="Einleitung", content="Dies ist die Einleitung.", word_count=5),
                DraftSection(heading="Analyse", content="Hier die Analyse.", word_count=3),
            ],
            timestamp="2026-03-05T12:00:00Z",
        )
        md = format_draft_as_markdown(result)
        assert "# KI-Mobilität" in md
        assert "## Einleitung" in md
        assert "## Analyse" in md
        assert "working_paper" in md

    def test_empty_sections_skipped(self):
        config = DraftingConfig(topic="Test")
        result = DraftResult(
            config=config,
            sections=[
                DraftSection(heading="Leer", content=""),
                DraftSection(heading="Voll", content="Inhalt hier.", word_count=2),
            ],
            timestamp="2026-03-05T12:00:00Z",
        )
        md = format_draft_as_markdown(result)
        assert "Leer" not in md
        assert "Voll" in md

    def test_selfcheck_markdown_no_findings(self):
        md = format_self_check_as_markdown([])
        assert "Keine Befunde" in md

    def test_selfcheck_markdown_with_findings(self):
        findings = [
            SelfCheckFinding(
                dimension="Evidenz",
                severity=SelfCheckSeverity.WARNING,
                section="Analyse",
                message="Keine Quellen.",
                suggestion="Quellen ergaenzen.",
            ),
            SelfCheckFinding(
                dimension="Vollstaendigkeit",
                severity=SelfCheckSeverity.CRITICAL,
                section="Gesamt",
                message="AI-Disclosure fehlt.",
            ),
        ]
        md = format_self_check_as_markdown(findings)
        assert "2 Befunde" in md
        assert "1 kritisch" in md
        assert "1 Warnungen" in md


# --- Persistenz ---


class TestSaveDraft:
    def test_save_creates_files(self, tmp_path: Path):
        config = DraftingConfig(topic="Test")
        result = DraftResult(
            config=config,
            sections=[DraftSection(heading="Einleitung", content="Text.", word_count=1)],
            self_check_findings=[
                SelfCheckFinding(
                    dimension="Klarheit",
                    severity=SelfCheckSeverity.INFO,
                    section="Einleitung",
                    message="Ok.",
                ),
            ],
            provenance_log=[
                create_provenance_entry("Einleitung", ProvenanceSource.GENERATED),
            ],
            timestamp="2026-03-05T12:00:00Z",
        )
        paths = save_draft(result, tmp_path)
        assert paths["draft"].exists()
        assert paths["selfcheck"].exists()
        assert paths["provenance"].exists()

        # Inhalt pruefen
        draft_text = paths["draft"].read_text(encoding="utf-8")
        assert "Einleitung" in draft_text

        selfcheck_data = json.loads(paths["selfcheck"].read_text(encoding="utf-8"))
        assert len(selfcheck_data) == 1

        provenance_data = json.loads(paths["provenance"].read_text(encoding="utf-8"))
        assert len(provenance_data) == 1


# --- DraftResult Stats ---


class TestDraftResult:
    def test_compute_stats(self):
        config = DraftingConfig(topic="Test")
        result = DraftResult(
            config=config,
            sections=[
                DraftSection(heading="A", content="Eins zwei drei.", word_count=3),
                DraftSection(heading="B", content="Vier fuenf.", word_count=2),
            ],
        )
        result.compute_stats()
        assert result.total_word_count == 5
        assert result.timestamp != ""


# --- Reflexive Limitations-Sektion ---


class TestReflexiveConfig:
    def test_reflexive_flag_default_false(self):
        config = DraftingConfig(topic="Test")
        assert config.reflexive is False

    def test_reflexive_flag_set(self):
        config = DraftingConfig(topic="Test", reflexive=True)
        assert config.reflexive is True


class TestReflexiveMetadata:
    def test_basic_metadata(self):
        meta = ReflexiveMetadata(
            tools_used=["Semantic Scholar API", "Exa Search"],
            databases=["Semantic Scholar", "Exa"],
            model_info="Claude Opus 4",
            known_biases=["Citation bias: populaere Papers bevorzugt"],
        )
        assert len(meta.tools_used) == 2
        assert meta.model_info == "Claude Opus 4"

    def test_empty_metadata(self):
        meta = ReflexiveMetadata()
        assert meta.tools_used == []
        assert meta.ceiling_notes == []


class TestGenerateReflexiveSection:
    def test_basic_section(self):
        meta = ReflexiveMetadata(
            tools_used=["Semantic Scholar API"],
            databases=["Semantic Scholar"],
        )
        section = generate_reflexive_section(meta)
        assert section.heading == "Methodische Transparenz"
        assert len(section.content) > 0

    def test_contains_tools(self):
        meta = ReflexiveMetadata(
            tools_used=["Semantic Scholar API", "SPECTER2 Embeddings"],
        )
        section = generate_reflexive_section(meta)
        assert "Semantic Scholar API" in section.content
        assert "SPECTER2 Embeddings" in section.content

    def test_contains_biases(self):
        meta = ReflexiveMetadata(
            known_biases=["English-language bias", "Citation count favors older papers"],
        )
        section = generate_reflexive_section(meta)
        assert "English-language bias" in section.content

    def test_contains_ceiling_notes(self):
        meta = ReflexiveMetadata(
            ceiling_notes=["Ranking hat keinen Ground-Truth-Feedback-Loop"],
        )
        section = generate_reflexive_section(meta)
        assert "Ground-Truth" in section.content

    def test_contains_model_info(self):
        meta = ReflexiveMetadata(model_info="Claude Opus 4")
        section = generate_reflexive_section(meta)
        assert "Claude Opus 4" in section.content

    def test_contains_prisma_flow(self):
        meta = ReflexiveMetadata(
            prisma_flow_summary="150 identified -> 98 dedup -> 30 ranked -> 22 included",
        )
        section = generate_reflexive_section(meta)
        assert "150 identified" in section.content

    def test_markdown_format(self):
        meta = ReflexiveMetadata(
            tools_used=["Tool A"],
            known_biases=["Bias A"],
        )
        section = generate_reflexive_section(meta)
        assert section.level == 2
        assert section.provenance == ProvenanceSource.GENERATED

    def test_empty_metadata_still_generates(self):
        meta = ReflexiveMetadata()
        section = generate_reflexive_section(meta)
        assert section.heading == "Methodische Transparenz"
        assert len(section.content) > 0


class TestSelfCheckReflexive:
    def test_warns_if_reflexive_but_no_section(self):
        venue = _venue()
        config = DraftingConfig(topic="Test", reflexive=True)
        sections = [
            _section(heading="Einleitung", content="Text " * 20),
        ]
        findings = self_check_draft(sections, _voice(), venue, config=config)
        reflexive_findings = [
            f for f in findings if f.dimension == "Reflexivitaet"
        ]
        assert len(reflexive_findings) >= 1

    def test_no_warning_if_reflexive_section_present(self):
        venue = _venue()
        config = DraftingConfig(topic="Test", reflexive=True)
        sections = [
            _section(heading="Einleitung", content="Text " * 20),
            _section(heading="Methodische Transparenz", content="Reflexive Analyse " * 30),
        ]
        findings = self_check_draft(sections, _voice(), venue, config=config)
        reflexive_findings = [
            f for f in findings
            if f.dimension == "Reflexivitaet"
        ]
        assert len(reflexive_findings) == 0

    def test_no_warning_if_not_reflexive(self):
        venue = _venue()
        config = DraftingConfig(topic="Test", reflexive=False)
        sections = [
            _section(heading="Einleitung", content="Text " * 20),
        ]
        findings = self_check_draft(sections, _voice(), venue, config=config)
        reflexive_findings = [
            f for f in findings if f.dimension == "Reflexivitaet"
        ]
        assert len(reflexive_findings) == 0
