"""Drafting-Agent — venue-gerechte Entwuerfe schreiben.

Zwei Modi:
1. Quick: 5-8 Entscheidungsfragen → autonomer Entwurf mit Self-Check
2. Detail: Kapitelweise Erstellung mit User-Feedback

Pipeline: Input → Venue-Struktur → Kapitel-Entwurf → Self-Check → Fix → Output
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# --- Enums ---


class DraftingMode(str, Enum):
    """Drafting-Modus."""

    QUICK = "quick"  # 5-8 Fragen, dann autonom
    DETAIL = "detail"  # Kapitelweise mit User-Feedback


class SelfCheckSeverity(str, Enum):
    """Schweregrad eines Self-Check-Befunds."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ProvenanceSource(str, Enum):
    """Herkunft eines Abschnitts."""

    GENERATED = "generated"  # Vom LLM generiert
    FORSCHUNGSSTAND = "forschungsstand"  # Aus Forschungsstand uebernommen
    USER_INPUT = "user_input"  # Vom User formuliert
    EVIDENCE_CARD = "evidence_card"  # Aus Evidence Card


# --- Datenmodelle ---


class VoiceProfile(BaseModel):
    """Stilprofil fuer den Schreibstil einer Organisation oder Publikationsreihe."""

    name: str
    description: str = ""
    sentence_length: dict = Field(default_factory=dict)
    formality: str = ""
    passive_ratio: str = ""
    typical_phrases: list[str] = Field(default_factory=list)
    tone: str = ""
    transition_patterns: list[str] = Field(default_factory=list)
    dos: list[str] = Field(default_factory=list)
    donts: list[str] = Field(default_factory=list)
    structural_patterns: dict = Field(default_factory=dict)
    paragraph_length: dict = Field(default_factory=dict)


class VenueProfile(BaseModel):
    """Venue-Profil einer Publikationsreihe (z.B. Working Paper, Conference Paper)."""

    venue_id: str
    name: str
    type: str = ""
    language: str = "de"
    page_range: list[int] = Field(default_factory=lambda: [20, 50])
    citation_style: str = "harvard"
    citation_format: str = "(Autor Jahr, S. XX)"
    sections: list[str] = Field(default_factory=list)
    handlungsempfehlungen: dict = Field(default_factory=dict)
    style_guide: dict = Field(default_factory=dict)
    review_criteria: list[str] = Field(default_factory=list)
    ai_disclosure_required: bool = False


class DraftSection(BaseModel):
    """Ein Kapitel/Abschnitt des Entwurfs."""

    heading: str
    level: int = 2  # Markdown-Heading-Level (##)
    content: str = ""
    word_count: int = 0
    citations: list[str] = Field(default_factory=list)  # Referenz-Keys
    provenance: ProvenanceSource = ProvenanceSource.GENERATED
    evidence_card_ids: list[str] = Field(default_factory=list)
    notes: str = ""  # Anmerkungen fuer den User


class SelfCheckFinding(BaseModel):
    """Ein Befund des Self-Checks."""

    dimension: str  # Klarheit, Argumentation, Evidenz, Vollstaendigkeit
    severity: SelfCheckSeverity
    section: str  # Betroffener Abschnitt
    message: str
    suggestion: str = ""


class ReflexiveMetadata(BaseModel):
    """Metadaten fuer die reflexive Limitations-Sektion."""

    tools_used: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    model_info: str = ""
    known_biases: list[str] = Field(default_factory=list)
    prisma_flow_summary: str = ""
    ceiling_notes: list[str] = Field(default_factory=list)


class DraftingConfig(BaseModel):
    """Konfiguration fuer einen Drafting-Durchlauf."""

    mode: DraftingMode = DraftingMode.QUICK
    venue_id: str = ""
    topic: str
    leitfragen: list[str] = Field(default_factory=list)
    forschungsstand_path: Path | None = None
    voice_profile_name: str = ""
    user_decisions: dict[str, str] = Field(default_factory=dict)
    reflexive: bool = False


class DraftResult(BaseModel):
    """Ergebnis eines Drafting-Durchlaufs."""

    config: DraftingConfig
    sections: list[DraftSection] = Field(default_factory=list)
    self_check_findings: list[SelfCheckFinding] = Field(default_factory=list)
    provenance_log: list[dict] = Field(default_factory=list)
    total_word_count: int = 0
    timestamp: str = ""

    def compute_stats(self) -> None:
        """Berechnet Statistiken."""
        self.total_word_count = sum(s.word_count for s in self.sections)
        if not self.timestamp:
            self.timestamp = datetime.now(tz=timezone.utc).isoformat()


