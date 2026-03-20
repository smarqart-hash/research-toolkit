# Facet 4: Data Standards — OCDS & eForms

Research Date: 2026-03-20
Facet: Data Standards in Public Procurement (OCDS, eForms, Interoperabilität)
Seed Papers: Telles 2025 (eForms-Kritik), Soylu et al. 2022 (DQ Barriers)

---

## Papers

| Titel | Erstautor | Jahr | DOI / URL | Zitationen | Institution | Land |
|-------|-----------|------|-----------|------------|-------------|------|
| Correcting the lost decade of electronic public procurement in the EU | Pedro Telles | 2025 | 10.1007/s12027-025-00851-x | — | Swansea University (ERA Forum / Springer) | GB |
| Looking Into the Public Procurement Data Space and eForms | Pedro Telles | 2024 | hdl.handle.net/10398/82ee3fd9 | — | CBS / Swansea University | GB |
| The evolution of electronic public procurement under Directive 2014/24/EU | Pedro Telles | 2024 | papers.ssrn.com/sol3/papers.cfm?abstract_id=4989521 | — | Swansea University | GB |
| Data Quality Barriers for Transparency in Public Procurement | Ahmet Soylu et al. | 2022 | 10.3390/info13020099 | 25 | OsloMet | NO |
| TheyBuyForYou platform and knowledge graph | Ahmet Soylu et al. | 2022 | 10.3233/sw-210442 | 26 | OsloMet / King's College London | NO/GB |
| From Public E-Procurement 3.0 to E-Procurement 4.0 (Literature Review) | Aristotelis Mavidis | 2022 | 10.3390/su141811252 | 33 | International Hellenic University | GR |
| Framework for interoperable public service architectures (PEPPOL) | Andreas Schmitz | 2022 | 10.1145/3543434.3543473 | 4 | Koblenz University of Applied Sciences | DE |
| The eForms Regulation and Sustainable Public Procurement Data Collection | Nadia-Ariadna Sava | 2023 | 10.21552/epppl/2023/3/5 | 2 | Babes-Bolyai University | RO |
| Looking at public procurement data in Europe in high-definition (OCP Blog) | Karolis Granickas | 2023 | open-contracting.org/2023/04/25 | — | Open Contracting Partnership | INT |
| OCDS for the European Union Profile v1.0 | Open Contracting Partnership | 2023+ | standard.open-contracting.org/profiles/eu | — | OCP | INT |
| Enhancing Public Procurement via Integrated Knowledge Graph | Soylu et al. | 2020 | 10.1007/978-3-030-62466-8_27 | — | OsloMet | NO |
| Open Contracting Data Standard (World Bank Reference) | World Bank / OCP | 2021 | documents1.worldbank.org/curated/en/744551614955316901 | — | World Bank | INT |

---

## Zusammenfassung

Der Open Contracting Data Standard (OCDS) ist der einzige internationale offene Standard fuer die Publikation von Vergabedaten ueber alle fuenf Beschaffungsphasen (Planung bis Durchfuehrung) und wird von G20/G7 unterstuetzt. Das EU-spezifische eForms-System (verpflichtend ab Oktober 2023) verbessert Datenvollstaendigkeit im TED-System, folgt jedoch einem notice-basierten Ansatz, der Informationen fragmentiert ueber mehrere Bekanntmachungen verteilt — im Gegensatz zum OCDS-Mechanismus, der Updates in einem einheitlichen Vergabedatensatz konsolidiert. Pedro Telles (2024/2025) kritisiert, dass eForms und der Public Procurement Data Space (PPDS) zwar Fortschritte bringen, aber strukturell begrenzt bleiben, weil sie analoge Notiz-Konzepte digital imitieren statt eine echte datenzentrierte Architektur zu schaffen. Soylu et al. (2022) zeigen mit dem TheyBuyForYou Knowledge Graph, dass Interoperabilitaet nur via Linked-Data-Integration und gemeinsamer Ontologie erreichbar ist, da technische Heterogenitaet und proprietaere Identifikatoren (z.B. DUNS) systematische Barrieren darstellen. Das OCDS-for-EU-Profil versucht eine Bruecke zwischen eForms und OCDS zu bauen, indem es das eForms-Modell integriert und OCDS-spezifische Verknuepfungen ermoeogelicht.

---

## Forschungsluecken

1. **Empirische Evaluierung der PPDS-Wirkung**: Der Public Procurement Data Space ist seit September 2024 operational — es fehlen empirische Studien zu tatsaechlicher Interoperabilitaet, Datenqualitaet und Nutzungseffekten in der Praxis.

2. **OCDS-for-EU Adoption**: Es gibt kaum Forschung zur praktischen Implementierungstiefe des OCDS-for-EU-Profils in Mitgliedstaaten — insbesondere ob nationale eSender-Systeme das Profil tatsaechlich unterstuetzen oder nur nominell implementieren.

3. **Below-Threshold-Daten**: eForms erfasst primaer EU-schwellenwertrelevante Vergaben. Wie nationale Datenstandards (unterhalb der EU-Schwellenwerte) mit eForms/OCDS interoperabel werden sollen, ist theoretisch und empirisch weitgehend unbearbeitet.

4. **Datenmodell-Vergleichsstudien**: Systematische Vergleiche zwischen eForms-Datenmodell, OCDS-Schema und nationalen Standards (z.B. deutsches XVergabe, franzoesisches DUME) fehlen — sowohl technisch (Schema-Mapping) als auch normativ (welcher Standard foerdert welche Transparenzziele besser).

5. **Incentive-Strukturen fuer Datenqualitaet**: Telles (2025) identifiziert einen Interessenskonflikt zwischen EU-Kommissionszielen und Implementierungsaufwand der Mitgliedstaaten — empirische Studien zum tatsaechlichen Compliance-Verhalten und den Datenqualitaetsunterschieden zwischen Mitgliedstaaten fehlen.

---

## Quellen

- Telles (2025): https://link.springer.com/article/10.1007/s12027-025-00851-x
- Telles (2024, CBS): https://research.cbs.dk/en/publications/looking-into-the-public-procurement-data-space-and-eforms
- Telles (2024, SSRN): https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4989521
- Soylu et al. (2022, DQ Barriers): https://www.mdpi.com/2078-2489/13/2/99
- Soylu et al. (2022, TBFY KG): https://content.iospress.com/articles/semantic-web/sw210442
- OCP Blog (2023): https://www.open-contracting.org/2023/04/25/looking-at-public-procurement-data-in-europe-in-high-definition/
- OCDS for EU Profile: https://standard.open-contracting.org/profiles/eu/latest/en/
- PPDS (EIPA): https://www.eipa.eu/blog/the-future-of-public-procurement-deploying-the-new-public-procurement-data-space-ppds/
- eForms GitHub Issue #260 (OCDS): https://github.com/eForms/eForms/issues/260
- OECD Digital Procurement (2025): https://www.oecd.org/content/dam/oecd/en/publications/reports/2025/06/digital-transformation-of-public-procurement_90ace30d/79651651-en.pdf
