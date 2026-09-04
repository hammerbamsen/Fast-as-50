# Ændringer 4/9-2026 — blok 3: I dag v2 i den rigtige app + check-in-pipeline

Branch `claude/0904-idag-v2` (oven på origin/main = program-config + plan 7/9–1/11).
Tests: `python3 -m pytest scripts/modules -q` → **460 passed, 1 skipped** (før: 452; +8 i `test_checkin.py`).
Ingen push. To commits: pipeline (`a1604d68`) og index.html (`a1e8eb90`).

## Hvad Kennet skal gøre

1. **`wrangler deploy`** i `workers/webhook-dispatch/` — `/checkin` sender nu også `sult`.
2. **Opret custom wellness-felt `Aftensult`** i Intervals.icu (Settings → Wellness → custom field,
   numerisk, 0/1/2). Uden feltet afviser Intervals PUT'en fra af-registrering.yml.
3. Første `update_kpi.py`-kørsel efter merge skriver `checkinLog`, `kpis.protein`, `energy7`,
   `af_kind` til data.json. Indtil da viser log-arkets 7-dages prikker og Krop-fanens
   protein-kort "ingen registreringer" (ikke eksempeldata).

## A. index.html

| Emne | Hvad |
|---|---|
| Palet | `:root` har prototypens blå tokens; mørk tilstand via `@media (prefers-color-scheme: dark)` + `:root[data-theme="dark"]`. `--wine/--gold` beholdt som navne (blå/rav-værdier); `--cream/--cream-d/--white` er aliaser for `--bg/--line/--card`, så gamle regler følger temaet. Nye: `--bg, --bg-2, --card, --line, --hero, --hero-ink, --hero-muted, --ok/--watch/--act`. Tekst på mørke kort bruger `--hero-ink`, på lyse `--ink`. Bike `#2874A6` → `#3A8FD1`, neutral grå `#7A6A58` → `#6B7A88`. `grep -c "#59182A"` = 0. `<meta name="color-scheme">` + theme-color `#16324F`. |
| Navigation | `PAGES` = today / plan / body / more og er eneste kilde for sidebar, bottom-nav, swipe (`PAGE_IDS = PAGES.map(...)`) og hash-routing. Bottom-nav i kort-farve (aktiv = blå lys / rav mørk). Header: titel + statuslinje ("Fredag 4. sep · Uge 14 af 14 · RACE") + data-alder-prik (grøn <6 t, gul 6-12, rød >12; "Offline — viser data fra …" ved `navigator.onLine===false`). `pm-week/pm-block` fjernet. |
| I dag | `renderToday` bygget om: ét banner-slot (datafejl > stale >12 t > nøgler > kritisk advarsel > stale >6 t > readiness) — de gamle `document.body.prepend`-bannere (`checkStaleness/showDataError/checkReadiness`) opdaterer nu slottet. Hero: readiness-linje (HRV i dag vs 7d-snit i %, z mod 42-dages baseline ±1 SD fra `hrvHistory`; søvn sidste nat; form=`tsb`; prik ok/watch/act efter prototypens regel), titel = `today[0].title` (ellers "Fri"), sub = `desc` (ellers varighed/zone, ellers `weekFocus`), ekstra pas som "+ …"-linjer, "Markér gennemført" (samme localStorage-flow), "Byt / aflys" → `plan.html#<dato>`. Ugestribe: 7 dagkort fra `week_sessions` med disciplin-chips (done = fyldt), i dag markeret, 🏆 fra `racesUpcoming`/`meta.nextRace` når datoen ligger i ugen; tap folder dagen ud (ekstra-pas med tag). "Én ting i dag": højeste `warnings` → `coachHighlight` → `weekFocus`; begrundelse af søvn <7, HRV ≤−10 % vs 7d, næste løb. "Registrér i dag" med "n af 4 registreret". Slettet: sticky-bar, KPI-grid (`kpiGrid`), gammel `weekStrip`, `afRing`, `renderWarnings/warnBanner`, coach-tale på I dag. |
| Plan | Knap "Åbn planlægning (flyt / aflys / skift pas)" → plan.html, derunder `renderWeek()`. Coach-tale (`coachSpeech`) + AI-vurdering (`coachAssessmentHtml`, ↻-knap) ligger nu i **ét foldet `<details>`-kort under** pas-listen og ugefokus. `changeWeekView` navigerer til `plan`. |
| Krop | Uændret + `proteinCard()`: 7 prikker fra `checkinLog`, `kpis.protein` (n/7 · "3/3-dage · 4 uger x,x") og linje "Energi-snit 7d". |
| Mere | Sektioner "Træning" (`renderOverview` uden hero-kort), "Regler" (`renderRules` uden hero-kort), "System" (sidst opdateret, coach-tid, nøgler fra `data.credentials`, push-toggle — `renderPushToggle('push-toggle-main')` kaldes efter render). |
| Uændret | Krop-sparklines, push-koden, pull-to-refresh, polling, `applyRemote` (kun tre nye linjer: `checkinLog`, `energy7`, `kpiProtein`). |

## B. Log-ark (bottom sheet)

