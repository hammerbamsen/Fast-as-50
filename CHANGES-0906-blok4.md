# Ændringer 6/9-2026 — blok 4: Plan-fanen i appen

Branch `claude/0906-plan-fane` (oven på origin/main 6/9). To commits: pipeline (`e4a2e36a`) og
index.html (`2f73d214`). Ingen push.
Tests: `python3 -m pytest scripts/modules -q` → **482 passed, 1 skipped** (før: 461; +21).

## A. Pipeline

| Fil | Hvad |
|---|---|
| `scripts/modules/plan_tab.py` (ny) | `build_plan_tab(plan, plan_view, week_sessions, all_weeks, today, *, lib, week_tss_actual, ctl_daily, travel)` — ren beregning, kan køres offline. Skriver `weeks` (uge −1..+7), `sessions` (pr. dag), `ctl` (history 12 uger / projection / targets / phases), `hardSpacing`, plus `today`, `programId`, `currentWeek`, `minHoursHard`, `rules`. |
| | Vinduet regnes i **kalenderuger** og hver mandag slås op i det program der er aktivt den dag — så det spænder over programskiftet 7/9 (uge 13-14 medoc → uge 1-7 tds-2027). `tssActual`, done/faktisk og projektion bruges kun når programId matcher det aktive program (weekTssActual/all_weeks/ctlCurve er indekseret mod det). |
| | `mesoWeek`: fortløbende uger med **samme** blockType (RECOVERY = "R" og bryder serien). Afviger bevidst fra opgavens "ikke-RECOVERY-uger": med den regel ville RACE-uge 2 + BASE 3-4 give "BASE 2/3", hvor plan.json's purpose siger "Base 1/2". Testet mod den rigtige plan. |
| | `load` for pas uden libraryId: heuristik på navnet (Z1/Z2/let/gang → let, Z3/SS/tempo → moderat, Z4+/VO2/tærskel/test/race/"4×3 min" → haard); beskrivelsen kan kun løfte løb/cykel. Styrke altid let. Svøm/gang: kun navnet (Z3-drills i beskrivelsen gør ikke passet moderat). Racedage (fra programmets `races`) → haard. |
| | `hardSpacing`: alle hårde pas (alle discipliner, `disc` følger med), timer = dage × 24 (entries har ingen klokkeslæt), `ok` = ≥ `minHoursBetweenHaard` (72). |
| | Ekstra Intervals-aktiviteter (ikke planlagte) på en dag følger med som entries med `extra: true`, `id: null`. |
| `scripts/modules/fitness.py` | `get_ctl_daily(days=91)`: CTL pr. dag på tværs af programmer (til 12-ugers historikken). |
| `scripts/modules/edit_apply.py` | `swap_template` accepterer nu også et **bike_library-id**: `_find_template` falder tilbage til `bike_library.to_intervals(id)` og sætter `libraryId` + `workout_doc` på entry'et; skift til et workout_library-pas eller hvile fjerner `libraryId`. Uden dette kunne "Skift pas" til et kælderpas ikke gennemføres server-side. |
| `scripts/update_kpi.py` | Efter all_weeks-blokken: læser `data/plan_view.json` fra disk, henter `get_ctl_daily()`, skriver `data['planTab']`. Ikke-blokerende (try/except beholder eksisterende planTab). |
| Tests | `test_plan_tab.py` (20): mesoWeek (syntetisk + rigtig plan), quotaUsed, load-heuristik (11 navne + entry-regler), hardSpacing (par/ok/ekstra ignoreres/sortering på tværs af uger), build_plan_tab mod plan.json (programskifte, kælderpas-felter, race, actuals fra week_sessions, tssActual, CTL-historik + projektions-guard). `test_edit_apply.py` (+1): swap til `ss_3x15` sætter libraryId, skift tilbage fjerner det. |

## B. index.html — ny Plan-fane

