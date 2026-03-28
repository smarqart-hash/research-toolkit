# Growth Mechanics: "50 Cent Intelligence Briefings" SaaS

**Datum:** 28. März 2026
**Projekt:** Micro-SaaS für akademisch fundierte Research Briefings
**Kontext:** Portfolio-Piece + Lead-Gen für B2B Consulting

---

## 1. Viral Mechanics: Was macht Briefings teilbar?

### 1.1 Share-Native Design Patterns
Erfolgreichere Benchmarks (Perplexity, Consensus, Elicit):
- **Öffentliche Briefing-URLs** — Jede generierte Briefing erhält einen Share-Link (uuid-basiert)
- **"Powered by" Attribution** — Subtle Branding in Fußzeile: "Intelligence briefing by [Logo]"
- **Social Preview Cards** — OpenGraph Meta-Tags (title, description, image) für Twitter/LinkedIn
- **Copy-to-Clipboard** — Ein-Klick Export als Markdown oder PDF

**Warum das funktioniert:**
- Briefings sind von Natur aus Argument+Evidenz-Pakete → ready-to-share
- "Informed discourse" Positioning resoniert mit intellectually-curious Audience (Twitter/LinkedIn)
- Seeding: 1 User nutzt Briefing in Slack/Forum → Kollegen sehen "powered by" → Viral-Loop

### 1.2 Content-Seeding durch User
**Mechanik:** Incentiviere bewusste Weitergabe:
- **"Cite this briefing" Button** — Generiere BibTeX/MLA-Citation → Rezitierbar in Papers/Artikeln
- **Research Community Crosspost** — r/MachineLearning, Twitter Thread Templates
- **Journalist Kit** — "Briefing ready for coverage" Badge bei hochrelevanten Topics
  - → Presseagenturen/Tech-Journalisten kommen von selbst
  - → Backlinks + Free Publicity

**Parallele:** How Consensus wächst — Blogger zitieren ihre "Evidence" Ratings in Thesen, Cross-Traffic entsteht organisch.

### 1.3 "Leaderboard"-Dynamics (Optional)
**Mechanik:** Top-Briefs zeigen:
- **"Trending Research Topics"** — Welche 10 Topics diese Woche am häufigsten recherchiert
- **"Most Referenced Papers"** — Welche Quellen am häufigsten in Briefings zitiert
- **User Collections** — "Favorited 47 times" Badge auf Public Briefings
- **No Auth Required** — Öffentliche Briefs sind für Nicht-Angemeldete lesbar (Viral-Fallback)

**Warum das funktioniert:**
- Schafft FOMO + Social Proof ("Alle lesen über X diese Woche")
- Macht Plattform transparent ("sieh dir die Intelligence an, die andere bauen")
- Creator-Incentive: "Mein Briefing ist Top 10" → weitere Shares

---

## 2. Pricing Psychology: Warum 50 Cent funktioniert (oder nicht)

### 2.1 Das 50-Cent-Modell — Vorteile
**Psychologische Schwellwerte:**
- **Sub-Dollar Psychology** — Unter 1 USD fühlt sich nicht wie "Kauf" an → Impulse Decision
- **Friction vs. Monetization Trade-off** — $0.50 deutlich unter der kognitiven Hürde von $5-20 für Recherche-Tools
- **Perceived Value** — "Professionelle Research für unter einem Kaffee" ist powerful Copy

**Unit Economics:**
- Bei 10k Monthly Users mit 3 Briefings/Monat = $15k/Monat MRR
- CAC Break-even realistisch bei <$5 (wegen Virality + SEO)
- Zahlungsabwicklung: Stripe/PayPal zahlt ab ~$0.30-0.50 Fee → Margin gering aber okay für Volumen

### 2.2 Das 50-Cent-Modell — Risiken

| Risiko | Manifestation | Lösung |
|--------|---------------|--------|
| **Price Anchoring** | Nutzer denken "50 Cent = nicht professional" | Premium Tier für Custom Briefings ($10-50) positionieren |
| **Payment Friction** | Card Charges < $1 triggern Fraud Detection | Stripe Radar tuning, Alternative: Credits-System |
| **Churn bei Freemium Grenze** | Kostenlos → Geld-Grenze ist größer als $0.50 | Freemium: 3 Briefings/Mo kostenlos, dann $0.50/Stück |
| **Revenue Ungrenzt** | Sehr Preis-sensitiv, kann nicht auf $5+ erhoben werden | Segments: Consumer ($0.50), Professional ($10), Enterprise (Custom) |

