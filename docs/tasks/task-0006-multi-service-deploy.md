---
nummer: task-0006
titel: deploy-update: flere services pr. kald og værn mod forkert image-navn
status: afsluttet
kilde: interview
oprettet: 2026-10-02
---

# task-0006 — deploy-update: flere services pr. kald og værn mod forkert image-navn

## Hvad og hvorfor
Den første app på `deploy-update.yaml` har ét image og to services, og måtte køre to deploy-jobs. Det gav to
commits på `main` og dermed to udrulninger i Portainer for én release. Et kald skal kunne opdatere flere
services i én commit. Samtidig skal workflowet nægte at skrive app-imaget ind på en service, der i dag peger
på et andet image, så en slåfejl i `service` ikke kan erstatte fx databasens image med appens.

## Færdig når
- [x] Et deploy-kald med flere services i inputtet opdaterer alle angivne services i én commit.
- [x] Et kald med én service virker som i dag.
- [x] Står nogle af servicene allerede på versionen, opdateres resten; står alle der, afsluttes grønt uden commit.
- [x] Peger en angiven service i dag på et andet image-navn end det, der skal skrives, stopper kørslen med en dansk fejl, der viser begge navne, og intet committes. Det gælder også ved én service.
- [x] Findes en angiven service ikke, eller mangler den et image-felt, stopper kørslen med en dansk fejl, og intet committes. Ingen service er ændret, når én fejler.
- [x] Commit-beskeden nævner de services, der blev opdateret.
- [x] Valideringen i dette repo afprøver scriptet med flere services, delvis idempotens og værnet, og er grøn.
- [x] README beskriver flere services i ét kald og værnet, og caller-eksemplets bemærkning skelner mellem ét image med flere services og flere images.

## Sådan bygger vi det

### `scripts/update_compose_image.py`
Andet argument bliver `<services>`: ét eller flere servicenavne adskilt af komma, mellemrum omkring kommaer
tolereres. Ét navn uden komma er uændret adfærd. Rækkefølge:

1. Parse filen med ruamel som i dag. For **hver** service: findes under `services:` og har `image:`, ellers
   `::error file=...,line=...::` og exit 1.
2. **Værnet:** det nuværende image-navn uden tag og digest skal være lig det nye image-navn uden tag. Navnet er
   alt før sidste `:` i sidste sti-led (så `host:5000/org/app:1.2` håndteres) og før et eventuelt `@sha256:...`.
   Afviger det: `::error::` med service, nuværende navn og nyt navn, og at linjen skal rettes i hånden på `main`,
   hvis skiftet er tilsigtet. Exit 1.
3. Først når alle services er kontrolleret, skrives ændringerne, med samme metode som i dag: tekstudskiftning
   af skalaren på netop den linje, og parse igen bagefter. Alt eller intet.
4. Pr. service skrives én linje til stdout: `<service>: <gammel version> -> <ny version>` eller
   `<service>: står allerede på <ny version>`. Exit 0 hvis mindst én ændring, 3 hvis ingen.

Eksisterende exit-koder (0, 1, 2, 3) og deres betydning er uændrede.

### `.github/workflows/deploy-update.yaml`
- Beskrivelsen af inputtet `service`: ét eller flere servicenavne adskilt af komma; alle skal pege på samme image.
- Trinnet *Opdatér image-feltet* sender inputtet videre uændret og viser scriptets linjer i loggen. Exit 3 giver
  `::notice::` om at alle angivne services allerede står på versionen.
- Commit-beskeden: `deploy(<app>): <services> -> <version>`, hvor `<services>` er de opdaterede services adskilt
  af komma og mellemrum, i den rækkefølge de blev angivet. Brødteksten uændret. Scriptet skal derfor give
  workflowet listen over ændrede services, fx som en linje `changed=web,worker` i `$GITHUB_OUTPUT` skrevet af
  workflowet ud fra scriptets stdout, eller ved at scriptet skriver listen på en genkendelig linje. Vælg det
  simpleste og skriv det i noterne.
