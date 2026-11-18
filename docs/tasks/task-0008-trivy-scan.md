---
nummer: task-0008
titel: Sårbarhedsscanning med trivy før push i docker-publish
status: planlagt
kilde: interview
oprettet: 2026-11-17
---

# task-0008 — Sårbarhedsscanning med trivy før push i docker-publish

## Hvad og hvorfor
`docker-publish.yaml` bygger, pusher og signerer i dag uden at se på hvad der
ligger i imaget. Et image med en kritisk sårbarhed, der allerede har en
rettelse, kan derfor blive udgivet og udrullet, uden at nogen ser det.

Opgaven lægger en trivy-scanning ind **før push**. Et image med en kritisk
sårbarhed med rettelse, eller med en hemmelighed i filerne, kommer aldrig i
registryet. Kritiske sårbarheder uden rettelse og høje med rettelse vises som
advarsler, men stopper ikke noget. Grænsen er den samme som scanneren på
Docker-værten (docker-monitor) bruger.

Grænsen er sat ud fra en scanning 2026-11-17 af tre kalderes nuværende images
med trivy 0.76.2. Navnene står ikke her, fordi repoet er offentligt og
app-repoerne er private:

| Image | Kritisk (med rettelse) | Høj (med rettelse) | Hemmeligheder |
|---|---|---|---|
| Kalder A | 0 (0) | 109 (6) | 0 |
| Kalder B | 2 (0) | 99 (0) | 0 |
| Kalder C | 2 (0) | 117 (7) | 0 |

Ingen af dem ville blive stoppet af grænsen. B og C får hver to advarsler
for kritisk uden rettelse. De fleste fund har ingen rettelse, så en grænse
der stoppede på dem, ville blokere alt, permanent.

## Færdig når
- [ ] `docker-publish.yaml` har et nyt valgfrit input `scan` (boolean, standard `true`) med en dansk beskrivelse. Øvrige inputs og outputs er uændrede.
- [ ] Med `scan: true` bygges og scannes imaget **før** "Build and push Docker image". Scanningen kører ved pull requests, push og tags, altså ved hver bygning.
- [ ] Kørslen fejler med `::error::` for hver **kritisk** sårbarhed **med rettelse**: pakke, installeret version, rettet version og CVE-nummer. Ingen push, ingen signering.
- [ ] Kørslen fejler med `::error::` for hver **hemmelighed** trivy finder i imagets filer: fil og regel, aldrig selve værdien.
- [ ] Hver **høj** sårbarhed **med rettelse** giver en `::warning::` med samme oplysninger og stopper ikke kørslen.
- [ ] Hver **kritisk** sårbarhed **uden rettelse** giver en `::warning::` med pakke, installeret version og CVE-nummer og stopper ikke kørslen.
- [ ] **Høj og lavere uden rettelse** giver hverken fejl eller advarsel. Antallet pr. alvorlighed står i kørslens opsummering (`$GITHUB_STEP_SUMMARY`).
- [ ] "Med rettelse" betyder at trivy melder `Status` `fixed`, som i docker-monitor.
- [ ] Opsummeringen har en tabel med antal pr. alvorlighed, med og uden rettelse, så den kan læses uden at åbne loggen.
- [ ] Findes `.trivyignore` i roden af det kaldende repo, bruges den. README viser formen med begrundelse og `exp:`-dato.
- [ ] trivy køres som containeren `aquasec/trivy`, pinnet til version **og** digest (`aquasec/trivy:0.76.2@sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb`). Ingen trivy-action.
- [ ] trivy-containeren får **ikke** Docker-socketen. Imaget gives til den som en tar-fil (`trivy image --input`).
- [ ] Sårbarhedsdatabasen caches mellem kørsler, så den ikke hentes ved hver bygning.
- [ ] Kan databasen ikke hentes, fejler kørslen med en dansk `::error::`, der siger at scanningen ikke kunne køre, og at `scan: false` er vejen uden om. Den består ikke i tavshed.
- [ ] Med `scan: false` springes scanningen over, og jobbet opfører sig som i dag.
- [ ] `validate.yaml` fejler, hvis trivy-referencen i `docker-publish.yaml` ikke er pinnet med `@sha256:`.
- [ ] README: inputtet `scan` i input-tabellen og et afsnit om scanningen. Afsnittet beskriver grænsen, hvad der er fejl og advarsel, `.trivyignore` og at trivy-pinnen bumpes i hånden.
- [ ] `CLAUDE.md`, afsnittet *Stak*: trivy-containeren og dens version, og at Dependabot ikke kan se pinnen, så den bumpes i hånden.
- [ ] Efterprøvet lokalt med Docker mod to images: ét med en kritisk sårbarhed med rettelse (fx `mcuadros/ofelia:0.3.22`), som skal fejle, og ét uden (fx `mcuadros/ofelia:0.3.23`), som skal bestå med advarsler. Resultatet står i noterne.

