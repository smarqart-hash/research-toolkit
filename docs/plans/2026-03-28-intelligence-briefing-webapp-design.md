# Intelligence Briefing for Everybody — Product Design

> Stand: 28. Maerz 2026 | V1 MVP Design
> Research: 5 Agent-Reports in `docs/research/20260328-*.md`

---

## Vision

Eine Web-App die fuer 50 Cent akademisch fundierte Intelligence Briefings erstellt.
Gleichzeitig Portfolio-Piece, gesellschaftliches Statement und B2B-Lead-Generator.

**Positioning:** "Die einzige Research-Plattform, wo jeder Claim zu einer Quelle
rueckverfolgbar ist — akademisch fundiert, bias-transparent, fuer alle."

**Tagline:** "Research you can cite." (EN) / "Faktencheck statt Faktenflucht." (DE)

**Kern-Differenzierung vs. ChatGPT/Perplexity:**
Nicht schneller, sondern vertrauenswuerdiger. Jeder Claim hat eine Quelle.
Transparent: "Modell X macht die Synthese, aber 5 Quality Gates pruefen das Ergebnis."
Latenz ist Feature, nicht Bug (30s statt 3s = gruendliche Recherche).

---

## User Flow (V1)

```
┌─────────────────────────────────────────────────┐
│  Was willst du wissen?                          │
│  ┌───────────────────────────────────────────┐  │
│  │ Freitext: Thema, Claim oder Frage         │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  Modus:  ○ Forschungsstand                     │
│          ○ Fact-Check                          │
│          ○ Intelligence Brief                  │
│                                                 │
│  ▸ Erweiterte Optionen                         │
│    Sprache: DE / EN                            │
│    Tiefe: Quick (2-3 S.) / Standard (5 S.)     │
│    Stil: Akademisch / Journalistisch / B1      │
│    Perspektiv-Split: Ja/Nein (+0,50€)          │
│                                                 │
│  [ Briefing erstellen — 0,50€ ]                │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│  Dein Briefing wird erstellt...                 │
│  ████████░░░░ 65%                               │
│                                                 │
│  ✓ 47 Quellen durchsucht (S2 + OpenAlex + Exa) │
│  ✓ Top 12 gerankt nach Relevanz + Zitationen   │
│  → Draft wird geschrieben...                   │
│  ○ Fact-Check (Claim-Verification)             │
│  ○ Quality Gate                                │
│                                                 │
│  Transparenz-Box: "So arbeitet unsere Pipeline" │
│  [Multi-Source Search → Ranking → Draft →       │
│   Claim-Verification → Quality Gate → Output]   │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│  Dein Intelligence Briefing                     │
│  "Thema XY"                                     │
│                                                 │
│  [Volltext mit inline Citations + Live-Links]   │
│                                                 │
│  12 Quellen | 8 Claims verified | 2:34 Min      │
│                                                 │
│  [ PDF ] [ Teilen ] [ BibTeX ] [ Permalink ]    │
│                                                 │
│  --- Bei Perspektiv-Split: ---                  │
│  Tab A: "Konservativ-Leaning Lesart"            │
│  Tab B: "Progressiv-Leaning Lesart"             │
│  Hinweis: "Gleiche Quellen, andere Sprache."    │
└─────────────────────────────────────────────────┘
```

---

## Kern-Flow: Subject Decomposition First

Statt einer einzelnen Suche laeuft jedes Briefing ueber Subject Decomposition
(basierend auf `/research-brief` Skill). Das liefert deutlich bessere Ergebnisse.

```
User-Input (Thema / Claim / Frage)
    │
    ▼
Subject Decomposition (research-brief Pattern)
    │ → 3-6 Facetten mit eigenen Search-Queries
    │ → Scope, Exclusions, Leitfragen
    ▼
Parallel Search pro Facette (SS + OpenAlex + Exa)
    │ → 45-90 Quellen-Pool (3-6 Facetten × 15 Papers)
    ▼
Ranking + Dedup (paper_ranker, optional SPECTER2)
    │ → Top 15-20
    ▼
Draft (venue + voice)
    │ → Optional: Perspektiv-Split (2× Draft mit verschiedenen Voices)
    ▼
Claim Verification (optional, bei Fact-Check Modus)
    ▼
Quality Gate (7-dimensionale Rubrik)
    ▼
Output (HTML + PDF + BibTeX + Permalink)
```

