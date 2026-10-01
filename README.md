# workflow

Genbrugelige GitHub Actions-workflows for HJK-Automatisering. Et app-repo bygger,
signerer og udruller sit Docker-image med to kald hertil — uden selv at eje
tagging-regler, action-versioner eller signeringslogik.

## Hvad repoet er

Alle actions herinde er pinnet til commit-SHA med versionskommentar. Det er
hele grunden til, at workflows bor her og ikke som en kopi i hvert projekt: når
en action skal bumpes, sker det ét sted, Dependabot åbner PR'en, og alle
kaldere følger med næste gang de kører. Et projekt kalder dem med

```yaml
uses: HJK-Automatisering/workflow/.github/workflows/<fil>@v1
```

hvor `v1` er et flytbart tag, der altid peger på den seneste udgave uden brud.

| Fil | Hvad |
|---|---|
| `.github/workflows/docker-publish.yaml` | Bygger imaget, pusher det til GHCR og signerer det keyless med cosign |
| `.github/workflows/deploy-update.yaml` | Verificerer signatur og digest og skriver den nye version ind i compose-filen på `main` |
| `.github/workflows/validate.yaml` | Strukturkontrol af de to ovenstående. Kører kun i dette repo |
| `scripts/update_compose_image.py` | Scriptet `deploy-update.yaml` opdaterer compose-filen med. Hentes herfra under kørslen |
| `requirements.txt` | `ruamel.yaml`, pinnet. Bruges af scriptet |

**Repoet er offentligt, og det skal det blive ved med.** `deploy-update.yaml`
tjekker dette repo ud fra app-repoets kørsel for at hente scriptet, og det går
kun uden token, fordi repoet er offentligt. App-repoerne er private.

### Sådan hænger udrulningen sammen

Apps kører som Git-baserede stacks i Portainer på den interne Docker-server.
Portainer følger `main` i app-repoet, læser `deploy/docker-compose.yml` og
udruller, når filen ændres. Serveren kan ikke nås fra GitHub, og intet workflow
forsøger det — ingen webhooks, ingen API-kald. Det eneste, workflowet gør, er at
committe den nye image-version til compose-filen på `main`. Den commit er det,
der udløser udrulningen.

Der bygges **kun ved tag-push**. Et commit på `main` bygger ikke, og derfor kan
deploy-commit'en aldrig udløse en ny bygning. Et nyt image går i drift, når
tagget har formen `vX.Y.Z` — præcis tre tal. `v1.2.3-rc1` bygges, men udrulles
ikke.

## Caller-eksempel

Læg filen som `.github/workflows/docker-publish.yaml` i app-repoet. Det eneste,
der skal rettes, er `service` i deploy-jobbet — navnet på servicen under
`services:` i compose-filen, hvis `image:`-felt skal opdateres.

