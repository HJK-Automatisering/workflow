---
nummer: task-0005
titel: compose-lint: regler for compose-filer i pull requests og før udrulning
status: afsluttet
kilde: interview
oprettet: 2026-10-02
---

# task-0005 — compose-lint: regler for compose-filer i pull requests og før udrulning

## Hvad og hvorfor
Compose-filen på `main` er det, der kører i Portainer. I dag tjekker udrulningen kun, at `docker compose`
kan læse filen; glemte felter, åbne porte, bind-mounts og hemmeligheder i klartekst går igennem. Udviklere
og agenter følger en fælles deploy-kontrakt for compose-filer, og de samme regler skal håndhæves maskinelt:
lokalt før en PR, i pull requests, og i deploy-jobbet før commit. Opgavebeskrivelsen: fase 2, krav 13 til 16.
Reglerne om miljøvariabler er ændret i forhold til opgavebeskrivelsen, fordi Portainer ikke skriver `stack.env`.

## Færdig når
- [x] En compose-fil, der bryder en regel, giver en dansk fejl med service, regelnavn og linjenummer, både ved lokal kørsel, i en pull request og i deploy-jobbet.
- [x] En fil efter referencen i README passerer uden fejl.
- [x] En gyldig undtagelse gør fejlen til en advarsel; en undtagelse uden godkender og dato, eller med ukendt regelnavn, er selv en fejl; en undtagelse ældre end et år giver en advarsel.
- [x] Scriptet kan køres lokalt mod en fil uden GitHub-kontekst og uden Docker; mangler Docker, springes compose-tjekket over med en advarsel.
- [x] Deploy-jobbet kører lint i stedet for sanity-tjekket, committer ikke hvis lint fejler, og opretter ikke længere en midlertidig `stack.env`.
- [x] Valideringen i dette repo tjekker det nye workflow med samme strukturkrav, kører scriptet mod mindst ét dårligt eksempel pr. regel, et godt eksempel, en gyldig og en ugyldig undtagelse, og er grøn.
- [x] README dokumenterer alle regler, undtagelsesformatet og lokal kørsel, og caller-eksemplet har lint-jobbet.

Efterprøves af mennesket før `v1` flyttes:

- [x] Scriptet er kørt lokalt mod compose-filerne i de kendte kaldere, og ingen app får en rød release af regler, den aldrig har set. (Kørt af mennesket 2026-10-02 mod ba-bfo-fagligt-ledelsestilsyn: fem fund, rettes i app-repoet; se loggen.)

## Sådan bygger vi det

### `scripts/compose_lint.py`
Argument: `<compose-fil>`. Exit 0 = ingen fejl (advarsler tilladt), 1 = fejl, 2 = forkerte argumenter.
`ruamel.yaml` fra `requirements.txt`, så hver fejl kan angive linjenummer. Fejl som `::error file=<fil>,line=<n>::`,
advarsler som `::warning file=...,line=...::`, begge på dansk med service og regelnavn, så fejlen kan rettes uden at
læse scriptet. Lokal kørsel: `.venv\Scripts\python.exe scripts\compose_lint.py deploy\docker-compose.yml`.

Rækkefølge: (1) parse; ugyldig YAML er én fejl. (2) `docker compose -f <fil> config -q --no-interpolate`,
så tjekket ikke afhænger af hvilke variabler der er sat, og ingen `stack.env` behøves. Findes `docker compose` ikke,
springes trinnet over med en advarsel. (3) reglerne pr. service. (4) undtagelser.

