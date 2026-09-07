# Ændringer 7/9-2026 — blok 7: robusthed (+ søndags-check-in punkt 2 og 3)

Branch `claude/0907-blok7-robusthed` oven på origin/main 7/9 (05b1225). Tre commits: pipeline, frontend, workflows/oprydning. Ingen push.
Tests: `python3 -m pytest scripts/modules scripts/test_health_report.py -q` → **551 passed, 1 skipped** (før 538; +4 alkohol, +9 health_report). `schemas/validate.py` grøn på plan.json, bike_library.json, data.json. `node --check sw.js` grøn. YAML på alle 13 workflows grøn.

## Hvorfor (fra check-in 7/9)
- **Datahul:** data.json var bygget 02:43, mens Garmin havde dagens HRV (50, ikke 35) kl. 06:24. Ingen kørsel mellem 00:44 og 05:10 UTC selv om `*/30` stod på — GitHub springer hyppige crons over. Coach og readiness talte om gårsdagens krop.
- **Ingen kunne se det.** Hverken at cron'en sprang over, at en workflow fejlede, eller at PAT'en udløber 15/10.
- Punkt 4 fra check-in (coach.py hardkodet til medoc-2026) var **forkert** — coach v2 er allerede program-styret (`prompts/coach_system.md` + `coach_context.build_context`). Intet ændret der; arbejdsreglerne rettes i projektet.

## A. Pipeline

| Fil | Hvad |
|---|---|
| `scripts/modules/body.py` | `alcohol_signal(af_log, today)`: registrerede drikkedage de seneste 7 dage + længste række (uregistreret dag bryder rækken). `cut_check(..., af_log=None)` får 6. signal `alcohol` → warn ved ≥ 3 dage/7 eller klynge ≥ 2 (`ALC_WARN_DAYS7`, `ALC_WARN_RUN`). Handlingstekst "N drikkedage på 7 dage · k i træk under cuttet — AF resten af ugen før du skærer mere", prioritet efter restitution, før styrke. Kun aktivt i cut (pre er stadig "Aktiveres uge 39"). `build_body` læser `data.af_log`. |
| `scripts/update_kpi.py` | `get_full_af_log()` hentes én gang **før** krop-modulet (var efter) og gives som `af_log`; AF-log-afsnittet genbruger den. |
| `scripts/modules/coach_context.py` | `body.cut.alcohol7d` = `{days7, run}` når cut-tjekket er aktivt. |
| `scripts/modules/test_body.py` | +4 tests (ingen data, ok/warn/klynge/brudt række, tekst + prioritet mod restitution, build_body). |

## B. Frontend (`sw.js`, `index.html`)