# --- Venue/Voice Loader ---


def load_venue_profile(venue_id: str, profiles_dir: Path | None = None) -> VenueProfile:
    """Laedt ein Venue-Profil aus JSON.

    Sucht in config/venue_profiles/{venue_id}.json.
    """
    if profiles_dir is None:
        profiles_dir = Path("config/venue_profiles")

    path = profiles_dir / f"{venue_id}.json"
    if not path.exists():
        logger.warning("Venue-Profil nicht gefunden: %s", path)
        return VenueProfile(venue_id=venue_id, name=venue_id)

    data = json.loads(path.read_text(encoding="utf-8"))
    return VenueProfile.model_validate(data)


def load_voice_profile(name: str, profiles_dir: Path | None = None) -> VoiceProfile:
    """Laedt ein Voice-Profil aus JSON.

    Sucht in config/voice_profiles/{name}_voice.json.
    """
    if profiles_dir is None:
        profiles_dir = Path("config/voice_profiles")

    path = profiles_dir / f"{name}_voice.json"
    if not path.exists():
        logger.warning("Voice-Profil nicht gefunden: %s", path)
        return VoiceProfile(name=name)

    data = json.loads(path.read_text(encoding="utf-8"))
    return VoiceProfile.model_validate(data)


# --- Kapitelstruktur generieren ---


def generate_chapter_structure(
    venue: VenueProfile,
    topic: str,
    leitfragen: list[str] | None = None,
) -> list[DraftSection]:
    """Generiert die Kapitelstruktur basierend auf dem Venue-Profil.

    Uebernimmt die Sektionen aus dem Venue-Profil und erstellt
    leere DraftSection-Objekte als Skelett fuer den Entwurf.
    """
    sections: list[DraftSection] = []

    for section_name in venue.sections:
        # Level bestimmen: Top-Level Sektionen = ##, Sub = ###
        level = 2
        if "/" in section_name:
            # z.B. "Analyse / Handlungsfelder" bleibt ##
            pass

        section = DraftSection(
            heading=section_name,
            level=level,
        )

        # Spezifische Hinweise pro Sektionstyp
        if "einleitung" in section_name.lower() or "problemstellung" in section_name.lower():
            section.notes = f"Thema: {topic}"
            if leitfragen:
                section.notes += f"\nLeitfragen: {'; '.join(leitfragen)}"

        if "handlungsempfehlungen" in section_name.lower():
            empf = venue.handlungsempfehlungen
            if empf:
                adressaten = empf.get("adressaten", [])
                count_range = empf.get("count_range", [5, 8])
                section.notes = (
                    f"Adressaten: {', '.join(adressaten)}\n"
                    f"Anzahl: {count_range[0]}-{count_range[1]}\n"
                    f"Stil: {empf.get('style', '')}"
                )

        sections = [*sections, section]

    return sections


# --- Self-Check ---


