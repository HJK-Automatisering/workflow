---
nummer: task-0010
titel: deploy-update kan pushe som GitHub App
status: afsluttet
kilde: bestilling fra udviklingscentralen (task-0030 dér)
oprettet: 2026-11-25
---

# task-0010 — deploy-update kan pushe som GitHub App

## Hvad og hvorfor
Udviklingscentralen har fået et ruleset på hovedgrenen, og GitHubs indbyggede
Actions-app kan ikke stå på bypass-listen i organisationen (API'et afviser med
422, og appen kan ikke installeres manuelt — efterprøvet 2026-11-25).
Organisationen har derfor sin egen app, `hjk-deploy-bot`, med kun Contents
read/write, installeret alene på det repo og allerede på rulesettets
bypass-liste. Org-hemmelighederne `DEPLOY_BOT_APP_ID` og
`DEPLOY_BOT_PRIVATE_KEY` findes, scoped til det repo.

`deploy-update.yaml` skal kunne pushe som den app — valgfrit og
bagudkompatibelt, så ingen eksisterende kalder kan mærke ændringen.

## Færdig når
- [ ] `deploy-update.yaml` har to valgfrie secrets, `deploy_bot_app_id` og
      `deploy_bot_private_key`.
- [ ] Er begge sat: et kortlivet token mintes med
      `actions/create-github-app-token` (SHA-pinnet), og checkout og push
      bruger det. Committen må gerne stå som appen i historikken.
- [ ] Er ingen af dem sat: præcis dagens adfærd med `GITHUB_TOKEN`.
- [ ] Er kun den ene sat: jobbet stopper med en dansk `::error` — aldrig et
      stille fald tilbage til `GITHUB_TOKEN`.
- [ ] `validate.yaml` fanger, hvis en af de to secrets forsvinder eller bliver
      påkrævet, og hvis et secretnavn får bindestreg.
- [ ] README: secrets i kontraktafsnittet for `deploy-update.yaml`,
      caller-eksemplet viser den eksplicitte `secrets:`-blok udkommenteret, og
      *Hvis `main` beskyttes* beskriver vej (b) som implementeret.
- [ ] Udgivet som minor-tag, og `v1` flyttet. Menneskets trin.

## Hvad vi ikke rører
- `docker-publish.yaml`, `compose-lint.yaml` og begge scripts.
- Docker-login i deploy-jobbet: `GITHUB_TOKEN` og kalderens `packages: read`.
- Kalder-ændringen i udviklingscentralen. Den er det repos eget trin bagefter.

## Afhænger af
intet

## Beslutninger
- BESLUTTET: Secrets hedder `deploy_bot_app_id` og `deploy_bot_private_key` —
  underscore som inputnavnene, og kalderen sender dem eksplicit; bestillingen
  forbyder `secrets: inherit` i kalderen.
- BESLUTTET: Én sat og én glemt er en fejl, ikke et fald tilbage til
  `GITHUB_TOKEN`. En slåfejl i kalderen skal vise sig med det samme, ikke som
  en afvist push med en vildledende besked.
- BESLUTTET: Commit-identiteten er appens bot-bruger (`<slug>[bot]` med id i
  noreply-adressen), slået op med app-tokenet — ikke hårdkodet, så en anden
  app kan bruges uden ændring her.
- BESLUTTET: `actions/create-github-app-token` pinnet til `v3.4.0`
  (`f418cff`). Det er GitHubs egen `actions`-organisation, samme kategori som
  `actions/checkout` — ikke en ny tredjepart.

## Åbne punkter
intet

## Indvendinger

## Developers noter
<Alt over denne overskrift ejes af architect. Alt under skrives kun af developer.>

Bygget i én session uden for rollerne, på grenen `task-0010-deploy-bot-push`.

**Lavet:**
- `deploy-update.yaml`: `secrets:`-blok med de to valgfrie secrets; job-env
  `APP_ID_SET`/`APP_KEY_SET`; nyt trin *Tjek app-secrets* (fejl ved kun én
  sat); nyt trin *Mint app-token* med `actions/create-github-app-token`
  pinnet til `f418cff` (v3.4.0); `token:` på checkout med fald tilbage til
  `github.token`; commit-identiteten er appens bot-bruger (id slås op med
  `gh api`), ellers `github-actions[bot]` som i dag; 403-beskeden ved push
  skelner mellem app og `GITHUB_TOKEN`.
- `validate.yaml`: `valgfrie_secrets` på deploy-update-kontrakten — fejl hvis
  en secret forsvinder eller bliver påkrævet — og bindestreg-tjekket dækker
  nu også secretnavne.
- README: secrets-tabel under kontraktafsnittet, udkommenteret
  `secrets:`-blok i caller-eksemplet, *Hvis `main` beskyttes* med vej (b)
  som implementeret, og noterne om at et app-push udløser workflows (men
  ingen byggeløkke, fordi der kun bygges på tags).
- `CLAUDE.md`: rækken for `deploy-update.yaml` nævner app-pushet.

**Efterprøvet lokalt:** strukturvalideringen fra `validate.yaml` er grøn og
viser de to secrets; negativtest med en fjernet secret, en påkrævet secret og
en bindestreg i navnet giver hver sin fejl; `bash -n` på alle `run:`-blokke.

**Hvad er ikke lavet, og hvorfor:** selve kørslen som app kan kun prøves i
Actions fra udviklingscentralen, når dens kalder sender de to secrets — det
er det repos eget trin. Udgivelsen (minor-tag og flyt af `v1`) er menneskets
trin.

**Uklart:** intet.