- Kommentaren øverst om "Repos med flere images kalder workflowet én gang pr. service" rettes: ét image med
  flere services er ét kald; flere images er ét kald pr. image.
- Alt andet urørt.

### `.github/workflows/validate.yaml`
Scripttesten udvides, eksisterende kontroller beholdes:
- `tests/compose/deploy-example.yml` får en service `worker` med samme image som `web` (samme version), samme
  form som `web` i øvrigt, så filen forbliver regelret for task-0005.
- Kald med `web,worker`: exit 0, præcis to ændrede linjer, begge image-linjer, kommentaren på `web` bevaret.
- Delvis idempotens: nyt kald med `web,worker`, hvor begge står på versionen: exit 3, fil uændret. Og et kald, hvor
  kun `worker` er sat tilbage i filen: exit 0, præcis én ændret linje.
- Værnet: kald med `db` og app-imaget: exit 1, `::error` nævner `postgres` og det nye navn, filen uændret.
- Ukendt service i en liste (`web,findes-ikke`): exit 1, filen uændret.

### `README.md`
- Inputtabellen for `deploy-update.yaml`, rækken `service`: flere navne adskilt af komma; alle skal pege på samme
  image; værnet beskrives i én sætning.
- *Caller-eksempel*, bemærkningen *Flere images i samme repo*: deles i to. Ét image, flere services:
  `service: web,worker`, én commit. Flere images: ét deploy-job pr. image, retry håndterer sammenstød.
- *Release*, trin 3: "Opdaterer `image:` på de angivne services".
- *Efter en release*, punktet *Deploy-jobbet rødt*: nævn værnet som en af de fejl, beskeden kan vise.
- *Tilbagerulning*: sætningen "Versionstags overskrives aldrig i GHCR" holder kun med `protect_release_tags` slået til (task-0004). Skriv det med forbehold og henvis til inputtet. (Fund fra task-0004.)
- `CLAUDE.md`: rækken for `scripts/update_compose_image.py` nævner flere services og værnet, hvis den ellers bliver forkert.

## Hvad vi ikke rører
- Alle øvrige trin i `deploy-update.yaml`: release-tjek, main-tjek, login, verifikation, digest-tjek, sanity-tjek, retry.
- `docker-publish.yaml`, `compose-lint` og alt i task-0005.
- Inputs og outputs: `service` beholder navn og type; kun beskrivelsen og det accepterede indhold udvides.
- Ingen tags, ingen udgivelse.

## Afhænger af
intet

## Beslutninger
- BESLUTTET: Flere navne i det eksisterende input `service`, adskilt af komma — et nyt input ved siden af ville kræve, at `service` stadig blev sat, fordi det er påkrævet. Nyt input `services` afvist.
- BESLUTTET: Værnet mod forkert image-navn, også ved én service — en slåfejl ville ellers erstatte fx databasens image med appens, og compose-tjekket fanger det ikke. Prisen er én manuel rettelse ved et tilsigtet skift af image-navn. Godkendt af mennesket 2026-10-02.
- BESLUTTET: Alt eller intet — fejler én service, skrives ingen; en halvt opdateret fil på `main` ville udrulle noget, ingen har bedt om.
- BESLUTTET: Delvis idempotens — allerede opdaterede services springes over med en besked, resten opdateres. Gen-kørsel forbliver ufarlig.
- BESLUTTET: Værnet er en stramning, der kun fyrer ved en fejlkonfiguration, og regnes som additiv — udgives med næste minor-tag, ikke som `v2`.

## Åbne punkter

## Indvendinger

---

## Developers noter

### Hvad er lavet

Gren `task-0006-multi-service-deploy` fra `main`. Fire commits, én pr. enhed; intet pushet, ingen tags.