```yaml
name: Docker

# Kalder de genbrugelige workflows i HJK-Automatisering/workflow. Selve
# bygningen, tagging-reglerne, signeringen og de SHA-pinnede actions bor der,
# så de kan bumpes ét sted.
#
# Skal du afvige fra standarden, så kommentér `with`-blokken ind under build.
# Ret ikke i det genbrugelige workflow for at løse et enkelt projekts behov —
# tilføj i stedet et input der.

on:
  push:
    # Kun udgivelser bygger. Et commit i en markdown-fil skal ikke koste en ny
    # digest i GHCR, en post i den offentlige Rekor-log og et tag der flytter
    # sig uden at noget er ændret. Uden et tag bygges der aldrig — og derfor
    # kan deploy-commit'en nedenfor heller aldrig udløse en ny bygning.
    tags: [ 'v*.*.*' ]
  pull_request:
    branches: [ "main" ]
  # Manuel kørsel fra en vilkårlig gren. Uden denne kan en ændring i selve
  # workflowet kun afprøves ved at tagge, og et PR-build pusher ikke noget image.
  workflow_dispatch:

# To tags pushet lige efter hinanden kappes ellers om at skrive :latest, og den
# langsomste build vinder. Afløs i stedet den igangværende.
#
# Denne hører her og ikke i det genbrugelige workflow: det er denne kørsel
# og denne reference der skal aflyses.
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    uses: HJK-Automatisering/workflow/.github/workflows/docker-publish.yaml@v1

    # Skal stå her. Et genbrugeligt workflow kan ikke give sig selv flere
    # rettigheder end kalderen har, og i organisationer hvor standarden er
    # read-only fejler push til GHCR uden denne blok.
    permissions:
      contents: read
      packages: write
      id-token: write

    # GITHUB_TOKEN følger automatisk med. `secrets: inherit` er ikke nødvendigt
    # og bør ikke tilføjes — det giver det kaldte workflow adgang til alt.

    # with:
    #   # Kun hvis noget faktisk kører på arm. Bygger ellers under QEMU for ingenting.
    #   platforms: linux/amd64,linux/arm64
    #   # Hvis Dockerfilen ikke ligger i roden.
    #   dockerfile: ./src/Dockerfile
    #   context: ./src
    #   # Andet imagenavn end <org>/<repo>.
    #   image_name: hjk-automatisering/mit-image
    #   # ADVARSEL: build-args kan læses af alle der kan pulle imaget.
    #   # Aldrig tokens, adgangskoder eller forbindelsesstrenge her.
    #   extra_build_args: |
    #     FEATURE_FLAG=true

  deploy:
    needs: build
    # Grov sortering: kun tags, og kun når der faktisk blev pushet et image
    # (digest er tom på pull_request). Den præcise kontrol af vX.Y.Z ligger i
    # deploy-update, som afslutter grønt uden ændring for fx v1.2.3-rc1.
    if: startsWith(github.ref, 'refs/tags/v') && needs.build.outputs.digest != ''
    uses: HJK-Automatisering/workflow/.github/workflows/deploy-update.yaml@v1

    # contents: write til commit på main. packages: read fordi pakkerne er
    # private; uden login ligner en 401 en manglende signatur. Verifikation
    # med cosign kræver ikke id-token.
    permissions:
      contents: write
      packages: read

    # Én udrulning ad gangen pr. repo, og en igangværende må ikke aflyses —
    # ellers kan en commit til main blive afbrudt midt i et push. Bemærk at
    # GitHub kun holder én ventende kørsel i gruppen: kommer der tre releases
    # hurtigt efter hinanden, springes den midterste over, og compose-filen
    # ender på den sidste.
    concurrency:
      group: deploy-${{ github.repository }}
      cancel-in-progress: false

    with:
      # Navnet på servicen under services: i deploy/docker-compose.yml.
      service: web
      image: ${{ needs.build.outputs.image }}
      digest: ${{ needs.build.outputs.digest }}
      version: ${{ needs.build.outputs.version }}
      # compose_path: deploy/docker-compose.yml   # standard; ret kun hvis filen ligger et andet sted
```

Tre ting at vide om eksemplet:

- **Rettighederne skal stå i kalderen.** Et genbrugeligt workflow kan ikke
  hæve sig over det kaldende jobs rettigheder. Står `permissions` kun i det
  genbrugelige workflow, fejler push til GHCR og commit til `main`.
- **Én ventende kørsel pr. concurrency-gruppe.** Deploy-jobbet har sin egen
  gruppe med `cancel-in-progress: false`, så en igangværende udrulning ikke
  afbrydes. Prisen er, at GitHub kun holder én kørsel i kø: pushes `v1.2.3`,
  `v1.2.4` og `v1.2.5` inden for samme minut, kan `v1.2.4`s deploy-job blive
  aflyst, mens det venter. Imaget `1.2.4` er bygget og signeret, men står
  aldrig i compose-filen. Compose-filen ender på `1.2.5`, som er det, man
  ville have alligevel.