| Regel | Fejler når |
|---|---|
| `build` | `build:` findes |
| `latest` | image mangler tag, tagget indeholder intet ciffer, eller tagget er et af `latest`, `main`, `master`, `stable`, `edge`, `dev`, `nightly`, `lts` |
| `privileged` | `privileged: true` |
| `docker-sock` | et volume peger på `/var/run/docker.sock` |
| `bind-mount` | et volume er en sti på værten (`/`, `./`, `../`), i kort eller lang form (`type: bind`), i stedet for et navngivet volume |
| `host-adgang` | `network_mode: host`, `pid: host`, `devices`, `cap_add`, `sysctls` eller `security_opt` |
| `hemmelighed` | en nøgle under `environment:` indeholder `PASSWORD`, `PASSWD`, `SECRET`, `TOKEN` eller `CREDENTIALS` som delstreng, eller `KEY` eller `PRIVATE` som helt led adskilt af `_`, og værdien ikke er præcis `${NAVN}`. `${NAVN:-standard}` og `${NAVN-standard}` fejler også |
| `env-vaerdi` | enhver anden værdi under `environment:`, der ikke er præcis `${NAVN}`. En nøgle uden værdi fejler også |
| `env-fil` | `env_file:` findes, eller en `stack.env` eller `.env` er committet. Tjekket bruger `git ls-files` i filens repo; uden git springes det over med en advarsel |
| `restart` | `restart` mangler eller er `no` (også YAML 1.1-boolean `False`) |
| `mem-limit` | `mem_limit` og `deploy.resources.limits.memory` mangler begge |
| `logging` | `logging.options.max-size` eller `max-file` mangler |
| `ports` | `ports:` findes |
| `container-name` | `container_name` findes |
| `eksternt-netvaerk` | et netværk med `external: true` er ikke `nginx-proxy-manager_default` |
| `alias` | en service på `nginx-proxy-manager_default` mangler et netværksalias |

`environment:` i både mapping-form (`NØGLE: ${NØGLE}`) og listeform (`- NØGLE=${NØGLE}`). Variabelnavnet i
substitutionen behøver ikke være lig nøglen. `hemmelighed` vinder over `env-vaerdi` for samme nøgle, så én
nøgle giver én fejl.

**Undtagelser** i topniveau-feltet `x-undtagelser` som i opgavebeskrivelsen: `service`, `regel`, `begrundelse`,
`godkendt-af`, `dato`. En regel dækket af en gyldig undtagelse giver en advarsel i stedet for en fejl. Ukendt
regelnavn, manglende `godkendt-af` eller `dato` er en fejl. Dato ældre end et år: advarsel. En undtagelse,
der ikke matcher nogen fejl, er en advarsel (den er død).

### `.github/workflows/compose-lint.yaml`
Genbrugeligt. Input `compose_path`, standard `deploy/docker-compose.yml`. Ét job `compose-lint`,
`permissions: contents: read`, `timeout-minutes: 10`, ingen `concurrency`, ingen `secrets:`. Trin: checkout af
kalderens repo; checkout af dette repo i `.workflow-repo` med `repository: HJK-Automatisering/workflow`,
`ref: ${{ github.job_workflow_sha }}`, `persist-credentials: false` (samme mønster og samme SHA'er som
`deploy-update.yaml`); `python -m pip install -r .workflow-repo/requirements.txt`; kør scriptet. Kommentarer på
dansk, der forklarer hvorfor.

### `.github/workflows/deploy-update.yaml`
Trinnet *Sanity-tjek compose-filen* erstattes af et trin, der kører `scripts/compose_lint.py` fra
`.workflow-repo` mod compose-filen efter opdateringen og før commit. Samme `if:` som i dag (kun ved ændring).
Ingen `stack.env` oprettes længere. Fejler lint: `::error::` om at intet er committet, og at filen skal rettes på
`main`. Kommentaren ved det gamle trin siger, at Portainer genererer `stack.env`; den forsvinder med trinnet.
Alt andet i workflowet urørt.

### `.gitignore`
Kommentaren ved `stack.env` siger, at Portainer genererer filen. Ret begrundelsen: filen hører ikke til modellen
og må aldrig committes, fordi lint-reglen `env-fil` afviser den. Selve ignoreringen bliver stående. (Fund fra task-0003.)

### `.github/workflows/validate.yaml`
- `WORKFLOWS` får `compose-lint.yaml` (job `compose-lint`, input `compose_path`, ingen outputs).
- Nyt trin *Afprøv scripts/compose_lint.py*: kører scriptet mod `tests/compose/ok/*.yml` (forventer exit 0, ingen `::error`),
  mod `tests/compose/fejl/<regel>.yml` for hver regel (forventer exit 1 og regelnavnet i output),
  mod `tests/compose/undtagelse-gyldig.yml` (exit 0, `::warning` med regelnavnet) og `tests/compose/undtagelse-ugyldig.yml` (exit 1).
  Referencen fra README ligger som et af de gode eksempler. `tests/compose/deploy-example.yml` bliver stående til
  scripttesten for `update_compose_image.py` og skal selv være regelret.
