# API-Handling Strategy — Effizient, Sustainable, Future-Proof

> Stand: 2026-03-06 | Kontext: Querschnitts-Thema fuer alle Projekte

---

## Problem

API-Handling ist aktuell ad-hoc: keine einheitlichen Tools, kein Monitoring, kein wiederverwendbares Pattern. Das fuehrt zu:
- Wiederholtem Debugging der gleichen API-Probleme
- Keinem Alert wenn APIs sich aendern oder ausfallen
- Keine versionierten API-Collections (Wissen geht verloren)
- Kein systematisches Testing externer APIs

---

## 1. Die 4 Schichten eines soliden API-Stacks

```
Schicht 4: MONITORING + ALERTING
  "Laeuft die API noch? Hat sich was geaendert?"
  → Gatus / GitHub Actions Cron / Custom Scripts

Schicht 3: AUTOMATION + CI/CD
  "Teste alle APIs automatisch bei jedem Deploy"
  → Bruno CLI / Playwright API Tests / GitHub Actions

Schicht 2: TESTING + PROTOTYPING
  "Erkunde, teste, dokumentiere APIs manuell"
  → Bruno (Desktop) / Hoppscotch (Browser)

Schicht 1: CODE + INTEGRATION
  "Baue die API-Calls in deine App"
  → httpx (Python) / fetch (Node) / Zod (Validation)
```

---

## 2. Tool-Auswahl: Bruno als Zentrale

### Warum Bruno (und nicht Postman/Insomnia)?

| Kriterium | Bruno | Postman | Hoppscotch | Insomnia |
|-----------|-------|---------|------------|----------|
| Open Source | Ja (MIT) | Nein | Ja | Teilweise |
| Daten-Speicherung | Lokale Dateien | Cloud | Cloud/Self-host | Lokal + Cloud |
| Git-kompatibel | Ja (Bru-Dateien) | Nein (JSON-Export) | Nein | Begrenzt |
| Offline-first | Ja | Nein | Web-Version: Nein | Ja |
| Privacy | Kein Telemetry | Tracking | Self-host moeglich | Kong-Telemetry |
| CLI fuer CI/CD | Ja (`bru run`) | Ja (Newman) | Nein | Nein |
| Scripting | Bru-Syntax + JS | JS (Pre/Post) | JS | JS Plugins |
| Lernkurve | Niedrig | Mittel | Niedrig | Mittel |

**Empfehlung**: Bruno als primaeres Tool + Hoppscotch fuer schnelle Ad-hoc-Tests im Browser.

### Bruno Setup

```bash
# Installation (Windows)
winget install Bruno.Bruno

# Oder Download: https://www.usebruno.com/downloads
```

**Workflow**:
1. Collection-Ordner im Projekt erstellen: `api/collections/`
2. Requests als `.bru`-Dateien speichern
3. Environment-Variablen fuer Dev/Staging/Prod
4. Collection in Git committen → Team-Sharing ohne Account
5. `bru run` in CI/CD Pipeline

### Collection-Struktur (Best Practice)

```
api/
├── collections/
│   ├── semantic-scholar/     # Research Toolkit APIs
│   │   ├── search-papers.bru
│   │   ├── paper-details.bru
│   │   └── environments/
│   │       ├── dev.bru
│   │       └── prod.bru
│   ├── exa/
│   │   ├── search.bru
│   │   └── get-contents.bru
│   ├── vergabe/              # Vergabe-Alert APIs
│   │   ├── ted-europa.bru
│   │   ├── bund-de.bru
│   │   └── dtvp.bru
│   └── linkedin/             # LinkedIn API (falls relevant)
│       └── profile.bru
└── bruno.json                # Collection-Config
```

---

## 3. API-Testing Strategy

### 3 Ebenen

| Ebene | Wann | Tool | Beispiel |
|-------|------|------|---------|
| **Manuell** | Explorieren, Debuggen | Bruno GUI | Neue API ausprobieren |
| **Automatisiert** | Pre-Commit, CI/CD | Bruno CLI / Playwright | Regression-Tests |
| **Monitoring** | Laufend (Cron) | Gatus / GitHub Actions | API-Health + Alert |

### Automatisierte Tests mit Bruno CLI

```bash
# Einzelne Collection testen
bru run --env prod

# In GitHub Actions
# .github/workflows/api-test.yml
name: API Tests
on:
  schedule:
    - cron: '0 8 * * 1-5'  # Mo-Fr 8:00 UTC
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm install -g @usebruno/cli
      - run: bru run api/collections/semantic-scholar --env prod
      - run: bru run api/collections/exa --env prod
```

