# Research Brief: Qualitaet europaeischer Vergabedaten
> Stand: Maerz 2026 | 5 Facetten recherchiert (OpenAlex + WebSearch)

## TL;DR

Die empirische Forschung zu TED-Datenqualitaet ist duenn: Nur ~5 Studien quantifizieren Probleme direkt, waehrend ~30 Papers TED als Datenquelle nutzen ohne ihre Qualitaet systematisch zu pruefen. Das Feld wird von einer kleinen Gruppe dominiert (GTI Budapest, OsloMet, Swansea). Zentrale Luecken: Keine EU-weite Field-Level-Completeness-Matrix, keine publizierte CN-CAN Coverage Rate, keine Evaluation der eForms-Reform. Single-Bidding stieg EU-weit von 23,5% (2011) auf 41,8% (2021) — ein dramatischer Befund, der aber auf Daten beruht, deren Qualitaet selbst nicht systematisch geprueft wurde.

---

## 1. Kernidee & Einordnung

"Vergabedatenqualitaet" ist kein etabliertes Forschungsfeld, sondern ein Querschnittsthema an der Schnittstelle von:
- **Korruptionsforschung** (Fazekas-Cluster: CRI, Single-Bidding als Proxy)
- **Open Data / Semantic Web** (Soylu-Cluster: TBFY Knowledge Graph, Linked Data)
- **E-Government / Rechtsforschung** (Telles: eForms-Kritik, Richtlinien-Analyse)
- **Data Science / Administrative Data Quality** (Methodentransfer aus Health, Welfare, Census)

Die Forschung ist stark projektgetrieben: TheyBuyForYou (H2020, 2018-2021), FALCON/Horizon Europe (GTI, laufend), und OpenOpps (UK) haben die meisten empirischen Beitraege produziert. Ausserhalb dieser Projekte gibt es kaum systematische Datenqualitaetsforschung zu TED.

---

## 2. Schluesselpersonen & Institutionen

| Name | Institution | Land | Schwerpunkt | Schluessel-Beitrag |
|------|-------------|------|-------------|-------------------|
| **Mihaly Fazekas** | Government Transparency Institute (GTI) | HU | Corruption Risk Indicators, GPPD | CRI-Framework, opentender.eu, 72 Mio. Vertraege |
| **Ahmet Soylu** | OsloMet / NTNU / SINTEF | NO | Knowledge Graphs, DQ Barriers | TBFY, 152 Mio. Tripel, DQ-Barriers-Paper |
| **Pedro Telles** | Swansea University | GB | eForms, PPDS, Rechtsanalyse | "Lost Decade" Kritik, PPDS-Analyse |
| **Gabor Kocsis** | GTI Budapest | HU | CRI-Methodik | Co-Autor CRI-Paper (177 Zit.) |
| **Agnes Czibik** | GTI Budapest | HU | CRI-Updates, Validierung | Updated opentender.eu Framework |
| **Eric Prier** | Florida Atlantic University | US | TED-Nutzbarkeit | "Possibilities and Pitfalls" (2018) |
| **Vojtech Svatek** | University of Economics Prague | CZ | LOD, Procurement Ontologie | Public Contracts Ontology (2014) |
| **Jindrich Mynarz** | University of Economics Prague | CZ | LOD Matchmaking | CPV-basiertes Matching |
| **Elizabeth David-Barrett** | University of Sussex | GB | Grand Corruption | Partisan Favoritism (101 Zit.) |
| **Karolis Granickas** | Open Contracting Partnership | INT | OCDS, Policy | OCDS-for-EU-Profil |

**Dominanz-Befund:** GTI Budapest (Fazekas et al.) hat ~60% aller empirischen Studien zu Korruptionsindikatoren in Vergabedaten produziert. OsloMet/SINTEF dominiert den Knowledge-Graph-Strang. Es fehlen unabhaengige Replikationsstudien.

---

## 3. Aktueller Forschungsstand

### 3.1 Top Papers