- Docker findes på runneren, så compose-tjekket kører med i selvtesten.

### README og CLAUDE.md
- Caller-eksemplet får jobbet `lint` med `uses: ...compose-lint.yaml@v1` og `permissions: contents: read`, uden `if:`;
  det kører på alle pull requests og ved manuel kørsel. Kommentar om hvorfor der ikke er stifilter.
- Nyt afsnit under *Inputs og outputs* for `compose-lint.yaml`, og et afsnit *Regler for compose-filen* med tabellen,
  undtagelsesformatet, lokal kørsel og at reglerne er de samme som i agenternes deploy-kontrakt.
- *Release*, trin 3: sanity-tjekket er nu lint. *Migrering*, trin 1: kør lint lokalt før PR'en.
- Filtabellen øverst og CLAUDE.md's mappestruktur får de nye filer; `validate.yaml`s række nævner selvtesten.

## Hvad vi ikke rører
- `docker-publish.yaml` (task-0004 ejer den), `scripts/update_compose_image.py`.
- Alle øvrige trin, inputs og fejlbeskeder i `deploy-update.yaml`.
- Regelnavnene fra opgavebeskrivelsen beholdes uændret; kun `env-vaerdi` er ny. Agenternes deploy-kontrakt opdateres i agenter-repoet af mennesket.
- Caller-skabelonen i agenter-repoet, app-repoerne, Portainer. Ingen tags, ingen udgivelse.

## Afhænger af
task-0003, task-0004, task-0006 (begge rører `deploy-update.yaml`, `tests/compose/deploy-example.yml` og README; lint bygges sidst, så eksempelfilen med `worker` er på plads)

## Beslutninger
- BESLUTTET: Ingen literaler under `environment:`; `hemmelighed` for de kendte nøglemønstre, `env-vaerdi` for resten, `env-fil` forbyder `env_file` helt — Portainer skriver ikke `stack.env` for Git-stacks, og princippet om ingen værdier i compose-filen består. Alternativ B (kun hemmelige nøgler) afvist, fordi en forbindelsesstreng under en neutral nøgle ville slippe igennem. Godkendt af mennesket 2026-10-02.
- BESLUTTET: Lint-jobbet i samme caller-workflow, på alle pull requests, uden stifilter — én skabelonfil, og et stifilter pr. job kræver en tredjeparts-action. Separat caller-fil afvist. Godkendt af mennesket 2026-10-02.
- BESLUTTET: Lint blokerer udrulningen i deploy-jobbet, som opgavebeskrivelsen siger. Prisen er, at en app, der aldrig har set reglerne, kan få en rød release; derfor efterprøver mennesket de kendte kaldere, før `v1` flyttes.
- BESLUTTET: `--no-interpolate` i stedet for en midlertidig `stack.env` — tjekket skal ikke afhænge af runnerens miljø, og filen hører ikke længere til modellen.
- BESLUTTET: Scriptet kører uden Docker lokalt med en advarsel — udviklere uden Docker skal stadig kunne lint'e før en PR; den fulde kontrol sker i Actions.
- BESLUTTET: `validate.yaml` forbliver på pyyaml; kun scriptet bruger ruamel — som opgavebeskrivelsen siger.
- BESLUTTET: Fase 2 delt i task-0004 og task-0005 — uafhængige leverancer; opgavebeskrivelsen siger selv, at tag-beskyttelsen kan trækkes ud.

## Åbne punkter

## Indvendinger

---

## Developers noter

Gren `task-0005-compose-lint`, fem commits (script, workflow, deploy-update, validering, README). Intet pushet.

### Hvad er lavet

Holdt op mod *Færdig når*:

- **Dansk fejl med service, regelnavn og linjenummer** — `scripts/compose_lint.py`. Hvert fund skrives som `::error file=<fil>,line=<n>::[<regel>] <service>: <besked>` (advarsler som `::warning`), på stderr som i `update_compose_image.py`. Samme script køres lokalt, i `compose-lint.yaml` og i `deploy-update.yaml`, så formatet er ens alle tre steder. Fund uden regel bruger `[yaml]`, `[compose]`, `[struktur]` og `[undtagelse]`. Rækkefølgen er som i opgaven: parse (ugyldig YAML er én fejl, resten springes over), `docker compose -f <fil> config -q --no-interpolate`, reglerne pr. service og for netværk, undtagelser. Exit 0/1/2.
- **Referencen passerer** — `tests/compose/ok/reference.yml` er README-referencen med pladsholderne udfyldt, og `tests/compose/ok/varianter.yml` dækker de tilladte varianter (mapping-form med andet variabelnavn, `deploy.resources.limits.memory`, `restart: always`, navngivet volume i lang form, anonymt volume, `network_mode: "service:web"`). `tests/compose/deploy-example.yml` passerer uden ændringer; image-linjerne er ikke rørt.
- **Undtagelser** — `x-undtagelser` med `service`, `regel`, `begrundelse`, `godkendt-af`, `dato`. Gyldig undtagelse gør fejlene for regel+service til advarsler med godkender og dato i beskeden. Manglende `service`, `godkendt-af` eller `dato` (eller dato ikke `AAAA-MM-DD`), eller ukendt regelnavn, er en fejl, og undtagelsen dækker intet. Dato ældre end 365 dage: advarsel. Undtagelse der ikke rammer noget: advarsel (død). `tests/compose/undtagelse-gyldig.yml` (to undtagelser, den ene gammel) og `tests/compose/undtagelse-ugyldig.yml` (uden godkender, uden dato, ukendt regel, død).
- **Lokal kørsel uden GitHub og uden Docker** — `shutil.which('docker')` og `docker compose version` afgør om compose-tjekket kører; ellers `::warning` og videre. Samme for `git` (regel `env-fil`): uden git, eller uden for et repo, en advarsel. Efterprøvet lokalt med tom `PATH` og med en fil uden for et repo.
- **Deploy-jobbet** — `.github/workflows/deploy-update.yaml`: trinnet *Sanity-tjek compose-filen* er erstattet af *Lint compose-filen* med samme `if:`. Kører `scripts/compose_lint.py` fra `.workflow-repo` mod filen efter opdateringen; fejler lint, skrives `::error::` om at intet er committet og at filen skal rettes på `main`, og jobbet stopper før commit-trinnet. Ingen `stack.env` oprettes; kommentaren om Portainer og `stack.env` er væk. Alt andet urørt. `.gitignore`: kun kommentaren ved `stack.env` er ændret (fund fra task-0003).
- **Valideringen** — `.github/workflows/validate.yaml`: `compose-lint.yaml` i `WORKFLOWS` (job `compose-lint`, input `compose_path`, ingen outputs). Nyt trin *Afprøv scripts/compose_lint.py*: `tests/compose/ok/*.yml` og `deploy-example.yml` skal give exit 0 uden `::error` og uden `[compose]`-fund; `tests/compose/fejl/<regel>.yml` for hver af de 16 regler skal give exit 1 med `[<regel>]` og **ingen anden regel** (så eksemplerne er præcise, og en løsnet regel opdages); en regel uden eksempel eller et eksempel uden regel er en fejl; gyldig undtagelse exit 0 med `::warning` for begge regler og for alderen; ugyldig undtagelse exit 1 med `[undtagelse]`-fejl for hver mangel, de dækkede fejl stadig som `::error`, og den døde som `::warning`. Alle tre Python-blokke kørt lokalt mod den endelige tilstand: grønne. Negativ kontrol: uden `fejl/ports.yml` bliver trinnet rødt. `bash -n` på alle run-blokke i de tre workflows: ok.
- **Det genbrugelige workflow** — `.github/workflows/compose-lint.yaml`: input `compose_path` med standard, job `compose-lint`, `permissions: contents: read`, `timeout-minutes: 10`, ingen `concurrency`, ingen `secrets:`. Checkout af kalderen; checkout af dette repo i `.workflow-repo` med `repository`, `ref: ${{ github.job_workflow_sha }}`, `persist-credentials: false` og samme `actions/checkout`-SHA som `deploy-update.yaml`; pip install fra `requirements.txt`; kør scriptet.
- **README** — `README.md`: filtabellen (tre nye rækker, `validate.yaml` nævner selvtesten), intro (tre kald), caller-eksemplet har jobbet `lint` først, uden `if:`, med `permissions: contents: read` og kommentar om hvorfor der ikke er stifilter; nyt afsnit `### compose-lint.yaml` under *Inputs og outputs*; nyt afsnit *Regler for compose-filen* (fundformat, exit-koder, tabellen med de 16 regler, forrang hemmelighed/env-vaerdi og docker-sock/bind-mount, *Undtagelser*, *Lokal kørsel* i PowerShell-form), placeret lige før referencen; *Release* trin 3 (lint i stedet for sanity, ingen stack.env); *Efter en release* punkt 3 og oprydningsafsnittet (lint-fejl i deploy-jobbet); *Migrering* trin 1 (kør lint lokalt før PR'en); *Udgivelse af dette repo* (selvtesten, og at en strammere regel er et brud). `CLAUDE.md`: mappestrukturen har de nye filer, og `validate.yaml`/`tests/compose/`/`requirements.txt`-rækkerne er opdateret.

- **Fund 9, lagt ind i opgaven af architect** — `README.md`: indledningen til punkterne efter caller-eksemplet siger nu "Fire ting at vide om eksemplet", så antallet passer til de fire punkter.

Eksempelfilerne bruger kun generiske værdier (`example-app`, `postgres:16.4`, `redis:7.4-alpine`, `Navn Navnesen`).

### Hvad er ikke lavet, og hvorfor

- Kørslen mod de kendte kalderes compose-filer er menneskets punkt før `v1` flyttes; ikke mit. Scriptet kører mod en vilkårlig sti (`..\<app-repo>\deploy\docker-compose.yml`), så det kan gøres uden at kopiere noget.
- Ellers intet.

### Uklart

Valg jeg har truffet inden for opgavens ordlyd, som `architect` bør kende:

1. **Image pinnet på digest uden tag** (`image: org/app@sha256:…`) fejler `latest` ("image mangler tag"), selvom en digest er strammere end et tag. Jeg fulgte tabellen bogstaveligt. Skal digest-pinning være tilladt, er det én linje i `lint_service`.
2. **Undtagelse for `eksternt-netvaerk`**: reglen gælder et netværk, ikke en service, så `service` i undtagelsen matcher netværkets navn. Dokumenteret i README og docstring. Alternativet var at reglen ikke kan undtages.
3. **Committet `stack.env`/`.env`** (filniveau-delen af `env-fil`) kan ikke undtages — der er ingen service at knytte den til. Tjekket dækker hele repoet (`git ls-files` fra repoets rod, basename præcis `stack.env` eller `.env`; `.env.example` går igennem). Et app-repo med en `.env` committet til lokal udvikling i roden vil derfor fejle.
4. **`docker-sock` vinder over `bind-mount`** for samme volume (ét volume, én fejl) — samme princip som hemmelighed/env-vaerdi, men ikke nævnt i opgaven.
5. **`restart: false`** håndteres i scriptet (opgavens YAML 1.1-bemærkning), men `docker compose config` afviser selv værdien ("must be a string"), så varianten står ikke i `tests/compose/fejl/restart.yml` — den ville give et `[compose]`-fund oveni og gøre eksemplet upræcist.
6. **`tests/compose/fejl/env-fil.yml`** bruger `env_file` i lang form med `required: false`, fordi compose ellers fejler på den manglende `stack.env` før reglen får lov at tale. Reglen rammer `env_file` uanset form.
7. **Lint-jobbet i caller-eksemplet kører også ved tag-push** (uden `if:`, som opgaven siger). Det er en ekstra kørsel på sekunder; deploy-jobbet linter alligevel før commit. Kommentaren i eksemplet siger det.
8. **Sprog i scriptets beskeder**: ASCII-translitereret dansk ("laeses", "vaerdi") som i `update_compose_image.py`, og fundene på stderr som dér. README og workflows bruger æøå som hidtil.
9. **Fund uden for opgaven**: README-afsnittet "Tre ting at vide om eksemplet" har fire punkter (fra før task-0006). Ikke rettet.
