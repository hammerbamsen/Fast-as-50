# Ændringer 9/9-2026 — blok 10: styrke ud af Krop, 14-dages check-in i stedet for RPE pr. pas

Baggrund: styrke-loggen (blok 8) blev ikke brugt — 4 pas, 0 RPE — så progressionsreglen "RPE ≤ 7 to pas i træk" var død. Kennet besluttede 8/9: intet log pr. pas, check-in hver 14. dag med to ja/nej, progression lægges automatisk på næste pas. Styrke-kortet hører ikke hjemme i Krop.

## A. App (`index.html`)
- **Krop**: kun STYRKE-tilen (X/2 · uge N) står tilbage — uden "Log pas". Styrke-kortet er væk fra Krop.
- **Plan**: styrke-kortet ("NÆSTE") ligger nu nederst i Plan-fanen (`strengthCardHtml`, efter ugedetaljen). Viser `data.strength.next.exercises` med progressionen lagt på (ændret kg/reps markeres med guld, MAX = største vægt hjemme), tilstandslinje (`stateSummary`, recovery-flag, dato for næste check-in). Ingen Log pas, ingen RPE-liste.
- **I dag**: `todayStrengthHtml` — øvelseslisten inline når dagens første pas er styrke og `next.date` er i dag. `ckCardHtml` — kortet "STYRKE CHECK-IN · d/m" når `data.strength.checkin.due` er sand: to ja/nej (Ben / Overkrop inkl. core) → `/plan-edit {action:'strength_checkin', entryId:'chk:YYYY-MM-DD', params:{legs, upper}}` + polling af `edit_result.json`. "Gemt ✓" skjuler kortet lokalt (`faf-checkin-<dato>`) indtil data.json følger med. Ubesvaret kort bliver stående (ingen alarm). Kun I dag — ingen fallback i Mere.
- Fjernet: styrke-log-arket (`sl-sheet`, `slOpenSheet`/`slSave` m.fl.) og hooket i `toggleDone`. "Markér gennemført" på styrkepas åbner ikke længere noget.

## B. Backend
- `scripts/modules/strength_progression.py` (ny, rene funktioner): `parse_load`/`step_load` (stiger KB 12,5→16→20 · DB 5→7→10→12,5→15, loft = hjemme-gym), `apply_state` (ben → næste trin; overkrop+core → +reps, meter-øvelser urørt), `advance` (ja ben → step+1; ja overkrop → +2 reps til +4, derefter step+1 og grund-reps), `apply_checkin` (skriver current/previous/effectiveFrom — recovery-uge lige efter check-in'et udskyder effectiveFrom en uge, så recovery-ugen kører den gamle tilstand), `state_for_date`, `build_checkin` (due-logik: søndage hver 14. dag fra 4/10-2026; seneste forfaldne søndag uden svar = due).
- `edit_apply.py`: action `strength_checkin` (entryId `chk:YYYY-MM-DD`, legs/upper 0/1) → `athletes.kennet.strengthCheckin[dato]` + `strengthProgression`. Ingen gate, `dates_changed: []`. `strength_log` bevaret bagudkompatibelt.
- `apply_edit.py`: `strength_checkin` behandles som `strength_log` (kun plan.json + edit_result; ingen Intervals/Outlook/Martin/Word).
- `body.py`: `next_strength(..., progression=)` → `next` har nu `exercises` (med `baseLoad`/`baseReps`/`capped`), `state`, `stateSummary`, `recovery`. `build_strength` → `data.strength.checkin`.
- `martin_signals.py`: linje 5 = "Styrke X/2 · check-in d/m ben ✓/✗ overkrop ✓/✗" (før: seneste RPE).
- `data/workout_library.json`: `progression`-teksten på de fire `styrke-fs4-*` omskrevet til check-in-reglen. Loads rettet så de kan parses: RDL `12 kg` → `12,5 kg KB` (12 kg findes ikke i gymmet), Farmers `2×10 kg` → `2×10 kg DB`.
- `CLAUDE.md`: kontrakter for `strengthCheckin`/`strengthProgression` og `data.strength.checkin`.

## Afvigelse fra planen 8/9
- "+2,5 kg" for overkrop findes ikke som trin i hjemme-gymmet (DB 5/7/10/12,5/15). Progressionen følger de vægte der findes: næste håndvægt på hylden.
- Rundetal (2→3) styres stadig af planens `templateId` (`-2r`/`-3r`) som før — ikke af check-in'et. Skift til 3 runder er en planændring (forslag), ikke automatik.

## QA
- `py_compile` på alle ændrede .py; `pytest scripts/modules` → 606 passed, 2 skipped (ny `test_strength_progression.py`, 9 tests; martin-tests rettet til ny linje).
- Mock mod rigtig `data/plan.json`: check-in 4/10 (ja/ja) → `effectiveFrom 2026-10-12` (uge 41 er recovery); næste pas 8/10 kører grundvægte, 16/10 kører RDL 16 kg KB · Pullover 14 reps. `due` falsk før 4/10, sand 4/10–17/10 uden svar, falsk efter svar, sand igen 18/10.
- App i jsdom med mock `data.strength`: Krop uden kort/Log pas, Plan med kort, I dag med check-in-kort + dagens øvelser, knapper aktiverer Gem, lokal skjulning efter gem, `slOpenSheet` findes ikke længere. Div-balance i markup uændret, `node --check` OK.
- Ikke kørt live: Worker → plan-edit.yml → `edit_result` for `strength_checkin` (samme vej som `strength_log`, som er verificeret i blok 8). Første rigtige check-in: søndag 4/10.
