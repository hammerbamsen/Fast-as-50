# Ændringer 3/9-2026 — programmet som førsteklasses entitet

Branch `claude/0903-program-driven-config`. Alt regner nu uge/dag ud fra det
program der er **aktivt på dagens dato** (`scripts/modules/programs.py`), ikke ud
fra ét fast `program.start`/`totalWeeks`. Systemet fryser derfor ikke længere på
"uge 16" mandag 21/9 — det skifter til `tds-2027` uge 1 mandag 7/9.

Tests: `python3 -m pytest scripts/modules -q` → **444 passed, 1 skipped**
(før: 424 passed, 1 skipped; +20 nye tests).

## Hvad er ændret pr. fil

### data/plan.json (version 3 → 4)
- Ny top-level `programs` (id → program):
  - `medoc-2026`: 14 uger 1/6–6/9, uger 1-14, løb Christiansborg + Médoc, goals som før (inkl. swimMeters/runKmPerWeek).
  - `tds-2027`: 51 uger 7/9-2026–29/8-2027. Uger fra `season2027.weeks`, men uge 1-2 har overtaget blockType/ctlTarget/tssTarget/location/note fra de gamle uge 15-16 (RECOVERY 40/265; RACE 41/336 CPH Half). Løb: CPH Half (B), Stelvio (B), Tour des Stations (A). goals {68 kg, 16 %, 6 AF, 7 t søvn, styrke 2x}. phases, weightPlan (cutStartsFrom 21/9, note "over 19 uger fra 21/9"), FTP/W-kg/timer/CTL-mål fra season2027.
- `programMeta.programs` har nu begge programmer (medoc-2026 phase active, tds-2027 phase planned — kun information; valget sker efter dato).
- `athletes.kennet.birthYear = 1974` og `athletes.kennet.actualsThroughWeekProgram = "medoc-2026"` (markerer hvilket program `actualsThroughWeek` hører til).
- Legacy-nøgler `program`, `weeks`, `races`, `goals`, `nextSeason`, `season2027` er **uændrede**. `athletes.*.days` er byte-identiske (verificeret).

### scripts/modules/programs.py (ny) + test_programs.py
`list_programs`, `programs_for`, `active_program(plan, athlete, today)`, `week_no`/`week_no_raw`, `program_day`, `days_total`, `in_program`, `week_meta`/`weeks_meta`, `ctl_plan`, `block_types`, `next_race`, `upcoming_races` (på tværs af programmer), `actuals_through_week` (program-scoped), `describe`. Legacy-syntese fra `program`/`weeks`/`races`/`goals`/`season2027`/`nextSeason` når `programs` mangler, og atlet-specifikke programmer fra `athletes.<a>.program` (Eva).

### scripts/modules/config.py
`ACTIVE_PROGRAM`, `PROGRAM_ID`, `PROJECT_START` (første programs start). `CTL_PLAN`, `BLOCK_TYPES`, `TOTAL_WEEKS`, `PLAN_START`, `RACES`, `NEXT_RACES`, `GOALS`, `CTL_START`, `CTL_GOAL`, `AF_GOAL` udledes af det aktive program. `SWIM_GOAL_M`, `RUN_KM_GOAL`, `RUN_KM_GOAL_WEEK` fjernet → `GOALS.get('swimMeters')`/`GOALS.get('runKmPerWeek')`. `athlete_age()` fra birthYear. Fallback-blok bevaret.

### scripts/modules/coach.py
Alder beregnet ved kørsel; programbeskrivelse (`programs.describe`) i AI-prompten i stedet for "14-ugers reset-år mod Christiansborg og Médoc"; `weeks_to_next_race()` erstatter Christiansborg-nedtællingen; citatet "14 uger er lang tid" → "Et program er lang tid".

### scripts/modules/sessions.py
`current_week_no()`; `get_planned_weeks(weeks_back=2, weeks_ahead=6)` henter kun et vindue (None/None = hele programmet); planlagt-TSS-fallback fra ugens tssTarget; svømhistorik fra programstart; AI-ugefokus uden "51 år"/"af 14".

