# ABM Go-to-Market Framework — CID GmbH

> Erstellt: 2026-03-05 | Methodik-Dokument

## Ziel

50 Account-basierte Zielkunden fuer CID identifizieren, priorisieren und mit personalisierten Value Propositions versehen.

## Tier-Struktur

| Tier | Accounts | Tiefe | Personas |
|------|----------|-------|----------|
| Tier 1 | 10 | Deep Research: individuelle Value Props, Custom Content | 3-5 (Multi-Threading) |
| Tier 2 | 15 | Segment-personalisiert: Branchen-Value-Prop + Account-Spezifika | 2 |
| Tier 3 | 25 | Template + Kontext: Branchen-Template + Firmenname/Pain Points | 1 |

## Branchen-Verteilung

| Branche | Tier 1 | Tier 2 | Tier 3 | Gesamt | Begruendung |
|---------|--------|--------|--------|--------|-------------|
| Industrie/Manufacturing | 5 | 8 | 12 | 25 | Staerkste Referenzbasis (Audi, Bosch, Knorr-Bremse, Schaeffler, Trumpf) |
| Handel/Retail | 3 | 5 | 7 | 15 | Bewiesener Track Record (Strauss), 20+ Jahre |
| Pharma/Life Sciences | 2 | 2 | 6 | 10 | Regulierungsdruck (GxP), Datenschutz, Security-Fit |

## ICP-Scoring (Ideal Customer Profile)

Jeder Account-Kandidat wird nach 7 Kriterien bewertet (Score 0-100):

| Kriterium | Gewicht | Scoring-Logik |
|-----------|---------|---------------|
| Umsatz >100 Mio. EUR | 20% | >500M=20, >250M=15, >100M=10, <100M=5 |
| DACH-HQ oder starke DACH-Praesenz | 15% | HQ in DACH=15, Niederlassung=10, kein DACH=0 |
| Sichtbarer Digitalisierungsbedarf | 20% | Aktive Initiativen=20, Stellenausschreibungen=15, unklar=5 |
| Regulierungsdruck (NIS2/GxP/DORA) | 15% | Direkt betroffen=15, indirekt=10, nein=0 |
| Kein dominanter IT-Dienstleister | 15% | Kein bekannter=15, mehrere Partner=10, Exklusivpartner=0 |
| Tech Stack Fit (Java, Cloud, Data/AI) | 10% | Hoher Fit=10, teilweise=5, kein Fit=0 |
| Warm Intro moeglich | 5% | Ja=5, vielleicht=3, nein=0 |

**Schwellenwerte:**
- Tier 1: Score >= 75
- Tier 2: Score >= 55
- Tier 3: Score >= 40
- <40: Nicht in Scope

## Trigger-Events (Tier-Boost)

Ein aktiver Trigger hebt einen Account um 1 Tier (z.B. Tier-3 → Tier-2):

| Trigger | Signal | Quelle |
|---------|--------|--------|
| CTO/CIO-Wechsel | Neue IT-Fuehrung = neue Partnerwahl | LinkedIn, Presseberichte |
| IT-Ausschreibung | Aktiver Bedarf, offenes Budget | Vergabeplattformen, News |
| NIS2-Compliance-Deadline | Regulatorischer Druck, Security-Bedarf | Branchenberichte |
| M&A / Carve-Out | IT-Separation, System-Integration | Geschaeftsberichte, News |
| Legacy-Abloesung angekuendigt | Modernisierungsprojekt, Budget vorhanden | Stellenanzeigen, Konferenzen |

## Persona-Framework

| Persona | Typische Titel | Pain Point | CID Value Prop |
|---------|---------------|------------|----------------|
| Tech-Entscheider | CTO, VP Engineering | Legacy-Systeme, Fachkraeftemangel, Time-to-Market | End-to-End Delivery, 260+ MA, Nearshore |
| Security-Verantwortlicher | CISO, Head IT Security | NIS2/Compliance, OT/IT-Konvergenz | Security-by-Design als DNA |
| Digital-Stratege | CDO, Head of Digital | Digitalisierungs-Roadmap, KI-Integration | Strategie bis Betrieb aus einer Hand |
| IT-Operations | Head Infrastructure, Cloud Architect | Multi-Cloud-Komplexitaet, Vendor Lock-in | Pragmatischer Cloud-Ansatz, Managed Ops |
| Fachbereich | Bereichsleiter Produktion/Einkauf/Vertrieb | Prozessdigitalisierung, Datensilos | Data/AI + Branchenverstaendnis |

**Ansprache-Tiefe:**
- Tier 1: Multi-Threading — min. 3 Personas parallel
- Tier 2: 2 Personas (Tech-Entscheider + 1 weiterer)
- Tier 3: 1 Persona (primaerer Entscheider)

## Recherche-Vorgehen pro Branche

1. **Longlist** — Web-Research: Branchenverzeichnisse, Rankings, Umsatz-Filter >100M EUR, DACH
2. **ICP-Scoring** — Gewichtete Bewertung → Shortlist
3. **Trigger-Scan** — Events recherchieren, Tier-Boost anwenden
4. **Tier-Zuweisung** — Top-Scores → Tier 1, Mitte → Tier 2, Rest → Tier 3
5. **Deep Research (Tier 1+2)** — Website, Impressum, Geschaeftsbericht, LinkedIn Org-Chart, News, Tech Stack via Job-Postings
6. **Value Prop Matching** — Persona x Pain Point x CID-USP = individualisierte Ansprache

## CID Referenz-Assets fuer Ansprache

| Referenz | Branche | Nutzbar fuer |
|----------|---------|-------------|
| Audi | Automotive/Industrie | Manufacturing, Automotive-Accounts |
| Bosch | Industrie/IoT | Manufacturing, IoT, Cross-Industry |
| Knorr-Bremse | Industrie/Mobility | Manufacturing, Safety-Critical |
| Schaeffler | Industrie/Automotive | Manufacturing, OT/IT |
| Trumpf | Industrie/Laser | Manufacturing, High-Tech |
| Strauss | Handel/Retail | Retail, E-Commerce |
| JP Morgan | Finance | (eingeschraenkt nutzbar — fehlende Zertifikate) |
