# Opgave: GitOps-udrulning via Portainer – udvid HJK-Automatisering/workflow

## Kontekst

Vi driver Portainer Business Edition 2.45.1 på én intern Docker standalone-server. Serveren er produktion, ligger på et internt net og kan ikke nås fra GitHub. Det er bevidst og skal forblive sådan.

Fremover udrulles alle løsninger som **Git-baserede stacks** i Portainer. Portainer følger grenen `main` i hvert app-repo, læser `deploy/docker-compose.yml` og udruller, når filen ændres. Det betyder:

- Images bygges fortsat af `docker-publish.yaml` og pushes til GHCR. Portainer bygger aldrig images.
- Intet workflow må kalde Portainer: ingen webhooks, ingen API-kald, ingen netværksadgang til serveren.
- Det nye ansvar er at skrive den nye image-reference ind i `deploy/docker-compose.yml` på `main`, når der laves en release. Den commit er det, der udløser udrulningen af et nyt image.
- Miljøvariabler og hemmeligheder leveres udelukkende via `stack.env`, som Portainer genererer ud fra variablerne på stacken. Compose-filen henviser til den med `env_file`. Der står aldrig værdier i compose-filen, og `stack.env` committes aldrig.

Udviklerne bruger AI-agenter, der følger en fælles deploy-kontrakt for compose-filer. Valideringsreglerne i fase 2 er de samme regler og regelnavne, som agenterne er instrueret i.

**Trusselsmodel, kort:** Alt nedenfor beskytter mod fejl, ikke mod en udvikler med skriveadgang og vilje. Den, der kan pushe til `main` i et app-repo, kan ændre compose-filen og dermed det, der kører på serveren. Det accepterer vi. Værnene skal fange forkerte tags, usignerede images, glemte felter og hemmeligheder i klartekst.

## Besluttet

| Emne | Beslutning |
|---|---|
| Placering | `deploy/docker-compose.yml` i hvert app-repo |
| Hvornår der bygges | **Kun ved tag-push.** Som i dag bygger caller-skabelonen ikke på push til `main`. Det fastholdes; derfor kan deploy-commit'en aldrig udløse en ny bygning, og der er ingen løkke at værne imod |
| Hvornår et nyt image går i drift | Kun ved release-tag på formen `vX.Y.Z` (præcis tre tal; fx `v1.2.3-rc1` bygges, men udrulles ikke) |
| Godkendelse | Ingen; workflowet committer direkte til `main` |
| Gren, Portainer følger | `main`. Strukturelle ændringer i compose-filen går derfor i drift ved merge; kun image-opdateringer venter på release |
| Image-reference | `ghcr.io/hjk-automatisering/<app>:<version>` (versionstags må aldrig overskrives, se fase 2, krav 12) |
| Tilbagerulning | `git revert` af udrulnings-commit'en på `main`. Bemærk i README, at det ruller imaget tilbage, ikke en kørt databasemigrering |
| Token | Kun `GITHUB_TOKEN`. Ingen nye secrets, ingen GitHub App. Se krav 5 |
| Udgivelse af dette repo | Additive ændringer udgives som `v1.1.0`, og `v1` flyttes med. Agenten tagger ikke selv |
| Opdeling | **Fase 1** leverer udrulningen. **Fase 2** leverer compose-lint og tag-beskyttelse. Fase 1 skal være testet på en ufarlig app, før fase 2 påbegyndes |

## Det eksisterende, som skal respekteres

Repoet er offentligt og indeholder i dag `docker-publish.yaml` (genbrugeligt build-workflow), `validate.yaml` (validerer det genbrugelige workflow med Python og uden tredjeparts-actions) og `dependabot.yml` (bumper SHA-pinnede actions ugentligt). Der findes **ingen README og ingen `.gitignore`**. Udgivelser er tagget `v1.0.0`, `v1.0.1`, `v1.0.2`, og det flyttende tag `v1` peger på den seneste.

Caller-skabelonen ligger i agenter-repoet (`plugins/agents/skills/workflow/assets/docker-publish.yaml`) og kalder `docker-publish.yaml@v1`. Den trigger på `push.tags: ['v*.*.*']`, `pull_request` og `workflow_dispatch`, med `concurrency` på `${{ github.workflow }}-${{ github.ref }}` og `cancel-in-progress: true`. Kendte kaldere: ba-nsp-data, ba-fritidsportalen, ba-xflow-sql-tool og ba-bfo-fagligt-ledelsestilsyn, alle private.