**Vorteile gegenueber direktem Search:**
- Breitere Abdeckung: Jede Facette findet andere Quellen
- Weniger Off-Topic: Facetten haben fokussierte Queries
- Transparenter: User sieht wie sein Thema zerlegt wurde
- Schon gebaut: `/research-brief` Skill + `search_papers()` existieren

---

## Features V1

### Kern (MVP)
- **Subject Decomposition**: Thema → Facetten → parallele Recherche → Synthese
- **Forschungsstand**: Facetten-basierte Search → Rank → Draft
- **Fact-Check**: Claim → Decompose → Search → Verify → Report
- **Intelligence Brief**: Thema → Decompose → Search → Draft (Executive-Stil)
- **Perspektiv-Split** (Killer-Feature): Gleiche Facts, zwei Lesarten (Side-by-Side)
- **Public Gallery**: Fertige Briefings oeffentlich + teilbar (SEO-Moat)
- **Share + Social Cards**: OpenGraph, Twitter Cards, Permalink
- **Transparenz-Box**: Pipeline-Visualisierung im UI (was passiert im Backend)
- **KI-Disclosure**: Automatisch in jedem Output

### Venue-Profile (Output-Formate)
| Venue | Seiten | Sprache | Zielgruppe |
|-------|--------|---------|------------|
| Quick Impuls | 2-3 | DE/EN | Alle, schneller Ueberblick |
| Impuls (Kurzstudie) | 4-6 | DE | Policy, Journalisten, Stiftungen |
| Akademisch | 5-10 | DE/EN | Studierende, Researcher |
| B1 Verstaendlich | 2-3 | DE | Breite Oeffentlichkeit |
| Executive Brief | 1-2 | EN | Manager, Entscheider |

**Impuls-Format** (inspiriert von Kurzstudie-Venue):
Zusammenfassung → Ausgangslage → Kernanalyse → Handlungsempfehlungen (adressiert) → Quellen.
Kompakt, handlungsorientiert, 5-7 nummerierte Empfehlungen mit Stakeholder-Adressaten.

### Anti-Polarisierung: Perspektiv-Split
Gleiche Quellenbasis, zwei Draft-Durchlaeufe mit unterschiedlichen Voice-Profilen:
- **Konservativ-Leaning**: Ordnungspolitisch, Eigenverantwortung, Subsidiaritaet, Risiko-Fokus
- **Progressiv-Leaning**: Sozialpolitisch, Solidaritaet, Strukturkritik, Chancen-Fokus

WICHTIG: Nicht "beide Seiten sind gleich", sondern Transparenz darueber wo
Evidenz asymmetrisch ist. Output zeigt: "Hier ist Wissenschaft einig, hier nicht."

Side-by-Side Darstellung. Kostet 1€ statt 50ct (doppelter Draft).

---

## Pricing

| Tier | Preis | Was |
|------|-------|-----|
| Single | 0,50€ | 1 Briefing (alle Formate) |
| Perspektiv-Split | 1,00€ | Side-by-Side zwei Lesarten |
| Deep (Fact-Check) | 2,00€ | Mit Claim-Verification |

Kein Free Tier. 50ct ab dem ersten Briefing.
Payment: Stripe (oder Lemon Squeezy fuer einfacheres EU Micro-Payment).
Kein Account noetig. Email optional (fuer PDF-Zustellung).

Spaeter (V2): Pro-Abo 20€/Mo (unbegrenzt), Enterprise Custom.

---

## Tech-Architektur

### Stack
- **Frontend**: Next.js 15 (App Router) + TypeScript + Tailwind v4 + shadcn/ui
- **Hosting Frontend**: Vercel
- **Backend API**: FastAPI (Python) — Wrapper um bestehende Research-Pipeline
- **Hosting Backend**: Railway oder Fly.io
- **Payment**: Stripe Checkout (oder Lemon Squeezy)
- **Storage**: Supabase (Briefings als JSONB + HTML)
- **Queue**: Celery + Redis (async Briefing-Generierung)

### Architektur-Diagramm