- **sw.js v20260907-swr**: app-shell (`./`, manifest, icon) stale-while-revalidate; ny index.html i baggrunden → `postMessage sw-new-version`. Datafiler (data.json, plan.json, plan_view.json, health.json, data/*.json — også via raw.githubusercontent.com) network-first med `no-store`; ved netfejl cachet kopi med header `X-From-Cache: 1`. Versioneret cache, gamle slettes; push/notificationclick uændret.
- **"Ny version klar · Genindlæs"**-bjælke øverst (ved SW-besked eller controllerchange på en allerede styret side).
- **Statuslinje** "… · data kl. 05:07" farvet efter alder (grøn < 60 min, gul ≤ 180, rød > 180). Badge "Offline · data kl. HH:MM" ved `X-From-Cache`/offline; "↻ opdaterer…" under auto-refresh.
- **Auto-refresh** (`maybeAutoRefresh`): online + data > 90 min + Worker-hemmelighed i localStorage → dispatch `/refresh` + poll, én gang pr. app-åbning, stille ved fejl. Det lukker morgenhullet fra brugersiden; cron-linjerne (C) lukker det fra serversiden.
- **Mere → System-kort** (`systemCardHtml`, `loadHealth`): data-alder, coach-tidsstempel, SW-version, installeret/online, "↻ Opdatér nu"; `<details>` med workflows fra health.json (prik grøn/rød/gul/grå, relativ tid, conclusion, event, varighed, interval, link til kørsel); nøgler med udløb (PRIVATE_REPO_TOKEN 15/10 — grøn > 21 d, gul ≤ 21, rød ≤ 7/udløbet); `data.credentials`. Findes health.json ikke: "Ingen health.json endnu — kommer ved næste workflow-kørsel".
- `cutCheckCard`: signalet ALKOHOL vises; tælleren "x af n signaler" er dynamisk.
- Verifikation: Playwright (iPhone 390×844, lys+mørk) i `screens-v3/shoot_system.py` (utracked som før): `system-*`, `sw-status-*`, `sw-newversion-*`, `sw-offline-*`, `sw-autorefresh-*`, `system-cutcheck-alkohol-*`. **0 JS-fejl.**

## C. Workflows, CI, oprydning, docs

- **`health.yml` (ny, "Workflow-sundhed")**: `workflow_run: completed` for alle 12 øvrige workflows → `scripts/health_report.py` skriver `health.json` via Contents API (lastRun, conclusion, event, runUrl, durationS, expectedEveryMin; secrets.PRIVATE_REPO_TOKEN expires 2026-10-15). Ved conclusion ≠ success/skipped: push "Workflow fejlede: <navn>" (tag `fast50-alert`, url `./#more`). 9 tests i `scripts/test_health_report.py`.
- **`scripts/send_push.py`**: `--alert "Titel" "Tekst" [--url]` — deler afsendelseskode med daglig-flowet.
- **`update-kpi.yml`**: `*/30` + faste `30 4 * * *` og `15 5 * * *` UTC (06:30/07:15 dansk sommertid) + `timeout-minutes: 15`.
- **`ci-pytest.yml`**: kører nu på alle push/PR (path-filtre væk). Trin: pytest · `schemas/validate.py` (draft 2020-12, kun felter koden læser, `additionalProperties: true`; fanger manglende programs/weeks/days/entries, forkert `load`/`erg`/`id`, manglende meta/kpis/today/week_sessions, `meta.updated`-format; unikke id'er) · `node --check sw.js` · `node --check` på hver inline `<script>` i index.html.
- **Slettet**: scripts `add_plan_ids, cleanup_uge2, debug_today, debug_week2, debug_wellness_fields, fix_outlook_week3, push_outlook_uge27, retro_af_week1, test_upload, debug_bike_ef, debug_subs, onedrive_reorg, create_sunday_reminder`; workflows `debug-bike-ef, debug-subs, onedrive-reorg, create-reminder, sync-onedrive`; mappen `debug/` (og debug-skrivningen i af-registrering/create-outlook-events). `delete-outlook-event.yml` beholdt som manuelt værktøj.
- **Docs**: `docs/PIPELINE.md` (ny), `CLAUDE.md` (ny, repo-roden), `docs/PAT_RENEWAL.md` (aktuel sektion om PRIVATE_REPO_TOKEN).

## Ikke verificeret / kendte begrænsninger
- `workflow_run` fyrer først når `health.yml` ligger på `main` — første health.json kommer ved næste kørsel af en hvilken som helst workflow. Selve push-afsendelsen ved fejl er kun testet med mocket sender.
- Contents API-oprettelse af health.json (PUT uden sha) er standard, men ikke afprøvet live.
- Auto-refresh bruger GitHub API anonymt til at se om data.json har flyttet sig (≤ 19 kald pr. session).
- Bannerne på I dag bruger stadig de gamle 6/12-timers-grænser for "gamle data"; statuslinje og System-kort bruger 60/180 min.
- `about-me.md` og `data/about-me.md` nævner stadig `sync-onedrive.yml` som arbejdsgang — ret når du alligevel rører dem.
