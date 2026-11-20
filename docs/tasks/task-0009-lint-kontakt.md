---
nummer: task-0009
titel: compose-lint: stackens kontaktperson i labelen hjk.kontakt
status: afsluttet
kilde: interview
oprettet: 2026-11-18
---

# task-0009 — compose-lint: stackens kontaktperson i labelen hjk.kontakt

## Hvad og hvorfor
docker-monitor overvåger Docker-værten og sender stackens kontaktperson en
ugentlig sårbarhedsrapport og en morgenmail om containere, der er gået ned.
Kontaktpersonen læses fra labelen `hjk.kontakt` på stackens containere, med
værdien fra stackens variabel `CONTACT_EMAIL`. En stack uden labelen får ingen
mail. Beslutningen i docker-monitor (2026-11-18): labelen er standard i begge
fælles repoer — kontrakten i agents-repoet definerer, lint-reglen her
håndhæver.

## Færdig når
- [ ] En compose-fil, hvor ingen service har labelen `hjk.kontakt`, giver en fejl med regelnavnet `kontakt`.
- [ ] En label med en anden værdi end præcis `${CONTACT_EMAIL}` — fast adresse, anden variabel, standardværdi — giver en fejl på den service, der bærer den. Stacken får så ikke også fejlen for at mangle labelen.
- [ ] Én service med labelen dækker hele stacken. Mapping- og listeform virker begge.
- [ ] `kontakt` kan undtages i `x-undtagelser`. `service` er den service, der skulle have båret labelen; en slåfejl i navnet giver en død undtagelse.
- [ ] Alle eksempler i `tests/compose/` bryder kun det, de skal; `validate.yaml` dækker reglen og er grøn.
- [ ] README: rækken i regeltabellen, punktet under *Undtagelser* og referencen.
- [ ] docker-monitors egen compose-fil består.

Efterprøves af mennesket før `v1` flyttes:

- [ ] De kaldere, der bruger compose-lint, har labelen i deres compose-fil og `CONTACT_EMAIL` på stacken. Reglen er strammere, og en app uden labelen får ellers en rød release (README, *Udgivelse af dette repo*).

## Hvad vi ikke rører
- Workflow-filerne `compose-lint.yaml` og `deploy-update.yaml`. Scriptet hentes ved samme SHA.
- Om adressen ligner en mailadresse. Den står aldrig i filen og kan ikke ses af lint.
- `deploy.labels`. De sættes på swarm-servicen og ses ikke på containeren.

## Afhænger af
intet

## Beslutninger
- BESLUTTET: Regelnavnet er `kontakt`.
- BESLUTTET: Reglen giver fejl, ikke advarsel. `v1` flyttes først, når kalderne har labelen. Svar fra mennesket 2026-11-18.
- REVIDERET 2026-11-18: `v1` er flyttet i `v1.5.0`, før kalderne har labelen. Kalderne er varslet i en fælles besked, og fejlen er påmindelsen. Det erstatter kriteriet om at efterprøve kalderne før `v1` flyttes.
- BESLUTTET: Fundet for en stack uden labelen har ingen service. En undtagelse på en hvilken som helst service i filen dækker det.

## Åbne punkter
intet

## Indvendinger

## Developers noter
<Alt over denne overskrift ejes af architect. Alt under skrives kun af developer.>

Bygget i én session uden for rollerne, på grenen `claude/lint-kontakt-b769aa`.

**Lavet:**
- `scripts/compose_lint.py`: ny regel `kontakt` i `REGLER`, funktionen `lint_kontakt` og `daekker` i undtagelserne.
- `tests/compose/fejl/kontakt.yml` (ingen label) og `tests/compose/kontakt-forkert-vaerdi.yml` (fast adresse, anden variabel, standardværdi).
- Labelen sat på alle øvrige eksempler, så de stadig kun bryder deres egen regel. `ok/varianter.yml` viser listeformen på en anden service end den første. `undtagelse-gyldig.yml` undtager `kontakt`.
- `validate.yaml`: `kontakt` i regellisten, i tjekket af gyldige undtagelser, og et nyt trin 5 for forkerte værdier.
- README og `CLAUDE.md` (18 → 19 regler).

**Efterprøvet lokalt** med `.venv` og Docker: begge scripttests fra `validate.yaml` er grønne. docker-monitors compose-fil består (tre advarsler fra dens egne undtagelser). En undtagelse med slåfejl i servicenavnet giver en død undtagelse, og fejlen bliver stående.

**Kørt mod lokale kloner af app-repoer:** ni har `deploy/docker-compose.yml`, og alle ni fejler på `kontakt`. Navnene står ikke her, fordi repoet er offentligt og app-repoerne er private. Klonerne kan være bagud for deres `main`. Det er flere end de fire kendte kaldere i `CLAUDE.md`.