```
Browser (Next.js on Vercel)
    │
    ├── /api/briefing/create   (Next.js API Route)
    │       │
    │       ├── Stripe Payment Intent / Free-Tier Check
    │       └── POST → FastAPI Backend
    │
    ├── /api/briefing/status   (SSE / Polling)
    │       └── GET → FastAPI Backend (Progress Updates)
    │
    └── /briefing/[id]         (Public Briefing Page)
            └── GET → Supabase

FastAPI Backend (Railway/Fly)
    │
    ├── POST /generate
    │       ├── search_papers()      ← forschungsstand.py
    │       ├── rank_papers()        ← paper_ranker.py
    │       ├── generate_draft()     ← drafting.py
    │       ├── verify_claims()      ← claim_verifier.py (optional)
    │       └── quality_gate()       ← reviewer.py
    │
    ├── GET /status/:job_id
    │       └── Progress aus Queue
    │
    └── GET /briefing/:id
            └── Fertiges Briefing als JSON
```

### Pipeline-Mapping (CLI → API)

| CLI Command | API Endpoint | Modus |
|-------------|-------------|-------|
| `/research-brief` | POST /generate (step 0) | Subject Decomposition |
| `search TOPIC` | POST /generate (step 1-2) | Pro Facette |
| `draft TOPIC --venue X` | POST /generate (step 3) | Forschungsstand, Brief |
| `check DOC --verify` | POST /generate (step 4) | Fact-Check |
| `review DOC` | POST /generate (step 5) | Quality Gate |

Die bestehende Pipeline mapped fast 1:1. FastAPI-Wrapper ruft dieselben
Funktionen auf die der CLI nutzt. Kein Rewrite noetig.

### Failure Modes

| Fehler | Auswirkung | Handling |
|--------|-----------|----------|
| S2/OpenAlex/Exa down | Weniger Quellen | Graceful Degradation: Pipeline laeuft mit verfuegbaren Quellen weiter. Min 1 Quelle muss antworten, sonst Abbruch + Refund. |
| LLM-Timeout (Decomposition/Draft) | Kein Output | 120s Timeout pro LLM-Call. Retry 1x. Danach: Fehler-Seite + automatischer Refund via Stripe. |
| Decomposition liefert Garbage | Schlechte Facetten | JSON-Schema-Validation auf Output. Facetten < 2 oder > 8 → Reject + Fallback auf direkten Search (ohne Decomposition). |
| Pipeline > 5 Min | User wartet zu lange | SSE-Updates halten User informiert. Hard-Timeout bei 8 Min → Partial Output liefern (was bisher fertig ist) + Hinweis. |
| Stripe Webhook fehlt | Bezahlt aber kein Briefing | Webhook-Retry (Stripe macht das automatisch). Idempotency-Key pro Briefing. Dead-Letter-Queue fuer manuelle Pruefung. |
| Exa Free-Tier erschoepft | Keine Web-Quellen | Exa wird uebersprungen, Warnung im Output. ~20 Briefings/Tag mit 6 Facetten im Free-Tier. |

**Timeout-Budget pro Step:**
- Decomposition: 15s
- Search (parallel, alle Facetten): 30s
- Ranking: 5s
- Draft: 45s (90s bei Perspektiv-Split)
- Verification: 30s (optional)
- Quality Gate: 15s
- **Gesamt: ~2-3 Min (Standard), ~4 Min (Deep + Split)**

### Perspektiv-Split Implementierung
Zwei Draft-Durchlaeufe mit unterschiedlichen Voice-Profilen:
1. `generate_draft(topic, venue, voice="konservativ_de")`
2. `generate_draft(topic, venue, voice="progressiv_de")`
Gleiche `search_results` als Input. Zwei neue Voice-Profile erstellen.

---

## Abgrenzung: "Warum nicht ChatGPT / Deep Research?"

### vs. ChatGPT / Claude (Chat)
1. **Halluzinations-Problem**: Gibt Antworten ohne pruefbare Quellen
2. **Daten vs. Intelligenz**: Wir suchen 50-100 Quellen, ranken, verifizieren Claims
3. **Vertrauen**: Typ 1 ("Glaub mir") vs. Typ 2 ("Pruef selbst") — wir sind Typ 2