def self_check_section(
    section: DraftSection,
    voice: VoiceProfile,
    venue: VenueProfile,
) -> list[SelfCheckFinding]:
    """Prueft einen Abschnitt gegen Voice- und Venue-Vorgaben.

    Automatisierbare Dimensionen (Stanford-7 Subset):
    1. Klarheit — Satzlaenge, Fachbegriffe
    2. Argumentation — Struktur-Pattern
    3. Evidenz — Quellenbeleg
    4. Vollstaendigkeit — Mindestlaenge
    """
    findings: list[SelfCheckFinding] = []

    if not section.content.strip():
        return findings

    # --- Klarheit: Satzlaenge pruefen ---
    sentences = _split_sentences(section.content)
    if sentences:
        avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
        max_range = voice.sentence_length.get("range", [8, 35])
        if avg_len > max_range[1]:
            findings = [
                *findings,
                SelfCheckFinding(
                    dimension="Klarheit",
                    severity=SelfCheckSeverity.WARNING,
                    section=section.heading,
                    message=f"Durchschnittliche Satzlaenge ({avg_len:.0f} Woerter) ueber Zielbereich ({max_range[1]}).",
                    suggestion="Lange Saetze aufteilen oder mit Doppelpunkten strukturieren.",
                ),
            ]

        # Zu kurze Saetze (< Minimum) als Pattern-Verletzung
        short_sentences = [s for s in sentences if len(s.split()) < max_range[0]]
        if len(short_sentences) > len(sentences) * 0.3:
            findings = [
                *findings,
                SelfCheckFinding(
                    dimension="Klarheit",
                    severity=SelfCheckSeverity.INFO,
                    section=section.heading,
                    message=f"{len(short_sentences)} von {len(sentences)} Saetzen unter Mindestlaenge ({max_range[0]} Woerter).",
                    suggestion="Kurze Reihungssaetze zu komplexeren Strukturen verbinden.",
                ),
            ]

    # --- Evidenz: Quellenbeleg pruefen ---
    if section.heading.lower() not in _non_evidence_sections():
        word_count = len(section.content.split())
        citation_count = len(section.citations)
        if word_count >= 200 and citation_count == 0:
            findings = [
                *findings,
                SelfCheckFinding(
                    dimension="Evidenz",
                    severity=SelfCheckSeverity.WARNING,
                    section=section.heading,
                    message=f"Abschnitt '{section.heading}' hat {word_count} Woerter aber keine Quellenangaben.",
                    suggestion="Claims mit Quellen aus dem Forschungsstand belegen.",
                ),
            ]

    # --- Vollstaendigkeit: Mindestlaenge pruefen ---
    word_count = len(section.content.split())
    if word_count < 50 and section.heading.lower() not in _short_sections():
        findings = [
            *findings,
            SelfCheckFinding(
                dimension="Vollstaendigkeit",
                severity=SelfCheckSeverity.INFO,
                section=section.heading,
                message=f"Abschnitt '{section.heading}' ist sehr kurz ({word_count} Woerter).",
                suggestion="Abschnitt ausbauen oder begruenden warum er kurz bleibt.",
            ),
        ]

    # --- Donts-Check ---
    for dont in voice.donts:
        if "bullet-point" in dont.lower() and section.content.count("- ") > 5:
            if section.heading.lower() not in ["literaturverzeichnis", "quellenverzeichnis"]:
                findings = [
                    *findings,
                    SelfCheckFinding(
                        dimension="Argumentation",
                        severity=SelfCheckSeverity.INFO,
                        section=section.heading,
                        message="Viele Bullet-Points in einem Fliesstext-Abschnitt.",
                        suggestion="Argumente als Fliesstext formulieren statt als Liste.",
                    ),
                ]
                break

    return findings


def self_check_draft(
    sections: list[DraftSection],
    voice: VoiceProfile,
    venue: VenueProfile,
    leitfragen: list[str] | None = None,
    *,
    config: DraftingConfig | None = None,
) -> list[SelfCheckFinding]:
    """Prueft den gesamten Entwurf."""
    findings: list[SelfCheckFinding] = []

    # Pro-Abschnitt-Checks
    for section in sections:
        section_findings = self_check_section(section, voice, venue)
        findings = [*findings, *section_findings]

    # --- Gesamtlaenge pruefen ---
    total_words = sum(len(s.content.split()) for s in sections)
    # Schaetzung: ~250 Woerter pro Seite
    estimated_pages = total_words / 250
    page_range = venue.page_range
    if page_range and estimated_pages < page_range[0] * 0.5:
        findings = [
            *findings,
            SelfCheckFinding(
                dimension="Vollstaendigkeit",
                severity=SelfCheckSeverity.WARNING,
                section="Gesamtdokument",
                message=(
                    f"Geschaetzte Seitenzahl ({estimated_pages:.0f}) deutlich unter "
                    f"Venue-Minimum ({page_range[0]} Seiten)."
                ),
                suggestion="Analyse-Abschnitte vertiefen, mehr Evidenz einbauen.",
            ),
        ]

    # --- AI-Disclosure pruefen ---
    if venue.ai_disclosure_required:
        has_disclosure = any(
            "ai" in s.heading.lower()
            or "ki" in s.heading.lower()
            or "transparenz" in s.heading.lower()
            for s in sections
        )
        has_impressum = any("impressum" in s.heading.lower() for s in sections)
        if not has_disclosure and not has_impressum:
            findings = [
                *findings,
                SelfCheckFinding(
                    dimension="Vollstaendigkeit",
                    severity=SelfCheckSeverity.CRITICAL,
                    section="Gesamtdokument",
                    message="AI-Disclosure erforderlich, aber kein entsprechender Abschnitt vorhanden.",
                    suggestion="Abschnitt zu AI-Nutzung im Methodik-Teil oder Impressum ergaenzen.",
                ),
            ]

    # --- Reflexive Transparenz pruefen ---
    if config is not None and config.reflexive:
        has_reflexive = any(
            "transparenz" in s.heading.lower()
            or "limitations" in s.heading.lower()
            or "reflexi" in s.heading.lower()
            for s in sections
        )
        if not has_reflexive:
            findings = [
                *findings,
                SelfCheckFinding(
                    dimension="Reflexivitaet",
                    severity=SelfCheckSeverity.WARNING,
                    section="Gesamtdokument",
                    message="Methodische Transparenz-Sektion fehlt (reflexive=True).",
                    suggestion="generate_reflexive_section() aufrufen und Sektion einfuegen.",
                ),
            ]

    return findings


