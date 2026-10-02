---
nummer: task-0006
titel: deploy-update: flere services pr. kald og værn mod forkert image-navn
status: planlagt
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
- [ ] Et deploy-kald med flere services i inputtet opdaterer alle angivne services i én commit.
- [ ] Et kald med én service virker som i dag.
- [ ] Står nogle af servicene allerede på versionen, opdateres resten; står alle der, afsluttes grønt uden commit.
- [ ] Peger en angiven service i dag på et andet image-navn end det, der skal skrives, stopper kørslen med en dansk fejl, der viser begge navne, og intet committes. Det gælder også ved én service.
- [ ] Findes en angiven service ikke, eller mangler den et image-felt, stopper kørslen med en dansk fejl, og intet committes. Ingen service er ændret, når én fejler.
- [ ] Commit-beskeden nævner de services, der blev opdateret.
- [ ] Valideringen i dette repo afprøver scriptet med flere services, delvis idempotens og værnet, og er grøn.
- [ ] README beskriver flere services i ét kald og værnet, og caller-eksemplets bemærkning skelner mellem ét image med flere services og flere images.

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
### Hvad er ikke lavet, og hvorfor
### Uklart