- **Lag 1** `ptStrip()`: vandret scroll-stribe med snap, ét kort pr. uge: "UGE N" + datoer, blok-chip
  (RECOVERY grøn-grå, BASE navy, BUILD rav, RACE guld, TAPER lyseblå — egne dark-varianter), mesoWeek,
  "CTL → 48", "TSS 348/93" (faktisk/mål; kun "mål" for kommende uger), kvoteprikker ●●○○ (hård rød,
  moderat rav, understreget hvis over kvote), 🏆/✈, purpose (2 linjer). Tap → `ptSelectWeek(i)`
  gentegner kun `#pt-detail` og centrerer kortet.
- **CTL-graf** `ptCtlChart()`: SVG 340×150, 12 ugers historik (fuld linje i `--num`, sidste punkt med
  tal), projektion fra `planTab.ctl.projection` (stiplet rav, fra i dag), pejlemærker som punkter +
  tynd stiplet linje, fase-bånd (blockType) i baggrunden med label når båndet er bredt nok, markører:
  i dag, næste løb (🏆) og første kommende `libraryId` der starter med `test_` (rød "FTP"). Dynamisk
  y-akse (min/max ±5 rundet til 5). Kun tokens (`--num/--ink/--muted/--gold/--act`), ingen `--wine`
  som tekstfarve.
- **Lag 2** `ptWeekDetail(i)`: "Uge N · BASE 1/2 · ✈ rejse" + purpose + "CTL-mål · TSS · nøgle: …" +
  flags (WARN/HARD-chips med dansk regelnavn; "✓ Friel OK" når ingen flags og ugen ikke er forbi).
  Dagsliste man–søn: kort pr. pas med disciplin-ikon, bibliotekets Zwift-navn, varighed, load-chip,
  ERG-chip ("ERG" / "IKKE ERG — styr selv" — kun kælderpas), done ✓ + faktisk min/TSS, "ikke kørt",
  nøglepas (guld venstrekant), ekstra (stiplet), valgfri. Tap folder formål/note/Intervals-navn ud.
  Fri dag = "Fri" (eller hvile-noten) + 🏆 hvis race. Mellem hårde pas: "96 t siden CPH HALF ✓" /
  "48 t til næste hårde ✗ (min 72 t)" — også over ugeskel (linjen vises før den første hårde dag i ugen).
- **Lag 3** `ptOpenSheet(id)` → `#plan-sheet` (samme `.sheet/.scrim`-stil som log-arket) med menu
  Flyt / Skift pas / Note / Aflys.
  - *Flyt*: dagvælger for den valgte uge (viser hvad der byttes med). Konsekvens FØR bekræftelse
    (`ptMoveConsequence`): timer til nærmeste andet hårde pas i vinduet (rød hvis < 72 t), kvote i
    målugen for kælderpas (rav hvis over ugens kvote, rød hvis over bibliotekets max), "Byttes med: …".
    Knappen hedder "Flyt til Tir 22. sep".
  - *Skift pas*: cykelpas → `data/bike_library.json` grupperet efter kategori (navn, minutter, første
    sætning af formålet, load-chip, IKKE ERG); andre → `data/workout_library.json` (eva-* filtreret
    fra). Kvote-konsekvens hvis belastningen ændres.
  - *Note*: textarea → `adjust {note}`. *Aflys*: advarsel hvis nøglepas.
  - `ptSubmit()` portet fra plan.html's `submitEdit`: samme payload
    `{requestId, action, entryId, params, confirmedWarn}`, `dispatchViaWorker('/plan-edit')` (index.html's
    eksisterende funktion, samme secret `af_plan_secret`), secret-prompt ved NO_SECRET/401/403 (som
    log-arket), polling af `data/edit_result.json` 60 × 3 s. reject → HARD-chips + besked; warn →
    WARN-chips + "Fortryd / Fortsæt alligevel" (confirmedWarn=true); ok → "✓ Opdateret", lokal
    opdatering af `D.planTab` (`ptApplyLocal`: swap af dagsindhold ved 1-pas-kildedag som edit_apply,
    ellers kun det ene pas), luk efter 1,5 s og `forceDataRefresh()` (ny: nulstiller poll-cachen og
    henter data.json igen).
- Nederst: `coachFoldedCard()` (som før) + "FULD PLAN (PLAN.HTML) →".
- **Fallback**: mangler `D.planTab` (pipelinen har ikke kørt endnu) vises den gamle `renderWeek()` +
  plan.html-knap + info-banner. `applyRemote` kopierer `remote.planTab`. I dag/Krop/Mere og `PAGES`
  er ikke rørt.

