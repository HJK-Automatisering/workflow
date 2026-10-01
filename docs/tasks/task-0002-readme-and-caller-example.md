---
nummer: task-0002
titel: README med caller-eksempel, release- og rollback-vejledning
status: i-gang
kilde: interview
oprettet: 2026-10-01
---

# task-0002 — README med caller-eksempel, release- og rollback-vejledning

## Hvad og hvorfor
Repoet har ingen README. Med task-0001 får det to genbrugelige workflows, og projekterne skal kunne
tage dem i brug uden at læse YAML'en. Caller-skabelonen vedligeholdes i agenter-repoet af en anden
tråd, så README er stedet, det komplette eksempel og vejledningerne står. Baggrund i
`docs/prompt-workflow-gitops-v2.md`, fase 1, krav 8 og 9.

## Færdig når
- [ ] En udvikler kan ud fra README alene sætte et app-repo op til at bygge ved tag og udrulle ved release, uden at åbne workflow-filerne.
- [ ] README beskriver alle inputs og outputs for begge genbrugelige workflows med standardværdier.
- [ ] README beskriver, hvordan en release laves, hvordan den rulles tilbage, og at tilbagerulning ikke omfatter en kørt databasemigrering.
- [ ] README beskriver, at der ingen tilbagemelding er fra Portainer til GitHub, og hvad man derfor skal tjekke efter en release.
- [ ] README har et afsnit om, hvad der skal ændres, hvis `main` beskyttes, og fejlbeskeden fra task-0001 peger på det.
- [ ] README beskriver, hvordan dette repo udgives: nyt minor-tag og flyt af `v1` ved additive ændringer, `v2` ved brud, og at versionstags aldrig flyttes.
- [ ] README har en kort vejledning i at migrere en eksisterende app, der i dag deployes via Portainers web-editor.
- [ ] `CLAUDE.md` henviser til README for kommandoer og udgivelse i stedet for at gentage dem, og dens stak og mappestruktur svarer til det, der ligger i repoet efter task-0001.

## Sådan bygger vi det
`README.md` i roden, på dansk, samme tone som kommentarerne i workflow-filerne. Afsnit i denne rækkefølge:

1. **Hvad repoet er** og hvorfor workflows bor her (SHA-pinning ét sted).
2. **Caller-eksempel**, komplet og kopierbart:
   - `on.push.tags: ['v*.*.*']`, `on.pull_request`, `workflow_dispatch`. **Ikke** `on.push.branches`.
   - `concurrency` på workflow-niveau som i dag (`${{ github.workflow }}-${{ github.ref }}`, `cancel-in-progress: true`).
   - build-jobbet som i dag med `permissions: contents: read, packages: write, id-token: write`.
   - deploy-jobbet med `needs: build`, `if: startsWith(github.ref, 'refs/tags/v') && needs.build.outputs.digest != ''`,
     `permissions: contents: write, packages: read`, egen `concurrency`-gruppe `deploy-${{ github.repository }}` med
     `cancel-in-progress: false`, og `with:` der sender `image`, `digest`, `version` og `service` videre.
   - Bemærkning om, at GitHub kun holder én ventende kørsel i gruppen, så to hurtige releases kan springe den midterste over.
