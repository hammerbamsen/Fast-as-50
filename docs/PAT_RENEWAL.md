# PAT-fornyelse

## Aktuelt (7/9-2026): `PRIVATE_REPO_TOKEN` — udløber 15. oktober 2026

Den eneste PAT der stadig er i brug. Fine-grained token med **Contents: Read and write** på det private repo (`secrets.PRIVATE_REPO`), hvor `push_subscriptions.json` ligger. Bruges af tre workflows: `send-push.yml` (daglig/aften-push + oprydning af døde subscriptions), `push-subscribe.yml` (gemmer nye subscriptions) og `health.yml` (push-alert ved fejlede workflows). Udløber den, stopper alle push-notifikationer stille — derfor står udløbsdatoen i `health.json` (`secrets.PRIVATE_REPO_TOKEN.expires`, sat i `scripts/health_report.py`), og System-kortet på Mere-fanen viser nedtællingen (gul ≤ 21 dage, rød ≤ 7).

Fornyelse:
1. GitHub → Settings → Developer settings → [Fine-grained tokens](https://github.com/settings/personal-access-tokens) → find tokenet (eller opret nyt: Repository access = kun det private repo, Permissions = Contents Read/Write, Metadata Read; udløb max 1 år).
2. Kopiér tokenet ind i `hammerbamsen/fast-as-50` → Settings → Secrets and variables → Actions → `PRIVATE_REPO_TOKEN`.
3. Opdatér `expires` i `SECRETS` i `scripts/health_report.py` (og kør `health.yml` manuelt, så System-kortet viser den nye dato).

Bedre: erstat PAT'en med et GitHub App-token. Worker'en autentificerer allerede som GitHub App (se `workers/webhook-dispatch/README.md`); installér samme app på det private repo og udsted et kortlivet token i workflowet (`actions/create-github-app-token`). Så er der ingen udløbsdato at holde øje med. Se `docs/PIPELINE.md`.

---

## Historik: klient-PAT'er (FORÆLDET — se workers/webhook-dispatch/README.md)

**Forældet 14/7:** ingen af klientsiderne (plan.html, eva.html, af.html, checkin.html, index.html) bruger længere et GitHub PAT i browseren. Alle dispatcher nu via Cloudflare Worker'en med én delt hemmelighed (`data/auth_config.json` + `PLAN_EDIT_SECRET`, indsat via ⚙ Hemmelighed-knappen på hver side). Denne fil er kun bevaret for historik.

---

GitHub Personal Access Token'et udløb periodisk. Sådan fornyede du det (historisk):

1. Gå til [GitHub Personal Access Tokens](https://github.com/settings/personal-access-tokens)
2. Find "fast-as-50 fine-grained" i listen (eller opret nyt hvis udløbet)
3. Klik **Regenerate** eller **Generate new token**
4. Indstillinger:
   - **Repository access:** kun `hammerbamsen/fast-as-50`
   - **Expiration:** 1 år frem
   - **Permissions:** Contents (Read+Write), Actions (Read+Write), Metadata (Read)
5. Copy tokenet
6. **Opdater 3 steder:**
   - `data/config.json` → felt `patExpiry` opdateres til ny udløbsdato
   - eva.html/af.html/checkin.html på iPhone → tap Token, indsæt nyt token, Gem (Safari overskriver Keychain-værdi). plan.html bruger ikke længere denne PAT — se `workers/webhook-dispatch/README.md` for dens delte hemmelighed i stedet.
   - Send til Claude → memory opdateres