### 2.3 Alternative Pricing-Modelle im Vergleich

#### Option A: Reines Credit-System
```
Free Tier:       3 Briefings/Mo
Credit Packs:    $5/5 Briefs, $20/25 Briefs (0.80, 0.67 pro Brief)
Pro Tier:        $20/Mo unlimited Briefs + API + Exports
```

**Vorteile:**
- Weniger Payment-Reibung (1 Transaktion pro Monat, nicht 3-10)
- Buyer Psychology: "$5 pack" fühlt sich besser an als "3 Mikro-Zahlungen"
- Flexibilität: 5er-Pack für Casual, 25er für Daily-User

**Nachteile:**
- Weniger Stimulation (nicht jede Aktion ist zahlbar)
- Hohe Conversion Friction von Free → Paid

#### Option B: Freemium + Micro-Payments (Hybrid)
```
Free:      2 Briefs/Mo, Basic Topics
Micro:     $0.50 per Brief after limit
Pro:       $20/Mo unlimited + Advanced Search + Exports
Enterprise: Custom pricing
```

**Vorteile:**
- Maximale Conversion Funnel (kostenlos → impulse $0.50 → committed $20/Mo)
- Psychological: Freemium reduziert friction, $0.50 ist "try" preis
- Best of both worlds: Viral potential (Free Users) + Impulse Revenue (Micro)

**Nachteiles:**
- Komplexe Payment-Logik
- Potential Churn wenn Free-User nach Limit einfach kündigt (nicht skaliert zu Paid)

#### Option C: Entirely Freemium + B2B Upsell
```
Free:       Unlimited Briefs, Branding (watermark)
Pro:        $20-50/Mo, Whitelabel, Custom Topics, API, Exports
Enterprise: $500-2k/Mo, Custom Pipeline, Integrations, SLA
```

**Vorteile:**
- Maximale Viral Potential (0 Zahlungshürde)
- B2B Upsell Path ist klarer (Free Users → Pro → Enterprise Pipeline)
- Alignment mit "informierte Diskurse für alle" Messaging

**Nachteile:**
- Zero Day-1 Revenue (Bootstrapping-Herausforderung)
- Retention an Nut-zu-Nutzen gebunden (nicht zahlbar)

### 2.4 Empfehlung: Hybrid-Ansatz (Option B)
**Start mit:**
- **Free Tier:** 2-3 Briefs/Monat, vollständig funktional (maximale Virality)
- **Micro-Payment:** $0.50 pro Brief nach Limit (Impulse-Revenue + Engagement Signal)
- **Pro Tier:** $20/Mo unlimited + API + Custom Exports (Commitment-Signal)
- **Enterprise:** Conversation-basiert (B2B Custom Pipelines)

**Grund:**
- Maximale Funnel-Breite (Free Users > $0.50 Impulsives > $20 Committed > Enterprise)
- Viral Loop nicht gestört, aber Revenue early
- Signal: "Leute zahlen für das" → Credibility-Boost für Free Users

---

## 3. Content-as-Marketing: Organische Traffic durch generierte Briefs

### 3.1 SEO-Play: Public Briefings als Index-Magnet
**Mechanik:**
- Jedes öffentliche Briefing:
  - Hat eindeutige URL (`/briefs/uuid`)
  - Hat Meta-Tags (Title, Description, H1-H2 Struktur)
  - Hat interne Links (verwandte Papers, andere Briefs)
  - Wird in Sitemap/robots.txt exponiert

**Hypothese:** 10k öffentliche Briefs = 10k "thin" Landing Pages für Long-Tail-Queries
- Query: "Is AI regulation necessary economics research 2024-2026"
  - → User generiert Briefing
  - → Briefing rankt für ähnliche Queries (KW-Variationen)
  - → 6 Monate später: 10k Sessions/Mo von organic?

**Parallele:** Wie Stackoverflow/GitHub funktionieren — Nutzer generieren Content, Google indexiert, Newcomer landen dort.

### 3.2 Content Moat: Warum Briefs besser rankbar sind als Blogposts

| Aspekt | Blog-Post | AI-Brief |
|--------|-----------|----------|
| **Aktualität** | Statisch, veraltet in Monaten | Dynamisch auf Search-Datum |
| **Tiefe** | 1.5k-3k Wörter | 2-5k Wörter mit Evidence |
| **Authority** | Subjektiv (Autor-Expertise) | Objektiv (50-100 zitierte Papers) |
| **Personalisierung** | 0 | Pro-Brief personalisiert (Topic-Subset) |
| **UX** | Lesetext | Strukturiert: Executive Summary, Facetten, Alle Papers |