## Sådan bygger vi det
- Nyt trin efter "Tjek at versionstagget er ledigt": byg `linux/amd64` med
  `docker/build-push-action` (samme pin som i dag), `push: false` og
  `outputs: type=docker,dest=<tar>`, med samme `context`, `file`,
  `build-args` og gha-cache som det rigtige build. Det rigtige build
  bagefter er uændret og henter lagene fra cachen.
- Scan tar-filen med trivy-containeren:
  `trivy image --input <tar> --scanners vuln,secret --format json --output <json>`.
  Brug `--ignorefile .trivyignore`, når filen findes i kalderens checkout.
- Afgør udfaldet i et Python-trin der læser JSON'en (kun standardbiblioteket):
  fejl, advarsler og opsummering. Det holder politikken ét sted og samme sted
  som resten af repoets logik, frem for i trivys flag.
- Databasen: `actions/cache` på trivys cache-mappe med en nøgle der skifter
  pr. dag, monteret ind i containeren. `actions/cache` er GitHubs egen action
  som `actions/checkout`, pinnet til SHA.
- `scan` følger mønstret fra `sign`: `if: ${{ inputs.scan }}` på de nye trin.
- `Rapportér efterladt image` er uændret. Scanningen ligger før push, så en
  fejlet scanning efterlader intet i registryet.

## Hvad vi ikke rører
- Det rigtige build, signering, tags og outputs.
- `deploy-update.yaml` og `compose-lint.yaml`.
- Caller-skabelonen og dens dokument i agenter-repoet. De skal nævne
  scanningen og `scan`, men det er en ændring i det repo.
- Fremmede images i kaldernes compose-filer. De bygges ikke her, og en
  scanning ved bygning kan ikke se dem. Dem ser docker-monitor.

## Afhænger af
intet

## Beslutninger
- BESLUTTET: Scanningen ligger **før push**. Afvist: scanning efter push og før
  signering. Den efterlader et usigneret image med versionstag i registryet,
  og med `protect_release_tags` kræver det et nyt versionsnummer.
- BESLUTTET: Grænsen er **fejl på kritisk med rettelse og på hemmeligheder,
  advarsel på kritisk uden rettelse og på høj med rettelse**. Høj og lavere
  uden rettelse tælles kun. Afvist: fejl på høj med rettelse, som ville
  stoppe to af kalderne ved næste udgivelse.
- BESLUTTET (2026-11-18): Kritisk uden rettelse advarer, som i docker-monitor.
  Erstatter "ingen fejl eller advarsel for fund uden rettelse". Afvist: at
  kritisk uden rettelse kræver en undtagelse, som stod i docker-monitors log
  2026-11-17. Det byggede i docker-monitor advarer, og mennesket bekræftede
  det 2026-11-18.
- BESLUTTET: Kun `linux/amd64` scannes. Runneren er fastlåst til amd64, alle
  kendte kaldere bygger kun til amd64, og et multi-platform-build kan ikke
  lægges lokalt.
- BESLUTTET: trivy køres som container pinnet til digest, ikke som action.
  Repoet tillader kun actions fra Docker og sigstore.
- BESLUTTET: trivy-containeren får aldrig Docker-socketen. Socketen giver
  kontrol over værten; en tar-fil giver kun imaget.
- BESLUTTET: `scan` er et nyt input med standard `true`. Kontrakten udvides
  additivt, og inputtet er vejen uden om, hvis databasen ikke kan hentes.

## Åbne punkter

## Indvendinger

---

## Developers noter

<Alt over denne overskrift ejes af architect. Alt herunder skrives kun af
developer, som aldrig retter i definitionen ovenfor.>