## Portet fra plan.html
`openSheet/renderSheet` (move/swap_template/cancel/adjust-note) → `ptSheet*`; `submitEdit` inkl.
polling og reject/warn/ok-håndtering → `ptSubmit`; `RULE_DA` → `PT_RULE_DA`; dispatch går gennem
index.html's `dispatchViaWorker` i stedet for plan.html's `dispatchPlanEdit` (identisk request).
Ikke portet: Justér (navn/type/varighed/beskrivelse), Gør valgfri, "Foreslå bedre dage"
(`suggest_move`), Historik/rollback, adaptationsbanner — de bor stadig i plan.html (linket nederst).

## Verifikation
- pytest: 482 passed, 1 skipped.
- `screens-v3/shoot.py` (kopi af v2-scriptet): planTab genereres offline af `build_plan_tab` mod
  repoets plan.json/plan_view.json/data.json (CTL pr. dag udledt af data.json's ctlCurve), Worker-URL
  og CDN'er mockes. iPhone 390×844 @2x, lys + mørk, **ingen JS-fejl**. Screenshots i
  `/tmp/fast-as-50/screens-v3/`: `plan-fold-*.png`, `plan-fuld-*.png`, `plan-uge3-*.png` (valgt tds-2027
  uge 3), `plan-uge3-fold-*.png` (FTP-testen foldet ud), `plan-sheet-*.png` (⋯-menu), `plan-flyt-*.png`
  (Flyt med konsekvens: 48 t til CPH Half ✗), `plan-skift-*.png` / `plan-skift-valgt-*.png`
  (bibliotekslisten), `today-*/body-*/more-*.png` (uændrede faner). `planTab.json` = den genererede
  planTab (42 KB).
- Rettet efter første runde: ugekortets "UGE 14" brød linjen ved lange datointervaller (ugenr og datoer
  på hver sin linje, nowrap); fase-labels i CTL-grafen overlappede ved smalle bånd (label kun når båndet
  er bredt nok).
- Tabler-ikonfonten er blokeret i testmiljøet → disciplin-ikoner er tomme i screenshots (som i blok 3).

## Bevidst ikke gjort
- `data.json` er ikke regenereret — planTab kommer ved næste `update_kpi.py`-kørsel; indtil da viser
  Plan-fanen fallback'en.
- Justér/valgfri/foreslå-dage/historik er ikke i arket (se ovenfor).
- Flyt tilbyder kun dage i den valgte uge (opgavens "vælg dag i ugen"); plan.html kan flytte ±3/+14 dage.
- Konsekvensberegningen er klient-side og vejledende — Friel-gaten i Python er stadig den der afgør.
- Screenshots og `screens-v3/` er ikke committet.

## Risici
- `hardSpacing`/konsekvens regner i hele døgn (ingen klokkeslæt på entries): "72 t" = tre dages afstand.
- `load`-heuristikken for pas uden libraryId er regex på navnet; nye navnemønstre kan lande forkert
  (fx et hårdt pas kaldt "Løb 45 min" bliver let). Kælderpas er altid korrekte (bibliotekets `load`).
- Lokal opdatering efter en redigering er en approksimation af edit_apply (swap-reglen er kopieret);
  `forceDataRefresh()` henter data.json, men planTab i data.json er først korrekt efter næste
  pipeline-kørsel (plan-edit.yml trigger ikke update_kpi). Arket viser derfor "Opdateret" mens striben
  kan være 30 min bagud i TSS/done-tal — pas-listen er dog opdateret lokalt.
- `swap_template` med bike_library-id går også gennem `apply_edit.py`'s Intervals/Outlook-synk; den
  bruger `workout_doc` fra entry'et som build_workouts gør — ikke testet end-to-end mod Intervals.
- `get_ctl_daily` er ét ekstra wellness-kald (91 dage) pr. kørsel.
- CTL-grafens x-akse spænder ~20 uger på 340 px; ved mange faser kan labels stadig blive tætte.
