# Foerderrichtlinien in Deutschland — Recherche-Synthese

> Stand: 2026-03-05 | Quellen: Wissensstand Mai 2025 (kein Live-Web-Zugriff)

## Wer foerdert?

| Ministerium | Schwerpunkt | Portal |
|---|---|---|
| **BMBF** | Forschung & Innovation (groesster Einzelfoerderer) | foerderportal.bund.de |
| **BMWK** | Mittelstand, Energie, Digitalisierung | foerderdatenbank.de |
| **BMAS** | Arbeitsmarkt, ESF-Programme | esf.de |
| **BMUV** | Umweltinnovationen | z-u-g.org (ZUG) |
| **BMEL** | Agrarforschung, laendlicher Raum | — |
| **BMDV** | Breitband, Mobilitaet | — |
| **BMG/BMFSFJ** | Gesundheit / Jugend & Demokratie | — |

## Wo stehen Foerderrichtlinien?

1. **Bundesanzeiger** (bundesanzeiger.de) — rechtlich verbindliche Veroeffentlichung (HTML + PDF)
2. **Ministeriums-Websites** — unter "Foerderung" / "Bekanntmachungen"
3. **Projekttraeger** (DLR-PT, VDI/VDE-IT, PTJ) — operative Details + Fristen
4. **easy-Online** (easy-online.de) — zentrales Antragsportal

## Datenbanken & Aggregatoren

| Datenbank | Scope | Aktualisierung | Zugang |
|---|---|---|---|
| **foerderdatenbank.de** | ~2.500+ Programme (Bund+Laender+EU) | 1-4 Wochen Verzoegerung | Frei, kein API |
| **ELFI** (elfi.info) | Wissenschaftsfoerderung, sehr detailliert | Taeglich | Kostenpflichtig (Hochschullizenzen) |
| **foerderinfo.bund.de** | Forschungsfoerderung (DFG, BMBF, EU) | Woechentlich-monatlich | Frei |
| **Foerderkatalog** (foerderportal.bund.de/foekat) | BMBF-Projektdatenbank | — | Frei |
| **EU Funding & Tenders** | Horizon Europe, ERC, EIC, MSCA | Sofort nach Launch | Frei |

## Struktur einer Foerderrichtlinie

Kein formales Schema — de-facto-Standard aus VV-BHO (§§ 23/44):

1. **Zuwendungszweck** / Foerderziel
2. **Gegenstand** der Foerderung
3. **Zuwendungsempfaenger** (wer darf beantragen)
4. **Zuwendungsvoraussetzungen**
5. **Art, Umfang, Hoehe** (Foerderquoten, Hoechstbetraege)
6. **Verfahren** (Antrag, Bewilligungsbehoerde, Projekttraeger)
7. **Geltungsdauer** / Inkrafttreten

## Begriffe

- **Foerderprogramm** = politisches Dach (z.B. "KMU-innovativ")
- **Foerderrichtlinie** = rechtlich bindende Verwaltungsvorschrift
- **Foerderbekanntmachung** = konkreter zeitlich begrenzter Call unter einer Richtlinie

## Sonderfaelle

- **Prototype Fund** (BMBF via OKF): Eigenes Webformular, bewusst niedrigschwellig
- **SPRIND**: Eigene Challenge-Formate, keine klassische ANBest-P-Logik
- **BMBF Softwareforschung**: Standard-Verfahren ueber Projekttraeger + easy-Online

## Maschinenlesbare Zugaenge (Tiefenrecherche)

Kein deutsches Aequivalent zu grants.gov (USA). Die Lage im Detail:

### Oeffentliche APIs & Feeds

| Quelle | Zugang | Details |
|---|---|---|
| **foerderdatenbank.de** | RSS 2.0 (2 Feeds) | Foerderprogramme + Pressemitteilungen. Kein JSON, kein Bulk-Download |
| **CORDIS** (EU) | REST API + SPARQL | Bester Zugang. Kostenloser API-Key (EU Login). JSON/XML/CSV. OpenAPI-Docs. R-Package verfuegbar |
| **EU Funding & Tenders** | API existiert | JS-basiert, schwer zugaenglich. CORDIS ist besser |
| **GovData.de** | CKAN-API | 120k+ Datensaetze, aber kaum Foerderdaten |
| **Bundesanzeiger** | Keine API | Nur HTML/PDF, kein maschinenlesbares Format |
| **foerderportal.bund.de** | Keine API | Reine Webplattform |
| **easy-Online** | Keine API | Browser-Formularsystem |

Nuetzliche Ressourcen:
- [bund.dev](https://bund.dev) — Community-Projekt, dokumentiert Bundes-APIs
- [github.com/bundesapi](https://github.com/bundesapi) — Open-Source Bundes-API-Sammlung

### Rechtliche Grundlage

**Datennutzungsgesetz (DNG)** + Novelle §12a EGovG verpflichten Bundesbehoerden zur Veroeffentlichung ("open by design and by default"). Foerderdaten sind aber nicht als hochwertige Datensaetze klassifiziert — Umsetzung hinkt massiv.

### Kommerzielle / Community-Plattformen

| Plattform | Typ | API? |
|---|---|---|
| **Foerderdata** (foerderdata.de, febis Service GmbH) | Kommerziell, Fokus Energieeffizienz/Bau | Nein, B2C mit Antragsbegleitung |
| **Foerderpilot** (foerderpilot.com) | AI-gestuetzter Foerderfinder fuer Unternehmen | Nein |
| **foerdersuche.org** | 10.500 Stiftungen, Non-Profit-Fokus | Nein |
| **Clever Funding** (clever-funding.de) | Beratung Forschungszulage | Nein, Beratungsmodell |
| **SIGU Foerderfinder** (sigu-plattform.de) | Soziale Innovationen, AI-kuratiert | Nein |
| **Subsidy4U** (github.com/Atypis/subsidy4u) | Open Source MCP-Server | Scrapt foerderdatenbank.de per Playwright. In Entwicklung, fragil |

**Hinweis:** "foerderal" und "subsidia" als eigenstaendige Plattformen existieren nicht. Moeglicherweise Verwechslung mit Foerderdata bzw. Subsidy4U.

### Fazit

Der deutsche Foerdermittel-Bereich ist eine **API-Wueste**. Einzige brauchbare Zugaenge:
1. **CORDIS REST API** — fuer EU-Foerderungen (vollstaendig, gut dokumentiert)
2. **RSS-Feeds foerderdatenbank.de** — fuer deutsche Programme (minimaler Datenumfang)
3. **Scraping** — fuer alles andere (fragil, rechtlich grau)

## Quellen

- [foerderdatenbank.de RSS](https://www.foerderdatenbank.de/FDB/DE/Service/RSS/rss.html)
- [CORDIS Data Extraction API](https://cordis.europa.eu/about/dataextractions-api)
- [CORDIS Services](https://cordis.europa.eu/about/services)
- [KTH CORDIS R-Package](https://github.com/KTH-Library/cordis)
- [bund.dev](https://bund.dev/)
- [github.com/bundesapi](https://github.com/bundesapi)
- [Subsidy4U MCP Server](https://lobehub.com/mcp/atypis-subsidy4u)
- [Datennutzungsgesetz - BMWK](https://www.bundeswirtschaftsministerium.de/Redaktion/DE/Artikel/Service/Gesetzesvorhaben/zweites-open-data-gesetz-und-datennutzungsgesetz.html)
- [§12a EGovG](https://www.gesetze-im-internet.de/egovg/__12a.html)
