---
nummer: task-0001
titel: Udrulning ved release-tag via deploy-update.yaml
status: planlagt
kilde: interview
oprettet: 2026-10-01
---

# task-0001 — Udrulning ved release-tag via deploy-update.yaml

## Hvad og hvorfor
Apps udrulles fremover som Git-baserede stacks i Portainer, der følger `main` i app-repoet og læser
`deploy/docker-compose.yml`. I dag rettes image-versionen i hånden i Portainers web-editor. Fremover skal
et release-tag `vX.Y.Z` på app-repoet føre til, at workflowet selv skriver den nye version ind i
compose-filen på `main`, verificeret mod signatur og digest. Portainer kan ikke nås fra GitHub, og
intet workflow må forsøge. Den fulde opgavebeskrivelse står i `docs/prompt-workflow-gitops-v2.md`,
afsnittet *Fase 1*; denne opgave dækker krav 3 til 7 deri.

## Færdig når

Efterprøvet af developer lokalt og i dette repo:

- [ ] Build-workflowet leverer image-navnet som et nyt output, og intet eksisterende input eller output er ændret.
- [ ] Et nyt genbrugeligt workflow kan opdatere image-feltet på én service i en compose-fil uden at ændre andet i filen, heller ikke kommentarer eller formatering.
- [ ] Et tag, der ikke er præcis tre tal efter `v`, fører til en grøn kørsel uden ændring og med en tydelig besked.
- [ ] Et tag, der ikke ligger på `main`, afvises med en dansk fejlbesked.
- [ ] Et image, der ikke er signeret af det fælles build-workflow fra et udgivet tag, afvises.
- [ ] Står versionen allerede i compose-filen, afsluttes kørslen grønt uden commit.
- [ ] Afvises push til `main`, peger fejlbeskeden på README-afsnittet om beskyttede grene.
- [ ] Valideringen i dette repo tjekker også det nye workflow med de samme strukturkrav og er grøn.
- [ ] Identiteten i cosign-certifikatet er dokumenteret i developers noter, og cosign-reglen passer til den.

Efterprøves af mennesket ved testkørsel på ba-bfo-fagligt-ledelsestilsyn, når det repo har fået
compose-fil og opdateret caller:

- [ ] Et release-tag fører uden manuel indgriben til en commit på `main` med den nye version, og Portainer udruller den.
- [ ] Et forhåndstag (fx `-rc1`) bygges, men udrulles ikke.

## Sådan bygger vi det

### Nyt output i `.github/workflows/docker-publish.yaml`
- `image`: fuld reference uden tag, med registry og små bogstaver, fx `ghcr.io/hjk-automatisering/<repo>`.
  Beregnes i ét trin og genbruges i signerings- og fejltrinnet, der i dag hver især laver `tr '[:upper:]' '[:lower:]'`.
- Inputs og eksisterende outputs røres ikke. `validate.yaml` skal fremover kræve outputtet `image`.

### Nyt genbrugeligt workflow `.github/workflows/deploy-update.yaml`
Inputs: `compose_path` (standard `deploy/docker-compose.yml`), `service`, `image`, `digest`, `version`.
Repos med flere images kalder workflowet én gang pr. service; push-konflikter håndteres af retry.
Ét job, `permissions: contents: write, packages: read`, `timeout-minutes` sat, ingen `concurrency`
(den hører i kalderen). Ingen `secrets:` deklareres. Trin i rækkefølge:

1. **Afgør om tagget skal udrulles.** Matcher `github.ref_name` ikke `^v[0-9]+\.[0-9]+\.[0-9]+$`,
   afsluttes **grønt** med `::notice::` om, at tagget ikke er en release. Den præcise kontrol er
   workflowets ansvar; kalderens `if:` er kun grov.
2. **Tjek at tagget ligger på `main`.** `git merge-base --is-ancestor <tag-sha> origin/main`.
   Kræver fuld historik ved checkout. Ellers dansk `::error::` og stop.
