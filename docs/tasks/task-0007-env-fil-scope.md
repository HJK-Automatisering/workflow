---
nummer: task-0007
titel: Afgræns env-fil-reglen til compose-filens mappe
status: i-gang
kilde: interview
oprettet: 2026-10-09
---

# task-0007 — Afgræns env-fil-reglen til compose-filens mappe

## Hvad og hvorfor
`lint_env_filer` i `scripts/compose_lint.py` fejler på en committet `.env`
eller `stack.env` **hvor som helst** i repoet (`git ls-files` mod repo-roden).
Reglens begrundelse er deploy-stakken: Portainer kører compose-filen (typisk
`deploy/docker-compose.yml`), og docker compose læser kun en `.env` fra
compose-filens egen mappe (projektmappen). En `.env` i repo-roden er usynlig
for stakken.

Det rammer virkelige projekter: itk-dev-baserede Drupal-projekter (fx
ai-screening-forken) kræver en committet `.env` i roden — upstreams CI kører
`docker compose` direkte mod rodens compose-filer og fejler uden den
(`DRUSH_OPTIONS_URI=http://` → drush-crash). Reglen som skrevet tvinger et
valg mellem grøn lint og grøn upstream-CI, selv om dens egen begrundelse ikke
dækker rodens fil.

## Færdig når
- [ ] En committet `.env`/`stack.env` i **compose-filens mappe** fejler stadig med `env-fil`.
- [ ] En committet `.env`/`stack.env` i **andre mapper** (fx repo-roden når compose-filen ligger i `deploy/`) fejler ikke.
- [ ] Fejlteksten siger præcis hvad der rammes: filen ligger i compose-filens mappe og læses af stakken.
- [ ] README-rækken for `env-fil` i regel-tabellen beskriver den nye afgrænsning.
- [ ] `env_file:`-tjekket på service-niveau er uændret.
- [ ] Advarsels-fallbacks (git mangler, ikke et repo, timeout) er uændrede i adfærd.
- [ ] Efterprøvet mod et scratch-git-repo: compose i `deploy/`, `.env` committet i roden → ok; `.env` committet i `deploy/` → fejl.

## Sådan bygger vi det
- I `lint_env_filer`: udregn compose-filens mappe relativt til repo-roden
  (`path.resolve().parent` mod `git rev-parse --show-toplevel`) og flag kun
  `git ls-files`-stier hvis mappe-del matcher. Pas på compose-fil i selve
  roden (relativ mappe er tom streng).
- Opdatér modulets regel-kommentar (linjen om at en committet `.env` ikke kan
  undtages — det gælder stadig, men kun i compose-mappen).
- README: rækken for `env-fil` i tabellen under "Regler for compose-filen".
- Efterprøvning: scratch-repo i `$TMPDIR` med `git init`, compose-filen i
  `deploy/`, kør scriptet begge veje (rod-`.env` committet / `deploy/.env`
  committet) og skriv resultatet i noterne. Kør desuden hele
  fixture-harnessen lokalt som `validate.yaml` gør, hvis miljøet tillader
  (ruamel.yaml i venv) — `tests/compose/fejl/env-fil.yml` dækker
  `env_file:`-delen og skal stadig fejle.

## Hvad vi ikke rører
- `tests/compose/`-fixtures (env-fil-eksemplet dækker `env_file:`-delen og er stadig korrekt).
- De øvrige regler og undtagelsesmekanikken (`x-undtagelser` gælder stadig ikke for env-fil).
- Workflow-filerne (`compose-lint.yaml`, `deploy-update.yaml`) — scriptet hentes ved samme SHA, ingen ændring behøves.

## Afhænger af
intet

## Beslutninger
- BESLUTTET: Afgrænsningen er compose-filens egen mappe — det er den eneste
  mappe hvis `.env` docker compose (og dermed Portainer-stakken) læser.
  Afvist: repo-rod + compose-mappe (roden er netop der upstream-projekter
  skal kunne have deres dev-`.env`).

## Åbne punkter

## Indvendinger

---

## Developers noter

<Alt over denne overskrift ejes af architect. Alt herunder skrives kun af
developer, som aldrig retter i definitionen ovenfor.>

### Hvad er lavet
- `scripts/compose_lint.py`, `lint_env_filer`: compose-filens mappe udregnes
  relativt til repo-roden (`path.resolve().parent.relative_to(rod)`, `.` →
  tom streng), og kun `git ls-files`-stier hvis mappe-del matcher flagges.
  Dækker både compose i undermappe og compose i selve roden.
- Fejlteksten siger nu at filen er committet i compose-filens mappe og derfor
  læses af stacken når den kører (ASCII-dansk som resten af scriptet).
- Modulets regelkommentar (docstring, undtagelses-afsnittet) præciseret:
  fund uden service er en committet `.env`/`stack.env` *i compose-filens
  mappe*. `lint_env_filer`s egen docstring forklarer afgrænsningen.
- `README.md`, rækken `env-fil` under "Regler for compose-filen": beskriver
  den nye afgrænsning, inkl. at rodens `.env` ikke rammes når compose ligger
  i en undermappe.
- `env_file:`-tjekket på service-niveau er uændret (koden ikke rørt);
  `tests/compose/fejl/env-fil.yml` fejler stadig med `[env-fil]`.
- Advarsels-fallbacks uændrede: mappe-udregningen sker først efter at både
  `rev-parse` og `ls-files` er lykkedes, så git-mangler/ikke-repo/timeout/
  ls-files-fejl rammer præcis samme kodeveje som før. "Ikke et git-repo"
  efterprøvet manuelt: advarsel + exit 0.
- Efterprøvet mod scratch-git-repo i $TMPDIR (env-filerne committet via
  git-plumbing, uden at materialisere dem):
  - ingen committet env-fil → ok (exit 0)
  - `.env` committet i roden, compose i `deploy/` → ok (exit 0)
  - samme repo, compose i roden → 1 fejl på `.env` (exit 1)
  - `.env` committet i både roden og `deploy/`, compose i `deploy/` →
    præcis 1 fejl, på `deploy/.env` (exit 1)
  - `deploy/stack.env` oveni → 2 fejl (exit 1)
  - `.env` i en tredje undermappe → stadig kun deploy-fundene
- Hele fixture-harnessen kørt lokalt som `validate.yaml` gør (venv i $TMPDIR
  med ruamel.yaml 0.19.1 fra requirements.txt): 3 gode eksempler exit 0 uden
  `[compose]`-fund, alle 16 `fejl/<regel>.yml` exit 1 med deres egen regel,
  begge undtagelsesfiler som forventet.

### Hvad er ikke lavet, og hvorfor
intet

### Uklart
intet