| # | Titel | Erstautor | Institution | Land | Jahr | Zit. | DOI |
|---|-------|-----------|-------------|------|------|------|-----|
| 1 | Uncovering High-Level Corruption (CRI) | Fazekas & Kocsis | GTI / Cambridge | HU/GB | 2020 | 177 | 10.1017/s0007123417000461 |
| 2 | Finding the Right Indicators | Ferwerda | Utrecht University | NL | 2016 | 109 | 10.1007/s10610-016-9312-3 |
| 3 | Grand Corruption and Government Change | David-Barrett | University of Sussex | GB | 2019 | 101 | 10.1007/s10610-019-09416-4 |
| 4 | TED: Possibilities and Pitfalls | Prier et al. | Florida Atlantic | US | 2018 | ~60 | 10.1504/IJPM.2018.095655 |
| 5 | DQ Barriers for Transparency | Soylu et al. | OsloMet | NO | 2022 | ~45 | 10.3390/info13020099 |
| 6 | Corruption in Transport Infrastructure | Fazekas | Cambridge | GB | 2018 | 40 | 10.1016/j.tra.2018.03.021 |
| 7 | LOD for Public Procurement | Svatek et al. | UE Prague | CZ | 2014 | ~120 | 10.1007/978-3-319-09846-3_10 |
| 8 | E-Procurement Literature Review | Mavidis | IHU | GR | 2022 | 33 | 10.3390/su141811252 |
| 9 | LOTED2 Ontology | Distinto | ISTC-CNR | IT | 2016 | 34 | 10.3233/sw-140151 |
| 10 | TBFY Knowledge Graph | Soylu et al. | OsloMet | NO | 2022 | ~26 | 10.3233/sw-210442 |

### 3.2 Was bekannt ist (mit Belegen)

**Datenqualitaet in TED:**
- CN-CAN-Linking ist optional und systematisch unvollstaendig — verhindert Lebenszyklus-Analyse (Soylu 2022)
- Placeholder-Eintraege (Wert = 0) ueberschreiten 10% in manchen Systemen; fuer TED EU-weit nicht quantifiziert (Fazekas 2024)
- 402+ zeitlich inkonsistente Vertraege in TED 2019 (Start > Ende) (Soylu 2022)
- Kein Verbesserungstrend 2011-2021 trotz neuer EU-Richtlinien (Fazekas 2024)
- TED-CSV-Struktur so komplex, dass sie Nutzbarkeit einschraenkt (Prier 2018)

**Single-Bidding:**
- EU-Schnitt stieg von 23,5% (2011) auf 41,8% (2021) — fast Verdopplung (ECA SR 28/2023)
- Osteuropa: 52%, Suedeuropa: 30%, Nord/West: 15-20% (ECA 2023)
- COVID/Notstaende verstaerken Single-Bidding signifikant (Fazekas 2024/2025)
- GTI-Paneldatensatz 2011-2025 fuer 30 Laender frei verfuegbar (GTI 2026)

**Entity Resolution:**
- GPPD nutzt buyer_masterid/bidder_masterid via Name + Source-ID + Adresse (Fazekas 2024)
- TBFY: Entity Linking ueber OpenCorporates, 152 Mio. Tripel (Soylu 2022)
- Kein standardisierter ER-Benchmark mit Precision/Recall (Luecke!)

**Data Standards:**
- eForms (ab Okt. 2023) verbessert Vollstaendigkeit, aber notice-basiert statt datenzentriert (Telles 2025)
- OCDS-for-EU-Profil brueckt eForms und OCDS (OCP 2023)
- PPDS seit Sept. 2024 operational — noch keine Evaluationsstudien (Telles 2024)

**Placeholder-Muster (Cross-Domain):**
- `999999999` in 63% grosser US-Kliniken als Preis-Placeholder (CMS 2025)
- `9999` als Geburtsjahr in Welfare-Daten (Goerge & Lee 2002)
- `0` als Organisations-ID in OCDS-Daten (Portugal IMPIC)
- `1900-01-01` als Datums-Placeholder in OCDS-Daten (OCP)

### 3.3 DACH-Beitraege

