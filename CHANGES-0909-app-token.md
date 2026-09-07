# Ændring 9/9-2026 — GitHub App-token i stedet for PAT til det private repo

Branch `claude/0909-app-token` oven på main efter PR #13. Ingen push.
Tests: **616 passed, 1 skipped** (før 612; +4 i `scripts/test_health_report.py`). `schemas/validate.py` grøn, YAML grøn på alle tre ændrede workflows, `node --check sw.js` grøn.

## Hvorfor
`PRIVATE_REPO_TOKEN` (fine-grained PAT, `contents: rw` på `fast-as-50-private`) udløber 15/10-2026. En fornyelse flytter bare problemet et år. Cloudflare Worker'en autentificerer allerede som GitHub App (4259031) — den samme app kan installeres på det private repo, og så kan Actions minte et kortlivet installations-token ved hver kørsel. Ingen udløbsdato at holde øje med.

## Ændringer

| Fil | Hvad |
|---|---|
| `.github/workflows/send-push.yml`, `push-subscribe.yml`, `health.yml` | Job-level `env.HAS_APP` = begge app-secrets sat. Nyt step "GitHub App-token til det private repo" (`actions/create-github-app-token@v2`, `id: apptoken`, `if: env.HAS_APP == 'true'`, `continue-on-error: true`, `repositories: fast-as-50-private`) før det step der bruger nøglen. `PRIVATE_REPO_TOKEN: ${{ steps.apptoken.outputs.token \|\| secrets.PRIVATE_REPO_TOKEN }}` + ny `PRIVATE_REPO_AUTH` (`app`/`pat`). Secrets kan ikke bruges i et step-`if`, derfor omvejen over job-env. |
| `scripts/health_report.py` | `SECRETS`-konstanten erstattet af `secrets_for(auth_mode)`: `app` → posten "GitHub App (privat repo)" uden `expires` (dashboardet skriver "ingen udløbsdato"); alt andet, inkl. tom værdi, → PAT'ens nedtælling som før (den sikre antagelse — udløbet forsvinder ikke tavst). `merge_run(..., auth_mode=None)` **sætter** `secrets` i stedet for at `update`'e, så et skift mellem tilstande ikke efterlader en spøgelsespost. `main()` læser `PRIVATE_REPO_AUTH` og printer hvilken tilstand kørslen brugte. `PAT_EXPIRES` og `PRIVATE_REPO_USED_BY` som konstanter. |
| `scripts/test_health_report.py` | +4 tests: pat er standard for `""`/`None`/ukendt, app-posten har intet udløb, returværdien er en kopi (ikke delt tilstand), og `merge_run` skifter nøgleblok begge veje. |
| `index.html` | Overskriften "Nøgler med udløb" → "Nøgler" (App-posten har ingen udløbsdato). `secretState` håndterede allerede manglende `expires`. |
| `docs/PAT_RENEWAL.md` | Skrevet om: App-token først med engangsopsætningen trin for trin, PAT'en som fallback/historik. |
| `docs/PIPELINE.md` | Afsnittet "PAT-udløb 15/10-2026" → "Nøgler til det private repo"; secrets-kolonnerne i workflow-tabellen opdateret. |

Ingen ændring i `store_subscription.py` eller `send_push.py`: de læser `PRIVATE_REPO_TOKEN` fra env, og et installations-token er et almindeligt bearer-token mod Contents API.

## Kennet skal gøre (ellers sker der ingenting — fallback holder push i live)
1. https://github.com/settings/installations → app'en → **Configure** → tilføj `fast-as-50-private` under *Repository access* → **Save**.
2. Tjek at app'ens *Repository permissions* har **Contents: Read and write** (ellers ret og godkend ændringen på installationen).
3. https://github.com/settings/apps → app'en → *Private keys* → **Generate a private key** (henter en `.pem`).
4. https://github.com/hammerbamsen/fast-as-50/settings/secrets/actions → to nye secrets: `FAF_APP_ID` = `4259031`, `FAF_APP_PRIVATE_KEY` = hele `.pem`-filens indhold inkl. BEGIN/END-linjerne.
5. Kør `send-push.yml` manuelt og se at token-steppet ikke blev sprunget over, og at kørslen er grøn.
6. Derefter: slet repo-secret `PRIVATE_REPO_TOKEN`, slet PAT'en på GitHub, og slet `.pem`-filen fra Downloads.

## Ikke verificeret
- Selve token-mintningen kan først testes når secrets er sat (trin 5). Indtil da kører alt videre på PAT'en, og System-kortet viser dens nedtælling som hidtil.
- `repositories: fast-as-50-private` forudsætter at app'en er installeret på netop det repo (trin 1). Mangler installationen, fejler mintningen med 404 — men steppet er `continue-on-error`, så `steps.apptoken.outputs.token` er tom og PAT'en bruges. Kørslen bliver grøn med et rødt kryds på det ene step, og System-kortet viser stadig PAT'ens nedtælling. Med andre ord: rækkefølgen af trin 1-4 er ikke kritisk, men uden trin 1 sker der ingen omlægning.