### vs. Deep Research (ChatGPT Pro, Gemini Deep Research, Perplexity Pro)
Deep Research ist der staerkste Konkurrent. Aber:

| Dimension | Deep Research | Wir |
|-----------|-------------|-----|
| **Quellen** | Web-Crawl, unkuratiert | Akademische DBs (S2, OpenAlex) + Web (Exa) |
| **Methodik** | Black Box, kein Audit Trail | Subject Decomposition → Facetten → parallele Suche |
| **Verification** | Keine Claim-Verification | NLI-basierter Fact-Check pro Claim |
| **Transparenz** | "Hier ist mein Report" | Pipeline-Schritte live sichtbar, Provenance-Log |
| **Quellen-Qualitaet** | Blogs, Reddit, Wikipedia gemischt | Peer-reviewed Papers priorisiert, Citation-Ranking |
| **Output-Format** | Freitext, ein Stil | Venue + Voice konfigurierbar (akademisch, B1, Policy) |
| **Perspektiven** | Eine Perspektive | Side-by-Side Perspektiv-Split |
| **Preis** | $20-200/Mo Abo | 50 Cent pro Briefing, kein Abo |
| **Bias-Check** | Keiner | Self-Enhancement Bias Test (Double-Blind) |

**Kern-Argument:** Deep Research gibt dir einen langen Text. Wir geben dir einen
auditierbaren Forschungsprozess mit nachpruefbaren Claims. Das ist der Unterschied
zwischen "ein LLM hat das Internet gelesen" und "eine Research-Pipeline hat
akademische Quellen systematisch ausgewertet."

**Fuer die Landing Page (kurz):**
"Deep Research liest das Internet. Wir lesen die Forschung — und beweisen es."

Transparenz-Box im UI zeigt die 5 Pipeline-Steps live waehrend Generierung.
Details: `docs/research/20260328-positionierung.md`

---

## Zielgruppen-Priorisierung (aus Research)

| Prio | Segment | Warum | Kanal |
|------|---------|-------|-------|
| 1 | Journalisten / Fact-Checker | Hoechster Pain, hohe Conversion (4/5) | LinkedIn, Netzwerk Recherche, DJV |
| 2 | Studierende | Hoechstes Volumen, viral (4.5/5 Conversion) | Instagram, WhatsApp, Uni-Gruppen |
| 3 | Knowledge Workers | Bester Micro-Payment Fit | LinkedIn, Newsletter |
| 4 | Policy / Stiftungen | B2B Upsell Pfad | Direktansprache, Konferenzen |

---

## Tone of Voice (Marketing)

- Smart, selbstbewusst, leichte Ironie
- Kein Corporate-Sprech, kein Tech-Bro
- B1-tauglich (einfache Sprache als Default)
- Gesellschaftlicher Anspruch ohne Moralkeule
- "Das baue ich zum Fruehstueck" Energy — kompetent, nicht arrogant

---

## Infra-Grundlagen (Was schon existiert)

### Voice-Profile (2 vorhanden, 4 neu noetig)

Bestehend in `config/voice_profiles/`:
- `academic_de_voice.json` — Hochformales akademisches Deutsch (Konjunktiv II, 30-40% Passiv)
- `academic_en_voice.json` — Formales akademisches Englisch

Struktur pro Voice-Profil (Pydantic-Modell in `drafting.py`):
```
name, description, sentence_length, formality, passive_ratio,
typical_phrases, tone, transition_patterns, uncertainty_language,
dos, donts, structural_patterns, paragraph_length, evidence_style
```

**Neu zu erstellen fuer V1:**
- `konservativ_de_voice.json` — Ordnungspolitisch, Eigenverantwortung, Risiko-Fokus
- `progressiv_de_voice.json` — Sozialpolitisch, Solidaritaet, Chancen-Fokus
- `b1_de_voice.json` — Einfache Sprache, kurze Saetze, keine Fachbegriffe
- `executive_en_voice.json` — Kurz, entscheidungsorientiert, Bullet-freundlich

### Venue-Profile (9 vorhanden, 2 neu noetig)