### Playwright fuer komplexere API-Tests

```typescript
// tests/api/semantic-scholar.spec.ts
import { test, expect } from '@playwright/test';

test('Semantic Scholar API returns papers', async ({ request }) => {
  const response = await request.get(
    'https://api.semanticscholar.org/graph/v1/paper/search',
    { params: { query: 'machine learning', limit: '5' } }
  );
  expect(response.ok()).toBeTruthy();

  const data = await response.json();
  expect(data.data.length).toBeGreaterThan(0);
  expect(data.data[0]).toHaveProperty('title');
});
```

---

## 4. Monitoring + Alerting

### Option A: GitHub Actions Cron (einfachste Loesung)

```yaml
# .github/workflows/api-monitor.yml
name: API Health Monitor
on:
  schedule:
    - cron: '0 */4 * * *'  # alle 4 Stunden

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm install -g @usebruno/cli
      - run: bru run api/collections/ --env prod
      - name: Alert on failure
        if: failure()
        uses: slackapi/slack-github-action@v2
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK }}
          payload: '{"text": "API Health Check failed!"}'
```

**Pro**: Kein Server noetig, kostenlos (GitHub Free: 2000 Min/Monat)
**Contra**: Min. 5-Minuten-Intervall, kein Dashboard

### Option B: Gatus (Self-hosted Dashboard)

```yaml
# docker-compose.yml
services:
  gatus:
    image: twinproduction/gatus
    ports: ["8080:8080"]
    volumes: ["./config:/config"]

# config/config.yaml
endpoints:
  - name: Semantic Scholar API
    url: https://api.semanticscholar.org/graph/v1/paper/search?query=test
    interval: 5m
    conditions:
      - "[STATUS] == 200"
      - "[RESPONSE_TIME] < 3000"
    alerts:
      - type: slack
        send-on-resolved: true

  - name: Exa API
    url: https://api.exa.ai/health
    interval: 10m
    conditions:
      - "[STATUS] == 200"
```

**Pro**: Schoenes Dashboard, flexible Alerts, viele Protokolle
**Contra**: Braucht Docker / Server

### Option C: Python Custom Script (maximale Flexibilitaet)

```python
# scripts/api_monitor.py
"""Einfacher API Health Checker mit Alert."""
from __future__ import annotations

import asyncio
import httpx
import json
from datetime import datetime
from pathlib import Path

ENDPOINTS = [
    {"name": "Semantic Scholar", "url": "https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1"},
    {"name": "Exa", "url": "https://api.exa.ai/health"},
]

async def check_endpoints() -> list[dict]:
    results = []
    async with httpx.AsyncClient(timeout=10) as client:
        for ep in ENDPOINTS:
            try:
                r = await client.get(ep["url"])
                results = [*results, {**ep, "status": r.status_code, "ok": r.is_success, "ms": r.elapsed.total_seconds() * 1000}]
            except Exception as e:
                results = [*results, {**ep, "status": 0, "ok": False, "error": str(e)}]
    return results

async def main():
    results = await check_endpoints()
    failed = [r for r in results if not r["ok"]]
    log = {"timestamp": datetime.now().isoformat(), "results": results, "failed": len(failed)}
    Path("logs/api-health.jsonl").parent.mkdir(exist_ok=True)
    with open("logs/api-health.jsonl", "a") as f:
        f.write(json.dumps(log) + "\n")
    if failed:
        # Hier: Slack/Email/Telegram Alert
        print(f"ALERT: {len(failed)} APIs down: {[f['name'] for f in failed]}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 5. Vergabe-Alerts (konkreter Usecase)

### Relevante APIs / Quellen

| Plattform | API | Typ |
|-----------|-----|-----|
| **TED (europa.eu)** | REST API (ted.europa.eu/api) | Offene API |
| **bund.de Vergabe** | RSS Feed / Scraping | Kein offizielles API |
| **DTVP** | Kein API | Scraping noetig |
| **service.bund.de** | Teilweise strukturiert | RSS + Scraping |

### Architektur fuer Vergabe-Monitor

```
1. ERKUNDEN (Bruno)
   → API-Endpunkte testen, Response-Struktur verstehen
   → Filter-Parameter identifizieren (Branche, Region, Volumen)

2. PROTOTYP (Python Script)
   → httpx + Pydantic Models fuer Vergabe-Daten
   → Filter-Logik (Keywords, CPV-Codes, Schwellenwerte)
   → Output: JSON/JSONL

