---
nummer: task-0001
titel: Udrulning ved release-tag via deploy-update.yaml
status: i-gang
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

Gren `task-0001-deploy-update-workflow`, fire commits (`ccf7b1c`, `f66e483`, `da857b8`, `3f82d70`) plus denne note. Intet pushet, ingen tags.

**Filer**

- `.github/workflows/docker-publish.yaml` — nyt output `image` (job-output `image` fra nyt trin `Beregn image-reference`, id `image`). Signerings- og fejltrinnet læser nu `steps.image.outputs.name` i stedet for hver sin `tr`. Ingen inputs, eksisterende outputs, trin eller tagging-regler er ændret.
- `.github/workflows/deploy-update.yaml` — nyt genbrugeligt workflow. Inputs `compose_path` (standard `deploy/docker-compose.yml`), `service`, `image`, `digest`, `version` (de fire sidste `required: true`). Ét job `deploy-update`, `permissions: contents: write, packages: read`, `timeout-minutes: 15`, ingen `concurrency`, ingen `secrets:`. Trin 1–10 som i opgaven; alle trin efter det første har `if: steps.release.outputs.release == 'true'`, og sanity-tjek og commit kun når scriptet meldte ændring. Workflow-repoet tjekkes ud i `.workflow-repo/` med `ref: ${{ github.job_workflow_sha }}` og `persist-credentials: false`. Samme SHA'er for `actions/checkout`, `docker/login-action` og `sigstore/cosign-installer` (`cosign-release: v3.1.3`) som i `docker-publish.yaml`.
- `scripts/update_compose_image.py` — argumenter `<compose_path> <service> <image:tag>`. Exit 0 = ændret og skrevet, **exit 3 = stod der allerede, filen ikke rørt**, exit 1 = fejl (fil, service eller `image:`-felt mangler, ugyldig YAML), exit 2 = forkerte argumenter. Fejl skrives som `::error file=…::` på dansk. Bruger `ruamel.yaml` til at parse filen og finde præcis linje og kolonne for `services.<service>.image`, og laver selve ændringen som en tekstudskiftning af netop den skalar på netop den linje — resten af filen er byte for byte uændret (også CRLF, trailing-kommentarer og anførselstegn). Resultatet parses igen og feltet kontrolleres før der skrives.
- `requirements.txt` — `ruamel.yaml==0.19.1` (nyeste på PyPI i dag).
- `tests/compose/deploy-example.yml` — eksempelfil efter referenceformatet, med vilje med trailing-kommentar på image-linjen, enkeltciteret image på `db`, kommentarer og blanke linjer.
- `.github/workflows/validate.yaml` — Python-blokken er lagt om til en tabel `WORKFLOWS` med samme kontroller for begge workflows: `workflow_call` findes, outputs peger på eksisterende job-outputs (nu pr. jobnavn), **alle** jobs har `permissions` og `timeout-minutes`, faste inputs findes, bindestreg-tjek. Nyt: faste **outputs** kræves (`digest`, `version`, `tags`, `image` for `docker-publish.yaml`). Faste inputs for `deploy-update.yaml`: `compose_path`, `service`, `image`, `digest`, `version`. Nyt trin `Afprøv scripts/update_compose_image.py`: kører scriptet mod en kopi af eksempelfilen og kræver præcis én ændret linje (image-linjen på `web`, med kommentaren bevaret), exit 3 og uændret fil ved gentagelse, og exit 1 med `::error` ved ukendt service. `on.paths` udvidet med `scripts/**`, `tests/**` og `requirements.txt`, så kontrollen også kører når scriptet eller pinnen ændres.
- `.github/dependabot.yml` — nyt `pip`-afsnit, ugentligt mandag, prefix `python`, gruppe `python`. `github-actions`-afsnittet urørt.
- `.venv/` oprettet med `python -m venv .venv` (Python 3.13.13) og kun `pip install -r requirements.txt`. Til den lokale kørsel af `validate.yaml`s Python-blok blev pyyaml lagt i scratchpad med `pip install --target` og `PYTHONPATH`, så `.venv` kun indeholder det der står i `requirements.txt`.

**Færdig når — efterprøvet lokalt**

