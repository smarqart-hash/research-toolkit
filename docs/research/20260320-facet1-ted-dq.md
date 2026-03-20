# Facet 1: TED Data Quality Empirics

**Research Brief:** Qualitaet europaeischer Vergabedaten
**Facette:** Empirische Studien zu Datenqualitaetsproblemen in TED (Tenders Electronic Daily)
**Erstellt:** 2026-03-20

---

## Gefundene Papers

| Titel | Erstautor | Institution | Land | Jahr | Zitierungen | DOI |
|-------|-----------|-------------|------|------|-------------|-----|
| Data Quality Barriers for Transparency in Public Procurement | Ahmet Soylu | Norwegian University of Science and Technology (NTNU) | NO | 2022 | ~45 | 10.3390/info13020099 |
| Analysing the European Union's Tenders Electronic Daily: possibilities and pitfalls | Eric Prier | Florida Atlantic University | US | 2018 | ~60 | 10.1504/IJPM.2018.095655 |
| Uncovering High-Level Corruption: Cross-National Objective Corruption Risk Indicators Using Public Procurement Data | Mihaly Fazekas | Transparency Lab / University of Cambridge | NL/GB | 2017/2020 | 177 | 10.1017/s0007123417000461 |
| Grand corruption and government change: an analysis of partisan favoritism in public procurement | Elizabeth David-Barrett | University of Sussex | GB | 2019 | 101 | 10.1007/s10610-019-09416-4 |
| Global Contract-level Public Procurement Dataset (GPPD) | Mihaly Fazekas | Government Transparency Institute | HU | 2024 | — | 10.1016/j.dib.2024.110412 |
| FOPPA: an open database of French public procurement award notices from 2010-2020 | [Lech et al.] | Independent / DBLP | FR | 2023 | — | 10.1038/s41597-023-02213-z |
| Quality Issues of Public Procurement Open Data | [Kucera et al.] | — | — | 2018 | — | 10.1007/978-3-319-98349-3_14 |
| The extent and cost of corruption in transport infrastructure | Mihaly Fazekas | University of Cambridge | GB | 2018 | 40 | 10.1016/j.tra.2018.03.021 |
| Corruption in Public Procurement: Finding the Right Indicators | Joras Ferwerda | Utrecht University | NL | 2016 | 109 | 10.1007/s10610-016-9312-3 |
| LOTED2: An ontology of European public procurement notices | Isabella Distinto | ISTC-CNR Laboratory for Applied Ontology | IT | 2016 | 34 | 10.3233/sw-140151 |

### Seed-Papers (nicht neu recherchiert, bereits bekannt)

| Titel | Erstautor | Jahr | Anmerkung |
|-------|-----------|------|-----------|
| Uncovering High-Level Corruption... | Fazekas & Kocsis | 2020 | BJPS, 28 EU-Laender, 2.8 Mio Vertraege, TED-basiert |
| Analysing the EU's TED: possibilities and pitfalls | Prier et al. | 2018 | IJPM, strukturelle TED-Probleme, CSV-Format |
| Data Quality Barriers for Transparency | Soylu et al. | 2022 | MDPI Information, TheyBuyForYou-Projekt, Slowenien |
| Global Contract-level Public Procurement Dataset | Fazekas et al. | 2024 | Data in Brief, 72 Mio Vertraege, 42 Laender |

---

## Kernbefunde

**Missing Values als systemisches Problem:** Soylu et al. (2022) dokumentieren fuer TED-Daten systematisch fehlende Felder: Vertragslaufzeiten, Vertragsendedaten, Auftragnehmer-Adressen und Vertragsstatus sind haeufig nicht vorhanden. Besonders kritisch: Das CN-CAN-Linking-Feld (Verknuepfung Contract Notice mit Contract Award Notice) ist optional und wird unzuverlaessig ausgefuellt, was eine Lebenszyklus-Analyse von Ausschreibungen de facto verhindert.