Statisk HTML nederst i `<body>` + JS-blokken "Log-ark" før Navigation. Fire spørgsmål, intet
obligatorisk, gemmer ved hvert tryk (debounced 600 ms så "Ja → Valgt" bliver ét kald) til
Worker `/checkin` med `{date, alkohol, protein, energi, sult}` — kun felter der er sat.
Værdier: alkohol 0 nej / 1 ja valgt / 2 ja bare skete (**"Ja" uden undervalg sendes som 1 = valgt**
og Valgt vises markeret); protein 2/1/0; energi 1/3/5 (eksisterende 1-5-skala, en serverværdi
2 vises som Lav, 4 som Høj); sult 0/1/2. Optimistisk UI: dagens valg i `localStorage`
(`faf-log-<dato>`, `null` = fravalgt lokalt) lægges oven på `data.checkinLog`. "Gemt hh:mm" ved
succes, rød "Ikke gemt — …" ved fejl; NO_SECRET/401 giver samme prompt som ↻-knappen.
7-dages prikker fra `data.checkinLog` (ikke eksempeldata). `index.html#log` åbner arket;
`scripts/send_push.py` aften-nudge peger nu dertil. `af.html`/`checkin.html` uændrede.
Bemærk: et fravalg sender blot feltet ikke med — det sletter ikke værdien i Intervals.

## C. Pipeline + Worker

- `workers/webhook-dispatch/worker.js`: `/checkin` payload får `sult: body.sult`.
- `.github/workflows/af-registrering.yml`: `SULT` → Intervals-felt `Aftensult`. Payload bygges nu
  af valgfrie felter (`{${FIELDS#, }}`) — før krævede den `Alkohol`, og log-arket kan sende uden.
  Alkohol 0/1/2: `af.py` regner `Alkohol == 0` som AF-dag og alt andet som drikkedag (verificeret i
  `get_af_this_week`, `get_af_history`, `get_full_af_log`, `get_af_streak`) — 1 og 2 tæller begge.
  `af_log` beholder 0/1 (af.html/index læser det); valgt/autopilot ligger i `data.af_kind`
  `{dato: 'valgt'|'autopilot'}` og i `checkinLog.alkohol`.
- `scripts/modules/checkin.py` (ny): `build_checkin_log(rows, today, days=28)`, `protein_days`,
  `protein_weekly_avg`, `protein_kpi` (→ `{value:"n", unit:"/7", sub:"3/3-dage · 4 uger x,x", color}`),
  `energy_avg`, `hunger_days`, `af_kinds`, `coach_line`, `get_checkin_log`. Feltnavne:
  `Alkohol`, `protein`, `motivation` (= energi, som checkin.html altid har brugt), `Aftensult`.
  Tests i `test_checkin.py`.
- `scripts/update_kpi.py`: efter AF-historikken skrives `data.checkinLog`, `data.kpis.protein`,
  `data.energy7`, `data.af_kind`; `checkin_line` sendes til `generate_ai_assessment`.
- `scripts/modules/coach.py`: ny parameter `checkin_line`; prompten får linjen
  "Check-in (Kennets egne registreringer): Protein 3/3-dage sidste 7: n · aftensult-dage: m ·
  energi-snit: x" — kun når data findes.

## D. Verifikation

- pytest: 460 passed, 1 skipped.
- `screens-v2/shoot.py` (Playwright, Chromium fra `/opt/pw-browsers`, `python3 -m http.server 8765`
  i repo-roden, `raw.githubusercontent.com/.../main/*` omdirigeret til lokale filer, data.json
  beriget med syntetisk `checkinLog` da pipelinen ikke har kørt): iPhone 390×844 @2x, lys og mørk.
  Ingen JS-fejl (`pageerror`/`console.error`; kun SW-registrering mod `/fast-as-50/sw.js` filtreret —
  lokalt path-artefakt). Screenshots i `/tmp/fast-as-50/screens-v2/`:
  `idag-fold-{light,dark}.png`, `idag-fuld-*.png`, `idag-dag-*.png` (dag foldet ud),
  `logark-*.png`, `logark-ja-*.png`, `plan-*.png`, `body-*.png`, `more-*.png`.
- Rettet efter første runde: lukket ark var synligt i full-page-screenshots (fixed + translate) →
  `.sheet { visibility:hidden }` når ikke `.show`; header-luft på mobil reduceret.
- `grep -c "#59182A" index.html` → 0.

## Ikke gjort / kendte forbehold

- Den rigtige Plan-fane (blokstribe, CTL-graf, ⋯-menu) er blok 4 — Plan viser nu Uge-indholdet.
- `data.json` er ikke regenereret; `checkinLog` m.m. kommer ved næste kørsel.
- Tabler-ikonfonten er blokeret i test-miljøet, så pas-ikoner på Plan-fanen er tomme i screenshots.
- `week_sessions` indeholder kun dage frem til i dag + planlagte pas; lør/søn uden entries vises som
  "Hviledag" på Plan og som tom chip i ugestriben (pre-eksisterende adfærd).
- Screenshots og `shoot.py` er ikke committet (ligger utracked i `screens-v2/`).