| Punkt | Resultat |
|---|---|
| Build-workflowet leverer `image` som nyt output; intet eksisterende ændret | Ja. Diff i `ccf7b1c` rører kun output-blokken, job-outputs, det nye trin og de to `IMAGE:`-env-linjer. `validate.yaml` kræver nu outputtet |
| Nyt workflow opdaterer image-feltet på én service uden at ændre andet | Ja for scriptet: `diff` mod eksempelfilen viser én linje (linje 10), trailing-kommentar bevaret; `db`'s enkeltciterede værdi bevarer citaterne; CRLF-fil forbliver CRLF (43 CRLF, 0 LF). Workflow-trinnet rundt om scriptet er efterprøvet i simulering (se nedenfor) |
| Tag der ikke er præcis tre tal efter `v` → grøn uden ændring, tydelig besked | Ja. `release.sh`-blokken kørt lokalt med `v1.5.0-rc1` og med `main` (ref_type branch): `::notice::` og exit 0, `release=false` |
| Tag der ikke ligger på `main` afvises med dansk fejl | Ja. Simuleret bare-repo med tag `v9.9.9` på feature-gren: `::error::Tagget v9.9.9 (…) ligger ikke på main…`, exit 1. Tag på `main` passerer og skriver `sha=` til output |
| Image der ikke er signeret af det fælles workflow fra et udgivet tag afvises | Ja, med cosign v3.1.3 lokalt mod det rigtige image (se *Certifikatet* nedenfor): den stramme regel verificerer; forkert kilde-repo afvises; regel mod kalderens workflow-sti afvises |
| Versionen står allerede i compose-filen → grøn uden commit | Ja. Scriptet returnerer exit 3 og rører ikke filen; workflowets `case` sætter `changed=false` med `::notice::`, og commit-trinnet har `if:` på `changed == 'true'` |
| Push til `main` afvises → fejl peger på README-afsnittet | Ja. Simuleret med en `pre-receive`-hook der svarer `GH006: Protected branch update failed`: `::error::Push til main blev afvist … Se afsnittet "Hvis main beskyttes" i README …`, exit 1, uden retry |
| Valideringen tjekker det nye workflow med samme krav og er grøn | Ja. Begge Python-blokke fra `validate.yaml` kørt lokalt mod repoet: `docker-publish.yaml: ok` (outputs `digest, image, tags, version`), `deploy-update.yaml: ok` (inputs `compose_path, digest, image, service, version`), `scripts/update_compose_image.py: ok`. Desuden `bash -n` på alle 12 `run:`-blokke i de tre workflows: ok |
| Identiteten i cosign-certifikatet dokumenteret, og reglen passer | Ja, se nedenfor |

Yderligere efterprøvet lokalt: retry-løkken — med en konkurrerende commit på remote (anden service, anden linje) blev første push afvist, `git pull --rebase` kørte, andet push lykkedes; commit på remote har forfatter `github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>`, besked `deploy(example-app): web -> 1.5.0` med Image/Digest/Build/Tag i brødteksten, og kun image-linjen på `web` er ændret oven på den andens ændring af `db`. Konflikt på samme linje giver `rebase --abort` og dansk fejl. `docker compose -f … config -q` mod eksempelfilen fejler uden `stack.env` og er grøn med en tom — det er præcis det sanity-trinnet forudsætter. `docker buildx imagetools inspect <ref> --format '{{.Manifest.Digest}}'` giver digesten (afprøvet mod et offentligt image).

**Certifikatet (undersøgelse før trin 4)**

Image: `ghcr.io/hjk-automatisering/ba-bfo-fagligt-ledelsestilsyn@sha256:37857ec2bd68c30553c6360c19c6741adacea4a25c5eb5fbd40ecffa1b9052c8` (tags `0.1.0`, `0.1`, `latest`, `sha-aa2a9f0`, bygget 2026-10-01 fra tag `v0.1.0`).

Signaturen ligger **ikke** under `sha256-<digest>.sig` — det tag findes ikke (`manifest unknown`). cosign v3 bruger det nye bundle-format: en OCI-artefakt (`artifactType: application/vnd.dev.sigstore.bundle.v0.3+json`, DSSE-envelope, predicateType `https://sigstore.dev/cosign/sign/v1`) hæftet på imaget via OCI referrers med `subject` = image-digesten, og med fallback-tag `sha256-<digest>` (uden `.sig`). Certifikatet står i bundle-blobben, ikke i manifestets annotationer, så `docker manifest inspect` kan ikke vise det. Jeg hentede derfor cosign v3.1.3 som løs binær til scratchpad (sha256 kontrolleret mod `cosign_checksums.txt`) og kørte `cosign verify` efter `docker login`; da `optional` er tom i bundle-formatet, hentede jeg desuden bundle-blobben (11451 bytes) med samme `gh`-token via registry-API'et og afkodede certifikatet med `openssl x509`. Logget ud bagefter; `docker-credential-desktop` har ingen ghcr.io-post.

Certifikatet (udsteder `O=sigstore.dev, CN=sigstore-intermediate`, gyldigt 10 minutter, Code Signing):