3. **Log ind på registryet** med `GITHUB_TOKEN` (samme mønster som i `docker-publish.yaml`).
4. **Verificér signaturen** med `cosign verify` mod `<image>@<digest>`, OIDC-udsteder
   `https://token.actions.githubusercontent.com`, identitet begrænset til
   `^https://github\.com/HJK-Automatisering/workflow/\.github/workflows/docker-publish\.yaml@refs/tags/v`,
   og certifikatets kilde-repo lig `github.repository`. Se *Undersøgelse før implementering* nedenfor.
   Installer cosign med samme SHA-pinnede `sigstore/cosign-installer` og samme `cosign-release` som `docker-publish.yaml`.
5. **Tjek at tagget peger på digesten.** `docker buildx imagetools inspect <image>:<version>` skal give
   præcis den verificerede digest. Ellers dansk fejl og stop.
6. **Tjek `main` ud** (ikke tagget) og **tjek workflow-repoet ud** i en undermappe med
   `repository: HJK-Automatisering/workflow` og `ref: ${{ github.job_workflow_sha }}`, så scriptet er samme commit som workflowet.
7. **Opdatér image-feltet** med `scripts/update_compose_image.py` (ruamel.yaml fra `requirements.txt`,
   `pip install -r`). Scriptet ændrer kun `services.<service>.image` og bevarer kommentarer og formatering.
   Tager argumenterne `<compose_path> <service> <image>:<version>` og afslutter med en særskilt exit-kode,
   når der ingen ændring er, så workflowet kan skelne.
8. **Idempotens.** Ingen ændring: grøn afslutning med `::notice::`, ingen commit.
9. **Sanity-tjek.** Opret tom, midlertidig `stack.env` ved siden af compose-filen, kør
   `docker compose -f <fil> config -q`, slet filen igen. (Fase 2 erstatter trinnet med compose-lint.)
10. **Commit og push til `main`.** Forfatter `github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>`.
    Besked: `deploy(<app>): <service> -> <version>` med `<app>` = `github.event.repository.name`; brødtekst med
    digest, link til build-kørslen (`github.server_url/<repo>/actions/runs/<run_id>`) og tag-commit'en.
    Ved konflikt: `git pull --rebase` og nyt forsøg, højst tre gange. Afvises push med 403 eller
    "protected branch": dansk fejl, der henviser til README-afsnittet "Hvis `main` beskyttes" (skrives i task-0002).

Alle fejlbeskeder på dansk som `::error::`, så en udvikler kan rette uden at læse workflowet.
Kommentarer på dansk, der forklarer hvorfor, i samme stil som `docker-publish.yaml`.

### Nye filer
- `scripts/update_compose_image.py` — se trin 7. Kan køres lokalt: `.venv\Scripts\python.exe scripts\update_compose_image.py <fil> <service> <image:tag>`.
- `requirements.txt` — `ruamel.yaml` pinnet til én version.
- `.venv/` oprettes lokalt (versionsstyres ikke, allerede i `.gitignore`). Alle lokale Python-kald går gennem den.
- `.github/dependabot.yml` udvides med `pip`-økosystemet, grupperet som `python`, så pinnen bumpes.

### Udvid `.github/workflows/validate.yaml`
Samme kontroller som for `docker-publish.yaml`, nu også for `deploy-update.yaml`: `workflow_call` findes,
outputs peger på eksisterende job-outputs, hvert job har `permissions` og `timeout-minutes`, ingen
bindestreger i inputnavne. Faste inputs for `deploy-update.yaml`: `compose_path`, `service`, `image`,
`digest`, `version`. Fast output for `docker-publish.yaml` udvides med `image`. Kør desuden
`scripts/update_compose_image.py` mod en lille eksempelfil i `tests/compose/` og tjek, at kun image-linjen ændrede sig.