- **Andreas Schmitz** (FH Koblenz): PEPPOL-Interoperabilitaetsframework (2022)
- **XVergabe**: Deutscher Standard — kein systematischer Vergleich mit eForms/OCDS publiziert
- **DACH-Luecke**: Keine empirischen TED-Datenqualitaetsstudien mit DE/AT/CH-Fokus identifiziert. Deutsche Vergabedaten werden kaum beforscht — die Forschung ist in HU, NO, GB konzentriert.

### 3.4 Aktuelle Entwicklungen (2025-2026)

- GTI CRI-Framework Update (Kofran, Czibik, Fazekas, Maerz 2026) — opentender.eu
- GTI Paneldatensatz 2011-2025 (30 Laender, TED-basiert, FALCON/Horizon Europe)
- PPDS operational seit Sept. 2024 — erste Nutzungserfahrungen kommen
- Text-Mining fuer versteckte Zugangsbarrieren in Ausschreibungstexten (Katona & Fazekas 2024)
- "Procuring Low Growth" (Fazekas et al. 2025) — Single-Bidding ↔ makrooekonomische Outcomes

---

## 4. Offene Fragen & Forschungsluecken

### Kritische Luecken (niemand hat das gemacht)

| # | Luecke | Warum relevant |
|---|--------|----------------|
| 1 | **Field-Level Completeness Matrix** — Vollstaendigkeitsrate pro TED-Feld, pro Land, pro Jahr | Grundlage fuer jede DQ-Analyse; existiert nicht publiziert |
| 2 | **CN-CAN Coverage Rate** — Anteil valider Verknuepfungen Ausschreibung → Vergabe | Verhindert Lifecycle-Tracking; bekannt aber nicht beziffert |
| 3 | **eForms-Evaluierung** — Hat die Reform seit 2023 die DQ verbessert? | Wichtigste Policy-Frage; keine Studie |
| 4 | **EU-weite Placeholder-Quantifizierung** — Systematische Messung von Null/Sentinel-Werten | Qualitativ belegt, quantitativ offen |
| 5 | **ER-Benchmark** — Ground-Truth-Datensatz fuer Buyer/Supplier-Matching | Methodische Grundlage; fehlt komplett |

### Strukturelle Luecken

| # | Luecke | Details |
|---|--------|---------|
| 6 | **Below-Threshold** | Vergaben unter EU-Schwellenwert = Data Blackhole |
| 7 | **Kausalitaet** | Single-Bidding ↔ Korruption nur korrelativ belegt |
| 8 | **Replikation** | GTI-Dominanz ohne unabhaengige Replikation |
| 9 | **DACH-Forschung** | Keine DE/AT/CH-spezifischen DQ-Studien |
| 10 | **Temporal ER** | Firmenfusionen ueber Zeit nicht adressiert |
| 11 | **LLM-basiertes Matching** | Multilinguale Firmennamen (GmbH, S.A., Sp.z.o.o.) unbehandelt |
| 12 | **XVergabe ↔ eForms** | Kein Schema-Mapping publiziert |

---

## 5. Relevanz fuer Vergabe Monitor

Diese Luecken definieren den Forschungsbeitrag eines Vergabedaten-Monitors:

1. **Field-Level DQ Dashboard** → Luecke 1 + 4 direkt adressierbar
2. **CN-CAN Tracker** → Luecke 2 als Feature
3. **eForms-Qualitaetsvergleich** → Luecke 3 (vorher/nachher Okt 2023)
4. **Placeholder-Detektor** → Luecke 4 mit Methoden aus Facette 5
5. **DACH-Fokus** → Luecke 9 als Alleinstellungsmerkmal
6. **Below-Threshold-Integration** → Luecke 6 wenn nationale Daten eingebunden

Der Blog-Artikel sollte diese Luecken als "Was wir NICHT wissen" framen — und Vergabe Monitor als Werkzeug positionieren, das einige davon erstmals messbar macht.

---

## Quellen