3. **Inputs og outputs** for `docker-publish.yaml` og `deploy-update.yaml`, som tabeller med standardværdi og beskrivelse.
4. **Release:** `git tag v1.2.3` og `git push origin v1.2.3`. Hvad der sker derefter, trin for trin, og hvor lang tid der typisk går, før Portainer poller.
5. **Tilbagerulning:** `git revert` af udrulnings-commit'en på `main`. Forbeholdet om databasemigreringer.
6. **Efter en release:** ingen tilbagemelding fra Portainer; tjek stacken i Portainer. Oprydning efter en rød kørsel.
7. **Migrering af en eksisterende app:** compose-fil i `deploy/`, `env_file: stack.env`, ingen værdier i filen, Git-stack i Portainer med variablerne, første release.
8. **Hvis `main` beskyttes:** bypass-aktør for GitHub Actions; alternativt App-token via `actions/create-github-app-token` (SHA-pinnet) og `secrets:` i workflow og kaldere; ved krav om signerede commits skift til GraphQL `createCommitOnBranch`.
9. **Udgivelse af dette repo** og vedligehold: minor-tag og flyt af `v1`; `v2` ved brud; versionstags flyttes aldrig; `cosign-release` bumpes manuelt, når Dependabot bumper `cosign-installer`; regexp'en for cosign-identitet skal rettes, hvis `docker-publish.yaml` omdøbes; repoet skal forblive offentligt, fordi kalderne checker scripts ud herfra.

Fund fra task-0001, der skal med:
- Signaturer fra cosign v3 ligger som OCI referrers med fallback-tag `sha256-<digest>` (uden `.sig`), og certifikatet
  står i bundle-blobben, ikke i manifestet. Skriv det i afsnittet om oprydning efter en rød kørsel: slettes et image i GHCR,
  skal signatur-artefaktet også væk, og det hedder ikke `.sig`.
- Vis den stramme verifikationsregel i README (identitet `^https://github\.com/HJK-Automatisering/workflow/\.github/workflows/docker-publish\.yaml@refs/tags/v`
  plus `--certificate-github-workflow-repository <repo>`), ikke den løse `^https://github\.com/ORG/`.
- Ret kommentaren i `.github/workflows/docker-publish.yaml` ved signeringstrinnet, så den viser samme stramme regel.
  Det er den eneste tilladte ændring i en workflow-fil i denne opgave, og den rører kun kommentarer.
- deploy-update logger fast ind på ghcr.io; nævn det ved inputtet `image`.

Kommandoer i PowerShell-venlig form: én pr. linje, ingen `&&`.
Ingen forretningsspecifikke værdier: ingen servernavne, ingen interne adresser. Portainer-serveren omtales som "den interne Docker-server".

`CLAUDE.md`: afsnittene *Kommandoer* og udgivelse forkortes til en henvisning til README. Desuden bringes *Stak* og
*Mappestruktur* ajour med task-0001: `deploy-update.yaml`, `scripts/update_compose_image.py`, `tests/compose/`,
`requirements.txt`, `.venv` (lokalt, ikke versionsstyret), outputtet `image`, og Dependabot-gruppen `python`. (Tilføjet 2026-10-01 efter fund fra developer.)

## Hvad vi ikke rører
- Ingen workflow-filer ud over kommentaren ved signeringstrinnet i `docker-publish.yaml` (se ovenfor). Dokumentationen beskriver det, task-0001 byggede; afviger den, er det en indvending, ikke en rettelse.
- Caller-skabelonen i agenter-repoet. README-eksemplet er forlægget, som den anden tråd kopierer fra.
- Ingen tags oprettes eller flyttes.

## Afhænger af
task-0001

## Beslutninger
- BESLUTTET (2026-10-01, efter bygning): Jobbet hedder `build` i README og dermed i den kommende skabelon; den eksisterende skabelons `publish` omdøbes af agenter-tråden, når den kopierer. Navnet siger, hvad jobbet gør, og projekterne opdateres alligevel for at få deploy-jobbet.
- BESLUTTET (2026-10-01, efter bygning): Portainers polling-interval omtales som produktstandard (5 min) med forbehold for stackens indstilling; `pull_request: branches: [main]` beholdes fra skabelonen; patch-tag ved rene rettelser nævnes, i tråd med kontraktens x.y.z-regler.
- BESLUTTET: README er det komplette caller-eksempel — skabelonen i agenter-repoet opdateres af en anden tråd ud fra README, så der kun er ét forlæg at holde ajour.
- BESLUTTET: Reserveløsninger ved beskyttet `main` dokumenteres, implementeres ikke — intet behov i dag; kode uden brug rådner.

