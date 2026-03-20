# Facette 2: Entity Resolution in Public Procurement

**Research Brief — Facet 2 von N**
Datum: 2026-03-20
Scope: Entity Resolution, Record Linkage, Deduplication in oeffentlichen Vergabedaten; Buyer/Supplier Matching, Knowledge Graphs, Identifier-Systeme

---

## Paper-Tabelle

| Titel | Erstautor | Institution | Land | Jahr | Zitierungen | DOI |
|-------|-----------|-------------|------|------|-------------|-----|
| Global Contract-level Public Procurement Dataset | Mihaly Fazekas | Central European University Wien | AT | 2024 | — | 10.1016/j.dib.2024.110412 |
| TheyBuyForYou Platform and Knowledge Graph: Expanding Horizons in Public Procurement with Open Linked Data | Ahmet Soylu | SINTEF Digital / NTNU | NO | 2022 | ~40 | 10.3233/SW-210442 |
| Linked Open Data for Public Procurement | Vojtech Svatek | University of Economics Prague | CZ | 2014 | ~120 | 10.1007/978-3-319-09846-3_10 |
| Matchmaking Public Procurement Linked Open Data | Jindrich Mynarz | University of Economics Prague | CZ | 2015 | ~40 | 10.1007/978-3-319-26148-5_27 |
| Towards an Ontology for Public Procurement Based on the Open Contracting Data Standard | (Werder et al.) | — | — | 2019 | ~25 | 10.1007/978-3-030-29374-1_19 |
| Data Quality Barriers for Transparency in Public Procurement | (unbekannt) | — | — | 2022 | — | 10.3390/info13020099 |
| Enhancing Public Procurement in the EU Through Constructing and Exploiting an Integrated Knowledge Graph | (TBFY Team) | SINTEF Digital | NO | 2020 | ~15 | 10.1007/978-3-030-62466-8_27 |
| Detection of Fraud in Public Procurement Using Data-Driven Methods: A Systematic Mapping Study | (Springer Nature) | — | — | 2025 | — | 10.1140/epjds/s13688-025-00569-3 |

**Seed-Papers (bestaetigt):**
- Fazekas et al. 2024 (GPPD): DOI 10.1016/j.dib.2024.110412 — 72 Mio. Contracts, 42 Laender, Body Matching via Name + Source-ID + Adressfelder, `buyer_masterid` / `bidder_masterid`
- Soylu et al. 2022 (TBFY): DOI 10.3233/SW-210442 — 152 Mio. Tripel, 1.58 Mio. Tenders, Entity Linking via OpenOpps + OpenCorporates, OCDS-Ontologie + euBusinessGraph-Ontologie

---

## Zusammenfassung

Entity Resolution in oeffentlichen Vergabedaten ist ein junges, aber wachsendes Forschungsfeld an der Schnittstelle von Data Integration, Semantic Web und Public-Sector Analytics. Der dominante Ansatz ist approximatives Record Linkage auf Basis von Name, Adresse und verfuegbaren Quellenidentifiern — ein Muster das sowohl Fazekas et al. (GPPD 2024, `buyer_masterid`/`bidder_masterid`) als auch das TBFY Knowledge Graph-Projekt (Soylu et al. 2022, Entity Linking ueber OpenCorporates) nutzen. Das Semantic-Web-Lager (Mynarz, Klimek, Svatek; 2014-2016) hat fruehzeitig Public Contracts Ontologie und LOD-Matching etabliert, waehrend neuere Arbeiten Fraud Detection via Machine Learning und Social Network Analysis ergaenzen, ohne das ER-Problem systematisch zu adressieren. Identifier-Systeme (LEI, DUNS, nationale Handelsregisternummern) sind im Fluss: Die USA haben DUNS 2022 durch SAM.gov ersetzt; die EU entwickelt mit dem eProcurement Ontology (ePO) und dem Public Procurement Data Space (PPDS, 2024) neue Infrastruktur. Matching-Qualitaet wird selten evaluiert — Precision/Recall-Benchmarks fuer Buyer- und Supplier-Matching auf echten Vergabedaten fehlen in der Literatur fast vollstaendig.

---

## Forschungsluecken

1. **Kein standardisierter ER-Benchmark fuer Vergabedaten**: Es existiert kein publizierter Ground-Truth-Datensatz mit Precision/Recall-Metriken fuer Buyer- oder Supplier-Matching auf oeffentlichen Vergabedaten (z.B. TED, OCDS-Daten). Bestehende Systeme (GPPD, TBFY) beschreiben ihre Methodik, evaluieren sie aber nicht systematisch gegen externe Register.

2. **Cross-Country Identifier Interoperabilitaet**: Nationale Unternehmensidentifier (HRB, SIREN, Companies House, KvK) sind nicht automatisch verbunden. Der Uebergang von DUNS zu LEI ist in der Procurement-Literatur kaum untersucht. Der EU PPDS-Rollout (2024-2025) schafft neuen Forschungsbedarf fuer grenzueberschreitendes Entity Matching.

3. **LLM-gestuetztes Entity Matching in Procurement**: Aktuelle Arbeiten zu Deep-Learning-basiertem ER (Ditto, Starmie, etc.) werden nicht auf Vergabedaten angewendet. Insbesondere multilinguale Firmennamen (DE/FR/PL) und Abkuerzungsvielfalt (GmbH, S.A., Sp. z o.o.) bei TED-Daten sind unbehandelt.

4. **Buyer-seitige Fragmentierung**: Vergabende Stellen (Buyer) treten in Vergabedaten unter inkonsistenten Namen auf (Abteilung vs. Behoerde vs. Gemeinde). GPPD adressiert dies mit `buyer_masterid`, aber die Methodik ist nicht replizierbar publiziert und nicht auf andere Laender uebertragbar gemacht.

5. **Temporal Entity Resolution**: Firmenfusionen, -umbenennungen und -insolvenz ueber Zeit werden in keinem bekannten Procurement-ER-System beruecksichtigt. Ein Supplier der 2018 als "Acme GmbH" auftritt und 2022 als "New Acme AG" — nach Akquisition — wird typischerweise als zwei separate Entitaeten behandelt.

---

## Quellen (URLs)

- https://www.sciencedirect.com/science/article/pii/S2352340924003810
- https://pmc.ncbi.nlm.nih.gov/articles/PMC11063991/
- https://doi.org/10.3233/sw-210442
- https://kclpure.kcl.ac.uk/portal/en/publications/theybuyforyou-platform-and-knowledge-graph-expanding-horizons-in-
- https://link.springer.com/chapter/10.1007/978-3-319-09846-3_10
- https://mynarz.net/dissertation/
- https://link.springer.com/chapter/10.1007/978-3-319-26148-5_27
- https://www.mdpi.com/2078-2489/13/2/99
- https://link.springer.com/article/10.1140/epjds/s13688-025-00569-3
- https://www.govtransparency.eu/global-contract-level-public-procurement-dataset/