### Hvad er lavet
- `docker-publish.yaml`: nyt input `scan` (boolean, standard `true`) og
  `jobs.build.env.TRIVY_IMAGE` pinnet til
  `aquasec/trivy:0.76.2@sha256:8f6bb947…768fb`. Fire nye trin mellem
  "Tjek at versionstagget er ledigt" og "Build and push", alle med
  `if: ${{ inputs.scan }}`:
  - "Forbered scanning": opretter `$RUNNER_TEMP/trivy` og
    `$RUNNER_TEMP/trivy-cache`, giver dagens dato som cache-nøgle.
  - "Hent trivys database fra cachen": `actions/cache@55cc834… # v6.1.0`,
    nøgle `trivy-db-<os>-<dato>`, `restore-keys` på præfikset.
  - "Byg til scanning": `docker/build-push-action` (samme pin), `push: false`,
    `platforms: linux/amd64`, `outputs: type=docker,dest=…/image.tar`, samme
    `context`, `file`, `build-args` og gha-cache som det rigtige build.
  - "Scan imaget med trivy": `docker run` med runnerens uid/gid, `HOME=/tmp`,
    kun cache-mappen og arbejdsmappen monteret, ingen Docker-socket.
    `--input`, `--scanners vuln,secret`, JSON. `.trivyignore` fra kalderens
    rod bruges, hvis den findes. Fejler trivy, kommer en dansk `::error::`
    med henvisning til `scan: false`.
  - "Afgør scanningen": Python (kun standardbiblioteket) læser JSON'en.
    Kritisk med rettelse og hemmeligheder → `::error::`, høj med rettelse →
    `::warning::`, tabel i `$GITHUB_STEP_SUMMARY`, exit 1 ved fejl.
    Hemmeligheder skrives med fil, linje, titel og regel, aldrig `Match`
    eller `Code`.
- `validate.yaml`: `scan` i docker-publish's kontrakt-inputs, og et nyt tjek
  `pinnede_images` der kræver `<image>:<version>@sha256:<64 hex>` for
  `jobs.build.env.TRIVY_IMAGE`.
- `README.md`: rækken `scan` i input-tabellen, afsnittet *Sårbarhedsscanning*
  med tabel over udfald, `.trivyignore` med `exp:` og vejen uden om, og et
  punkt under *Vedligehold* om at bumpe trivy-pinnen i hånden.
- `CLAUDE.md`, *Stak*: trivy-containeren, pinnen og at den bumpes i hånden.

Efterprøvet lokalt (Windows, Docker Desktop):
- Strukturvalideringen fra `validate.yaml` kørt mod de tre workflows: ok.
  Negativ prøve med digesten fjernet fra `TRIVY_IMAGE`: fejler med den nye
  besked.
- De tre `run:`-blokke trukket ud af `docker-publish.yaml` med pyyaml og kørt
  med `RUNNER_TEMP`, `GITHUB_OUTPUT` og `GITHUB_STEP_SUMMARY` sat. Imaget lagt
  som tar med `docker save` i stedet for buildx-eksporten:
  - `mcuadros/ofelia:0.3.22`: exit 1, 2 `::error::` (CVE-2026-31789 i
    libcrypto3 og libssl3), 39 `::warning::`, tabellen i opsummeringen.
  - `mcuadros/ofelia:0.3.23`: exit 0, 0 fejl, 2 advarsler.
  - `mcuadros/ofelia:0.3.22` med `.trivyignore` der undtager CVE-2026-31789
    med `exp:2027-01-01`: exit 0, 39 advarsler. Scan-trinnet skrev "Bruger
    .trivyignore fra repoets rod."
  - Databasen hentet ved første kørsel og givet videre som cache til de
    næste, som actions/cache ville gøre.

Rettet 2026-11-18 efter den nye beslutning om kritisk uden rettelse:
- "Afgør scanningen" afgør "med rettelse" ud fra `Status == "fixed"` som
  docker-monitor, og kritisk uden rettelse giver `::warning::` med en
  henvisning til `.trivyignore`. Kommentaren over trinnet, `scan`-inputtets
  beskrivelse, opsummeringens tekst og README-tabellen følger med.
- `Status == "fixed"` og en udfyldt `FixedVersion` faldt sammen i alle fund i
  fem scanninger fra 2026-11-17, så skiftet ændrer ingen optælling.
- Afgørelsen kørt igen på de gemte scanninger: `ofelia:0.3.22` exit 1 med 2
  fejl; `ofelia:0.3.23` exit 0 med 2 advarsler; med `.trivyignore` exit 0. De
  to kalder-images med 2 kritiske uden rettelse: exit 0 med 2 og 9
  advarsler, heraf 2 for kritisk uden rettelse hver. Kalderen uden kritiske:
  exit 0 med 6 advarsler.

### Hvad er ikke lavet, og hvorfor
- Ikke kørt i GitHub Actions. Ikke efterprøvet: buildx' `type=docker`-eksport
  til tar (lokalt brugt `docker save`, samme format), `actions/cache` på
  runneren, og at det rigtige build bagefter rammer cachen.
- Fejlvejen når databasen ikke kan hentes, er ikke fremprovokeret.
- Hemmelighedsfund er ikke efterprøvet med et image der indeholder en.

### Uklart
- Lokalt viste Windows-konsollen æ, ø og å forkert i `::error::`-linjerne,
  fordi Python skrev med konsollens tegnsæt. På runneren er tegnsættet UTF-8;
  hvis annotationerne alligevel viser forkerte tegn, sættes
  `PYTHONIOENCODING=utf-8` på trinnet.