### Primaerliteratur (mit DOI)
1. Fazekas & Kocsis (2020): [10.1017/s0007123417000461](https://doi.org/10.1017/s0007123417000461)
2. Fazekas et al. (2024): [10.1016/j.dib.2024.110412](https://doi.org/10.1016/j.dib.2024.110412)
3. Prier et al. (2018): [10.1504/IJPM.2018.095655](https://doi.org/10.1504/IJPM.2018.095655)
4. Soylu et al. (2022a): [10.3390/info13020099](https://doi.org/10.3390/info13020099)
5. Soylu et al. (2022b): [10.3233/sw-210442](https://doi.org/10.3233/sw-210442)
6. Telles (2025): [10.1007/s12027-025-00851-x](https://doi.org/10.1007/s12027-025-00851-x)
7. Potin et al. (2023): [10.1038/s41597-023-02213-z](https://doi.org/10.1038/s41597-023-02213-z)
8. Ferwerda (2016): [10.1007/s10610-016-9312-3](https://doi.org/10.1007/s10610-016-9312-3)
9. David-Barrett (2019): [10.1007/s10610-019-09416-4](https://doi.org/10.1007/s10610-019-09416-4)
10. Fazekas (2018): [10.1016/j.tra.2018.03.021](https://doi.org/10.1016/j.tra.2018.03.021)
11. Distinto (2016): [10.3233/sw-140151](https://doi.org/10.3233/sw-140151)
12. Svatek et al. (2014): [10.1007/978-3-319-09846-3_10](https://doi.org/10.1007/978-3-319-09846-3_10)
13. Mynarz et al. (2015): [10.1007/978-3-319-26148-5_27](https://doi.org/10.1007/978-3-319-26148-5_27)
14. Mavidis (2022): [10.3390/su141811252](https://doi.org/10.3390/su141811252)
15. Schmitz (2022): [10.1145/3543434.3543473](https://doi.org/10.1145/3543434.3543473)
16. Sava (2023): [10.21552/epppl/2023/3/5](https://doi.org/10.21552/epppl/2023/3/5)
17. Harron et al. (2017): [10.1177/2053951717745678](https://doi.org/10.1177/2053951717745678)
18. Andrade et al. (2026): [10.1186/s13054-025-05677-0](https://doi.org/10.1186/s13054-025-05677-0)

### Graue Literatur & Policy
19. ECA Special Report 28/2023: [eca.europa.eu/sr-2023-28](https://www.eca.europa.eu/en/publications/sr-2023-28)
20. GTI Datenpublikation 2011-2025: [govtransparency.eu](https://www.govtransparency.eu/national-and-regional-annual-aggregated-public-procurement-data-ted-2011-2025-version-202603/)
21. GTI CRI-Update 2026: [imonitor.govtransparency.eu](https://imonitor.govtransparency.eu/2026/03/12/corruption-risk-indicators-in-public-procurement-an-updated-opentender-eu-framework/)
22. OCP Blog (Granickas 2023): [open-contracting.org](https://www.open-contracting.org/2023/04/25/looking-at-public-procurement-data-in-europe-in-high-definition/)
23. OCDS-for-EU-Profil: [standard.open-contracting.org/profiles/eu](https://standard.open-contracting.org/profiles/eu/latest/en/)
24. Katona & Fazekas (2024): [govtransparency.eu/text-mining](https://www.govtransparency.eu/wp-content/uploads/2024/05/Katona-Fazekas_HU_text-miningPP-corruption240417_GTIpublish240430final.pdf)
25. Goerge & Lee (2002): [nap.nationalacademies.org](https://nap.nationalacademies.org/read/10206/chapter/9)
26. CMS Nine-Nines Guidance (2025): [cms.gov](https://www.cms.gov/priorities/key-initiatives/hospital-price-transparency/resources)
27. OCDS DQ Guidance: [standard.open-contracting.org](https://standard.open-contracting.org/latest/en/guidance/publish/quality/)

---

## Facetten-Dateien (Detail-Recherchen)

- [Facette 1: TED Data Quality](20260320-facet1-ted-dq.md)
- [Facette 2: Entity Resolution](20260320-facet2-entity-resolution.md)
- [Facette 3: Single-Bidding](20260320-facet3-single-bidding.md)
- [Facette 4: Data Standards](20260320-facet4-data-standards.md)
- [Facette 5: Placeholder Detection](20260320-facet5-placeholder-detection.md)
- [Brief (JSON)](20260320-ted-data-quality-brief.json)
