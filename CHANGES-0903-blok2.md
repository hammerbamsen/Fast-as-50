# Ændringer 3/9-2026 — blok 2: plan 7/9–1/11 + småbugs

Branch `claude/0903-program-driven-config`, oven på CHANGES-0903-program.md.
Tests: `python3 -m pytest scripts/modules -q` → **452 passed, 1 skipped** (før: 444).
Ingen push.

## Del A — plan 7/9 → 1/11 skrevet til data/plan.json

Alle entries for 2026-09-07 … 2026-11-01 i `athletes.kennet.days` er erstattet
(56 dage, 62 entries, alle med nye unikke 8-tegns id'er). 5/9 og 6/9 samt alt
uden for intervallet er byte-identisk (verificeret mod HEAD). Kælderpas er
skrevet som `bike_library.to_intervals(wid)` + `libraryId` på entry'et.
Løb/gang/styrke/svøm følger de eksisterende skabeloner (Hike/Run/WeightTraining/Swim).

| Uge | Blok | Man | Tir | Ons | Tor | Fre | Lør | Søn |
|---|---|---|---|---|---|---|---|---|
| 1 | RECOVERY | Gang 45 | Gang 60 (Bordeaux) | Gang 60 | Cykel Z2 60 (ude) | Svøm 2000 teknisk | Løb Z1 30 + Styrke overkrop 25 | Cykel Z2 90 |
| 2 | RACE B | Cykel Z2 45 + Styrke overkrop 25 | Løb 4×3 min @4:16 | Cykel Z1 40 | Løb let 40 + 6 strides | Svøm 2000 let | Gang 30 (+racesko 10) | **CPH HALF** 21,1 km |
| 3 | BASE 1/2 | Styrke A | K `z2_grundtur_80` (PROBE) | Løb Z2 45 (PROBE) | K `test_ftp20` | Styrke B + Svøm teknik 1500 (catch) | K `z2_depottur_2t` | Lang løb Z2 50 |
| 4 | BASE 2/2 | Styrke A | K `z2_grundtur_80` | Løb Z2 45 | K `z2_aabnere_60` + Styrke B | Svøm teknik 1500 (hoved) | K `dur_negativ_split` | Lang løb Z2 50 |
| 5 | RECOVERY | Styrke recovery | K `z2_aabnere_60` | Løb Z2 40 | Styrke recovery | Svøm teknik 1500 (hofte) | K `z2_grundtur_80` | Gang 60 |
| 6 | BASE 1/2 | Styrke A | K `ss_3x15` | Løb Z2 45 | K `tae_over_unders` | Styrke B + Svøm teknik 1500 (catch) | K `dur_bjergtur_3t` | Lang løb Z2 50 |
| 7 | BASE 2/2 | Styrke A | K `tae_3x12` | Løb Z2 45 (PROBE md 2) | K `z2_grundtur_80` + Styrke B | Svøm teknik 1500 (hoved) | K `dur_sent_i_turen` | Løb Z2 40 let |
| 8 | RECOVERY | Styrke recovery | K `z2_aabnere_60` | Løb Z2 40 | Styrke recovery (Stelvio-deadline) | Svøm teknik 1500 (hofte) | K `z2_depottur_2t` | Løb let Z1 30 |

Noter: "ude hvis tørt og >8 °C"-noten ligger på lør 26/9, 3/10, 10/10 og 31/10.
CPH Half-beskrivelsen har fået beslutningsreglen ved 5 km (4:16 kun hvis
kontrolleret, ellers 4:35 og nyd det). Ingen hviledage-entries — den godkendte
plan har et let pas alle 7 dage.

### Ugemetadata (programs.tds-2027.weeks = season2027.weeks uge 1-8)
- Uge 1: ctl 47 / tss 150 · uge 2: ctl 45 / tss 250 · uge 3: ctl 48 / tss 380.
- Noter uge 2, 3, 5 som aftalt. `purpose` (én sætning) og `quota {haard, moderat}`
  på uge 1-8 (1-2: 0/0, 3: 1/0, 4: 0/1, 5: 0/0, 6: 1/2, 7: 2/0, 8: 0/0).
- Legacy `weeks` 15-16 ctlTarget → 47/45. `test_programs.py` opdateret (låste 40/265, 41/336).

### Gate-resultat
- `bike_library.check_week()` for uge 1-8: **tom liste alle uger**.
  Faktisk belastning matcher quota: uge 3 1H/0M, 4 0H/1M, 5 0/0, 6 1H/2M, 7 2H/0M (96 t imellem), 8 0/0.
- `friel.validate(plan, today=2026-09-07)` (struktur): **ingen flags**.
- Med `fitnessSeed.current` (seed 7/7, CTL 46,8) — kun **WARN**, ingen HARD:
  - uge 2 `race_tsb` TSB −12,3 på CPH Half (mål +5..+15) og `taper_ctl_rising` +3,6 —
    projektionen kører fra et to måneder gammelt seed; reel TSB 3/9 er +5.
  - uge 3 `ctl_ramp` +6,0 og uge 4 +5,4 (blødt loft 5) — konsekvens af de aftalte
    tssTargets 250→380→400.
  - uge 39/51 `race_tsb` ≈ 0 (Stelvio/TdS) — ligger uden for den planlagte periode.

## Del B — bugs rettet

| # | Fil | Rettelse |
|---|---|---|
| 1 | `scripts/update_kpi.py`, `.github/workflows/update-kpi.yml` | Blokken der hentede index.html, regex-erstattede `kpis:[...]` og pushede, er fjernet. Det døde "Commit og push data.json"-step er fjernet (data.json skrives via Contents API i `modules/github.gh_put` — verificeret). |
| 2 | `index.html` `applyRemote` | `D.meta = remote.meta` (sticky-bar/CTL-mål læser `D.meta.week`). Alle KPI-farver kommer nu fra data.json's `kpis.*.color` (hardkodede farver fjernet, neutral grå som fallback). "SIDST OPDATERET" renderes fra `D.lastUpdated` i templaten, så den overlever `navigate()`-re-render. |
| 3 | `scripts/update_kpi.py` (`sleep_kpi`) | Søvn = sidste nat (seneste `sleepHistory`-punkt med værdi), sub "Snit 7d X,Xt · mål 7t" fra ægte 7-punkts snit, farve på snittet (≥7,0 grøn / 6,5-7,0 orange / <6,5 rød). Fallback til wellness `sleep_avg` uden historik. |
| 4 | `scripts/update_kpi.py` (`af_kpi`), `index.html` | `kpis.afStreak` = AF-dage denne uge, sub "af 6 denne uge · snit 4 uger X,X · streak N" (4-ugers snit fra `af_history`, afsluttede uger). `get_af_history()` hentes nu før KPI-blokken. index.html-label "AF DAGE"; ugekortets "x/7" → "x/6" (target). |
| 5 | `index.html` `STATIC.rules` | De 10 regler erstattet med Kennets 7 principper. "Weekend som belønning" væk. DEFAULT-tekster "5 AF-dage" → "6 AF-dage" (2 steder). |
| 6 | `scripts/modules/sessions.py` | `'strength'` i `DURATION_FIRST_DISCS` — styrke regnes gennemført på tid. +2 tests i `test_sessions.py`. |
| 7 | `scripts/modules/coach.py` | Fokus-linjen ved vægt over mål nævner ikke længere kulhydrater; nu principperne (protein ved hvert måltid, alkohol som valg, søvn 7-8 t) + "vægt/fedt vurderes på 7d-snit mod planen". `weight_goal`/`fat_goal` default `None` → `GOALS.weightKg`/`bodyFatPct` fra det aktive program (68/16) via `_goal()`. `test_weight_fallback.py`: asserten `'målt' not in` ramte "måltid" — præciseret til `'(målt'`. |
| 8 | `scripts/apply_edit.py` | `_is_iso_date()`; Intervals- og Outlook-synk kører kun for ægte datoer i `dates_changed` — `"restore"` (og andre ikke-datoer) logges og springes over. |

Nye tests: `scripts/modules/test_kpi_sleep_af.py` (6 tests for `sleep_kpi`/`af_kpi`).

## Ikke gjort
- `data.json` er ikke regenereret — kpis/meta bærer først de nye søvn/AF-felter
  efter næste `update_kpi.py`-kørsel. index.html falder pænt tilbage indtil da.
- Ingen faktisk upload til Intervals/Outlook (build_workouts kører søndag 6/9).
- Wine-kortets "AF STREAK"-overskrift (streak-tallet, ikke KPI'en) er beholdt.
- Friel-WARN'ene ovenfor er ikke "løst" — de er rapporteret; tssTargets er som aftalt.
