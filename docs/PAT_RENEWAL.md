# Nøgler til det private repo (push-subscriptions)

Push-abonnementer ligger i `hammerbamsen/fast-as-50-private`. Tre workflows skriver eller læser dem: **Send daglig push-påmindelse**, **Modtag push-subscription** og **Workflow-sundhed**.

## Nu: GitHub App-token (ingen udløb)

Siden 9/9-2026 minter workflowsene selv et installations-token pr. kørsel med `actions/create-github-app-token`, fra den samme GitHub App som Cloudflare Worker'en bruger (App ID **4259031**). Tokenet lever en time og skal aldrig fornys. `health.json` viser "GitHub App (privat repo) · ingen udløbsdato" i System-kortet.

Fallback er indbygget: mangler `FAF_APP_ID` eller `FAF_APP_PRIVATE_KEY`, bruges den gamle PAT i stedet, og System-kortet viser dens nedtælling igen. Push stopper altså aldrig midt i en omlægning.

### Engangsopsætning (gjort 9/9-2026)

1. **Giv app'en adgang til det private repo:** https://github.com/settings/installations → app'en → **Configure** → under *Repository access* tilføj `fast-as-50-private` (behold `fast-as-50`) → **Save**.
2. **Tjek rettigheden:** app'ens indstillinger → *Permissions* → Repository permissions → **Contents: Read and write**. Ændrer du den, skal installationen godkende ændringen (banner på siden fra punkt 1).
3. **Hent en privat nøgle:** https://github.com/settings/apps → app'en → *Private keys* → **Generate a private key**. Filen `.pem` hentes ned én gang. (Den nøgle Worker'en bruger, ligger i Cloudflare og kan ikke læses ud igen — generér bare en ny; en app må have flere.)
4. **Læg to secrets i repoet:** https://github.com/hammerbamsen/fast-as-50/settings/secrets/actions → *New repository secret*:
   - `FAF_APP_ID` = `4259031`
   - `FAF_APP_PRIVATE_KEY` = **hele** indholdet af `.pem`-filen, inklusive `-----BEGIN RSA PRIVATE KEY-----` og `-----END RSA PRIVATE KEY-----` og linjeskiftene.
5. **Verificér:** kør https://github.com/hammerbamsen/fast-as-50/actions/workflows/send-push.yml manuelt. I loggen skal steppet *GitHub App-token til det private repo* være kørt (ikke sprunget over), og kørslen slutte grønt. Bagefter viser Mere → System-kort "GitHub App (privat repo)" uden udløbsdato.
6. **Ryd op**, når punkt 5 er grønt: slet `PRIVATE_REPO_TOKEN` fra repo-secrets og slet PAT'en på https://github.com/settings/personal-access-tokens. Slet også `.pem`-filen fra Downloads — den er en nøgle, ikke et dokument.

## Før: fine-grained PAT (`PRIVATE_REPO_TOKEN`, udløb 15/10-2026)

Bevaret som fallback og som historik. Skal den fornys: https://github.com/settings/personal-access-tokens → *Generate new token* → adgang kun til `fast-as-50-private`, **Contents: Read and write**, udløb 1 år → indsæt værdien i repo-secret `PRIVATE_REPO_TOKEN`. Udløbsdatoen i System-kortet står i `scripts/health_report.py` (`PAT_EXPIRES`) og skal rettes samtidig.

---

## Historik: PAT i browseren (forældet 14/7-2026)

Ingen af klientsiderne bruger længere et GitHub-token i browseren. Alle dispatcher via Cloudflare Worker'en med én delt hemmelighed (`data/auth_config.json` + `PLAN_EDIT_SECRET`, indsat via ⚙ Hemmelighed-knappen). Se `workers/webhook-dispatch/README.md`.