## Åbne punkter

## Indvendinger

---

## Developers noter

### Hvad er lavet

Gren `task-0002-readme-and-caller-example` oprettet fra `main` (grenen manglede). Fem commits (`da16bb6`, `7bc6f22`, `65e3716`, `f5a55b6`, `d27e294`) plus noterne. Intet pushet, ingen tags. `d27e294` er anden runde, efter architects udvidelse af opgaven i `dd931fe`.

**Filer**

- `README.md` — ny. Afsnit i opgavens rækkefølge: Hvad repoet er (med filtabel og hvorfor repoet skal forblive offentligt), Caller-eksempel, Inputs og outputs (tabeller for begge workflows med standardværdier, rettigheder i kalderen, og den stramme verifikationsregel som kørbar PowerShell-blok), Release (trin for trin, Portainer-poll), Tilbagerulning (`git revert`, forbehold om databasemigrering, flyt aldrig tags), Efter en release (ingen tilbagemelding fra Portainer; tre tjek; oprydning efter rød kørsel inkl. cosign v3 referrers-format med tag `sha256-<digest>` uden `.sig`), Migrering af en eksisterende app (fire skridt), Hvis `main` beskyttes (a/b/c, fejlbeskeden fra deploy-update citeret), Udgivelse af dette repo og Vedligehold (minor-tag + flyt af `v1`; `v2` ved brud; versionstags flyttes aldrig; `cosign-release` bumpes manuelt i begge workflows; regexp følger filnavnet; repoet skal forblive offentligt), og referencen for compose-format med pladsholdere i stedet for app-specifikke navne.
- `.github/workflows/docker-publish.yaml` — kun kommentaren i signeringstrinnets `run:`-blok: viser nu den stramme regexp plus `--certificate-github-workflow-repository`, forklarer at SAN er dette workflows sti, og at regexp'en skal rettes hvis filen omdøbes. `git diff` viser 7+/4− linjer, alle kommentarer; `bash -n` på alle tre `run:`-blokke er ok.
- `CLAUDE.md` — *Kommandoer* er blevet *Kommandoer og udgivelse* med én henvisning til README; `README.md` tilføjet øverst i mappestrukturen (`f5a55b6`). Anden runde (`d27e294`): *Stak* nævner nu `scripts/` med `ruamel.yaml` pinnet i `requirements.txt`, at lokale Python-kald går gennem `.venv` (ikke versionsstyret), at cosign også verificerer før udrulning, og Dependabot-gruppen `python`. *Mappestruktur* har fået rækker for `deploy-update.yaml`, `scripts/update_compose_image.py`, `tests/compose/`, `requirements.txt` og `.venv/`; rækken for `docker-publish.yaml` nævner outputtet `image`, og rækkerne for `validate.yaml` og `dependabot.yml` siger at de også dækker scriptet og pip-pinnen. Alle stier i tabellen er tjekket mod repoet og findes. Designprincipper og Domænebegreber urørt.

**Færdig når — holdt op punkt for punkt**

| Punkt | Resultat |
|---|---|
| Sætte et app-repo op ud fra README alene | README har caller-filens sti og indhold, Dockerfile-kravet (`ARG APP_VERSION`, `ARG GIT_SHA`), compose-filens form, Portainer-stackens opsætning og første release. Ikke efterprøvet af en udvikler — kan kun afgøres ved brug |
| Alle inputs og outputs for begge workflows med standardværdier | Ja. Efterprøvet maskinelt: alle 7 inputs og 4 outputs for `docker-publish.yaml` og 5 inputs for `deploy-update.yaml` har en tabelrække, og hver standardværdi i tabellen matcher `default:` i workflow-filen |
| Release, tilbagerulning, og at tilbagerulning ikke omfatter en kørt migrering | Ja, afsnittene *Release* og *Tilbagerulning* |
| Ingen tilbagemelding fra Portainer, og hvad man tjekker | Ja, *Efter en release* |
| Afsnit om beskyttet `main`, som fejlbeskeden peger på | Ja, overskrift *Hvis `main` beskyttes*; fejlbeskeden fra `deploy-update.yaml` er citeret i afsnittet |
| Udgivelse af dette repo | Ja, *Udgivelse af dette repo* |
| Migrering af eksisterende app | Ja, fire skridt |
| `CLAUDE.md` henviser til README, og stak og mappestruktur svarer til repoet efter task-0001 | Ja. Henvisning i `f5a55b6`; stak og mappestruktur i `d27e294` |

