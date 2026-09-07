# Ændringer 8/9-2026 — blok 8: styrke + Martin (+ tidsregel i kalenderen)

Branch `claude/0908-blok8-styrke-martin` oven på origin/main efter blok 7 (PR #10). Ingen push.
Tests: **580 passed, 1 skipped** (før 551; +3 edit_apply, +6 body, +4 martin_signals, +10 outlook_times, +6 øvrige). `schemas/validate.py` grøn. `node --check` på sw.js og index.html's tre inline scripts grøn.

## A. Styrke-templates (`data/workout_library.json`)
Fire nye templates med Kennets startvægte (KB 12,5/16/20, DB 5-15): `styrke-fs4-a-2r`/`-3r` (Thruster 2×5 kg ×10 · Renegade row 10 kg ×8/side · KB swing 12,5 kg ×15 · KB row 10 kg ×10/side · Press 2×5 kg ×10) og `styrke-fs4-b-2r`/`-3r` (RDL 12 kg ×12 · Split squat 12,5 kg goblet ×8/ben · Pullover 7 kg ×12 · Bænkpres 2×7 kg ×12 · Farmers 2×10 kg 40 m). 2 runder ≈ 25 min, 3 runder ≈ 35 min. Nye felter `rounds`, `exercises[{name, load, reps, unit, group}]`, `progression`: ben først (næste KB-trin efter to fulde pas med RPE ≤ 7), overkrop +2 reps (max +4) før +2,5 kg, recovery-uger 2 runder uden progression, 3 runder fra uge 41 ved to fulde uger. Gamle `styrke-a-*` bevaret.

## B. Styrke-log (3 felter efter pas)
- **App**: arket `Styrke-log` åbner automatisk ved "Markér gennemført" på et styrkepas og fra Krop → STYRKE "Log pas". RPE 1-10, "Alle runder × reps?" ja/nej, note ≤ 140 tegn. Gem → `/plan-edit` med `action:'strength_log'`, `entryId:'log:YYYY-MM-DD'`, poll af `edit_result.json`, "Gemt ✓". Dagens værdier huskes lokalt.
- **Backend**: `edit_apply.strength_log_record` + special-case i `_simulate_mutation` → `plan.athletes.kennet.strengthLog[dato] = {rpe, complete, note, template, at}`; ingen Friel-gate, `dates_changed: []`. `apply_edit.py` springer Intervals/Outlook/Martin-signal/Word over for denne action.
- **Pipeline**: `data.strengthLog.sessions` beriges med loggen (`merge_strength_log`); `data.strength = {templates, next{ab, templateId, name, rounds, date, reasoning}, last4}` (`body.build_strength`). `next` = template i planen næste gang, ellers skiftevis A/B ud fra seneste log.
- **Krop**: nyt styrke-kort — NÆSTE + øvelsesliste med kg/reps, progressionslinje, seneste 4 (dato · A/B · RPE · ✓/✗ · note).

## C. Martin-mail
`martin_signals.build_weekly(data, plan, today, signals_md)` → 8 linjer (uge-TSS/CTL/TSB · vægt/fedt/glidepath · HRV/RHR/søvn · AF/protein/aftensult · styrke + RPE · cut-tjek · næste uges blok, TSS-mål og hårde/lange dage · antal planændringer siden sidst). `update_kpi.py` sætter `data.martinMail` hver kørsel og appender "### Signaler uge N" til `data/martin_signals.md` om søndagen (én gang pr. uge, ikke-blokerende). Mere → kort "MARTIN · UGE N" med Kopiér/Del. Smoke-test 7/9 gav otte korrekte linjer med rigtige tal.

## D. Tidsregel i Outlook (Kennets punkt 7/9)
Ny `scripts/modules/outlook_times.py` — eneste tidstabel: styrke 06:30 og først på dagen; næste pas starter ved forrige slut + 15 min (varighed min 30 min); `timeOverrides` i plan.json respekteres, og pas uden override skubbes ved overlap. To pas kan ikke længere overlappe. Bruges af både ugesynken (`sync_outlook.py`) og plan-edit (`apply_edit.outlook_sync_date`, som før havde sin egen tabel med styrke 07:00 og ingen kæde). 10 tests.

## E. Fedtfri masse: hold-mål
`body.ffm` får `baseline` (avg14 ved cut-start; i pre = nu), `floor` = baseline − 0,5, `status` ok/warn mod floor. Tile: "hold ≥ 56,1 · start 56,6". 57,1-målet var 68 kg × 84 % regnet baglæns — ikke et mål man kan nå i et underskud.

## F. Plan-data
`data/plan.json` 15/9 og 20/9 rettet til B-løb 4:35-4:45/km (1:37-1:40) — samme som Intervals-events 7/9, så ugesynken ikke ruller dem tilbage.

## Ikke verificeret / næste
- Live: `strength_log` gennem Worker → plan-edit.yml → edit_result; søndags-append til martin_signals.md (første gang søn 13/9); Outlook-synk med kæde (første ugesynk).
- Planens styrkepas fra 21/9 hedder stadig "Styrke Unilateral A/B 3 sæt" uden `libraryId` — blok 9 skriver uge 3-8 med de nye templates (`styrke-fs4-a-2r`/`-b-2r`), så `next` peger på planen.
- "Del"-knappen findes kun hvor Web Share API findes (iOS).