# --- Reflexive Limitations-Sektion ---


def generate_reflexive_section(
    metadata: ReflexiveMetadata,
) -> DraftSection:
    """Generiert die Methodische-Transparenz-Sektion.

    Dokumentiert verwendete Tools, Datenbanken, Known Biases und
    Ceiling-Limitations der Pipeline.
    """
    lines: list[str] = []

    lines.append(
        "Dieser Abschnitt dokumentiert die methodischen Grenzen und "
        "eingesetzten Werkzeuge der vorliegenden Analyse."
    )
    lines.append("")

    if metadata.tools_used:
        lines.append("**Verwendete Tools:**")
        for tool in metadata.tools_used:
            lines.append(f"- {tool}")
        lines.append("")

    if metadata.databases:
        lines.append("**Datenbanken und Suchquellen:**")
        for db in metadata.databases:
            lines.append(f"- {db}")
        lines.append("")

    if metadata.model_info:
        lines.append(f"**Sprachmodell:** {metadata.model_info}")
        lines.append("")

    if metadata.prisma_flow_summary:
        lines.append(f"**PRISMA-Flow:** {metadata.prisma_flow_summary}")
        lines.append("")

    if metadata.known_biases:
        lines.append("**Known Biases:**")
        for bias in metadata.known_biases:
            lines.append(f"- {bias}")
        lines.append("")

    if metadata.ceiling_notes:
        lines.append("**Systemische Grenzen (Ceiling):**")
        for note in metadata.ceiling_notes:
            lines.append(f"- {note}")
        lines.append("")

    if not any([
        metadata.tools_used,
        metadata.databases,
        metadata.model_info,
        metadata.known_biases,
        metadata.ceiling_notes,
        metadata.prisma_flow_summary,
    ]):
        lines.append(
            "Keine spezifischen Metadaten verfuegbar. "
            "Bitte ReflexiveMetadata mit konkreten Angaben befuellen."
        )
        lines.append("")

    content = "\n".join(lines)
    return DraftSection(
        heading="Methodische Transparenz",
        level=2,
        content=content,
        word_count=len(content.split()),
        provenance=ProvenanceSource.GENERATED,
    )


# --- Provenance-Tracking (leichtgewichtig) ---