`docker-publish.yaml` leverer allerede det nødvendige: outputs `digest`, `version` og `tags`, semver-tags ved tag-push og keyless cosign-signering. Outputbeskrivelsen siger selv, at deploy skal bruge digest og ikke et tag, og at deploy-jobbet skal have et `if:` på digest. Den tanke skal udbygges, ikke erstattes.

Følg samme designprincipper som resten af repoet: actions pinnet til commit-SHA med versionskommentar, så Dependabot kan bumpe dem; så få tredjepartsafhængigheder som muligt (hellere Python i et `run`-trin end endnu en action); inputnavne med `_`; kommentarer på dansk, der forklarer hvorfor; `permissions` og `timeout-minutes` på hvert job; `concurrency` i caller-workflowet, ikke i de genbrugelige.

**Grenbeskyttelse er undersøgt:** Der er hverken rulesets eller branch protection på `main` i workflow-repoet, ba-fritidsportalen, ba-bfo-fagligt-ledelsestilsyn og agents. SAEH-Punchly kræver ét review. Org-rulesets kunne ikke læses uden `admin:org`; se krav 1.

---

# Fase 1: Udrulning

**1. Analyse før ændring.** Bekræft ovenstående beskrivelse af repoet. Tjek org-rulesets i HJK-Automatisering (kræver `admin:org`; bed om det, eller bed mig bekræfte, at der ingen er). Læs certifikatet fra et eksisterende signeret image, fx ba-fritidsportalen, med `cosign verify ... | jq`, og dokumentér hvilken identitet (SAN) og hvilke extensions certifikatet faktisk indeholder, når der signeres fra et genbrugeligt workflow. Præsenter derefter en plan for filer, inputs, outputs og jobstruktur. **Vent på min godkendelse, før du ændrer noget.**

**2. `.gitignore` først.** Opret `.gitignore` med `stack.env`, `.env`, `__pycache__/` og `.venv/`, før der oprettes andre filer.

**3. Additiv kontrakt for `docker-publish.yaml`.** Eksisterende kaldere må ikke gå i stykker. Kontrakten må kun udvides additivt: nye valgfrie inputs med en standard, der bevarer nuværende adfærd, og nye outputs. Intet eksisterende input eller output ændres eller fjernes. I fase 1 er den eneste ændring ét nyt output:

- `image`: den fulde image-reference uden tag, med registry og små bogstaver, fx `ghcr.io/hjk-automatisering/ba-fritidsportalen`. Beregnes ét sted og genbruges i signerings- og fejltrinnet, der i dag hver især gentager `tr '[:upper:]' '[:lower:]'`.

**4. `deploy-update.yaml`.** Nyt genbrugeligt workflow. Inputs: `compose_path` (standard `deploy/docker-compose.yml`), `service`, `image`, `digest` og `version`. Repos med flere images kalder workflowet én gang pr. service; konflikter ved push håndteres af retry-trinnet. Trinnene i rækkefølge:

- *Afgør om tagget skal udrulles.* Allerførste trin. GitHub-udtryk har ikke regex, så den præcise kontrol af `vX.Y.Z` er workflowets eget ansvar, ikke kalderens. Matcher `github.ref_name` ikke `^v[0-9]+\.[0-9]+\.[0-9]+$`, afsluttes kørslen **grønt** med `::notice::` om, at tagget ikke er en release og ikke udrulles. Det er ikke en fejl.
- *Tjek at tagget ligger på `main`.* Tag-commit'en skal kunne nås fra `origin/main` (`git merge-base --is-ancestor`); ellers stoppes med en tydelig fejl. Det forhindrer, at et tag på en feature-gren udrulles.
- *Log ind på registryet* med `GITHUB_TOKEN`. App-repos og deres pakker er private; uden login fejler både verifikation og opslag med en 401, der ligner en manglende signatur.
- *Verificér signaturen* med `cosign verify` mod `image@digest`, med OIDC-udsteder `https://token.actions.githubusercontent.com`. Identiteten begrænses til det genbrugelige workflow selv: `^https://github\.com/HJK-Automatisering/workflow/\.github/workflows/docker-publish\.yaml@refs/tags/v`, så kun images bygget gennem jeres fælles workflow fra et udgivet tag kan komme i drift. Tjek desuden, at certifikatets kilde-repo er det kaldende repo (`github.repository`), så repo A ikke kan udrulle repo B's image. Det præcise cosign-flag og den præcise form af identiteten fastlægges ud fra undersøgelsen i krav 1. README skal nævne, at regexp'en skal rettes, hvis `docker-publish.yaml` omdøbes.
- *Tjek at tagget peger på den verificerede digest.* Opslag af `<image>:<version>` i registryet (`docker buildx imagetools inspect`) skal give præcis den digest, der lige er verificeret; ellers stoppes med en tydelig fejl.
- *Tjek ud på `main`*, ikke på tagget (som er en løsrevet commit).
- *Opdatér kun image-feltet* på den angivne service til `<image>:<version>`. Brug `ruamel.yaml` i en fastlåst version fra `requirements.txt`, så kommentarer og formatering bevares. Ikke `sed`. Begrund valget, hvis du vælger noget andet.
- *Idempotens.* Giver opdateringen ingen ændring i filen, afsluttes kørslen grønt med `::notice::` om, at `<service>` allerede står på `<version>`. Der committes ikke. Gen-kørsel af et deploy-job skal altid være ufarlig.
- *Sanity-tjek af compose-filen.* Opret en tom, midlertidig `stack.env` ved siden af compose-filen, og kør `docker compose -f <fil> config -q`. I fase 2 erstattes dette trin af compose-lint.
- *Commit og push til `main`* med beskeden `deploy(<app>): <service> -> <version>`, hvor `<app>` er `github.event.repository.name`, og i brødteksten digest, link til build-kørslen og tag-commit'en. Ved konflikt under push: `git pull --rebase` og prøv igen, højst tre gange. Afvises push med 403 eller "protected branch", skal fejlbeskeden henvise til README-afsnittet "Hvis `main` beskyttes".

**5. Token og grenbeskyttelse.** `main` er ubeskyttet i de berørte repos, og commits pushet med `GITHUB_TOKEN` udløser ikke nye kørsler. Brug `GITHUB_TOKEN` og git CLI. Deklarér ingen `secrets:` i `deploy-update.yaml`. Implementér ingen reserveløsning, men skriv i README et afsnit "Hvis `main` beskyttes" med tre punkter: (a) GitHub Actions som bypass-aktør i rulesettet, (b) alternativt et GitHub App-token via `actions/create-github-app-token` (SHA-pinnet) og tilføjelse af `secrets:` til workflowet og kalderne, (c) ved krav om signerede commits skift til GraphQL `createCommitOnBranch`, der giver verificerede commits. Svæk aldrig en eksisterende beskyttelse uden min godkendelse.

**6. Rettigheder.** Hvert job får de snævrest mulige `permissions`. `deploy-update` skal have `contents: write` og `packages: read`; verifikation med cosign kræver ikke `id-token`. Ligesom med `docker-publish.yaml` skal rettighederne også stå i caller-workflowet, da et genbrugeligt workflow ikke kan hæve sig over kalderen. Dokumentér det.

**7. Udvid `validate.yaml`.** De samme kontroller, som i dag gælder `docker-publish.yaml` (findes `workflow_call`, peger outputs på eksisterende job-outputs, har jobs `permissions` og `timeout-minutes`, ingen bindestreger i inputnavne), skal også gælde `deploy-update.yaml`. Kravet om faste inputs udvides med outputtet `image` på `docker-publish.yaml`.

**8. Caller-eksempel.** Caller-skabelonen ligger i agenter-repoet og opdateres af den tråd, der vedligeholder agenterne. Lever derfor den nye caller-skabelon som et komplet eksempel i README, med:

- `on.push.tags: ['v*.*.*']`, `on.pull_request` og `workflow_dispatch` som i dag. **Ikke** `on.push.branches`.
- build-jobbet som i dag,
- deploy-jobbet med `needs: build` og et groft `if:` på `startsWith(github.ref, 'refs/tags/v') && needs.build.outputs.digest != ''`. Den præcise kontrol ligger i `deploy-update` (krav 4),
- `permissions` pr. job, og på deploy-jobbet en egen `concurrency`-gruppe pr. repo (`deploy-${{ github.repository }}`) med `cancel-in-progress: false`, så en igangværende udrulning ikke annulleres. Nævn i README, at GitHub kun holder én ventende kørsel i gruppen, så to hurtige releases kan springe den midterste over.

**9. README.** Opret README med: alle inputs og outputs for begge workflows; caller-eksemplet; hvordan en release laves (`git tag v1.2.3 && git push origin v1.2.3`); hvordan der rulles tilbage (`git revert` af udrulnings-commit'en, og at det ikke ruller en databasemigrering tilbage); at der ingen tilbagemelding er fra Portainer til GitHub, så nogen skal kigge i Portainer efter en release; en kort vejledning i at migrere en eksisterende app; afsnittet "Hvis `main` beskyttes"; og et afsnit om udgivelse af dette repo: nyt minor-tag og flyt `v1` ved additive ændringer, nyt major-tag ved fjernede inputs/outputs eller ændret standardadfærd, og at versionstags i dette repo aldrig flyttes.

**10. Test.** Test med en ufarlig test-app, før det rulles ud. Fase 2 påbegyndes først derefter.

---

# Fase 2: Compose-lint og tag-beskyttelse

**11. Afhængigheder.** Opret `requirements.txt` med `ruamel.yaml` pinnet. Tilføj `pip`-økosystemet til `dependabot.yml`, grupperet som `python`. `cosign-release` i `cosign-installer` kan Dependabot ikke bumpe; skriv i README under vedligehold, at den bumpes manuelt, når Dependabot bumper `cosign-installer`.

**12. Uforanderlige versionstags.** Compose-filen henviser til imaget med versionstagget alene (`:1.4.2`), så tagget skal reelt være uforanderligt. Tilføj et valgfrit input til `docker-publish.yaml`, `protect_release_tags` (standard `false`). Når det er slået til og kørslen er et tag på formen `vX.Y.Z`, tjekkes det før bygningen, om versionstagget allerede findes i registryet (`docker buildx imagetools inspect`). Findes det, stoppes kørslen med en tydelig dansk fejl om, at en ny bygning kræver et nyt versionsnummer. Ingen undtagelser. Når inputtet er slået til, skal trinnet "Rapportér efterladt image" ændre sin besked til: slet imaget i GHCR, eller tag en ny version; gen-kørsel vil blive afvist. README får et kort afsnit om oprydning efter en rød release-kørsel. Caller-skabelonen slår inputtet til. (Kan trækkes frem til fase 1, hvis fase 1 viser sig hurtig.)

**13. `compose-lint.yaml` og `scripts/compose_lint.py`.** Lint-scriptet ligger som fil i dette repo, ikke inline i workflowet. Det genbrugelige workflow checker workflow-repoet ud med `repository: HJK-Automatisering/workflow` og `ref: ${{ github.job_workflow_sha }}`, så script og workflow altid er samme commit. README dokumenterer, at repoet skal forblive offentligt, ellers kræver checkout et token. Scriptet skal kunne køres lokalt som `python scripts/compose_lint.py <fil>` uden workflow-kontekst, så udviklere og agenter kan køre det før en PR. Det bruger `ruamel.yaml`, så fejl kan angive linjenummer. `validate.yaml` forbliver på pyyaml.

Workflowet kører på pull requests, der ændrer `deploy/**`, og erstatter sanity-trinnet i `deploy-update`. Det kører `docker compose -f <fil> config -q`; da `stack.env` aldrig ligger i repoet, opretter lint-trinnet en tom, midlertidig `stack.env` ved siden af compose-filen før kørslen. Derudover tjekkes disse regler for hver service:

| Regel (navn) | Fejler når |
|---|---|
| `build` | `build:` findes |
| `latest` | image mangler tag, eller tagget indeholder intet ciffer, eller tagget er et af `latest`, `main`, `master`, `stable`, `edge`, `dev`, `nightly`, `lts`. (`postgres:16` og `redis:7-alpine` er tilladt; jeres egne images er altid `X.Y.Z` via deploy-update) |
| `privileged` | `privileged: true` |
| `docker-sock` | et volume peger på `/var/run/docker.sock` |
| `bind-mount` | et volume er en sti på værten (starter med `/`, `./` eller `../`) i stedet for et navngivet volume |
| `host-adgang` | `network_mode: host`, `pid: host`, `devices`, `cap_add`, `sysctls` eller `security_opt` |
| `hemmelighed` | `environment:` indeholder en nøgle, der indeholder `PASSWORD`, `PASSWD`, `SECRET`, `TOKEN` eller `CREDENTIALS` som delstreng, eller `KEY` eller `PRIVATE` som helt led adskilt af `_` (så `API_KEY` fejler, `KEYCLOAK_URL` gør ikke). Uanset værdi; de hører i `stack.env` |
| `env-fil` | en `env_file` peger på andet end `stack.env`, eller der ligger en `stack.env` eller `.env` committet i repoet. Tjekket bruger `git ls-files`, ikke filsystemet, så lint ikke snubler over sin egen midlertidige fil; uden et git-repo springes tjekket over med en advarsel |
| `restart` | `restart` mangler eller er `no` |
| `mem-limit` | `mem_limit` (eller `deploy.resources.limits.memory`) mangler |
| `logging` | `logging.options.max-size` eller `max-file` mangler |
| `ports` | `ports:` findes (al adgang går via Nginx Proxy Manager) |
| `container-name` | `container_name` findes (kolliderer på tværs af stacks) |
| `eksternt-netvaerk` | et netværk med `external: true` er ikke `nginx-proxy-manager_default` |
| `alias` | en service på `nginx-proxy-manager_default` mangler et netværksalias. Ingen krav til aliasets form |

**Undtagelser** markeres i compose-filen med topniveau-feltet `x-undtagelser`, som Docker Compose ignorerer:

```yaml
x-undtagelser:
  - service: web
    regel: bind-mount
    begrundelse: "Leverandørens image kræver konfigurationsfil på denne sti"
    godkendt-af: "Navn Navnesen"
    dato: "2026-10-01"
```

En regel dækket af en gyldig undtagelse giver en advarsel i stedet for en fejl. En undtagelse uden `godkendt-af` og `dato`, eller med et ukendt regelnavn, er selv en fejl. Undtagelser udløber ikke, men en undtagelse ældre end et år giver en advarsel. Fejlbeskeder skrives som `::error file=...,line=...::` på dansk med service og regelnavn, så en udvikler eller agent kan rette dem uden at kende scriptet.

**14. Rettigheder.** `compose-lint` kræver kun `contents: read`. Skal også stå i caller-workflowet.

**15. Udvid `validate.yaml`.** Samme strukturkontroller for `compose-lint.yaml` som for de andre genbrugelige workflows. Kravet om faste inputs udvides med `protect_release_tags`. Tilføj en selvtest af `scripts/compose_lint.py` mod en lille samling gode og dårlige eksempelfiler i `tests/compose/`, herunder et eksempel for hver regel, et med gyldig undtagelse, et med ugyldig undtagelse og referencen nederst, så en ændring i reglerne ikke uopdaget slår alle projekter i stykker.

**16. Caller-eksempel og README.** Udvid caller-eksemplet i README med lint-jobbet på pull requests, der ændrer `deploy/**`, og `protect_release_tags: true` på build-jobbet. Dokumentér alle regler, undtagelsesformatet og lokal kørsel af scriptet.

---

## Uden for opgaven

Ingen ændringer i Portainer og ingen forbindelse til serveren. Portainers læseadgang til GHCR og til Git-repoerne, variablerne i `stack.env` og selve oprettelsen af Git-stacks håndteres af udviklere og administratorer inde i Portainer. Grenbeskyttelse ændres ikke.

## Reference: forventet compose-format

```yaml
services:
  web:
    # Sættes af deploy-update ved release. Ret ikke i hånden.
    image: ghcr.io/hjk-automatisering/sagsoverblik:1.4.2
    restart: unless-stopped
    env_file:
      - stack.env
    networks:
      default:
      nginx-proxy-manager_default:
        aliases:
          - ba-sagsoverblik
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