### scripts/modules/af.py, fitness.py
AF-historik pr. uge følger aktivt program (14-ugers cap fjernet); dag-for-dag AF-log fra `PROJECT_START`; CTL-kurven starter ved det aktive programs uge 1 (matcher `ctlPlan`-indeks).

### scripts/update_kpi.py
`meta.nextRace {name,date,daysTo,priority}`, `meta.programId/programName/phase/blockType/programDay/programDays`; `daysToMedoc`/`daysToChristiansborg` fjernes fra data.json. Header "Dag X af 98" → "af {days_total}". `kpis.ctl.sub` = "Uge N-mål X · BLOK" (farve mod ugens mål). `runKm`/`swimM` kun med mål hvis programmet har dem, og farven måles mod samme tal som teksten. Ugenote læses fra programmets `weeks[].note` (hardkodet uge 1-14-dict fjernet). `racesUpcoming` fra alle programmer. Nyt: `data.blockTypes`, `data.goals`, `data.blockType`.

### scripts/modules/friel.py
`_phase`: BASE/BASE+/TRANSITION → BASE; SPECIFIK*/STELVIO/PEAK/CAMP/BUILD* → BUILD; RECOVERY/TAPER/RACE uændret. `structural_flags`/`project_fitness`/`load_flags`/`validate`/`_camp_weeks` læser start/totalWeeks/weeks/races fra `programs.active_program(plan, athlete, today)` (ny `today`-parameter). `historic` bruger program-scoped actualsThroughWeek. VO2-reglen flagger kun build-uger der faktisk har planlagte dage.

### scripts/modules/plan_view.py, plan_coherence.py, adaptation.py, martin_signals.py
Uge via programs; `plan_view.compute(today=...)` + `kennet.programId`; `current_week` kun når i dag ligger inde i programmet.

### scripts/modules/xlsx_master.py, word_master.py
Excel: ét faneblad "Plan <år>" pr. program; løb og sæsonmål fra `programs`; Ugesummer mod det aktive program. Word (Eva): `active_program(plan, "eva")` → Evas eget program (frosset efter 7/9).

### scripts/build_workouts.py, .github/workflows/scripts/sync_outlook.py, build-workouts.yml, create-outlook-events.yml
Uge fra programs. Auto-tilstand uploader alle planlagte dage fra mandag i denne uge **på tværs af programmer** (søndagskørslen 6/9 får tds-2027 uge 1 med). `sync_outlook.py` tager `PROGRAM` (env) + `WEEK`; workflows beregner "næste uge" som program+uge for dato+7 og sender `program` videre. Ingen hardkodet 2026-06-01/14.

### plan.html, eva.html, index.html
- plan.html: `programsFor`/`activeProgram`/`upcomingRaces` i JS (samme regel); overskrift, CTL-graf, "Denne uge + 2" og "Fuld plan uge 1–N" bruger det aktive program. Projektion/ctlCurve vises kun hvis `programId` matcher (eller feltet mangler).
- eva.html: `activeProgram(plan, "eva", today)` med Evas eget program som primært; minimal ændring.
- index.html: `meta.nextRace` i sticky-bar, race-nedtælling (nu kun "Kommende løb"-kortet) og svømkort (skjules når `goals.swimMeters` mangler). `STATIC.periodization`/`ctlGoal` og "MÅL 60" fjernet; periodisering fra `data.blockTypes`, CTL-graf med dynamisk y-akse (min/max ±5) og udtyndede uge-labels. DEFAULT-tekster (linje ~459-461) er ikke rørt.

### Tests
- `test_plan_view.py`: antog legacy `program.totalWeeks` (16) og kørselsdatoen; låser nu `today` til seed-datoen (medoc-2026, 14 uger) + ny test for tds-2027.
- `test_friel.py`: +3 tests (_phase, programskifte mod rigtig plan.json, VO2-regel).
- `test_programs.py`: 16 tests inkl. "hver dato 1/6-2026..29/8-2027 har et aktivt program" og "hver dag i athletes.kennet.days ligger i et program hvis uge har ctlTarget" (fejler mod gammel plan.json, består nu).

