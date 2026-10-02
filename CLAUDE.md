# workflow

Genbrugelige GitHub Actions-workflows for HJK-Automatisering. Projekternes egne
workflows kalder dem med `uses: HJK-Automatisering/workflow/.github/workflows/<fil>@v1`,
så SHA-pinnede actions kan bumpes ét sted. Repoet er offentligt; app-repoerne er private.

Procesregler står i `AGENTS.md`. Åbent arbejde står på `docs/BOARD.md`.

## Stak

- GitHub Actions (YAML). Alle actions pinnet til commit-SHA med versionskommentar.
- Python 3 i `run:`-trin til validering, kun `pyyaml`. Ingen tredjeparts-actions ud over Docker og sigstore.
- Python-scripts i `scripts/` med `ruamel.yaml`, pinnet i `requirements.txt`. Lokale Python-kald går gennem `.venv` (`.venv\Scripts\python.exe`), som ikke versionsstyres.
- cosign v3.1.3 til keyless signering af images mod GHCR og til verifikation før udrulning.
- Dependabot bumper actions og pip-pinnen ugentligt, grupperet `docker`, `sigstore` og `python`.

## Kommandoer og udgivelse

Der er ingen lokal build- eller testkommando. Validering kører i GitHub Actions via `validate.yaml`.
Hvordan repoet udgives (minor-tag og flyt af `v1`, `v2` ved brud, versionstags flyttes aldrig) står i
`README.md` under *Udgivelse af dette repo*. Gentag det ikke her.

## Mappestruktur

| Sti | Hvad |
|---|---|
| `README.md` | Caller-eksempel, inputs og outputs, release, tilbagerulning, migrering og udgivelse af repoet. Forlægget for caller-skabelonen i agenter-repoet |
| `.github/workflows/docker-publish.yaml` | Genbrugeligt build-, push- og signeringsworkflow. Outputs `digest`, `version`, `tags`, `image` |
| `.github/workflows/deploy-update.yaml` | Genbrugeligt udrulningsworkflow. Verificerer signatur og digest, linter compose-filen og skriver `<image>:<version>` i den på `main` |
| `.github/workflows/compose-lint.yaml` | Genbrugeligt lint-workflow. Kører `scripts/compose_lint.py` mod kalderens compose-fil i pull requests. Input `compose_path`, ingen outputs |
| `.github/workflows/validate.yaml` | Strukturvalidering af de genbrugelige workflows og selvtest af begge scripts mod `tests/compose/`. Kører kun i dette repo |
| `.github/dependabot.yml` | Bumper SHA-pinnede actions og pinnen i `requirements.txt` |
| `scripts/update_compose_image.py` | Opdaterer `services.<service>.image` på én eller flere services (kommasepareret) i en compose-fil og rører intet andet. Nægter at skrive, hvis en service peger på et andet image-navn. Hentes af `deploy-update.yaml` under kørslen |
| `scripts/compose_lint.py` | Linter en compose-fil mod de 16 regler i README (*Regler for compose-filen*) med undtagelser i `x-undtagelser`. Regelnavnene deles med agenternes deploy-kontrakt. Hentes af `compose-lint.yaml` og `deploy-update.yaml` under kørslen |
| `tests/compose/` | Eksempelfiler til `validate.yaml`: `deploy-example.yml` til scripttesten for `update_compose_image.py` (skal selv være regelret), `ok/` gode eksempler, `fejl/<regel>.yml` ét dårligt pr. regel, `undtagelse-gyldig.yml` og `undtagelse-ugyldig.yml` |
| `requirements.txt` | `ruamel.yaml`, pinnet. Bruges af `scripts/` og installeres af `deploy-update.yaml` og `compose-lint.yaml` |
| `.venv/` | Lokalt virtuelt miljø med indholdet af `requirements.txt`. Ikke versionsstyret |
| `.gitattributes` | LF i alt, fordi `run:`-blokke er shell |
| `docs/` | Tavle, beslutningslog og rapporter efter `AGENTS.md` |
| `docs/prompt-workflow-gitops-v2.md` | Opgavebeskrivelse for GitOps-udvidelsen (fase 1 og 2). Grundlag for `architect`s interview |

## Designprincipper, der skal holdes

- Inputnavne med `_`, aldrig `-`. Bindestreg læses som minus i GitHub-udtryk.
- `permissions` og `timeout-minutes` på hvert job. `concurrency` kun i caller-workflowet.
- Kommentarer på dansk, der forklarer *hvorfor*. Fejlbeskeder på dansk som `::error::`.
- Kontrakten for et genbrugeligt workflow udvides kun additivt. Eksisterende inputs og outputs fjernes eller ændres aldrig uden `v2`.
- Hellere Python i et `run`-trin end endnu en action, der skal pinnes og bumpes.
- Ingen hemmeligheder i workflows eller build-args. Build-args ender som ENV i imaget.

## Domænebegreber

- **Caller / caller-skabelon:** Det workflow i et app-repo, der kalder dette repos workflows. Skabelonen vedligeholdes i agenter-repoet under `plugins/agents/skills/workflow/assets/`.
- **Keyless signering:** cosign signerer med et kortlivet certifikat fra GitHubs OIDC-token. Kræver upload til den offentlige Rekor-log, så digest og repo-sti bliver offentlige.
- **Digest vs. tag:** Digest er uforanderlig og bruges til deploy og verifikation. Tags som `:main` og `:latest` flytter sig.
- **Portainer / GitOps:** Produktionsserveren kan ikke nås fra GitHub. Udrulning sker ved, at Portainer følger `main` i app-repoet og læser `deploy/docker-compose.yml`. Workflows må aldrig kalde Portainer.
- **Kendte kaldere:** ba-nsp-data, ba-fritidsportalen, ba-xflow-sql-tool, ba-bfo-fagligt-ledelsestilsyn.
