# Browser Power-User Setup — Landscape-Übersicht

> Stand: 2026-03-05 | Basis: Brave Browser (Chromium)

---

## 1. LinkedIn-Extensions (fertige Lösungen)

### LinkOff — Filter and Customizer for LinkedIn

- **Was es macht**: Komplettlösung für LinkedIn-Cleanup
- **Key Features**:
  - Feed komplett ausblenden oder filtern
  - Filter nach Inhaltstyp (Polls, Videos, Promoted, Shares)
  - Filter nach Companies/Personen
  - Keyword-Filter (z.B. Politik, Buzzwords)
  - Dark Mode
  - UI-Elemente ausblenden (Learning, Premium-Upsell, etc.)
- **Kosten**: Kostenlos, werbefrei
- **Bewertung**: 4.17/5 (46 Reviews)
- **Plattform**: Chrome, Firefox
- **Schwächen**: Gelegentliche Stabilitätsprobleme, Redraws, Chrome-spezifische Bugs
- **Open Source**: [GitHub](https://github.com/njelich/LinkOff)
- [Chrome Web Store](https://chromewebstore.google.com/detail/linkoff-filter-and-custom/maanaljajdhhnllllmhmiiboodmoffon)

### LinkedIn Feed Filter

- **Was es macht**: Keyword-basiertes Filtern von Posts
- **Key Features**:
  - Custom Keyword-Liste (z.B. "10x", "vibe coding")
  - Pause/Resume mit einem Klick
  - Badge-Counter für versteckte Posts
  - Live-Filterung beim Scrollen
- **Kosten**: Kostenlos
- [Chrome Web Store](https://chromewebstore.google.com/detail/linkedin-feed-filter/hhnigbcfgjngmbempkofojkikbabfofd)

### FilterIn

- **Was es macht**: Keyword-Filter, Privacy-fokussiert
- **Key Features**:
  - Keyword-basiertes Ausblenden
  - Kein Login nötig, alle Daten lokal
  - Keine Datensammlung
- **Kosten**: Kostenlos

### LinkedIn Keyword Filter

- **Was es macht**: Posts nach Keywords highlighten ODER verstecken
- **Unterschied**: Kann auch positiv filtern (relevante Posts hervorheben)
- [Chrome Web Store](https://chromewebstore.google.com/detail/linkedin-keyword-filter/ifapldipchmgojgbplomabaafmagbopn)

### Bewertung der Extension-Landschaft

| Kriterium | LinkOff | Feed Filter | FilterIn | Keyword Filter |
|-----------|---------|-------------|----------|----------------|
| Umfang | Sehr hoch | Mittel | Basis | Basis |
| Keyword-Filter | Ja | Ja | Ja | Ja |
| Content-Type-Filter | Ja | Nein | Nein | Nein |
| Dark Mode | Ja | Nein | Nein | Nein |
| UI-Cleanup | Ja | Nein | Nein | Nein |
| Stabilität | Mittel | Gut | Gut | Gut |
| Open Source | Ja | Nein | Nein | Nein |

**Fazit**: LinkOff ist die umfassendste Lösung, aber mit Stabilitätsproblemen. Die anderen sind schlanker und zuverlässiger, aber Feature-ärmer.

---

## 2. Userscript-Engines (DIY-Ebene)

### Was sind Userscripts?

Kleine JavaScript-Programme die automatisch auf bestimmten Websites ausgeführt werden. Du kannst damit beliebige Änderungen an jeder Website vornehmen — DOM manipulieren, Elemente ausblenden, Funktionen hinzufügen, APIs abfangen.

### Tampermonkey vs Violentmonkey

| Kriterium | Tampermonkey | Violentmonkey |
|-----------|-------------|---------------|
| Open Source | Teilweise | Vollständig |
| Performance | Mehr Ressourcen, schnellerer Start | Leichter, weniger RAM/CPU |
| UI/UX | Poliert, Tutorials, Tooltips | Minimalistisch, technischer |
| Script-Management | Bessere Verwaltung bei vielen Scripts | Schlanker, weniger Features |
| Tracking | Unklar (Closed Source Teile) | Kein Tracking |
| Empfehlung | Power-User mit vielen Scripts | Privacy-bewusste User |

**Empfehlung für dich**: **Violentmonkey** — Open Source, leicht, kein Tracking, passt zum Privacy-Ansatz mit Brave.

### Verfügbare LinkedIn-Userscripts (Greasy Fork)

| Script | Funktion |
|--------|----------|
| [Hide LinkedIn Promoted Posts](https://greasyfork.org/en/scripts/527966) | Entfernt Promoted-Ads aus dem Feed |
| [LinkedIn Unsponsored](https://greasyfork.org/en/scripts/379003) | Blockt Sponsored Posts |
| [LinkedIn Promoted Content Blocker](https://greasyfork.org/en/scripts/475168) | Blockt Promoted Content |
| [LinkedIn Tool](https://greasyfork.org/en/scripts/472097) | Keyboard Shortcuts + Navigation |
| [LinkedIn Filter](https://greasyfork.org/en/scripts/418405) | Job-Filterung nach Titel/Company |

### Eigene Userscripts schreiben

- **Schwierigkeit**: Mittel — JavaScript + DOM-Kenntnis nötig
- **Vorteil**: Volle Kontrolle, kein Abhängigkeit von Extension-Updates
- **Nachteil**: LinkedIn ändert regelmäßig DOM-Struktur → Maintenance-Aufwand
- **Template**: Ca. 20-50 Zeilen für einen einfachen Feed-Filter

---

## 3. uBlock Origin — Custom Filter

### Was kann uBlock?

Zwei Filter-Typen:

| Typ | Funktion | Beispiel |
|-----|----------|---------|
| **Cosmetic Filter** (CSS) | Elemente visuell ausblenden | `www.linkedin.com##.ad-banner` |
| **Network Filter** | Requests komplett blocken | `||linkedin.com/ads/*` |

### Konkrete LinkedIn-Filter

```
# Promoted Posts entfernen
www.linkedin.com##span:has-text(/^Promoted$/):upward(8)

# Alternative Promoted-Filter
www.linkedin.com##li:has-text(Promoted)

# Ad-Banner
www.linkedin.com##.ad-banner

# Feed-Sponsored-Content
linkedin.com#?#.feed-shared-update:-abp-contains(Promoted)
```

### Grenzen von uBlock vs Extensions/Userscripts

| Fähigkeit | uBlock | Extension | Userscript |
|-----------|--------|-----------|------------|
| Elemente ausblenden | Ja | Ja | Ja |
| Keyword-Filter (dynamisch) | Begrenzt | Ja | Ja |
| Content-Type-Filter | Nein | Ja (LinkOff) | Möglich |
| DOM-Manipulation | Nein | Ja | Ja |
| API-Interception | Nein | Begrenzt | Ja |
| Eigene UI/Buttons | Nein | Ja | Ja |
| Maintenance bei DOM-Änderungen | Selector anpassen | Extension-Update | Script anpassen |

**Fazit**: uBlock ist ideal für statische Sachen (Ads, Promoted-Label). Für dynamische Filterung (Keywords, Content-Types) braucht man Extensions oder Userscripts.

---

## 4. Brave Browser — Power-User Features

### Shields (eingebaut)

Brave blockt by Default:
- Third-Party Tracker
- Cross-Site Cookies
- Fingerprinting (Standard-Schutz)
- Ads (Basis-Level)

**Aggressive Einstellungen** (pro Site oder global):
- Tracker & Ads: Standard → **Aggressiv** (kann Seiten brechen)
- Fingerprinting: Standard → **Strikt**
- Cookies: Cross-Site blockieren (empfohlen)
- HTTPS erzwingen
- JavaScript blocken (nur für spezifische Sites sinnvoll)

### Profile

- Brave unterstützt **mehrere Profile** (wie Chrome)
- Jedes Profil hat eigene Extensions, Bookmarks, History, Cookies
- Ideal für: "Daily Driver" vs "Dev Mode" Trennung

### Weitere Power-User Features

- **Vertical Tabs**: Ja (eingebaut)
- **Tab Groups**: Ja
- **Sidebar**: Ja (Bookmarks, History, Reading List)
- **Reading Mode**: Ja (vereinfachte Artikelansicht)
- **brave://flags**: Experimentelle Features (wie chrome://flags)
- **Keyboard Shortcuts**: Standard-Chrome-Shortcuts, anpassbar über Extensions

### Brave + Extensions Kompatibilität

- **99% Chrome-Extensions funktionieren** (gleiche Chromium-Basis)
- Bekannte Ausnahmen: Google-spezifische Extensions (Google Meet, etc.)
- uBlock Origin funktioniert (zusätzlich zu Shields)

---

## 5. Architektur-Optionen (Zusammenfassung)

### Option A: "Extension-First" (einfach)

```
Brave + Shields (Aggressiv)
  + LinkOff (LinkedIn-Komplett-Lösung)
  + uBlock Origin (allgemeiner Ad-Block + Custom Filter)
```

- Pro: Schnell aufgesetzt, GUI-Konfiguration
- Contra: Abhängig von Extension-Maintenance, begrenzte Customization

### Option B: "Hybrid" (empfohlen)

```
Brave + Shields (Aggressiv)
  + uBlock Origin (Basis-Blocking + Custom LinkedIn-Filter)
  + Violentmonkey (eigene Userscripts für spezifische Wünsche)
  + ggf. LinkOff als Basis (oder ersetzen durch eigene Scripts)
```

- Pro: Flexibel, erweiterbar, Privacy-freundlich
- Contra: Etwas mehr Setup, Script-Maintenance

### Option C: "Full Custom" (maximale Kontrolle)

```
Brave + Shields (Aggressiv)
  + uBlock Origin (nur Netzwerk-Filter + Cosmetic Basics)
  + Violentmonkey + eigene Userscripts (komplette Feed-Kontrolle)
  + Eigene CSS via Stylus (Visual Customization)
```

- Pro: Volle Kontrolle, kein Drittanbieter-Code
- Contra: Höchster Aufwand, JavaScript + CSS Skills nötig

---

## 6. Dev-Browser: Chrome Canary Setup

### Warum Chrome Canary?

- **Separate Binary** — installiert sich neben Brave, eigenes Datenverzeichnis, kein Konflikt
- **Auto-Update** (nightly) — immer neueste DevTools-Features
- **Playwright-nativ** — `channel: 'chrome-canary'` in Config
- **Keine Shields/Ad-Blocker** — saubere Test-Basis ohne Interference
- **Download**: [google.com/chrome/canary](https://www.google.com/chrome/canary/)

### Dev-Extensions (Chrome Canary)

| Extension | Zweck | Users |
|-----------|-------|-------|
| **React Developer Tools** | Component-Tree, Props, State, Hooks inspizieren | 3M+ |
| **Vue DevTools** | Vue Component Hierarchy, Pinia/Vuex State | 500k+ |
| **Lighthouse** | Performance, SEO, Accessibility Audits (auch in DevTools integriert) | Eingebaut |
| **JSON Formatter** | Raw JSON → lesbare, navigierbare Struktur | 2M+ |
| **ModHeader** | HTTP Request/Response Headers modifizieren, Profile speichern | 1M+ |
| **CORS Unblock** | `Access-Control-Allow-Origin` Bypass für lokale Entwicklung | 500k+ |
| **VisBug** | Visual Editing direkt auf der Seite (Padding, Margins, Farben) | 100k+ |
| **ColorZilla** | Eyedropper, Farbpicker, Gradient Generator | 3M+ |
| **Wappalyzer** | Tech-Stack einer Website erkennen (Framework, CMS, Analytics) | 2M+ |
| **Violentmonkey** | Userscript-Engine (auch im Dev-Browser nützlich) | 500k+ |

### Playwright-Integration

```bash
# Installation
npm init playwright@latest

# oder in bestehendem Projekt
npm install -D @playwright/test
npx playwright install
```

**Config für Chrome Canary** (`playwright.config.ts`):

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  projects: [
    // Chrome Canary für Dev-Testing
    {
      name: 'chrome-canary',
      use: {
        channel: 'chrome-canary',
        headless: false, // sichtbar für Debugging
      },
    },
    // Standard-Chromium für CI
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Mobile Viewports
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 7'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 14'] },
    },
  ],
  use: {
    baseURL: 'http://localhost:3000',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry',
  },
});
```

**Nützliche Playwright-Features**:

| Feature | Command | Zweck |
|---------|---------|-------|
| UI Mode | `npx playwright test --ui` | Visuelles Test-Debugging |
| Codegen | `npx playwright codegen localhost:3000` | Tests aufnehmen durch Klicken |
| Trace Viewer | `npx playwright show-trace trace.zip` | Schritt-für-Schritt Replay |
| Device Emulation | In Config (s.o.) | Mobile Viewports testen |
| Network Throttling | `page.route()` API | Langsame Verbindungen simulieren |

---

## 7. Tech-Stack Essentials (über Browser hinaus)

### Bereits bei dir vorhanden

- **Claude Code** (CLI + IDE) — AI Coding Assistant
- **Git + GitHub** — Versionierung
- **Python 3.14** + venv — Backend/Scripting
- **Node.js 24** — Frontend/Tooling

### Empfohlene Ergänzungen

| Tool | Kategorie | Warum |
|------|-----------|-------|
| **Playwright** | E2E Testing | 45% Adoption, Standard für Browser-Testing |
| **Bruno / Hoppscotch** | API Testing | Open Source Postman-Alternative, Git-friendly |
| **Bitwarden** | Passwort-Manager | Open Source, Browser-Extension + CLI |
| **Warp / Alacritty** | Terminal | GPU-beschleunigt (Warp nur Mac, Alacritty cross-platform) |
| **ngrok / Cloudflare Tunnel** | Tunnel | Lokale Dienste extern erreichbar machen |
| **Stylus** | Browser CSS | Eigene CSS-Styles pro Website injizieren |

### Was du NICHT brauchst (Overengineering-Warnung)

- **Postman** → Bruno/Hoppscotch sind leichter und Git-kompatibel
- **Separate JSON-Tools** → JSON Formatter Extension + `jq` in Terminal reicht
- **Viele AI-Extensions** → Claude Code deckt das meiste ab
- **Docker Desktop** (wenn nicht aktiv benötigt) → Ressourcen-Fresser

---

## Quellen

- [LinkOff — Chrome Web Store](https://chromewebstore.google.com/detail/linkoff-filter-and-custom/maanaljajdhhnllllmhmiiboodmoffon)
- [LinkOff — GitHub](https://github.com/njelich/LinkOff)
- [LinkedIn Feed Filter — Chrome Web Store](https://chromewebstore.google.com/detail/linkedin-feed-filter/hhnigbcfgjngmbempkofojkikbabfofd)
- [Greasy Fork — LinkedIn Scripts](https://greasyfork.org/en/scripts/by-site/linkedin.com)
- [uBlock LinkedIn Filter — GitHub Gist](https://gist.github.com/jaydorsey/d728423051fbcb54f1abd53ed3920c9e)
- [Tampermonkey vs Violentmonkey — Oreate AI](https://www.oreateai.com/blog/tampermonkey-vs-violentmonkey-choosing-the-right-user-script-manager-for-you/78095eed7f58994b0da54486b9104d04)
- [Brave Shields — Help Center](https://support.brave.app/hc/en-us/articles/360023646212)
- [Brave Shields Advanced Config — Browserfy](https://browserfy.net/index.php/2025/05/31/advanced-configuration-of-braves-shields/)
- [Chrome Canary — Google](https://www.google.com/chrome/canary/)
- [Playwright Browsers — Docs](https://playwright.dev/docs/browsers)
- [Best Chrome Extensions for Developers 2026 — Builder.io](https://www.builder.io/blog/best-chrome-extensions-for-developers-2026)
- [Must-Have Chrome Extensions 2026 — Level Up Coding](https://levelup.gitconnected.com/must-have-chrome-extensions-for-developers-in-2026-78b47f47faea)
- [Modern Developer Stack 2026 — DEV Community](https://dev.to/eva_clari_289d85ecc68da48/the-modern-developer-stack-in-2026-tools-you-actually-need-3g5p)