## Bevidst ikke gjort
- Legacy-nøgler i plan.json (`program`, `weeks`, `races`, `season2027`, `nextSeason`, `goals`) er beholdt uændrede — fjernes i en senere fase.
- index.html: DEFAULT-tekster ("14 uger", "5 AF-dage", "SÆSON 2026"-eyebrow) og alt uden for de nævnte steder er ikke rørt.
- `word_master._season_page` (død kode fra Kennets docx) er ikke fjernet.
- `sessions.generate_week_focus_ai`'s BLOCK_LABELS kender ikke BASE/SPECIFIK (falder tilbage til "Træningsuge") — kosmetisk.
- Ingen push.

## Kendte risici
- **Worker/plan-edit og andre klienter der læser legacy-nøgler** (`plan.program`, `plan.weeks`) ser stadig det 16-ugers legacy-program. Alt i dette repo går nu via `programs`; eksterne læsere skal migreres før legacy-nøglerne fjernes.
- `data.json` og `plan_view.json` bærer først `programId`/`blockTypes`/`goals`/`nextRace` efter næste update_kpi-kørsel. Indtil da: index.html viser periodisering udledt af ctlPlan (fallback), sticky-bar uden race-felt, svømkort som før.
- `ctlCurve` og `weekTssActual` i data.json nulstilles til uge 1 ved programskiftet 7/9 (indekseret mod det aktive program). Historik for medoc-2026 findes stadig i Intervals og i Excel-masteren.
- tds-2027 uge 3 har ctlTarget 48 efter uge 2 = 41 (arvet fra gamle uge 16, jf. opgaven) → Friel WARN "CTL-ramp +7" kan dukke op i uge 3. Justér ctlTarget i plan.json hvis det støjer.
- `get_planned_weeks` henter nu kun uge −2..+6 → `all_weeks` i data.json indeholder ikke længere hele programmet (index.html's ugenavigation viser tomme uger uden for vinduet).
- Eva efter 7/9: `active_program(plan,"eva")` fryser på hendes 13-ugers program (uge 13) — acceptabelt jf. opgaven.
- `actualsThroughWeek` gælder kun medoc-2026 (via `actualsThroughWeekProgram`); når tds-2027 får faktiske uger skal markøren og tallet opdateres.

## De 7 datotests (`programs.active_program` mod data/plan.json)

| dato | program | uge | blockType | ctlTarget | phase | nextRace |
|---|---|---|---|---|---|---|
| 2026-09-03 | medoc-2026 | 14 | RACE | 43 | – | Marathon du Médoc (2 d, A) |
| 2026-09-06 | medoc-2026 | 14 | RACE | 43 | – | CPH Half (14 d, B) |
| 2026-09-07 | tds-2027 | 1 | RECOVERY | 40 | TRANSITION | CPH Half (13 d, B) |
| 2026-09-20 | tds-2027 | 2 | RACE | 41 | TRANSITION | CPH Half (0 d, B) |
| 2026-09-21 | tds-2027 | 3 | BASE | 48 | TRANSITION | Stelvio (258 d, B) |
| 2026-10-09 | tds-2027 | 5 | RECOVERY | 50 | TRANSITION | Stelvio (240 d, B) |
| 2027-08-28 | tds-2027 | 51 | RACE | 82 | TAPER | Tour des Stations (0 d, A) |

Samme resultat fra plan.html's JS-`activeProgram` (verificeret i node).

Slut-grep for `2026-06-01|af 98|51 år|14-ugers|daysToMedoc` i scripts/, .github/ og
html: kun tests med legacy-fixtures, plan.json's egne programfelter samt
kommentaren/oprydningen i update_kpi.py der fjerner de gamle meta-felter.