- `scripts/update_compose_image.py` — andet argument er nu `<services>`: ét navn, eller flere adskilt af komma, med mellemrum omkring kommaer tolereret og tomme led ignoreret. Ny `image_name()` fjerner `@sha256:…` og tagget i sidste sti-led (`host:5000/org/app:1.2@sha256:…` → `host:5000/org/app`). To gennemløb: først findes og kontrolleres alle services (findes, har `image:`, samme image-navn som det nye), uden at skrive; fejler én, returneres exit 1 og filen er urørt. Derefter tekstudskiftning af skalaren på hver linje som før, re-parse og kontrol af hvert felt, så skrives filen. Pr. service én stdout-linje `<service>: <gammel version> -> <ny version>` eller `<service>: staar allerede paa <ny version>`; ved exit 0 til sidst `changed=<liste>` i inputtets rækkefølge. Exit 0/1/2/3 betyder det samme som før. Værnets fejl: `::error file=…,line=…::servicen `db` peger paa imaget `postgres`, men der skulle skrives `ghcr.io/…/example-app`. Er det en slaafejl i inputtet service? Er skiftet af image-navn tilsigtet, saa ret linjen i haanden paa main foerst.`
- `tests/compose/deploy-example.yml` — ny service `worker` mellem `web` og `db`, samme image og version som `web`, med `restart`, `environment` kun som `${NØGLE}`, `mem_limit` og `logging`, ingen `ports`. Image-linjen uden trailing-kommentar, så testen kan se at kommentaren på `web` er den der bevares.
- `.github/workflows/deploy-update.yaml` — kommentaren øverst skelner ét image med flere services (ét kald) fra flere images (ét kald pr. image). Beskrivelsen af `service` nævner komma og kravet om samme image-navn. Trinnet *Opdatér image-feltet* fanger scriptets stdout, viser linjerne pr. service i loggen, læser `changed=`-linjen og skriver den som output `services`; exit 3 giver `::notice::Alle angivne services (…) står allerede på …`; fejlteksten nævner alle tre krav til hver service og at intet er ændret. Commit-trinnet får `SERVICES` fra outputtet og skriver `deploy(<app>): ${SERVICES//,/, } -> <version>`; brødteksten er uændret. Alle øvrige trin urørte.
- `.github/workflows/validate.yaml` — scripttesten udvidet med punkt 4–8 som beskrevet i opgaven; de tre eksisterende beholdt. Den første Python-blok er uændret (inputs er de samme).
- `README.md` — inputtabellens `service`-række, bemærkningen i caller-eksemplet delt i *Ét image, flere services* og *Flere images i samme repo*, Release trin 3 (opdaterer de angivne services; delvis idempotens; stop før skrivning), commit-beskeden med flere services, *Deploy-jobbet rødt* nævner værnet, og *Tilbagerulning* siger at det forrige image kun med sikkerhed er det samme med `protect_release_tags` slået til. Desuden *Efter en release* punkt 2: "image-linjen på de nævnte services".
- `CLAUDE.md` — rækken for `scripts/update_compose_image.py` nævner flere services og værnet.

**Valget om listen af ændrede services** (opgaven bad om det simpleste): scriptet skriver `changed=web,worker` som sidste stdout-linje ved exit 0, og workflowet gør `grep '^changed=' | cut -d= -f2-`. Det er én linje i scriptet og én i workflowet, og de menneskelæselige linjer pr. service forbliver fri for syntaks. Alternativet, at workflowet selv skulle udlede navnene af ` -> `-linjerne, ville binde workflowet til formatet på logteksten.

**Færdig når — efterprøvet lokalt** (`.venv\Scripts\python.exe`, ruamel 0.19.1; pyyaml kun i scratchpad med `--target`/`PYTHONPATH`):

