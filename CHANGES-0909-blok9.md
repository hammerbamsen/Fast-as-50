# Ændringer 9/9-2026 — blok 9: rester (uge 3-8, forslag, Plan-fanen samlet, oprydning)

Branch `claude/0909-blok9-rester` oven på origin/main efter blok 8 (PR #11). Ingen push.
Tests: **607 passed, 1 skipped** (før 580; +21 proposals, +6 coach). `schemas/validate.py` grøn på plan.json, bike_library.json, data.json og `data/proposals/*.json`. `node --check` grøn på sw.js + index.html's tre inline scripts. 0 JS-fejl i Playwright (24 screenshots `screens-v3/prop-*`).

## A. Forslag (proposal-JSON) — søndags-check-in som noget du accepterer i appen
- `data/proposals/<id>.json`: `{id, createdAt, createdBy, title, note, summary[], status pending|accepted|rejected|applied-offline, changes[{date, action:'set_day', entries[]}]}`. `set_day` erstatter dagens entries; `done`-entries bevares; uændrede pas beholder deres id. Skema `schemas/proposal.schema.json`.
- `scripts/modules/proposals.py` (ny): load/save/validate, `apply_changes`, `check_weeks` (bike_library.check_week pr. berørt uge), `summarize_for_data` (før/efter pr. ISO-uge), `apply_offline` + CLI `python3 -m modules.proposals apply-offline <id> [--dry-run]`.
- `edit_apply.py`: actions `apply_proposal` / `reject_proposal` (entryId `proposal:<id>`). check_week kører FØR Friel-gaten og kan ikke bekræftes væk; derefter normal gate. `apply_edit.py`: `proposal_decide()` skriver status/decidedAt/result til forslagsfilen via Contents API; accept = plan.json-commit + synk af alle datoer + Martin-signal; afvis = kun forslagsfilen.
- `update_kpi.py`: `data.proposals` = ventende forslag med før/efter.
- **Plan-fanen**: kort "FORSLAG · {titel}" med note, summary og uge-for-uge før → efter; Afvis / Acceptér (gate-warn → "Acceptér alligevel", reject → tekst). Efter accept: "Accepteret ✓ — synkes…" indtil data.json ikke længere har forslaget.

## B. Uge 3-8 (21/9 → 1/11) skrevet — som forslag `2026-09-07-uge3-8`, anvendt offline gennem samme kode (status `applied-offline`, godkendt 7/9)
- Svøm fjernet uge 3-8. Styrke → `styrke-fs4-a-2r` (man) / `styrke-fs4-b-2r` (tor/fre); uge 5 og 8 med note "recovery: 2 runder, ingen progression". Lørdage 26/9, 3/10, 10/10: note "Ude som ren Z2 hvis vejret tillader — samme varighed". Fra uge 6 kælder. FTP-test 24/9 og bibliotek-id'er var allerede på plads.
- check_week grøn og kvoter holder: uge 3 1/0 · 4 0/1 · 5 0/0 · 6 1/2 · 7 2/0 · 8 0/0. `programs.tds-2027.weeks[3,5,8]` note/purpose opdateret. Uge 1-2 urørt.

## C. Plan-fanen samler plan.html's funktioner
- Arket (`ptOpenSheet`) har nu Justér (varighed + note → `adjust`), Gør valgfri/obligatorisk (`toggle_optional`) og ⟲ Historik på ugeniveau (seneste commits på plan.json fra GitHub's offentlige API, Gendan → `restore_from_commit` gennem gaten). Fælles `ptRunEdit` (dispatch + poll + gate-svar).
- I dag: "Byt / aflys" åbner Plan-fanens ark for dagens entry (`ptOpenToday`). Ingen links til plan.html tilbage; filen beholdes indtil videre.

## D. Oprydning
- `af.html`, `checkin.html`, `manifest-af.json` slettet (log-arket i index#log gør arbejdet). Aften-push peger på `./#log`. Tekster i index.html ("prøv af.html?reset", "som i AF-appen") rettet. Kommentarer i af.py/checkin.py/update_kpi.py/af-registrering.yml/CLAUDE.md rettet.
- Coach (`coach.py`): ingen "N procent af ugens TSS"-linjer i RACE/RECOVERY/TAPER — i stedet "Lavere belastning er meningen i en {blok}".

## Ikke verificeret / næste
- Live: accept/afvis gennem Worker → plan-edit.yml → `proposal_decide` (kun enhedstestet). Intervals/Outlook for uge 3-8 synkes af ugesynken/næste build-workouts — tjek Intervals-kalenderen fra 21/9 efter merge.
- `workers/webhook-dispatch/worker.js` + README nævner af.html/checkin.html i kommentarer.
- Historik-arket bruger 60 anonyme GitHub-kald/t (cachet pr. session).
- plan.html kan slettes i en senere blok når Plan-fanen har kørt et par uger.