- **Flere images i samme repo:** kald `deploy-update.yaml` én gang pr.
  service, som to deploy-jobs med hver sin `service`. Rammer de hinanden på
  push, henter workflowet `main` igen og prøver igen, op til tre gange.

Dockerfilen skal have `ARG APP_VERSION` og `ARG GIT_SHA`. Build-workflowet
sender dem med som build-args, så appen kan logge ved opstart, hvilken version
der kører.

## Inputs og outputs

### `docker-publish.yaml`

Bygger imaget, pusher det til registryet og signerer det. På `pull_request`
bygges der uden push, og `digest` er tom.

**Inputs**

| Input | Standard | Beskrivelse |
|---|---|---|
| `image_name` | `''` | Imagenavn uden registry. Tom = `<org>/<repo>` for det kaldende repo |
| `registry` | `ghcr.io` | Container-registry |
| `context` | `.` | Build-kontekst |
| `dockerfile` | `./Dockerfile` | Sti til Dockerfile |
| `platforms` | `linux/amd64` | Målplatforme. Tilføj kun arm64, hvis noget faktisk kører på arm — alt andet end runnerens egen platform bygger under QEMU-emulering og tager mange gange så lang tid |
| `sign` | `true` | Signér imaget med cosign. Slå kun fra, hvis registryet ikke understøtter det. Et usigneret image kan ikke udrulles af `deploy-update.yaml` |
| `extra_build_args` | `''` | Ekstra build-args, én pr. linje. **Build-args ender som ENV i det færdige image og kan læses af alle, der kan pulle det. Aldrig hemmeligheder her** |

**Outputs**

| Output | Beskrivelse |
|---|---|
| `digest` | Image-digest, fx `sha256:…`. Brug denne til deploy og verifikation — ikke et tag. Tom på `pull_request`, hvor der bygges uden at pushe; derfor har deploy-jobbet et `if:` på den |
| `version` | Den version, metadata-action udledte. For tagget `v1.2.3` er det `1.2.3` |
| `tags` | Alle tags, der blev bygget, ét pr. linje |
| `image` | Fuld image-reference uden tag, med registry og små bogstaver, fx `ghcr.io/hjk-automatisering/<repo>`. Sendes videre til `deploy-update.yaml`, der skriver `<image>:<version>` i compose-filen |

Tags, der laves ved tag-push `v1.2.3`: `:1.2.3`, `:1.2`, `:latest` og
`:sha-<kort sha>`. Alle peger på samme digest, og der signeres én gang.

**Rettigheder i kalderen:** `contents: read`, `packages: write`, `id-token: write`.

### `deploy-update.yaml`

Skriver `<image>:<version>` ind i `services.<service>.image` i compose-filen
på `main` — efter at have tjekket, at tagget er en release, ligger på `main`,
og at imaget er signeret af det fælles build-workflow og peger på den
verificerede digest. Har ingen outputs.

**Inputs**

| Input | Standard | Beskrivelse |
|---|---|---|
| `compose_path` | `deploy/docker-compose.yml` | Sti til compose-filen i det kaldende repo |
| `service` | *(påkrævet)* | Navnet på servicen under `services:`, hvis `image:`-felt skal opdateres |
| `image` | *(påkrævet)* | Fuld image-reference uden tag, med registry og små bogstaver. Tag outputtet `image` fra `docker-publish.yaml`. **Workflowet logger fast ind på `ghcr.io`** — et image i et andet registry kan ikke verificeres eller slås op |
| `digest` | *(påkrævet)* | Digest på det byggede image. Tag outputtet `digest` fra `docker-publish.yaml`. Det er digesten, der verificeres — ikke tagget |
| `version` | *(påkrævet)* | Versionen uden `v`, fx `1.2.3`. Tag outputtet `version` fra `docker-publish.yaml`. Skrives som `<image>:<version>` i compose-filen |

