---
nummer: task-0002
titel: README med caller-eksempel, release- og rollback-vejledning
status: planlagt
kilde: interview
oprettet: 2026-10-01
---

# task-0002 — README med caller-eksempel, release- og rollback-vejledning

## Hvad og hvorfor
Repoet har ingen README. Med task-0001 får det to genbrugelige workflows, og projekterne skal kunne
tage dem i brug uden at læse YAML'en. Caller-skabelonen vedligeholdes i agenter-repoet af en anden
tråd, så README er stedet, det komplette eksempel og vejledningerne står. Baggrund i
`docs/prompt-workflow-gitops-v2.md`, fase 1, krav 8 og 9.

## Færdig når
- [ ] En udvikler kan ud fra README alene sætte et app-repo op til at bygge ved tag og udrulle ved release, uden at åbne workflow-filerne.
- [ ] README beskriver alle inputs og outputs for begge genbrugelige workflows med standardværdier.
- [ ] README beskriver, hvordan en release laves, hvordan den rulles tilbage, og at tilbagerulning ikke omfatter en kørt databasemigrering.
- [ ] README beskriver, at der ingen tilbagemelding er fra Portainer til GitHub, og hvad man derfor skal tjekke efter en release.
- [ ] README har et afsnit om, hvad der skal ændres, hvis `main` beskyttes, og fejlbeskeden fra task-0001 peger på det.
- [ ] README beskriver, hvordan dette repo udgives: nyt minor-tag og flyt af `v1` ved additive ændringer, `v2` ved brud, og at versionstags aldrig flyttes.
- [ ] README har en kort vejledning i at migrere en eksisterende app, der i dag deployes via Portainers web-editor.
- [ ] `CLAUDE.md` henviser til README for kommandoer og udgivelse i stedet for at gentage dem.

## Sådan bygger vi det
`README.md` i roden, på dansk, samme tone som kommentarerne i workflow-filerne. Afsnit i denne rækkefølge:

1. **Hvad repoet er** og hvorfor workflows bor her (SHA-pinning ét sted).
2. **Caller-eksempel**, komplet og kopierbart:
   - `on.push.tags: ['v*.*.*']`, `on.pull_request`, `workflow_dispatch`. **Ikke** `on.push.branches`.
   - `concurrency` på workflow-niveau som i dag (`${{ github.workflow }}-${{ github.ref }}`, `cancel-in-progress: true`).
   - build-jobbet som i dag med `permissions: contents: read, packages: write, id-token: write`.
   - deploy-jobbet med `needs: build`, `if: startsWith(github.ref, 'refs/tags/v') && needs.build.outputs.digest != ''`,
     `permissions: contents: write, packages: read`, egen `concurrency`-gruppe `deploy-${{ github.repository }}` med
     `cancel-in-progress: false`, og `with:` der sender `image`, `digest`, `version` og `service` videre.
   - Bemærkning om, at GitHub kun holder én ventende kørsel i gruppen, så to hurtige releases kan springe den midterste over.
3. **Inputs og outputs** for `docker-publish.yaml` og `deploy-update.yaml`, som tabeller med standardværdi og beskrivelse.
4. **Release:** `git tag v1.2.3` og `git push origin v1.2.3`. Hvad der sker derefter, trin for trin, og hvor lang tid der typisk går, før Portainer poller.
5. **Tilbagerulning:** `git revert` af udrulnings-commit'en på `main`. Forbeholdet om databasemigreringer.
6. **Efter en release:** ingen tilbagemelding fra Portainer; tjek stacken i Portainer. Oprydning efter en rød kørsel.
7. **Migrering af en eksisterende app:** compose-fil i `deploy/`, `env_file: stack.env`, ingen værdier i filen, Git-stack i Portainer med variablerne, første release.
8. **Hvis `main` beskyttes:** bypass-aktør for GitHub Actions; alternativt App-token via `actions/create-github-app-token` (SHA-pinnet) og `secrets:` i workflow og kaldere; ved krav om signerede commits skift til GraphQL `createCommitOnBranch`.
9. **Udgivelse af dette repo** og vedligehold: minor-tag og flyt af `v1`; `v2` ved brud; versionstags flyttes aldrig; `cosign-release` bumpes manuelt, når Dependabot bumper `cosign-installer`; regexp'en for cosign-identitet skal rettes, hvis `docker-publish.yaml` omdøbes; repoet skal forblive offentligt, fordi kalderne checker scripts ud herfra.

Fund fra task-0001, der skal med:
- Signaturer fra cosign v3 ligger som OCI referrers med fallback-tag `sha256-<digest>` (uden `.sig`), og certifikatet
  står i bundle-blobben, ikke i manifestet. Skriv det i afsnittet om oprydning efter en rød kørsel: slettes et image i GHCR,
  skal signatur-artefaktet også væk, og det hedder ikke `.sig`.
- Vis den stramme verifikationsregel i README (identitet `^https://github\.com/HJK-Automatisering/workflow/\.github/workflows/docker-publish\.yaml@refs/tags/v`
  plus `--certificate-github-workflow-repository <repo>`), ikke den løse `^https://github\.com/ORG/`.
- Ret kommentaren i `.github/workflows/docker-publish.yaml` ved signeringstrinnet, så den viser samme stramme regel.
  Det er den eneste tilladte ændring i en workflow-fil i denne opgave, og den rører kun kommentarer.
- deploy-update logger fast ind på ghcr.io; nævn det ved inputtet `image`.

Kommandoer i PowerShell-venlig form: én pr. linje, ingen `&&`.
Ingen forretningsspecifikke værdier: ingen servernavne, ingen interne adresser. Portainer-serveren omtales som "den interne Docker-server".

`CLAUDE.md`: afsnittene *Kommandoer* og udgivelse forkortes til en henvisning til README.

## Hvad vi ikke rører
- Ingen workflow-filer ud over kommentaren ved signeringstrinnet i `docker-publish.yaml` (se ovenfor). Dokumentationen beskriver det, task-0001 byggede; afviger den, er det en indvending, ikke en rettelse.
- Caller-skabelonen i agenter-repoet. README-eksemplet er forlægget, som den anden tråd kopierer fra.
- Ingen tags oprettes eller flyttes.

## Afhænger af
task-0001

## Beslutninger
- BESLUTTET: README er det komplette caller-eksempel — skabelonen i agenter-repoet opdateres af en anden tråd ud fra README, så der kun er ét forlæg at holde ajour.
- BESLUTTET: Reserveløsninger ved beskyttet `main` dokumenteres, implementeres ikke — intet behov i dag; kode uden brug rådner.

## Åbne punkter

## Indvendinger

---

## Developers noter

### Hvad er lavet
### Hvad er ikke lavet, og hvorfor
### Uklart