**SEO-Konsequenz:**
- Brief zu "AI regulation" rankt gegen Blog-Posts wegen: Structure, Recency, Evidence-Dichte
- Google bevorzugt E-E-A-T (Experience, Expertise, Authority, Trustworthiness) → AI-Brief mit 80 Quellen schlägt Blog-Post

### 3.3 Internal Linking = Discovery Engine
**Automatische Link-Struktur:**
```
Brief: "AI Regulation in Europe"
  → Zitierte Paper: Hinweis zu anderen Briefings die das Paper nutzen
  → Ähnliche Topics (via Semantic Search): "EU AI Act Implementation"
  → Autor-Page: "Alle Briefs von dieser Anfrage"
```

**Effekt:**
- Erhöht Crawl-Efficiency (Google indexiert tiefer in Seite)
- Erhöht Session-Duration (User springt zu verwandten Briefs)
- Ranking-Boost durch interne Link-Juice

### 3.4 Paid Content Play: Briefings als Listicles/Guides
**Mechanik:**
- Generiere monatlich **Curated Collection** aus Top-Briefings:
  - "50 Most Important AI Research Briefings (March 2026)"
  - "Complete Guide to EU AI Regulation Intelligence"
- Poste auf Blog/Medium/Substack
- Linke zu Briefs zurück → Referral-Traffic

**Warum das funktioniert:**
- Listicles sind massiv teilbar (Journalisten lieben "50 most" Artikel)
- Repositionier Plattform als Curator, nicht nur Tool
- Organische Backlinks von Publikationen, die Lists zitieren

### 3.5 Estimate: Content-as-Marketing ROI
**Worst Case (Low Traffic):**
- 10k Briefs indexed
- 5% ranking in Top-50 für eine KW (~500 Briefs)
- 100 Clicks/Monat pro Brief = 50k Sessions/Mo
- 2% Conversion (micro + pro) = 1000 neuer Users
- → $500 MRR (wenn 50% micro, 50% upgrade to Pro)

**Best Case (Moat funktioniert):**
- Same 10k, aber 15% ranking Top-20
- 500 Clicks/Mo pro Brief = 500k Sessions/Mo (realistic?? Eher 50k-100k)
- 5% Conversion = 5k neuer Users
- → $5k+ MRR (mix micro/pro/enterprise)

