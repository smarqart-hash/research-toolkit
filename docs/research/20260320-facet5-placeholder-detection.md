# Facet 5: Placeholder Detection in Administrative Data

**Research Brief — Facette fuer systematische Recherche**
**Datum:** 2026-03-20
**Bearbeiter:** Research Agent (Claude Code)

---

## Ueberblick

Diese Facette untersucht das Vorkommen, die Erkennung und die Bereinigung von Placeholder-, Phantom- und Sentinel-Werten in administrativen Datensaetzen. Das Phaenomen ist sektoruebergreifend dokumentiert: von Wohlfahrtsdaten (Geburtsjahr 9999) ueber Krankenhauspreistransparenz (999999999 als Estimat-Platzhalter) bis zu oeffentlichen Beschaffungsdaten (ID "0" als Placeholder in Portugal IMPIC). Methodisch relevante Erkenntnisse fuer den Procurement-Kontext liegen vor.

---

## Kerndokumente: Tabelle

| Titel | Erstautoren | Jahr | DOI / Quelle | Zitationen | Kontext |
|-------|-------------|------|--------------|-----------|---------|
| Matching and Cleaning Administrative Data | Goerge, R.M. & Lee, B.J. | 2002 | National Academies Press, Kap. 7 | Klassiker | US Welfare-Daten |
| Challenges in administrative data linkage for research | Harron, K. et al. | 2017 | 10.1177/2053951717745678 | Hoch zitiert | Multi-Sektor |
| Data Quality Barriers for Transparency in Public Procurement | Diverse Autoren | 2022 | mdpi.com/2078-2489/13/2/99 | Einschlägig | EU Procurement (TED/OCDS) |
| Quality Issues of Public Procurement Open Data | Diverse Autoren | 2018 | 10.1007/978-3-319-98349-3_14 | Einschlägig | EU/OCDS |
| Discovery of data quality issues in EHR | Andrade, J.B.C. et al. | 2026 | 10.1186/s13054-025-05677-0 | Neu | Krankenhaus-ICU |
| Systematic Mapping of Data Quality in the Public Sector | Silva, M.I.V. et al. | 2025 | 10.5753/sbqs.2025.15065 | Neu | Oeffentl. Sektor |
| OCDS Data Quality Assessment Guidance | Open Contracting Partnership | lfd. | standard.open-contracting.org | Standard | Procurement |
| CMS Hospital Price Transparency Guidance (Nine 9s) | Centers for Medicare & Medicaid Services | 2025 | cms.gov/priorities/key-initiatives/hospital-price-transparency | Policy | US Krankenhaus |
| Statistical Quality Standard C2: Editing and Imputing Data | U.S. Census Bureau | lfd. | census.gov/about/policies/quality/standards/standardc2 | Standard | Census |

---

## Konkrete Placeholder-Muster aus der Literatur

| Wert / Muster | Kontext | Typ | Erkennungsmethode |
|---------------|---------|-----|-------------------|
| `9999` (Geburtsjahr) | US Welfare-Daten (Goerge & Lee 2002) | Sentinel / Impossible Value | Wertbereichspruefung vor Record Linkage |
| `999999999` (neun Neunen) | CMS Krankenhauspreise (MRF-Dateien) | Placeholder fuer fehlende Kostendaten | Frequency Analysis: 63% der grossen Kliniken betroffen, 38% nutzten ihn in >90% der Felder |
| `0` (als ID) | Portugal IMPIC (OCDS Procurement) | Placeholder fuer unbekannte Organisation | Integritaetspruefung auf Non-Null/Non-Zero ID-Felder |
| `1900-01-01` (Datum) | OCDS-Daten (Open Contracting Partnership) | Placeholder fuer fehlende Datumsangaben | Frequenzanalyse auf unnatuerliche Datumshaeufungen |
| Start- > Enddatum | TED Procurement 2019 | Logisch unmoeglich | Konsistenzpruefung: >402 Contracts betroffen |
| CPV-Fehlklassifikation | EU TED | Kodierungsfehler (kein numerischer Placeholder) | Klassifikationsvalidierung gegen CPV-Taxonomie |

---

## Zusammenfassung (3-5 Saetze)

Placeholder- und Sentinel-Werte in administrativen Datensaetzen sind ein sektoruebergreifendes, gut dokumentiertes Phaenomen. Sie entstehen, wenn Systeme Pflichtfelder verlangen, aber keine echten Daten vorliegen: Nutzer greifen dann zu wiedererkennbaren Musterloesungen wie maximalen Ganzzahlen, fixen Referenzdaten oder Null-Werten. Die Erkennungsmethodik ist etabliert: Wertbereichspruefungen, Frequenzanalysen auf unnatuerliche Haeufungen, logische Konsistenzpruefungen (Start > Ende) und Integritaetspruefungen auf implausible ID-Werte. Besonders der CMS-Fall (63% der US-Kliniken nutzten `999999999` als Estimated Allowed Amount) zeigt, dass das Phaenomen in erheblichem Ausmass vorkommt, wenn regulatorischer Druck Datenpflicht schafft, aber Erhebungsprozesse unzureichend sind. In der Procurement-Forschung sind Placeholder-Werte ein Teilaspekt des breiteren Data-Quality-Problems, das durch TED/OCDS-Analysen gut dokumentiert ist.