def create_provenance_entry(
    section_heading: str,
    source: ProvenanceSource,
    confidence: str = "medium",
    evidence_card_ids: list[str] | None = None,
) -> dict:
    """Erstellt einen Provenance-Eintrag fuer PRISMA-trAIce."""
    return {
        "section": section_heading,
        "source": source.value,
        "confidence": confidence,
        "evidence_card_ids": evidence_card_ids or [],
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


# --- Output ---


def format_draft_as_markdown(result: DraftResult) -> str:
    """Formatiert den Entwurf als Markdown."""
    lines: list[str] = []

    # Titel
    lines.append(f"# {result.config.topic}")
    lines.append("")

    # Meta-Info
    lines.append(f"*Venue: {result.config.venue_id} | Modus: {result.config.mode.value}*")
    lines.append(f"*Erstellt: {result.timestamp}*")
    lines.append("")

    # Kapitel
    for section in result.sections:
        if not section.content.strip():
            continue
        prefix = "#" * section.level
        lines.append(f"{prefix} {section.heading}")
        lines.append("")
        lines.append(section.content)
        lines.append("")

    return "\n".join(lines)


def format_self_check_as_markdown(findings: list[SelfCheckFinding]) -> str:
    """Formatiert Self-Check-Befunde als Markdown."""
    if not findings:
        return "## Self-Check\n\nKeine Befunde — Entwurf entspricht den Vorgaben.\n"

    lines: list[str] = ["## Self-Check Befunde", ""]

    # Statistik
    critical = sum(1 for f in findings if f.severity == SelfCheckSeverity.CRITICAL)
    warnings = sum(1 for f in findings if f.severity == SelfCheckSeverity.WARNING)
    infos = sum(1 for f in findings if f.severity == SelfCheckSeverity.INFO)
    lines.append(
        f"**{len(findings)} Befunde:** {critical} kritisch, {warnings} Warnungen, {infos} Hinweise"
    )
    lines.append("")

    # Befunde nach Schweregrad sortiert
    sorted_findings = sorted(findings, key=lambda f: _severity_order(f.severity))
    for finding in sorted_findings:
        icon = _severity_icon(finding.severity)
        lines.append(f"- {icon} **[{finding.dimension}]** {finding.section}")
        lines.append(f"  {finding.message}")
        if finding.suggestion:
            lines.append(f"  → {finding.suggestion}")
        lines.append("")

    return "\n".join(lines)


def save_draft(
    result: DraftResult,
    output_dir: Path,
    evidence_cards: list | None = None,
    provenance_logger: object | None = None,
) -> dict[str, Path]:
    """Speichert Entwurf, Self-Check und Provenance.

    Optional: Citation Tracking wenn evidence_cards + provenance_logger uebergeben.

    Returns:
        Dict mit Pfaden: {"draft": Path, "selfcheck": Path, "provenance": Path}
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Markdown-Entwurf
    draft_path = output_dir / "draft.md"
    draft_md = format_draft_as_markdown(result)
    draft_path.write_text(draft_md, encoding="utf-8")

    # Self-Check JSON
    selfcheck_path = output_dir / "selfcheck.json"
    selfcheck_data = [f.model_dump() for f in result.self_check_findings]
    selfcheck_path.write_text(json.dumps(selfcheck_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Provenance JSON (PRISMA-trAIce leichtgewichtig)
    provenance_path = output_dir / "provenance.json"
    provenance_path.write_text(
        json.dumps(result.provenance_log, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Citation Tracking (optional)
    if evidence_cards and provenance_logger is not None:
        from utils.citation_tracker import track_citations

        cited_ids = track_citations(draft_md, evidence_cards)
        for paper_id in cited_ids:
            provenance_logger.log_action(
                phase="synthesis",
                agent="citation-tracker",
                action="CITATION_USED",
                evidence_card_id=paper_id,
                metadata={"cited_in_draft": True},
            )

    return {
        "draft": draft_path,
        "selfcheck": selfcheck_path,
        "provenance": provenance_path,
    }


# --- Hilfsfunktionen ---


def _split_sentences(text: str) -> list[str]:
    """Teilt Text in Saetze (einfache Heuristik)."""
    import re

    # Satz-Enden: . ! ? gefolgt von Leerzeichen oder Zeilenende
    # Ausnahmen: Abkuerzungen (z.B., S., et al.), Dezimalzahlen
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])", text)
    return [s.strip() for s in sentences if s.strip()]


def _non_evidence_sections() -> set[str]:
    """Sektionen die keine Quellenbelege brauchen."""
    return {
        "executive summary",
        "kurzzusammenfassung",
        "inhaltsverzeichnis",
        "fazit und ausblick",
        "fazit",
        "impressum",
        "autorenangaben",
        "literaturverzeichnis",
        "abbildungsverzeichnis",
        "tabellenverzeichnis",
    }


def _short_sections() -> set[str]:
    """Sektionen die kurz sein duerfen."""
    return {
        "executive summary",
        "kurzzusammenfassung",
        "impressum",
        "autorenangaben",
    }


def _severity_order(severity: SelfCheckSeverity) -> int:
    """Sortier-Reihenfolge: CRITICAL zuerst."""
    return {
        SelfCheckSeverity.CRITICAL: 0,
        SelfCheckSeverity.WARNING: 1,
        SelfCheckSeverity.INFO: 2,
    }.get(severity, 3)


def _severity_icon(severity: SelfCheckSeverity) -> str:
    """Icon fuer Schweregrad."""
    return {
        SelfCheckSeverity.CRITICAL: "🔴",
        SelfCheckSeverity.WARNING: "⚠️",
        SelfCheckSeverity.INFO: "ℹ️",
    }.get(severity, "❓")