**Efterprøvet** med `.venv\Scripts\python.exe` (ruamel.yaml) i et script i scratchpad, der parser caller-blokken ud af README og holder den op mod de faktiske workflow-filer:

- `on:` er præcis `push.tags: ['v*.*.*']`, `pull_request`, `workflow_dispatch`; ingen `on.push.branches`.
- `concurrency` på workflow-niveau er `${{ github.workflow }}-${{ github.ref }}` med `cancel-in-progress: true`; deploy-jobbets er `deploy-${{ github.repository }}` med `cancel-in-progress: false`.
- Begge `uses:` matcher `HJK-Automatisering/workflow/.github/workflows/<fil>@v1`, og filerne findes. Alle `uses:` i hele README (også prosa) matcher samme mønster.
- `build.permissions` = `contents: read, packages: write, id-token: write`; `deploy.permissions` = `contents: write, packages: read`; `deploy.needs: build`; `deploy.if` ordret som i opgaven.
- `deploy.with` sender `service`, `image`, `digest`, `version` — alle fire påkrævede inputs i `deploy-update.yaml`, ingen ukendte; `compose_path` vist som kommentar. De tre `needs.build.outputs.*` (`image`, `digest`, `version`) findes alle som outputs i `docker-publish.yaml`. De udkommenterede `with:`-nøgler under build er alle rigtige inputs.
- Den stramme regexp og `--certificate-github-workflow-repository` står i README, `docker-publish.yaml` og `deploy-update.yaml`; `github\.com/ORG/` findes ikke længere nogen steder.
- Ingen `&&` eller `;`-kæder i nogen PowerShell-blok i README.
- `##`-overskrifterne står i opgavens rækkefølge 1–9.

### Hvad er ikke lavet, og hvorfor

- `validate.yaml`s Python-blok er ikke kørt lokalt — den kræver pyyaml, som ikke er i `.venv` (og ikke skal være det). Ændringen i `docker-publish.yaml` er kun kommentarer inde i en `run:`-streng, så strukturen er uændret; efterprøvet med ruamel-parse og `bash -n` i stedet.
- Punkt 1 i *Færdig når* ("ud fra README alene") kan kun efterprøves af en udvikler, der faktisk gør det. Første lejlighed er testkørslen på BOARD.
- Udgivelse (`v1.1.0`, flyt af `v1`) er menneskets skridt og ikke rørt.

**Fund uden for opgaven (ikke rettet):**

1. ~~`CLAUDE.md`s mappestruktur er bagud efter task-0001~~ — architect lagde det ind i opgaven (`dd931fe`), og det er rettet i `d27e294`. Står her for sporbarhed.
2. Caller-skabelonen i agenter-repoet (`plugins/agents/skills/workflow/assets/docker-publish.yaml`) kalder jobbet `publish`, mens opgaven foreskriver `build` og `needs: build`. README følger opgaven. Den tråd, der opdaterer skabelonen ud fra README, skal omdøbe jobbet — det er ikke et fund i dette repo, men det bør siges videre.

### Uklart

intet.

De fire punkter fra første runde (jobnavn `build`, Portainers polling-interval som produktstandard med forbehold, `pull_request: branches: [main]`, omtalen af patch-tag) er afgjort af architect i `dd931fe` som BESLUTTET, alle i README's nuværende form. Ingen ændring i README.