---

## Forschungsluecken

1. **Keine systematische Taxonomie:** Es existiert keine einheitliche Klassifikation von Placeholder-Typen ueber Domänen hinweg. Jeder Sektor entwickelt eigene Ad-hoc-Erkennungsregeln.

2. **Fehlende Praevalenzstudien:** Der CMS-Fall (2025) ist eine Ausnahme — fuer die meisten administrativen Datensaetze (Steuer, Zensus, EU-Beschaffung) fehlen empirische Praevalenzschaetzungen.

3. **Intendierte vs. zufaellige Placeholder:** Die Literatur unterscheidet nicht systematisch zwischen absichtlichen Platzhaltern (Systemzwang), Dateneingabefehlern und strategischen Falschangaben (Fraud).

4. **Automatisierte Erkennung noch unreif:** Die meisten beschriebenen Ansaetze sind regelbasiert. ML-basierte Methoden (Isolation Forest etc.) werden zwar erwaehnt, aber nicht spezifisch fuer den Placeholder-Fall evaluiert.

5. **Procurement-Luecke:** Fuer TED/OCDS-Daten ist bekannt, dass Probleme existieren (z.B. `0` als Organisations-ID), aber eine systematische Quantifizierung von Placeholder-Mustern fehlt in der publizierten Literatur.

---

## Methodische Uebertragbarkeit auf den Procurement-Kontext

| Methode | Herkunft | Uebertragung auf Procurement |
|---------|----------|------------------------------|
| **Wertbereichspruefung** | Welfare/Health (Goerge & Lee, Harron et al.) | Direktuebertragbar: Auftragswerte < 0 oder > Jahresbudget, Datumsfelder mit 1900-01-01 |
| **Frequenzanalyse** | CMS Nine-Nines-Fall | Hochfrequente, runde oder extreme Werte in Preisfeldern identifizieren (z.B. exakt 1.000, 10.000, 100.000) |
| **Logische Konsistenzpruefung** | TED (Start > Ende), OCDS | Zuschlagsdatum < Bekanntmachungsdatum; Laufzeit 0 Tage; Zahl Bieter = 0 bei Wettbewerbsverfahren |
| **Integritaetspruefung auf IDs** | OCDS Portugal IMPIC | Organisations-ID = "0" oder leerer String statt valider Registernummer |
| **Ethnographische Datenrecherche** | Goerge & Lee 2002 | Prozessverstaendnis: Welche Felder sind in Beschaffungssystemen Pflichtfelder ohne Datenquelle? |
| **23-Programm-DQ-Framework** | EHR (Andrade et al. 2026) | Strukturiertes Pruefprogramm: Vollstaendigkeitscheck + Wertekonformanz als Kombination |

### Spezifische Hypothesen fuer Procurement-Analyse

- **Auftragswert-Placeholder:** Runde Summen (1.000, 10.000 EUR exakt) koennen auf systemgenerierte Platzhalter hinweisen, wenn die Verteilung eine unnatuerliche Haeufiung zeigt.
- **Bieteranzahl = 1 als Signal:** Kann legitimer Direktauftrag oder Placeholder fuer "Anzahl unbekannt" sein — nur durch Kontextpruefung unterscheidbar.
- **Geburtsdaten von Unternehmen:** Gruendungsjahre 1900, 0001 oder aktuelles Jahr bei alten Unternehmen deuten auf Placeholder hin.
- **CPV-Placeholder:** Sehr generische CPV-Codes (z.B. 98000000 "Sonstige Dienstleistungen") koennen als Placeholder fuer unbekannte Klassifikation genutzt werden.

---

## Quellen

- [National Academies Press: Matching and Cleaning Administrative Data (Kap. 7)](https://nap.nationalacademies.org/read/10206/chapter/9)
- [Harron et al. 2017: Challenges in administrative data linkage for research](https://journals.sagepub.com/doi/10.1177/2053951717745678)
- [Harron et al. — PMC-Volltext](https://pmc.ncbi.nlm.nih.gov/articles/PMC6187070/)
- [MDPI 2022: Data Quality Barriers for Transparency in Public Procurement](https://www.mdpi.com/2078-2489/13/2/99)
- [Andrade et al. 2026: Discovery of data quality issues in EHR (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12784561/)
- [Silva et al. 2025: Systematic Mapping of Data Quality in the Public Sector](https://sol.sbc.org.br/index.php/sbqs/article/view/39004)
- [OCDS Data Quality Guidance — Open Contracting Partnership](https://standard.open-contracting.org/latest/en/guidance/publish/quality/)
- [CMS Nine Nines Guidance (Norton Rose Fulbright Summary)](https://www.nortonrosefulbright.com/en-us/knowledge/publications/e4299751/cms-updates-price-transparency-guidance)
- [CMS Hospital Price Transparency Resources](https://www.cms.gov/priorities/key-initiatives/hospital-price-transparency/resources)
- [Census Bureau Statistical Quality Standard C2](https://www.census.gov/about/policies/quality/standards/standardc2.html)
