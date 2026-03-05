# Sprint 2 Spec: Reflexivitaet

> Branch: `feature/reflexive-loop` | Findings: F5, F3

## Ziel

Der Draft-Skill bekommt ein `--reflexive` Flag, das automatisch eine
Limitations-Sektion generiert. Rubric-Kalibrierung wird transparent
dokumentiert statt geloest.

---

## Deliverable 1: Reflexive Limitations-Sektion (F5)

### Was

Neues Flag `reflexive` in `DraftingConfig`. Wenn aktiv, wird automatisch
eine "Methodische Transparenz"-Sektion generiert, die dokumentiert:
- Verwendete Tools und APIs
- Datenbanken und Suchquellen
- Modell/LLM (wenn bekannt)
- Known Biases und Limitations
- PRISMA-Flow (wenn aus Search vorhanden)

### Dateien

| Datei | Aenderung |
|-------|-----------|
| `src/agents/drafting.py` | `reflexive` Flag + `generate_reflexive_section()` |
| `tests/test_drafting.py` | Erweitern (reflexive Tests) |

### Datenmodell

```python
# drafting.py — DraftingConfig Erweiterung
class DraftingConfig(BaseModel):
    ...
    reflexive: bool = False  # NEU

# Neues Datenmodell fuer reflexive Metadaten
class ReflexiveMetadata(BaseModel):
    """Metadaten fuer die reflexive Limitations-Sektion."""
    tools_used: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    model_info: str = ""
    known_biases: list[str] = Field(default_factory=list)
    prisma_flow_summary: str = ""
    ceiling_notes: list[str] = Field(default_factory=list)
```

### Funktion

```python
def generate_reflexive_section(
    metadata: ReflexiveMetadata,
) -> DraftSection:
    """Generiert die Methodische-Transparenz-Sektion."""
```

### Integration

```python
# In generate_chapter_structure() oder als Post-Processing:
# Wenn config.reflexive == True:
#   → ReflexiveMetadata aus Pipeline-Context zusammenstellen
#   → generate_reflexive_section() aufrufen
#   → Als letzte Sektion VOR Literaturverzeichnis einfuegen
```

### Self-Check Integration

Neue Dimension im Self-Check: Wenn `reflexive=True` aber keine
Limitations-Sektion vorhanden → CRITICAL Finding.

### Tests

- `test_reflexive_flag_default_false` — Default ist aus
- `test_generate_reflexive_section_basic` — Section hat Heading + Content
- `test_reflexive_section_contains_tools` — Tools werden gelistet
- `test_reflexive_section_contains_biases` — Known Biases aufgefuehrt
- `test_reflexive_section_contains_ceiling` — Ceiling-Notes enthalten
- `test_reflexive_section_markdown_format` — Korrektes Markdown
- `test_self_check_warns_if_reflexive_missing` — Warning wenn Flag aber keine Sektion

---

## Deliverable 2: Rubric-Kalibrierung dokumentieren (F3)

### Was

Known Limitations im Repo erweitern. Kein Code-Change, reine Dokumentation.

### Dateien

| Datei | Aenderung |
|-------|-----------|
| `docs/architecture.md` | Sektion "Calibration Status" ergaenzen |
| `skills/review.md` | Kalibrierungs-Transparenz ergaenzen |

### Inhalt

1. **Ordinale Labels sind nicht benchmark-kalibriert** — "stark" vs "angemessen"
   basiert auf Rubric-Ankern, nicht auf empirischem Vergleich
2. **Inter-Rater-Reliability unbekannt** — Kein Vergleich LLM vs. Mensch
3. **Spearman-Korrelation** — 0.42 ist ein Referenzwert ohne Konfidenzintervall
4. **Goodhart's Law** — `compute_delta()` misst Legibility, nicht epistemische Qualitaet

---

## Reihenfolge

1. **Reflexive Section** (Deliverable 1) — Code + Tests
2. **Kalibrierung Docs** (Deliverable 2) — reine Dokumentation
3. **Tests** — Begleitend zu Deliverable 1

## Abgrenzung (Out of Scope)

- LLM-basierte Reflexion (Section 6.3 im Meta-Paper ist manuell geschrieben)
- Automatische Bias-Detection (waere eigener Agent)
- Rubric-Kalibrierung implementieren (waere empirische Studie)
