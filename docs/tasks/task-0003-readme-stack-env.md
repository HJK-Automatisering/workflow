---
nummer: task-0003
titel: README: stackens variabler substitueres, Portainer skriver ikke stack.env
status: afsluttet
kilde: interview
oprettet: 2026-10-02
---

# task-0003 — README: stackens variabler substitueres, Portainer skriver ikke stack.env

## Hvad og hvorfor
Migreringen af den første app til `deploy-update.yaml` viste, at Portainer **ikke** genererer `stack.env`
for Git-baserede stacks. Stakformularen siger, at filen i så fald skal ligge i repoet; stackens variabler
bruges i stedet til `${VAR}`-substitution i compose-filen. README beskriver det modsatte tre steder, og
referencen for compose-format viser `env_file: stack.env`. Appen løste det med `environment:` og rene
substitutioner uden værdier. Dokumentationen skal følge virkeligheden, før næste app migreres.

## Færdig når
- [x] README påstår intet sted, at Portainer skriver `stack.env`. De berørte afsnit siger, at stackens variabler substitueres ind i compose-filen.
- [x] Referencen for compose-format viser `environment:` med rene `${VAR}`-substitutioner og ingen værdier, og ingen `env_file`.
- [x] Migreringens trin 3 nævner, at Git-kilden oprettes separat med token og polling, og at registryet vælges på stacken.
- [x] Eksempelfilen under `tests/compose/` følger den nye reference, og valideringen i dette repo er stadig grøn.
- [x] Intet workflow og intet script er ændret.

## Sådan bygger vi det
Kun `README.md`, `tests/compose/deploy-example.yml` og, hvis nødvendigt, `CLAUDE.md`.

**README, afsnit for afsnit:**
- *Sådan hænger udrulningen sammen*: tilføj én sætning om, at variabler og hemmeligheder sættes på stacken i Portainer og substitueres ind i compose-filen ved udrulning. Ingen `stack.env`.
- *Migrering af en eksisterende app*, trin 1: alt under `environment:` beholdes som nøgler med `${NØGLE}` som værdi; selve værdierne flyttes til stackens variabler. Ingen `env_file`. Sætningen om at lægge `stack.env` i `.gitignore` udgår.
- *Migrering*, trin 3: Git-kilden (repo-URL, token, polling) oprettes separat i Portainer og vælges på stacken; registryet vælges også på stacken. Variablerne på stacken substitueres i compose-filen.
- *Reference: forventet compose-format*: erstat `env_file: - stack.env` på begge services med `environment:` i listeform, fx
  `- DB_SERVER=${DB_SERVER}` og `- DB_PASSWORD=${DB_PASSWORD}` på `web`, `- POSTGRES_PASSWORD=${POSTGRES_PASSWORD}` på `db`. Ingen literaler.
  Kommentér ved blokken, at der aldrig står værdier i compose-filen; de sættes på stacken.
- *Release*, trin 3: linjen om sanity-tjek med tom `stack.env` **beholdes**, fordi workflowet stadig gør det. Den rettes i task-0005.

**Eksempelfil:** `tests/compose/deploy-example.yml` bringes på samme form som referencen. Image-linjen på `web`
(`example-app:1.4.2` med trailing-kommentaren `# sidste release`) og den enkeltciterede image-linje på `db` skal
blive stående uændret, fordi `validate.yaml`s scripttest kigger på netop dem. Kør scripttesten lokalt med
`.venv\Scripts\python.exe` på samme måde som i `validate.yaml` for at bekræfte, at den stadig er grøn.

**CLAUDE.md:** kun hvis en sætning der er blevet forkert. Domænebegrebet *Portainer / GitOps* nævner ikke `stack.env`; lad det stå.

Kommandoer i PowerShell-venlig form, ingen `&&`. Ingen forretningsspecifikke værdier; nøglerne i eksemplerne er generiske.

## Hvad vi ikke rører
- `.github/workflows/*` — sanity-trinnets midlertidige `stack.env` er harmløst og erstattes af lint i task-0005.
- `scripts/`, `requirements.txt`, `.gitignore` (`stack.env` og `.env` bliver stående deri; de må aldrig committes).
- `docs/prompt-workflow-gitops-v2.md` — opgavebeskrivelsen er historik; fundet står i beslutningsloggen.
- Ingen tags, ingen udgivelse.

## Afhænger af
intet

