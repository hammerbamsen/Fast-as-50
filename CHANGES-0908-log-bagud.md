# Ændring 8/9-2026 — log-arket kan rette tidligere dage (AF/protein/energi)

Branch `claude/0908-log-bagud` oven på main. Ingen push. Kun `index.html` er rørt.
Tests: **617 passed** (uændret), `schemas/validate.py` grøn, `node --check` på sw.js og de tre inline-scripts grøn. jsdom-test af arket (19 tjek, 0 JS-fejl) — se "Verifikation".

## Hvorfor
af.html (slettet blok 9) kunne bladre bagud og rette AF-dage. Log-arket i index.html kunne kun logge i dag. Backend'en (Worker `/checkin` → `af-registrering.yml` → `PUT wellness/<date>`) har hele tiden taget datoen fra payloaden, så det manglende var udelukkende i arket.

## Ændringer i `index.html`
- **Dagvalg**: `LOG_DATE` (null = i dag). ‹ › ved titlen stepper én dag; "I dag"-knap springer tilbage; tryk på en af de 7 prikker vælger den dag. Grænse `LOG_BACK_DAYS = 27` (checkinLog dækker 28 dage); fremtid afvises. Arket åbner altid på i dag.
- **Titel/label**: "Mandag 7. sep · rettes bagud" og "Alkohol den dag?" når det ikke er i dag. Valgt dag har ramme i prikkerne.
- **Værdier pr. dato**: `logLocal/logPersist/logCurrent` tager `iso` — localStorage-nøglen var allerede `faf-log-<dato>`, så rettelser bagud ligger lokalt oven på `checkinLog` indtil næste cron. Prikkerne læser nu `logCurrent(iso)` for alle 7 dage; `af_kind` fra pipelinen ignoreres for en dag der er rettet lokalt siden (`_localAlk`), så en drikkedag ændret til AF bliver grøn med det samme.
- **Debounce pr. dato**: `_logSendTimers[iso]` og `logSend(iso)` — et dagskift inden for de 600 ms sender stadig den rigtige dags payload (testet).
- **Gemt-besked** for tidligere dag: "Gemt 15.51 · 7/9 — vises i Krop efter næste opdatering".
- `logStateText()` (knappen på I dag) læser altid dagen i dag, ikke valgt dag.

## Kendt begrænsning (uændret adfærd)
`/checkin`-events opdaterer kun Intervals; `data.json` (AF-tælling, Krop, streak) følger først med ved næste `update-kpi`-kørsel (cron throttles 2-3,5 t) eller "Opdatér data". Det gjaldt allerede for dagens log. Vil du have det med det samme, kan alkohol-ændringer sendes som `/af-registrering` (den kører `update_kpi.py` i samme workflow) — ikke lavet i denne blok.

## Verifikation
jsdom (Chromium kan ikke hentes i sessionen): ark åbner på i dag · prik i går → titel/label skifter, Ja/valgt + protein forudfyldt fra checkinLog · Nej → skift til i dag før debounce → payload `{date: i går, alkohol 0, protein 2, energi 3}` · prik grøn · localStorage `faf-log-<i går>` skrevet, i dag urørt · 27-dages-grænse og fremtid · logStateText = i dag · genåbning = i dag.
Ikke verificeret: rigtig Worker/Intervals (samme kald som før, kun anden dato) og iPhone-layout af ‹ › (34 px runde knapper i `.log-head`).