| Punkt | Resultat |
|---|---|
| Flere services i ét kald, én commit | Ja. Simuleret app-repo med bare remote: trinnet *Opdatér image-feltet* kørt som fil med `SERVICE="web, worker"` gav `changed=true`, `services=web,worker`; commit-trinnet pushede én commit `deploy(example-app): web, worker -> 9.9.9` fra `github-actions[bot]`, 2 linjer ændret |
| Én service som i dag | Ja. `SERVICE=web`: `services=web`, besked `deploy(example-app): web -> 9.9.9`, én linje ændret. Scriptet med ét navn uden komma: samme adfærd som før, kun loglinjens form er ny |
| Delvis idempotens; alle på versionen → grønt uden commit | Ja. Kun `worker` sat tilbage: exit 0, én linje, `changed=worker`, besked `deploy(example-app): worker -> 9.9.9`. Begge på versionen: exit 3, `changed=false`, `::notice::`, fil urørt |
| Værnet, også ved én service | Ja. `db` og `web,db` mod app-imaget: exit 1, `::error file=…,line=44::` med `postgres` og `ghcr.io/hjk-automatisering/example-app`, fil urørt, `git status` tom |
| Ukendt service / manglende image-felt, intet ændret | Ja. `web,findes-ikke`: exit 1, `Kendte services: db, web, worker`, fil urørt. Manglende `image:` giver samme vej som før (kontrolleres i første gennemløb, før noget skrives) |
| Commit-beskeden nævner de opdaterede services | Ja, se ovenfor; kun de ændrede, i inputtets rækkefølge, adskilt af komma og mellemrum |
| Valideringen afprøver flere services, delvis idempotens og værnet, og er grøn | Ja. Begge Python-blokke fra `validate.yaml` kørt lokalt: `deploy-update.yaml: ok` (inputs uændrede), `scripts/update_compose_image.py: ok (aendring, idempotens, ukendt service, flere services, delvis idempotens, vaern mod forkert image-navn)`. `bash -n` på alle 13 `run:`-blokke i de tre workflows: ok. `git diff --check` ren, alle filer LF |
| README beskriver flere services og værnet; bemærkningen skelner | Ja, se listen ovenfor |

Desuden: `image_name()` afprøvet på `postgres:16.4`, `postgres`, `host:5000/org/app:1.2`, `host:5000/org/app:1.2@sha256:…`, `ghcr.io/o/a@sha256:…`, `ghcr.io/o/a`. `web,web` giver exit 2 (argparse), tom liste (` , `) giver exit 2.

### Hvad er ikke lavet, og hvorfor

- **Ikke efterprøvet i GitHub Actions:** at `validate.yaml` er grøn på runneren, og at `deploy-update.yaml` med `web,worker` kører end-to-end fra et app-repo. Kræver push og udgivelse, som er menneskets skridt. Alle `run:`-blokke er kørt lokalt som beskrevet.
- Kommentaren `# Navnet på servicen under services: …` ved `service: web` i caller-eksemplets YAML er uændret — opgaven nævner kun bemærkningen under eksemplet, og skabelonen vedligeholdes i agenter-repoet.

### Uklart

- **Dubletter i listen** (`web,web`) stod ikke i opgaven. Jeg afviser dem med exit 2 og en argparse-fejl frem for at fjerne dem i stilhed, fordi det er en fejlkonfiguration i kalderen og en dublet ellers ville ramme samme linje to gange. Skal det i stedet tolereres, er det to linjer i `main()`.
- **Stdout-linjerne viser versionen, ikke hele referencen.** Opgaven skriver `<gammel version> -> <ny version>`; det gamle script skrev hele image-referencen. Jeg fulgte opgaven: `web: 1.4.2 -> 9.9.9`. Har referencen hverken tag eller digest, vises hele referencen, så linjen aldrig er tom.
- **Loglinjen `Pushet til main i forsøg N: … -> …`** i commit-trinnet bruger nu også listen af ændrede services (`web, worker`) i stedet for det rå input. Opgaven siger "brødteksten uændret", og det er den; loglinjen regnede jeg som en del af samme ændring. Sig til, hvis den skal tilbage til `${SERVICE}`.
- **`worker` i eksempelfilen har ingen `networks:`-blok.** `web` har aliaset til proxy-netværket; en worker er ikke nået udefra, så jeg udelod blokken. "Samme form som web i øvrigt" er ellers fulgt. Skal `worker` have `networks: default:` for at ligne `web` helt, er det tre linjer.
