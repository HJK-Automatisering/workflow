# workflow

Genbrugelige GitHub Actions-workflows for HJK-Automatisering. Projekternes egne
workflows kalder dem med `uses: HJK-Automatisering/workflow/.github/workflows/<fil>@v1`,
så SHA-pinnede actions kan bumpes ét sted. Repoet er offentligt; app-repoerne er private.

Procesregler står i `AGENTS.md`. Åbent arbejde står på `docs/BOARD.md`.

## Stak

- GitHub Actions (YAML). Alle actions pinnet til commit-SHA med versionskommentar.
- Python 3 i `run:`-trin til validering, kun `pyyaml`. Ingen tredjeparts-actions ud over Docker og sigstore.
- cosign v3.1.3 til keyless signering af images mod GHCR.
- Dependabot bumper actions ugentligt, grupperet `docker` og `sigstore`.

## Kommandoer

Der er ingen lokal build- eller testkommando. Repoet indeholder kun workflows.

- **Validér:** Kører automatisk i GitHub Actions via `validate.yaml` på PR'er og push til `main`, der rører `.github/workflows/**`. Kan startes manuelt under Actions. Ingen lokal ækvivalent endnu; se BOARD.
- **Udgiv en ny version** (additive ændringer, der ikke bryder kaldere):

  ```
  git tag v1.X.Y && git push origin v1.X.Y
  git tag -f v1 && git push -f origin v1
  ```

  Versionstags (`v1.X.Y`) flyttes aldrig. Kun `v1` flyttes. Fjernede inputs/outputs eller ændret standardadfærd kræver `v2`.

## Mappestruktur

| Sti | Hvad |
|---|---|
| `.github/workflows/docker-publish.yaml` | Genbrugeligt build-, push- og signeringsworkflow. Outputs `digest`, `version`, `tags` |
| `.github/workflows/validate.yaml` | Strukturvalidering af de genbrugelige workflows. Kører kun i dette repo |
| `.github/dependabot.yml` | Bumper SHA-pinnede actions |
| `.gitattributes` | LF i alt, fordi `run:`-blokke er shell |
| `docs/` | Tavle, beslutningslog og rapporter efter `AGENTS.md` |

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