### Undersøgelse før implementering af trin 4
Læs certifikatet på et eksisterende signeret image fra et af de kaldende repos (fx ba-bfo-fagligt-ledelsestilsyn
eller ba-fritidsportalen). Metode: `gh auth token | docker login ghcr.io -u <bruger> --password-stdin`, derefter
`docker manifest inspect ghcr.io/hjk-automatisering/<repo>:sha256-<digest>.sig` (eller cosign, hvis det installeres i `.venv`-fri form).
Dokumentér SAN og extensions i *Developers noter*. Bekræftes det, at SAN er det genbrugelige workflows ref,
bruges den stramme regexp ovenfor. Er SAN i stedet kalderens workflow, bruges `^https://github\.com/HJK-Automatisering/`
og det skrives som indvending, så architect kan tage stilling. Log ud af registryet bagefter (`docker logout ghcr.io`).

## Hvad vi ikke rører
- Eksisterende inputs, outputs, trin og tagging-regler i `docker-publish.yaml`. Kun det nye output og genbrug af den beregnede reference.
- Eksisterende kontroller i `validate.yaml`; der tilføjes, intet fjernes.
- `.github/dependabot.yml` ud over det nye `pip`-afsnit.
- Caller-skabelonen i agenter-repoet, app-repoerne og Portainer. De håndteres i andre tråde.
- Ingen `on.push.branches` eller `paths-ignore` i noget eksempel: der bygges kun på tags.
- Ingen tags oprettes eller flyttes. Udgivelse som `v1.1.0` er menneskets skridt efter task-0002.

## Afhænger af
intet

## Beslutninger
- BESLUTTET: Kun `GITHUB_TOKEN`, ingen App-token, ingen `secrets:` — `main` er ubeskyttet i de berørte repos, og commits med `GITHUB_TOKEN` udløser ikke nye kørsler. Reserveløsninger dokumenteres kun i README (task-0002).
- BESLUTTET: Scriptet ligger som fil og hentes med `job_workflow_sha` — gør det testbart lokalt og i `validate.yaml`, og fase 2's lint-script følger samme mønster. Inline-Python i `run:` afvist som uvedligeholdeligt ved denne størrelse.
- BESLUTTET: `ruamel.yaml` frem for pyyaml eller `sed` — bevarer kommentarer og formatering i en fil, Portainer og mennesker læser. `sed` afvist som skrøbeligt over for indrykning og dubletter.
- BESLUTTET: Den præcise `vX.Y.Z`-kontrol i workflowet, ikke i kalderen — kalderen kan ikke regex-matche, og workflowet skal ikke stole på en kopieret skabelon. Ikke-matchende tag er grøn no-op, ikke fejl.
- BESLUTTET: `packages: read` og login før verifikation — pakkerne er private; uden login ligner en 401 en manglende signatur.
- BESLUTTET: Stram cosign-identitet til `docker-publish.yaml@refs/tags/v` plus kilde-repo-tjek, under forudsætning af undersøgelsen — kun images fra det fælles workflow fra et udgivet tag kan komme i drift, og repo A kan ikke udrulle repo B's image.
- BESLUTTET: `requirements.txt`, `pip` i Dependabot og `.venv` kommer med i fase 1 — ruamel ankommer nu, og kontrakten kræver virtuelt miljø til lokale Python-kald. Trukket frem fra fase 2's krav 11.
- BESLUTTET: Developer må logge ind på GHCR med menneskets lokale `gh`-token, kun lokalt og kun under denne opgave, for at læse signaturens manifest. Logout bagefter.
- BESLUTTET: Testen sker på ba-bfo-fagligt-ledelsestilsyn, ikke et demo-repo — mennesket vil have den første rigtige app med i fase 1. Compose-fil og caller i det repo og Git-stacken i Portainer ligger uden for denne opgave.

## Åbne punkter

## Indvendinger

---

## Developers noter

### Hvad er lavet
### Hvad er ikke lavet, og hvorfor
### Uklart