**Rettigheder i kalderen:** `contents: write`, `packages: read`. Ingen
`id-token`; verifikation kræver det ikke. Ingen `secrets:`; `GITHUB_TOKEN`
følger automatisk med og rækker, så længe `main` ikke er beskyttet — se
[Hvis `main` beskyttes](#hvis-main-beskyttes).

### Verifikationsreglen

`deploy-update.yaml` accepterer kun images, der er signeret af
`docker-publish.yaml` i dette repo fra et udgivet tag, og hvor certifikatets
kilde-repo er det kaldende repo. Identiteten i certifikatet (SAN) er det
**genbrugelige** workflows sti og ref — ikke kalderens — og kilde-repoet står i
certifikatets GitHub-extension. Vil du efterprøve et image selv, er det den
samme regel. Pakkerne er private, så log ind først:

```powershell
gh auth token | docker login ghcr.io -u <github-bruger> --password-stdin
cosign verify `
  --certificate-oidc-issuer https://token.actions.githubusercontent.com `
  --certificate-identity-regexp '^https://github\.com/HJK-Automatisering/workflow/\.github/workflows/docker-publish\.yaml@refs/tags/v' `
  --certificate-github-workflow-repository HJK-Automatisering/<app-repo> `
  ghcr.io/hjk-automatisering/<app-repo>@sha256:<digest>
docker logout ghcr.io
```

Den løsere regel `--certificate-identity-regexp '^https://github\.com/HJK-Automatisering/'`
verificerer også, men den siger kun, at *noget* i organisationen signerede. Den
stramme regel siger, at det var det fælles build-workflow fra et udgivet tag, og
at imaget hører til det repo, der udruller det. Brug den stramme.

## Release

```powershell
git tag v1.2.3
git push origin v1.2.3
```

Tagget skal sidde på en commit, der ligger på `main`. Merge først, tag derefter.

Hvad der sker derefter:

1. **Tag-pushet starter caller-workflowet.** `concurrency` aflyser en eventuel
   kørsel på samme ref.
2. **Build-jobbet** bygger imaget, pusher tags `:1.2.3`, `:1.2`, `:latest` og
   `:sha-…` til GHCR og signerer digesten med cosign. Signaturen og certifikatet
   lægges i den offentlige Rekor-log — også for private repoer. Tager typisk
   nogle minutter; længere ved multi-platform.
3. **Deploy-jobbet** starter, fordi ref'en er et tag og digesten ikke er tom.
   `deploy-update.yaml` gør i rækkefølge:
   - Tjekker, at tagget er præcis `vX.Y.Z`. Er det ikke (fx `v1.2.3-rc1`),
     afsluttes grønt med en `notice`, og intet udrulles.
   - Tjekker ud på `main` og kontrollerer, at tag-commit'en kan nås derfra.
     Ellers rød fejl: et tag på en feature-gren udrulles ikke.
   - Logger ind på `ghcr.io` og verificerer signaturen med den stramme regel.
   - Slår `<image>:1.2.3` op i registryet og kræver, at det peger på præcis den
     verificerede digest.
   - Opdaterer `image:` på den angivne service til `<image>:1.2.3`. Kun den
     linje ændres; kommentarer og formatering bevares. Står versionen der
     allerede, afsluttes grønt uden commit.
   - Kører `docker compose config` som sanity-tjek med en tom, midlertidig
     `stack.env`.
   - Committer som `github-actions[bot]` med beskeden
     `deploy(<app>): <service> -> 1.2.3` og pusher til `main`. Ved konflikt
     hentes `main` igen, op til tre gange.
4. **Portainer opdager ændringen ved næste poll.** Der er ingen webhook, så det
   er polling-intervallet på stacken, der afgør ventetiden. Portainers standard
   er 5 minutter; regn med op til intervallet plus tiden til at pulle imaget og
   genstarte containeren. Det nye image kører, når Portainer har gjort det — og
   først da.

Den deploy-commit, workflowet laver, bygger ikke noget nyt. Der bygges kun ved
tag-push, og `GITHUB_TOKEN` udløser ikke nye kørsler.

## Tilbagerulning

En udrulning er en commit på `main`. Den rulles tilbage ved at vende commit'en:

```powershell
git fetch origin
git revert --no-edit <sha på deploy-commit'en>
git push origin main
```

Compose-filen peger så igen på den forrige version, og Portainer udruller den
ved næste poll. Versionstags overskrives aldrig i GHCR, så det forrige image
findes stadig og er præcis det, der kørte før.

**Tilbagerulningen gælder imaget — ikke databasen.** Har den nye version kørt
en databasemigrering, kører det gamle image nu mod et skema, det ikke kender.
Om det er et problem, afhænger af migreringen; det skal vurderes, før der
rulles tilbage, og det skal stå i app-repoets egen dokumentation, hvordan
migreringer rulles tilbage. Workflowet ved intet om det.

Flyt aldrig et versionstag i app-repoet for at rulle tilbage. Tagget er
historik; det er compose-filen, der siger, hvad der kører.

## Efter en release

**Der er ingen tilbagemelding fra Portainer til GitHub.** En grøn kørsel i
Actions betyder, at compose-filen er opdateret på `main` — ikke, at den nye
version kører. Det skal nogen tjekke:

1. **I Actions:** begge jobs grønne. Deploy-jobbets log slutter med
   `Pushet til main … Portainer udruller ved næste poll.`
2. **På `main`:** en commit `deploy(<app>): <service> -> <version>` fra
   `github-actions[bot]`, der kun ændrer image-linjen.
3. **I Portainer**, når polling-intervallet er gået: stacken viser den nye
   image-reference, containeren er genskabt, og dens log viser den nye
   `APP_VERSION` ved opstart. Står stacken stadig på den gamle version, så se
   Portainers egen log for stacken — typisk manglende læseadgang til GHCR eller
   en fejl i compose-filen, som sanity-tjekket ikke fanger.

### Oprydning efter en rød kørsel

Hvad der skal ryddes op, afhænger af hvor det gik galt:

- **Build-jobbet rødt før push:** intet er publiceret. Ret fejlen og tag en ny
  version — eller slet tagget lokalt og på origin og tag igen; der ligger
  intet i GHCR under det nummer.
- **Build-jobbet rødt efter push** — typisk fejlet signering. Loggen siger det
  udtrykkeligt: *Kørslen er rød, men imaget blev publiceret og er IKKE
  signeret.* Imaget ligger i GHCR, og alle tags peger på det, også `:latest`.
  Det kan ikke udrulles (verifikationen afviser det), men det bør væk: slet
  versionen under pakkens *Versions* i GitHub. Når årsagen er rettet, kan
  kørslen genstartes.
- **Deploy-jobbet rødt:** imaget er bygget og signeret, men compose-filen er
  ikke ændret. Fejlbeskeden er på dansk og siger, hvad der mangler — tag på
  forkert gren, forkert `service`, manglende compose-fil. Ret det og kør
  deploy-jobbet igen fra Actions; det er ufarligt at gentage.

**Signaturen er et selvstændigt artefakt i GHCR.** cosign v3 hæfter den på
imaget som en OCI-referrer med fallback-tagget `sha256-<digest>` — **uden**
`.sig`, som ældre cosign-udgaver brugte. Certifikatet står inde i den blob,
ikke i manifestet. Slettes et image i GHCR, skal versionen med tagget
`sha256-<digest>` også slettes, ellers ligger der en signatur uden image.
Omvendt: slettes kun signaturen, bliver imaget stående og kan ikke længere
udrulles.

## Migrering af en eksisterende app

For en app, der i dag udrulles ved at rette compose-filen i Portainers
web-editor. Fire skridt, i rækkefølge.

**1. Compose-fil i repoet.** Opret `deploy/docker-compose.yml` ud fra det, der
kører i dag. Image med den version, der kører nu — så første udrulning fra Git
ændrer ingenting. Miljøvariabler via `env_file: - stack.env`, og **ingen værdier
i filen**: alt, der i dag står under `environment:`, flyttes til stackens
variabler i Portainer. `stack.env` committes aldrig; læg den i `.gitignore`.
Resten af filen bør følge referencen nederst i denne README.

**2. Caller-workflow.** Læg [caller-eksemplet](#caller-eksempel) i
`.github/workflows/docker-publish.yaml`, og sæt `service` til servicens navn i
compose-filen. Har repoet allerede filen fra den gamle skabelon, er det
deploy-jobbet, der skal tilføjes.

**3. Git-stack i Portainer.** Opret stacken som *Repository*: app-repoets URL,
ref `refs/heads/main`, compose-sti `deploy/docker-compose.yml`, GitOps-opdatering
slået til med polling. Tilføj stackens variabler — det er dem, Portainer skriver
til `stack.env`. Stacken skal kunne læse fra GHCR og fra app-repoet; begge dele
sættes op i Portainer af dem, der administrerer den. Giv den nye stack **samme
navn som den gamle**, hvis navngivne volumes skal følge med: Docker præfikser
volumes med stacknavnet, og et nyt navn giver tomme volumes. Stop den gamle
stack, før den nye startes, så de ikke kører side om side.

**4. Første release.** Tag en ny version og push den. Følg kørslen som under
[Efter en release](#efter-en-release). Når compose-filen på `main` viser den
nye version, og Portainer har skiftet, er migreringen færdig, og web-editoren
bruges ikke mere. Ret aldrig image-linjen i hånden derefter — næste release
overskriver den.

## Hvis `main` beskyttes

`deploy-update.yaml` committer til `main` med `GITHUB_TOKEN`. Det virker, fordi
`main` ikke er beskyttet i de berørte repos. Indføres grenbeskyttelse eller et
ruleset, afvises pushet, og deploy-jobbet fejler med:

> Push til main blev afvist. GITHUB_TOKEN kan ikke skrive til en beskyttet
> gren. Se afsnittet "Hvis main beskyttes" i README for
> HJK-Automatisering/workflow.

Tre veje, i den rækkefølge de bør overvejes. Ingen af dem er implementeret, og
det er med vilje: der er intet behov i dag, og kode uden brug rådner.

**a) Bypass-aktør i rulesettet.** Tilføj GitHub Actions som *bypass actor* på
rulesettet for `main`. Så gælder reglerne stadig for mennesker, men workflowets
push går igennem. Intet ændres i workflows eller kaldere. Det er den enkleste
løsning, og den rækker til krav om PR og reviews.

**b) GitHub App-token.** Rækker (a) ikke — fx fordi rulesettet er sat på
organisationsniveau og ikke må have bypass — så opret en GitHub App med
`contents: write` på de berørte repos, og hent et kortlivet token i
deploy-jobbet med `actions/create-github-app-token` (SHA-pinnet som alle andre
actions her). Det kræver, at `deploy-update.yaml` får en `secrets:`-blok med
app-id og private key, at kalderne sender dem med, og at hemmelighederne
oprettes som organisationshemmeligheder. Det er en kontraktudvidelse og hører
til en opgave.

**c) Signerede commits.** Kræver rulesettet signerede commits, hjælper hverken
(a) eller (b): et git-push fra runneren er ikke signeret. Så skal commit-trinnet
lægges om til GraphQL-mutationen `createCommitOnBranch`, som GitHub selv
signerer, og som giver *Verified*-mærket. Det er en ombygning af
commit-trinnet og hører til en opgave.

Svæk aldrig en eksisterende beskyttelse for at få et deploy-job igennem. Det
er en beslutning for den, der ejer repoet — ikke for workflowet.

## Udgivelse af dette repo

Kaldere peger på `v1`. Det er et flytbart tag, der altid skal pege på den
seneste udgave, der ikke bryder dem.

**Additive ændringer** — nyt valgfrit input med en standard, der bevarer
nuværende adfærd, nyt output, nyt genbrugeligt workflow — udgives som et nyt
minor-tag (`v1.X.0`), og `v1` flyttes med. En ren rettelse uden ny
funktionalitet, fx en bumpet action, nøjes med et patch-tag (`v1.X.Y`):

```powershell
git tag v1.1.0
git push origin v1.1.0
git tag -f v1
git push -f origin v1
```

**Brud** — et input eller output fjernes eller omdøbes, en standardværdi
ændres, eller adfærden ændres, så en eksisterende kalder opfører sig
anderledes — udgives som `v2.0.0` med et nyt flytbart tag `v2`. `v1` bliver
stående, hvor det var, og kaldere skifter selv, når de er klar.

**Versionstags flyttes aldrig.** `v1.0.2` peger på samme commit for evigt.
Kun de flytbare major-tags (`v1`, `v2`) flyttes, og kun med `-f`, som vist.
Et versionstag, der er pushet forkert, rettes med et nyt nummer — ikke ved at
flytte det.

`validate.yaml` kører på PR'er og push til `main` og fanger, hvis et af de
faste inputs eller outputs forsvinder, hvis et job mangler `permissions` eller
`timeout-minutes`, og hvis scriptet ændrer andet end image-linjen. Den er grøn,
før der tagges.

### Vedligehold

- **Dependabot** bumper de SHA-pinnede actions ugentligt, grupperet som
  `docker`, `sigstore` og `python`. En bumpet action er en additiv ændring:
  merge, tag, flyt `v1`.
- **`cosign-release` bumpes i hånden.** Dependabot bumper `cosign-installer`,
  men ikke versionen af cosign, den installerer. Når der kommer en PR på
  `sigstore/cosign-installer`, så ret `cosign-release` i **både**
  `docker-publish.yaml` og `deploy-update.yaml` til nyeste cosign i samme PR.
  De to skal følges ad; signering og verifikation med forskellige
  major-udgaver af cosign er ikke efterprøvet.
- **Regexp'en for cosign-identiteten følger filnavnet.** Identiteten i
  certifikatet er stien til `docker-publish.yaml` i dette repo. Omdøbes eller
  flyttes filen, skal `--certificate-identity-regexp` i `deploy-update.yaml`
  og i denne README rettes med — ellers afvises alle nye images. Det er et
  brud, og det kræver `v2`.
- **Repoet skal forblive offentligt.** `deploy-update.yaml` tjekker det ud fra
  app-repoernes kørsler med `GITHUB_TOKEN`, som kun rækker til offentlige repos.
  Gøres det privat, fejler alle udrulninger ved checkout af scriptet.
- **`requirements.txt`** pinner `ruamel.yaml`. Dependabot bumper den; en bump er
  en additiv ændring, men `validate.yaml`s scripttest skal være grøn først.

## Reference: forventet compose-format

```yaml
services:
  web:
    # Sættes af deploy-update ved release. Ret ikke i hånden.
    image: ghcr.io/hjk-automatisering/<app>:1.4.2
    restart: unless-stopped
    env_file:
      - stack.env
    networks:
      default:
      nginx-proxy-manager_default:
        aliases:
          - <alias>
    mem_limit: 512m
    logging:
      options:
        max-size: "10m"
        max-file: "3"

  db:
    image: postgres:16.4
    restart: unless-stopped
    env_file:
      - stack.env
    volumes:
      - db-data:/var/lib/postgresql/data
    mem_limit: 1g
    logging:
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  db-data:

networks:
  nginx-proxy-manager_default:
    external: true
```
