---
nummer: task-0005
titel: compose-lint: regler for compose-filer i pull requests og før udrulning
status: planlagt
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
- [ ] En compose-fil, der bryder en regel, giver en dansk fejl med service, regelnavn og linjenummer, både ved lokal kørsel, i en pull request og i deploy-jobbet.
- [ ] En fil efter referencen i README passerer uden fejl.
- [ ] En gyldig undtagelse gør fejlen til en advarsel; en undtagelse uden godkender og dato, eller med ukendt regelnavn, er selv en fejl; en undtagelse ældre end et år giver en advarsel.
- [ ] Scriptet kan køres lokalt mod en fil uden GitHub-kontekst og uden Docker; mangler Docker, springes compose-tjekket over med en advarsel.
- [ ] Deploy-jobbet kører lint i stedet for sanity-tjekket, committer ikke hvis lint fejler, og opretter ikke længere en midlertidig `stack.env`.
- [ ] Valideringen i dette repo tjekker det nye workflow med samme strukturkrav, kører scriptet mod mindst ét dårligt eksempel pr. regel, et godt eksempel, en gyldig og en ugyldig undtagelse, og er grøn.
- [ ] README dokumenterer alle regler, undtagelsesformatet og lokal kørsel, og caller-eksemplet har lint-jobbet.

Efterprøves af mennesket før `v1` flyttes:

- [ ] Scriptet er kørt lokalt mod compose-filerne i de kendte kaldere, og ingen app får en rød release af regler, den aldrig har set.

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
task-0003, task-0004

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

### Hvad er lavet
### Hvad er ikke lavet, og hvorfor
### Uklart