Bestehend in `config/venue_profiles/` (alle mit Sections, Citation-Style, Review-Criteria):
- `kurzstudie_de` (3-7 S., DE, Handlungsempfehlungen) ← **Basis fuer Impuls**
- `policy_brief` (10-20 S., EN)
- `position_paper` (5-15 S., EN)
- `research_report` (30-80 S., EN)
- `literature_review` (20-40 S., EN)
- `conference_paper` (8-12 S., EN)
- `working_paper` (15-30 S., EN)
- `nature_communications` (5000 words, EN)
- `arxiv_cs_ai` (kein Limit, EN)

**Neu zu erstellen:**
- `quick_impuls_de.json` — 2-3 Seiten, verdichtet, B1-tauglich
- `executive_brief_en.json` — 1-2 Seiten, Decision-focused

### Research-Brief Skill (Subject Decomposition)

Skill-Datei: `.claude/skills/research-brief/SKILL.md`
Output-Format: JSON mit `topic, research_question, scope, core_terms, exclusions, facets[]`
Jede Facette hat: `name, description, search_query`

Fuer die Web-App: Skill-Logik in eine Python-Funktion extrahieren (`decompose_topic()`),
die den LLM-Call macht und das JSON zurueckgibt. Die Facetten werden dann parallel
an `search_papers()` uebergeben.

### Quellen-Infrastruktur (3 APIs, production-ready)

| Quelle | Client | Config | Status |
|--------|--------|--------|--------|
| Semantic Scholar | `semantic_scholar.py` | `S2_API_KEY` (optional) | 100 Papers/Query |
| OpenAlex | `openalex_client.py` | `OPENALEX_API_KEY` (optional) | 200 Papers/Query |
| Exa | `exa_client.py` | `EXA_API_KEY` (optional) | 50 Papers/Query, DACH-Domains |

Parallel via `asyncio.gather`. Dedup via DOI + Title-Hash.
Ranking: Citation-weighted + Recency + OA-Bonus + optional SPECTER2.

### Quality Gates (5-stufig, alle implementiert)

1. **Relevance Filter** — OpenAlex Pre-Filter (relevance_score < 0.5 raus)
2. **LLM Ranking Judge** — Relevanz 0-10, Score < 4 entfernt (`ranking_judge.py`)
3. **Claim Extraction** — FactScore-Pattern, atomare Claims (`claim_verifier.py`)
4. **NLI Verification** — Supported/Refuted/Neutral pro Claim
5. **Self-Enhancement Bias Test** — Double-Blind Scoring (`bias_test.py`)

### Review-System (7-dimensionale Rubrik)

`config/rubrics/` — akademisch, policy, antrag
`reviewer.py` — Verdict: PASS / PASS_WITH_CAVEATS / NEEDS_REVISION / REJECT
`review_loop.py` — Iterativ: Draft → Review → Revise → Re-Review (max 2 Revisionen)

### Provenance (Audit Trail)

`provenance.py` — Append-only JSONL: timestamp, phase, agent, action, source, claim, evidence_card_id
Volle Rueckverfolgbarkeit: Output-Claim → Source-Satz → Paper → DOI/URL

### Kostenrechnung pro Briefing

| Komponente | Kosten |
|-----------|--------|
| Search (3 APIs, 3-6 Facetten) | ~$0.02-0.08 |
| LLM: Decomposition | ~$0.01-0.02 |
| LLM: Draft | ~$0.05-0.10 |
| LLM: Verification (optional) | ~$0.05-0.10 |
| Infra (Queue, Cache, Hosting) | ~$0.05-0.10 |
| **Gesamt ohne Verification** | **~$0.15-0.30** |
| **Gesamt mit Verification** | **~$0.20-0.40** |
| **Retail: 0,50€ (Standard)** | **~40-60% Marge** |
| **Retail: 2,00€ (Deep)** | **~80% Marge** |

---

## Kern-Decisions (Stand 28. Maerz 2026)