3. SCHEDULER (GitHub Actions / Cron)
   → Taeglich/stuendlich laufen lassen
   → Neue Vergaben erkennen (Dedup via ID/Hash)
   → Alert: Telegram/Slack/Email

4. DASHBOARD (optional, spaeter)
   → Simple Web-UI oder Notion-Integration
   → Historische Daten, Trends
```

---

## 6. Adversarial Check — Was kann schiefgehen?

### Bruno: Bekannte Schwaechen

| Problem | Schwere | Workaround |
|---------|---------|------------|
| Tabs nicht verschiebbar | Nervig | Keyboard Navigation |
| Environment-Variablen nicht durchsuchbar | Nervig | Gut benennen (Prefix-Convention) |
| Collection-Import bricht manchmal | Mittel | Manuell `.bru`-Files anlegen |
| gRPC-Support unreif | Mittel | Fuer REST/GraphQL kein Problem |
| Kleinere Community als Postman | Niedrig | Waechst, MIT-Lizenz = fork-sicher |
| Kein Cloud Sync | Feature | Ist by Design — Git ersetzt das |

**Fazit**: Keine Showstopper. Die Probleme sind UX-Polish, nicht Architektur. Bruno ist fuer unseren Usecase (lokale API-Exploration + Git + CLI) die richtige Wahl.

### Gatus: Bekannte Schwaechen

| Problem | Alternative |
|---------|------------|
| UI weniger poliert als Uptime Kuma | **Uptime Kuma** als Alternative (schoener, aber weniger Config-as-Code) |
| Kleinere Community | Stabil genug, YAML-Config ist simpel |
| Braucht Docker | GitHub Actions Cron als leichtere Alternative |

**Empfehlung revidiert**: Fuer den Start **GitHub Actions Cron** (Option A) statt Gatus. Gatus erst wenn wir 5+ APIs monitoren und ein Dashboard brauchen. Uptime Kuma als bessere Alternative zu Gatus merken.

### Generelle API-Risiken

| Risiko | Mitigation |
|--------|-----------|
| LinkedIn aendert DOM → Userscripts brechen | `data-*` Attribute statt Klassennamen, MutationObserver |
| Externe APIs aendern Schema | Pydantic-Validation, Schema-Diff in CI |
| Rate Limits (S2, Exa) | Backoff-Logik, Request-Budget pro Tag |
| API-Keys in Repos | `.env` + `.gitignore`, Bruno Environments mit Secrets |

---

## 7. Claude Code Ecosystem — Community Favorites

### Relevante Skills/Plugins die wir SCHON haben

| Skill | Was es tut | Status |
|-------|-----------|--------|
| `webapp-testing` | Playwright-basiertes Browser-Testing | Installiert |
| `web-research` | Strukturierte Web-Recherche | Installiert |
| GitHub Plugin | PR, Issues, Actions Monitoring | Installiert |

### Skills/Plugins die wir EVALUIEREN sollten

| Skill/Plugin | Was es tut | Quelle | Prioritaet |
|-------------|-----------|--------|-----------|
| **playwright-skill** | Claude schreibt + fuehrt Playwright-Tests autonom aus | [GitHub](https://github.com/lackeyjb/playwright-skill) | Hoch |
| **connect-apps** (Composio) | 500+ SaaS-Integrationen (Slack, Gmail, Notion) | [Composio](https://composio.dev/blog/top-claude-code-plugins) | Mittel |
| **cc-monitor-worker** | Claude Code Usage Monitoring via Cloudflare | [GitHub](https://github.com/hesreallyhim/awesome-claude-code) | Niedrig |
| **ship** | PR Automation (Lint → Test → Review → Deploy) | Community | Mittel |

### Playwright-Skill vs. webapp-testing Skill

Wir haben bereits `webapp-testing` installiert. Der Community **playwright-skill** von lackeyjb geht weiter:
- Claude schreibt **custom Playwright-Code on-the-fly**
- Sichtbarer Browser (nicht headless)
- Zero Module Resolution Errors
- Progressive Disclosure (laedt nur was noetig ist)

**Empfehlung**: `playwright-skill` zusaetzlich installieren — deckt API-Testing UND Browser-Automation ab.

```bash
# Installation
claude plugins add lackeyjb/playwright-skill
```

---

## 8. Synthese — Revidierte Empfehlung

### Was sich durch Adversarial Check geaendert hat

1. **Monitoring**: GitHub Actions Cron statt Gatus als Einstieg (einfacher, kein Docker)
2. **Uptime Kuma** als bessere Gatus-Alternative gemerkt (falls Dashboard spaeter noetig)
3. **playwright-skill** als Community-Favorit identifiziert — installieren
4. **Bruno-Schwaechen** sind UX-Probleme, keine Architektur-Risiken

### Der Stack (final)

```
DAILY DRIVER (Brave)
├── Shields (Aggressiv)
├── uBlock Origin + LinkedIn Custom Filter
├── Violentmonkey (Userscripts)
└── LinkedIn Keyword Filter (Extension)