## Beslutninger
- BESLUTTET: Kun dokumentation og eksempelfil; intet workflow ændres — fundet rører ikke `deploy-update.yaml`s adfærd, og sanity-trinnet lægges om i lint-opgaven alligevel.
- BESLUTTET: Referencen viser ingen literaler under `environment:`, kun `${NØGLE}` — samme regel som compose-lint håndhæver i task-0005 (alternativ A). Godkendt af mennesket 2026-10-02.
- BESLUTTET: Listeformen `- NØGLE=${NØGLE}` i referencen, fordi det er den form den første app bruger. Mapping-form er også gyldig for lint.

## Åbne punkter

## Indvendinger

---

## Developers noter

Gren `task-0003-readme-stack-env`, to commits: `6a664a2` (README) og `2da6359` (eksempelfil). Ikke pushet.

### Hvad er lavet
Holdt op mod *Færdig når*, punkt for punkt:

- **README påstår intet sted, at Portainer skriver `stack.env`** — `README.md`:
  - *Sådan hænger udrulningen sammen*: én sætning tilføjet om, at variabler og hemmeligheder sættes på stacken i Portainer og substitueres ind i compose-filen ved udrulning, hvor der står `${NØGLE}`, og at der ikke er nogen `stack.env`.
  - *Migrering*, trin 1: `env_file: - stack.env` og sætningen om `.gitignore` er ude. Alt under `environment:` beholdes som nøgler med `${NØGLE}` som værdi (eksempel `- DB_SERVER=${DB_SERVER}`), værdierne flyttes til stackens variabler, ingen `env_file`.
  - *Migrering*, trin 3: "det er dem, Portainer skriver til `stack.env`" er ude; variablerne substitueres ind i compose-filen.
  - De eneste tilbageværende omtaler af `stack.env` i README er den nye sætning ("der er ingen `stack.env`") og release-trin 3 om sanity-tjekket, som opgaven siger skal blive stående.
- **Referencen viser `environment:` med rene `${VAR}`-substitutioner og ingen `env_file`** — `README.md`, *Reference: forventet compose-format*: `web` har `- DB_SERVER=${DB_SERVER}` og `- DB_PASSWORD=${DB_PASSWORD}`, `db` har `- POSTGRES_PASSWORD=${POSTGRES_PASSWORD}`. Kommentar ved blokken på `web` om, at der aldrig står værdier i compose-filen; de sættes på stacken.
- **Trin 3 nævner Git-kilde med token og polling, oprettet separat, og registry valgt på stacken** — `README.md`, *Migrering*, trin 3, med opgavens ordlyd. Jeg har ikke beskrevet Portainers menupunkter, kun hvad der oprettes hvor.
- **Eksempelfilen følger referencen, valideringen er grøn** — `tests/compose/deploy-example.yml`: samme `environment:`-blokke og samme kommentar som referencen. Image-linjen på `web` (`example-app:1.4.2  # sidste release: 2026-09-30`) og den enkeltciterede på `db` er urørte. Scripttestens Python-blok fra `validate.yaml` (linje 131–182) kørt lokalt med `.venv\Scripts\python.exe`: `scripts/update_compose_image.py: ok (aendring, idempotens, ukendt service)`, exit 0. Derudover kørt `docker compose -f … config -q` mod eksempelfilen med en tom `stack.env` ved siden, som sanity-trinnet i `deploy-update.yaml` gør: exit 0, med tre advarsler om usatte variabler (`DB_SERVER`, `DB_PASSWORD`, `POSTGRES_PASSWORD`), der sættes til tom streng. Sanity-trinnet bliver altså grønt mod det nye format.
- **Intet workflow og intet script er ændret** — `git diff --stat` mod `main` viser kun `README.md` og `tests/compose/deploy-example.yml`. `CLAUDE.md` er ikke rørt; dens tekst om *Portainer / GitOps* er stadig rigtig.

### Hvad er ikke lavet, og hvorfor
intet

### Uklart
intet

### Fund uden for opgaven
To kommentarer, der stadig siger at Portainer genererer `stack.env`. Begge ligger under *Hvad vi ikke rører*, så jeg har ladet dem stå:

1. `.github/workflows/deploy-update.yaml` linje 215–216: "stack.env genereres af Portainer og ligger aldrig i repoet, men compose-filen henviser til den med env_file." Forsvinder formentlig med task-0005, når sanity-trinnet erstattes af lint.
2. `.gitignore` linje 12–13: "stack.env genereres af Portainer og må aldrig committes." Selve ignoreringen er stadig rigtig; begrundelsen er det ikke.