| # | Decision | Entscheidung | Notiz |
|---|----------|-------------|-------|
| 1 | Repo-Struktur | **Getrennte Repos** — `research-toolkit/` (Python) + neue Repo `briefing-app/` (Next.js + FastAPI-Wrapper) | Toolkit bleibt stabil, FastAPI importiert als Package. Dev-Team kann abweichen wenn begruendet. |
| 2 | Subject Decomposition | **LLM-basiert** — `decompose_topic()` als neue Funktion im Python-Toolkit mit `llm_complete()` (Haiku) | Festes JSON-Output-Schema. Wird Teil von `src/agents/`, nicht nur Skill. |
| 3 | Job Queue | **Celery + Redis** auf Railway | Python-nativ, kein Oekosystem-Bruch. Redis trivial auf Railway. |
| 4 | Briefing-Storage | **Supabase** — Briefings als JSONB + generated HTML | Auth kommt in V2, Supabase dann schon da. |
| 5 | Domain | **auguri.us** (noch nicht gekauft) | Social Cards, OG-Tags, Stripe-Config haengen davon ab. Manueller Step. |
| 6 | Free Tier | **Kein Free Tier.** Email optional (fuer PDF-Zustellung). | Niedrigste Friction, 50ct ab dem ersten Briefing. |

---

## V2 Ideen (NICHT V1)

- User-Accounts + Credit-System (Supabase Auth)
- Pro-Abo (20€/Mo unbegrenzt)
- Trending Topics Dashboard / Leaderboard
- "Cite this Briefing" Button (BibTeX/MLA)
- Bundestags-API als Quelle (nur wenn Policy-Segment validiert)
- Destatis/Eurostat Integration
- B2B API-Zugang
- Newsletter mit Weekly Top Briefings
- Community Features

---

## Umsetzung: Reihenfolge

### Phase 1: Automatable (Dev-Team)
1. FastAPI-Wrapper um bestehende Pipeline (search, rank, draft, verify, review)
2. `decompose_topic()` Funktion aus research-brief Skill extrahieren
3. 4 neue Voice-Profile (konservativ, progressiv, B1, executive)
4. 2 neue Venue-Profile (quick_impuls, executive_brief)
5. Next.js Frontend: Landing Page + Input-Form + Progress-UI + Output-Page
6. Public Gallery mit Permalink, Social Cards, Share-Buttons
7. SSE/Polling fuer Progress-Updates
8. Transparenz-Box (Pipeline-Visualisierung)
9. Deploy: Vercel (Frontend) + Railway (Backend)

### Phase 2: Manuell (braucht Stefan)
10. **Stripe/Lemon Squeezy Account** — Setup, Verifizierung, Pricing-Config
11. **Domain** — Kaufen, DNS konfigurieren
12. **API Keys** — S2, Exa, OpenAlex, OpenRouter fuer Production
13. **Vercel/Railway Accounts** — Billing, Env-Vars setzen
14. **Legal**: Impressum, Datenschutz, AGB (Micro-Payment)
15. **Landing Page Copy** — Finale Texte reviewen/anpassen
16. **Soft Launch** — Erste 10 Tester, Feedback, Iterate

---

## Research-Quellen

| Datei | Inhalt |
|-------|--------|
| `docs/research/20260328-zielgruppen-assessment.md` | 4 Segmente bewertet |
| `docs/research/20260328-growth-mechanics.md` | Viral, Pricing, SEO, B2B |
| `docs/research/20260328-positionierung.md` | Positioning, Taglines, Differenzierung |
| `docs/research/20260328-persona-simulation.md` | 6 Personas simuliert |

## Infra-Referenzen (Cross-Projekt)

| Asset | Pfad | Relevanz |
|-------|------|----------|
| Voice-Profile (2) | `config/voice_profiles/*.json` | Direkt nutzbar, 4 neue noetig |
| Venue-Profile (9) | `config/venue_profiles/*.json` | Direkt nutzbar, 2 neue noetig |
| Research-Brief Skill | `.claude/skills/research-brief/SKILL.md` | Kern-Flow (Subject Decomposition) |
| Rubrics (3) | `config/rubrics/*.json` | Quality Gate Dimensionen |
| Drafting Pipeline | `src/agents/drafting.py` | VoiceProfile + VenueProfile Loader + Self-Check |
| Search Pipeline | `src/agents/forschungsstand.py` | Multi-Source parallel, 575 Tests |
| Claim Verifier | `src/agents/claim_verifier.py` | FactScore-Pattern, NLI |
| Provenance Logger | `src/pipeline/provenance.py` | Append-only JSONL Audit Trail |