DEV BROWSER (Chrome Canary)
├── Dev-Extensions (ModHeader, CORS Unblock, JSON Formatter, etc.)
├── Playwright-ready
└── Saubere Test-Basis

API STACK
├── Bruno (Exploration + Prototyping + Git-versionierte Collections)
├── Playwright (E2E + API Tests, via playwright-skill)
├── GitHub Actions Cron (Monitoring + Alerting)
└── httpx + Pydantic (Code-Integration, Python-Projekte)

CLAUDE CODE SKILLS
├── webapp-testing (bereits installiert)
├── playwright-skill (NEU — installieren)
├── web-research (bereits installiert)
└── GitHub Plugin (bereits installiert)
```

### Naechste Aktionen (priorisiert)

| # | Aktion | Aufwand | Impact |
|---|--------|---------|--------|
| 1 | Chrome Canary installieren + Dev-Extensions | 15 Min | Hoch |
| 2 | Brave Shields + uBlock + LinkedIn Filter konfigurieren | 20 Min | Hoch |
| 3 | Bruno installieren (`winget install Bruno.Bruno`) | 5 Min | Hoch |
| 4 | `playwright-skill` installieren | 2 Min | Mittel |
| 5 | Bruno Collection fuer S2 + Exa APIs anlegen | 30 Min | Mittel |
| 6 | GitHub Actions API-Health Cron einrichten | 1h | Mittel |
| 7 | Vergabe-Alert Prototyp (eigenes Projekt) | 4h+ | Hoch (Business) |

---

## 9. Empfohlener Rollout-Plan

| Phase | Was | Aufwand |
|-------|-----|--------|
| **Jetzt** | Bruno installieren, erste Collection anlegen (S2 + Exa APIs) | 30 Min |
| **Diese Woche** | Bruno Collections in Git committen, Environments einrichten | 1h |
| **Naechste Woche** | GitHub Actions Cron fuer API-Health (Option A) | 2h |
| **Bei Bedarf** | Vergabe-Alert Prototyp mit Python | Eigenes Projekt |
| **Spaeter** | Gatus Dashboard wenn mehrere APIs gemonitort werden | Halber Tag |

---

## Quellen

- [Bruno — API Client](https://www.usebruno.com/)
- [Hoppscotch — Open Source API Platform](https://hoppscotch.io/)
- [Gatus — Health Dashboard](https://github.com/TwiN/gatus)
- [Uptime Kuma — Monitoring](https://github.com/louislam/uptime-kuma)
- [API Testing Best Practices 2026 — AIO Tests](https://www.aiotests.com/blog/api-testing-best-practices)
- [Best API Monitoring Tools 2026 — Better Stack](https://betterstack.com/community/comparisons/api-monitoring-tools/)
- [Bruno vs Postman vs Insomnia — Oden](https://getoden.com/blog/postman-vs-insomnia-vs-hoppscotch-vs-bruno)
- [Bruno Reviews 2026 — G2](https://www.g2.com/products/bruno-bruno/reviews)
- [Bruno Limitations — Grizzly Peak](https://www.grizzlypeaksoftware.com/articles/p/bruno-vs-postman-2026-why-developers-are-leaving-the-api-giant-for-local-first-t-COB9nz)
- [Playwright Skill — GitHub](https://github.com/lackeyjb/playwright-skill)
- [Awesome Claude Skills — GitHub](https://github.com/travisvn/awesome-claude-skills)
- [Claude Code Plugins + Skills (270+) — GitHub](https://github.com/jeremylongshore/claude-code-plugins-plus-skills)
- [Top Claude Code Plugins 2026 — Composio](https://composio.dev/blog/top-claude-code-plugins)
- [Gatus Alternatives — OpenAlternative](https://openalternative.co/alternatives/gatus)
- [Top API Monitoring Tools 2026 — SigNoz](https://signoz.io/blog/api-monitoring-tools/)
- [Skopos — Open Source API Monitoring](https://skopos-api-monitoring.github.io/)