**Realistische Annahme (6-12 Monate):**
- Organic = 15-20% des Total DAU nach 1 Jahr
- Content-as-Marketing wird Efficient CAC-Source (#1 nach Virality)

---

## 4. Community/Discourse Angle: "Informed Discourse für alle" als Growth-Lever

### 4.1 Mission Alignment = Retention Signal
**These:** Nutzer, die sich mit "informed discourse" Missiven identifizieren, churnen weniger.

**Mechanik zur Verstärkung:**
- **Transparency Dashboard**: "Dieser Monat: 15k Briefs generiert, 800 Stunden Research aggregiert"
  - Nutzer sehen: "Ich helfe, informierte Diskurse zu ermöglichen"
- **Citation Tracking**: "Dein Briefing wurde 12x zitiert in Twitter/Reddit/Blogs diese Woche"
  - Nutzer fühlen sich als Contributors zu besseren Diskursen
- **Community Guidelines für Public Briefs**:
  - "Wir moderieren Hate-Speech/Misinformation aus Public Briefs"
  - Schaffe vertrauenswürdige, Non-Partisan Intelligence Space

### 4.2 Social Impact as Moat
**Langfrist-These:** Im Gegensatz zu ClosedAI/Proprietary Tools kannst du sagen:
- "Wir monetarisieren, aber nicht um Zugang zu beschränken — um Qualität zu finanzieren"
- "50 Cent ist bewusste Preis-Wahl: unter 'Kaffee', über 'Frei' (damit wir Server zahlen können)"

**Messaging-Spielraum:**
- Finanziere dich durch Micro-Payments, nicht durch Daten-Selling
- Published Policy: "Wir trainieren keine Modelle auf User-Briefs"
- → Wird zum Kompetitiv-Vorteil gegen Perplexity/Claude.ai ("Sie trainieren auf deinen Queries")

### 4.3 "Discourse Communities" Sponsoring
**Mechanik:**
- Sponsore 5-10 High-Signal Communities:
  - r/MachineLearning, r/ResearchPapers, LessWrong, Lesswrong, Twitter Policy-Accounts
  - Syntax: "All members get 10 free briefings with this code"
  - → Organic seeding in educated audiences

**Cost-Benefit:**
- $200-500/Mo sponsorship budget
- → 100-200 High-Quality User Signups
- → $50-100 immediate revenue (micro), $2k+ LTV wenn 10% upgrade

### 4.4 Newsletter/Substack Strategy
**Mechanik:**
- Starten "Research Briefing Weekly"
- Kuriere Top 5 Briefs der Woche (auto-generated summaries)
- Seite-Note: "These are actual user-generated briefs, see full analysis [link]"

**Warum das funktioniert:**
- Newsletter sammelt engaged Audience (Research-Enthusiasts)
- Exponiert Plattform zu High-LTV Users (bereits zahlungsbereit)
- Substack → Twitter → mehr Organic

---

## 5. B2B Upsell Path: 50-Cent-User → Enterprise Custom Pipeline

### 5.1 Upsell-Funnel Design
```
Free Tier (2 Briefs/Mo)
    ↓
User Behavior Signal: "Generiert 10+ Briefs"
    ↓
Email Trigger: "You're a power user! Try Pro for unlimited"
    ↓
Pro Tier ($20/Mo)
    ↓
Behavior: "Exports to PDF 5+ times" OR "Uses API"
    ↓
Email Trigger: "Ready to integrate? Contact us about Enterprise"
    ↓
Sales Conversation: Custom Pipeline ($500-5k/Mo)
```

### 5.2 What Enterprise Customers Want (Benchmarks: Consensus, Elicit)
**Tier: Professional ($50-200/Mo)**
- Whitelabel Option (remove "powered by")
- Scheduled Reports (Email every Monday)
- Export to Notion/Zapier
- Custom Search Filters (only papers from specific years, venues)

**Tier: Enterprise ($500-2k+/Mo)**
- Dedicated Account Manager
- Custom Research Pipeline (e.g., "Monitor all EU regulation papers monthly")
- API Access + Webhooks
- SLA + Uptime Guarantees
- Custom Voice/Tone Profile
- Integration: Slack, Teams, Confluence

### 5.3 Sales Motion für Enterprise
**Micro → Pro:**
- Automated email at 30-day milestone (if 10+ briefs)
- 2-4 Week trial Pro free (triggered by Behavior)
- Product-led (no Sales call required)

**Pro → Enterprise:**
- Identify Pro users with "Export API" or "10+ Exports/Mo" usage
- Outreach from Sales (1 email, then call if interested)
- Case Study + Demo
- 2-Week POC mit Custom Use-Case (z.B. "Monitor AI Regulation für Legal Team")

### 5.4 Playbook: How Perplexity/Elicit Did This
**Pattern (Perplexity):**
- Free: 5 Queries/Day
- Plus: $20/Mo unlimited
- Enterprise: (Not public, but exists via sales)

**Pattern (Elicit):**
- Free: Limited search, public papers
- Elicit Plus: $15/Mo, custom research, API access
- Enterprise: White-label via partnership

**Your Advantage:**
- Sie bauen generalist AI Chat Tools
- Du baust Vertikal auf Research + Intelligence (=stickier, higher LTV)
- → B2B upsell ist natürlicher für "intelligence" Use Cases (Legal, Consulting, Government) als für Chat

### 5.5 B2B Messaging Frame
**Zielgruppe 1: Legal/Compliance Teams**
- Problem: "Wir müssen EU AI Act Compliance verstehen, haben aber nicht 200 Stunden für Research"
- Solution: Custom Pipeline: "Generate monthly intelligence briefing on AI Regulation"
- Price: $1000/Mo
- LTV: 24-36 Monate (retention high wegen Compliance Liability)

**Zielgruppe 2: VC/Private Equity**
- Problem: "We due-diligence AI companies, need deep market intelligence on every board agenda"
- Solution: API + Scheduled Reports on Custom Topics (e.g., "AI agent market 2026")
- Price: $2k-5k/Mo
- LTV: 36+ Monate (due diligence is ongoing)

**Zielgruppe 3: Government/Think Tanks**
- Problem: "Policy teams need evidence-based intelligence to draft regulations"
- Solution: Whitelabel + Custom Voice (formal tone) + Multi-Source Integration
- Price: $3k-10k/Mo
- LTV: 24+ Monate (policy cycles are long)

### 5.6 Estimate: Enterprise Revenue Impact
**Year 1:**
- 50k Free Users (from organic/virality)
- 5% → Pro ($20/Mo) = 2,500 users = $50k MRR
- 2% of Pro → Enterprise ($1500/Mo avg) = 50 accounts = $75k MRR
- Total MRR: $125k

**Year 2 (with Product-Led Growth + Content):**
- 200k Free Users
- 8% → Pro = 16k users = $320k MRR
- 3% of Pro → Enterprise = 480 accounts = $720k MRR
- Total MRR: $1.04M

**Year 3 (Mature):**
- 500k+ Free Users
- 10% → Pro = 50k users = $1M MRR
- 5% of Pro → Enterprise = 2.5k accounts = $3.75M MRR
- Total MRR: $4.75M

---

## 6. Integrated Growth Strategy: Konkrete Roadmap (Monate 1-12)

### Phase 1: Foundation (Mo 1-3)
| Metric | Target | Owner |
|--------|--------|-------|
| **Product** | Free Tier (2/Mo) + Share Links + Public Briefs | Engineering |
| **Pricing** | Free + $0.50 Micro + $20 Pro (Email-triggered) | Product |
| **Content** | Sitemap Setup, Meta-Tags, Open Graph | Engineering |
| **Community** | r/MachineLearning Sponsorship ($200/Mo) | Growth |
| **Sales** | 0 (focus: product) | — |

**Expected Outcome:** 5k DAU, $5k MRR (mostly micro), 2% Pro Conversion

### Phase 2: Viral Loop (Mo 4-6)
| Metric | Target | Owner |
|--------|--------|-------|
| **Product** | Collections + Leaderboards + "Cite This" Button | Engineering |
| **Marketing** | Blog: "50 Most Powerful AI Research Briefs" (Monthly) | Growth |
| **Content** | First SEO Results (500-1k Sessions/Mo Organic) | SEO |
| **Community** | Twitter Seeding, Newsletter Start (1k Subs) | Growth |
| **Sales** | 0 (still PLG only) | — |

**Expected Outcome:** 20k DAU, $25k MRR, 5% Pro Conversion, 3% Organic Traffic

### Phase 3: Professional Tier (Mo 7-9)
| Metric | Target | Owner |
|--------|--------|-------|
| **Product** | Pro Features: Exports, Webhooks, API (read-only) | Engineering |
| **Marketing** | Case Studies: "How [Customer] Uses Briefs" | Content |
| **Content** | 5-10k Briefs indexed, 20k+ Organic Sessions/Mo | SEO |
| **Sales** | 1 Sales/Growth Manager hire, outreach to power users | Sales |
| **Enterprise** | 0 deals, but 5+ POC Conversations | Sales |

**Expected Outcome:** 50k DAU, $75k MRR, 10% Pro Conversion, Enterprise Pipeline

### Phase 4: Enterprise Traction (Mo 10-12)
| Metric | Target | Owner |
|--------|--------|-------|
| **Product** | Custom Topics, White-Label Option | Engineering |
| **Sales** | 1st Enterprise Deal ($2k/Mo), 3+ POC | Sales |
| **Marketing** | Case Study: Enterprise Customer Profile | Content |
| **Content** | 10k+ Briefs, 50k+ Organic Sessions/Mo | SEO |
| **Revenue** | $125k MRR (Pro $50k + Enterprise $75k) | CFO |

---

## 7. Key Metrics to Track

| Dimension | Metric | Target (Mo 12) | Why |
|-----------|--------|---|---|
| **Acquisition** | DAU (Daily Active Users) | 50k | Health of Viral Loop |
| **Acquisition** | CAC (Customer Acquisition Cost) | <$5 | Unit Economics |
| **Activation** | Free → Pro Conversion Rate | 5-10% | Pricing Psychology Works |
| **Activation** | Micro-Payment Conversion | 20-30% (of users hitting limit) | $0.50 Pricing Effectiveness |
| **Retention** | Day-7 Retention (Free Tier) | >40% | Content Quality + Usefulness |
| **Retention** | Day-30 Retention (Pro Tier) | >70% | Pro Product-Market Fit |
| **Monetization** | MRR | $100-125k | Revenue Health |
| **Monetization** | LTV:CAC Ratio | >3:1 | Sustainable Growth |
| **Referral** | Share Click-Through Rate | 10-15% | Viral Coefficient |
| **Content** | Organic Traffic % of DAU | 10-20% | SEO Moat |
| **Enterprise** | Enterprise ARR | $500k+ | Strategic Revenue |

---

## 8. Risk Assessment & Mitigation

| Risk | Manifestation | Mitigation |
|------|---------------|-----------|
| **Payment Friction** | 30% cart abandonment <$1 charges | Stripe Radar config, SMS verification, Credit Pack alternative |
| **Content Moderation Fail** | Public Brief spreads misinformation | Review Pipeline vor Public, Flagging System, Expert Panel |
| **SEO Cannibalization** | Deine Briefs konkurrieren untereinander | Canonical Tags, Topic Clustering, Allow Search Index Pruning |
| **Churn nach Free Limit** | 70% Nutzer chuurn sobald Limit hit | Free Trial $20 Pro (1 Woche), Behavior-triggered Email mit Discount |
| **Enterprise Sales Flop** | 0 Deals nach 12 Mo | Start mit PLG → Pro, nicht mit Sales-Led. Build Enterprise features only after 10+ $20/Mo users |
| **Viral Loop fällt Flat** | Growth stalled bei 10k DAU | Falls passiert, pivot to Content-as-Marketing (Mo 4) — SEO trägt dann meisten Traffic |

---

## 9. Competitive Positioning

### vs. Perplexity
- **They:** Generalist Chat, $20/Mo for premium
- **You:** Vertical on Research Briefs, $0.50 for impulse, $20 for committed
- **Advantage:** Higher LTV (B2B Upsell), More Trustworthy for Intelligence (not ChatGPT fine-tuning)

### vs. Elicit
- **They:** Free Research Tool, $15/Mo for premium
- **You:** Same free tier, but Briefs are more "ready-to-cite" (not exploratory)
- **Advantage:** Better for "intelligence reports", worse for exploratory research

### vs. Consensus
- **They:** Paper database + AI Finder, Freemium + API
- **You:** Multi-source briefings, faster generation
- **Advantage:** Speed + Breadth, but less deep-dive per paper

### Your Moat
1. **Pricing:** $0.50 is the sweet spot between free (no revenue) and $5-20 (high friction)
2. **Portfolio + Lead-Gen:** Unlike Perplexity, you have explicit B2B motion from Day 1
3. **Content SEO:** Your indexable Briefs become organic engine over time
4. **Mission-Alignment:** "Informed Discourse" resonates with research community more than generic "AI Chat"

---

## 10. Success Criteria (Prove This Works)

**Months 1-3:**
- ✓ Free Tier active with 2-3k DAU
- ✓ $0.50 Micro Payments: 20+ transactions/day
- ✓ Share Links: 15%+ click-through rate
- ✓ First Public Briefs indexed in Google

**Months 4-6:**
- ✓ $20 Pro Tier: 100+ customers ($2k MRR)
- ✓ Organic Traffic: 5k+ Sessions/Mo
- ✓ Newsletter: 500+ Subs
- ✓ Community Sponsorship: 50+ signups/Mo

**Months 7-9:**
- ✓ $50k+ MRR (Pro + Micro)
- ✓ 50+ Organic Sessions/Day
- ✓ 1-3 Enterprise POCs in pipeline
- ✓ Day-7 Retention: >40%

**Months 10-12:**
- ✓ 1+ Signed Enterprise Deal ($1k+/Mo)
- ✓ $100k+ MRR
- ✓ 10k Indexed Briefs, 50k+ Organic Sessions/Mo
- ✓ Content-as-Marketing delivering 20%+ of DAU

---

## Fazit: Die "50 Cent Intelligence" Formel

Deine 3 Growth-Levers sind:

1. **Viral Mechanics (Free → $0.50):** Public Briefings mit Share-Links, Auto-Attribution, Citation-Ready Format
2. **Content SEO Moat:** 10k+ Briefs werden zu "thin content pages", organischer Traffic wächst exponentiell
3. **B2B Enterprise Upsell:** $0.50 → $20 → $2k pipeline für Legal/VC/Government custom pipelines

Das unterscheidet dich von Perplexity (Generalist) und positioniert dich als **"Professional Intelligence Platform masquerading as $0.50 Hobby Tool"**.

**Die psychologische Wahrheit:** $0.50 ist nicht zu billig — es ist genau richtig. Es sagt: "Diese Software kostet geld, daher ist sie wertvoll. Aber nicht so viel, dass ich es überdenken muss."

Danach skalierst du über Content-Marketing (SEO) + B2B Sales (Enterprise) + Community Building (Discourse Alignment) bis zu $1-5M ARR im Jahr 3.