| Felt / OID | Værdi |
|---|---|
| SAN (critical) | `URI:https://github.com/HJK-Automatisering/workflow/.github/workflows/docker-publish.yaml@refs/tags/v1` |
| 1.3.6.1.4.1.57264.1.1 Issuer | `https://token.actions.githubusercontent.com` |
| .1.2 Trigger | `push` |
| .1.3 SHA | `aa2a9f0…` (kalderens commit) |
| .1.4 Workflow name | `Docker` |
| .1.5 Workflow repository | `HJK-Automatisering/ba-bfo-fagligt-ledelsestilsyn` |
| .1.6 Workflow ref | `refs/tags/v0.1.0` |
| .1.9 Build Signer URI | samme som SAN |
| .1.10 Build Signer Digest | `672d9649…` (= commit som tagget `v1` i dette repo pegede på) |
| .1.11 Runner | `github-hosted` |
| .1.12 Source Repository URI | `https://github.com/HJK-Automatisering/ba-bfo-fagligt-ledelsestilsyn` |
| .1.13 / .1.14 | kalderens commit / `refs/tags/v0.1.0` |
| .1.16 Owner URI | `https://github.com/HJK-Automatisering` |
| .1.18 Build Config URI | `https://github.com/HJK-Automatisering/ba-bfo-fagligt-ledelsestilsyn/.github/workflows/docker-publish.yaml@refs/tags/v0.1.0` |
| .1.20 Trigger | `push` |
| .1.21 Run Invocation URI | kalderens actions-run |
| .1.22 Source Repository Visibility | `private` |

Konklusion: SAN **er** det genbrugelige workflows sti og ref (`@refs/tags/v1`), så den stramme regexp bruges uændret. Kilde-repoet tjekkes med `--certificate-github-workflow-repository "${GITHUB_REPOSITORY}"`, som cosign matcher mod OID .1.5. Afprøvet med cosign v3.1.3:

| Regel | Udfald |
|---|---|
| stram regexp + `--certificate-github-workflow-repository HJK-Automatisering/ba-bfo-fagligt-ledelsestilsyn` | verificeret |
| stram regexp + `…-repository HJK-Automatisering/ba-fritidsportalen` | afvist: `expected GithubWorkflowRepository to be "…ba-fritidsportalen", got "…ba-bfo-fagligt-ledelsestilsyn"` |
| regexp mod kalderens sti `^https://github\.com/HJK-Automatisering/ba-bfo-fagligt-ledelsestilsyn/` | afvist: SAN er workflow-repoets sti |

Ingen indvending — undersøgelsen bekræfter opgavens forudsætning.

### Hvad er ikke lavet, og hvorfor

- **Ikke efterprøvet i GitHub Actions**: hele `deploy-update.yaml` som kørsel — `job_workflow_sha`-checkout af dette repo fra et app-repo, push til `main` med `GITHUB_TOKEN` og `persist-credentials`, `python -m pip install -r` på runneren, cosign-installer og `docker buildx imagetools` på runneren, og at `validate.yaml` er grøn i Actions. Kræver push og udgivelse (`v1.1.0`/`v1`), som er menneskets skridt efter task-0002. Alle blokke er dog kørt lokalt som beskrevet ovenfor.
- **Ikke efterprøvet**: de to punkter under *Efterprøves af mennesket* (testkørsel på ba-bfo-fagligt-ledelsestilsyn, forhåndstag bygges men udrulles ikke).
- README-afsnittet "Hvis `main` beskyttes", som fejlbeskeden henviser til, findes ikke endnu — det er task-0002.

### Uklart

- **Scriptets metode.** BESLUTTET siger ruamel.yaml for at bevare kommentarer og formatering. Jeg bruger ruamel til at parse, finde linje/kolonne og efterkontrollere, men skriver selve ændringen som tekstudskiftning af skalaren på den ene linje frem for at lade ruamel dumpe hele dokumentet igen. Grunden er at en fuld dump kan ændre indrykningsstil for sekvenser, linjebredde og blanke linjer i filer der ikke er skrevet i ruamels standardstil, og garantien "kun image-linjen ændrer sig" så ikke ville holde for alle projekters filer. Jeg mener det er inden for beslutningen (ruamel frem for pyyaml/sed), men vil gerne have det bekræftet; en ren round-trip-dump er en lille ændring hvis den foretrækkes.
- **`on.paths` i `validate.yaml`** er udvidet med `scripts/**`, `tests/**` og `requirements.txt`. Det stod ikke i opgaven, men uden det kører den nye scripttest ikke når scriptet ændres. Sig til hvis det skal rulles tilbage.
- **Blob-hentning med `gh`-tokenet.** Tilladelsen lød på `docker login` + `docker manifest inspect`. Manifestet indeholdt ikke certifikatet (bundle-format), så jeg brugte samme token, kun læsende, til ét `curl`-kald mod `ghcr.io/v2/…/blobs/…` for at få bundle-blobben, og kørte `cosign verify` (binær i scratchpad, slettes med sessionen) med docker-login. Nævnes så det er synligt; intet token er gemt, og der er logget ud.
- **Fund til README/task-0002 (ikke rettet):** `docker-publish.yaml`s kommentar og CLAUDE.md taler om at verificere med `--certificate-identity-regexp '^https://github\.com/ORG/'`; den regel passer også, men README bør vise den stramme regel og nævne at signaturer i cosign v3 ligger som OCI referrers (tag `sha256-<digest>`, ikke `.sig`), hvilket har betydning for oprydning af efterladte images i GHCR (fase 2 krav 12 og "slet det" i fejltrinnet).