**Placeholder-Eintraege als Compliance-Taktik:** Mehrere Studien belegen, dass Auftraggeber Felder mit Nullwerten (z.B. Auftragswert = 0) befuellen, um formale Meldepflichten zu erfuellen ohne nutzbare Daten bereitzustellen. Im britischen Contracts Finder ueberstiegen Null-Wert-Eintraege in jedem Jahr seit Launch 10% aller Contract Award Notices -- ein aehnliches Muster wird fuer TED vermutet, ist aber laenderuebergreifend nicht systematisch quantifiziert.

**Strukturelle Komplexitaet als Nutzungsbarriere:** Prier, Prysmakova & McCue (2018) zeigen empirisch, dass die redundante XML/CSV-Struktur von TED-Daten fuer 33 EU-Laender und mehrere Verwaltungsebenen die Interpretierbarkeit so stark einschraenkt, dass Transparenz- und Accountability-Ziele nicht erreicht werden. TED-CSV-Daten sollten "with an abundance of caution" genutzt werden.

**Zeitliche Inkonsistenzen quantifiziert:** Soylu et al. (2022) fanden in TED-Daten fuer 2019 ueber 402 Vertraege, die nach ihrem Ablaufdatum veroeffentlicht wurden -- ein Indikator fuer fehlende Validierungsregeln beim Einspeisung in die Datenbank.

**Kein Trend zur Verbesserung:** Fazekas et al. (2024) stellen fuer den Zeitraum 2011-2021 fest, dass es seit der Umsetzung der EU-Vergaberichtlinien 2014 (Transposition 2016-2018) keinen erkennbaren Trend zu weniger fehlenden Angaben in Contract Award Notices gibt. Missing information wird von Fazekas & Kocsis (2020) selbst als Korruptionsrisikoindikator operationalisiert (kein Call for Tender veroeffentlicht = Red Flag).

---

## Bekannte Forschungsluecken

1. **Keine laenderuebergreifende Quantifizierung von Placeholder-Eintraegen in TED:** Studien belegen das Phaenomen qualitativ, aber eine systematische EU-weite Messung des Anteils von Null-Wert-Eintraegen pro Land und Zeitraum fehlt.

2. **CN-CAN Coverage Rate unbekannt:** Wie gross der Anteil von Contract Award Notices ist, die valide auf eine Contract Notice verweisen, ist nicht publiziert. Die Luecke ist bekannt (Soylu 2022, TED Codebook), aber nicht empirisch beziffert.

3. **Field-Level Completeness Matrix fehlt:** Keine Studie liefert eine vollstaendige Tabelle der Vollstaendigkeitsrate pro TED-Feld, pro Land, pro Jahr. Vorliegende Arbeiten sind meist fallstudienbasiert (Slowenien, Frankreich, UK) oder aggregieren ueber alle Felder.

4. **Laengsschnitt-Analyse der Richtlinien-Wirkung:** Ob die TED-Reformen 2019-2023 (neue eForms-Standard-Formulare) die Datenqualitaet verbessert haben, ist noch nicht systematisch untersucht. Fazekas 2024 deckt nur bis 2021 ab.

5. **Interoperabilitaet mit nationalen Systemen:** Die Abdeckungsluecke zwischen nationalen Vergabeplattformen (unterhalb der EU-Schwellenwerte) und TED ist qualitativ beschrieben, aber quantitativ nicht systematisch erfasst.

---

## Quellen (URLs)

- Soylu et al. 2022 (MDPI): https://www.mdpi.com/2078-2489/13/2/99
- Prier et al. 2018 (IJPM): https://www.inderscienceonline.com/doi/abs/10.1504/IJPM.2018.095655
- Fazekas & Kocsis 2020 (BJPS): https://ideas.repec.org/a/cup/bjposi/v50y2020i1p155-164_7.html
- Fazekas et al. 2024 (Data in Brief): https://www.sciencedirect.com/science/article/pii/S2352340924003810
- FOPPA 2023 (Scientific Data): https://www.nature.com/articles/s41597-023-02213-z
- GovTransparency PP Data Processing 2025: https://www.govtransparency.eu/wp-content/uploads/2025/06/PP_data_processing_20250613.pdf
- Quality Issues of PP Open Data (Springer 2018): https://link.springer.com/chapter/10.1007/978-3-319-98349-3_14
