---
nummer: task-0004
titel: Uforanderlige versionstags via protect_release_tags
status: i-gang
kilde: interview
oprettet: 2026-10-02
---

# task-0004 — Uforanderlige versionstags via protect_release_tags

## Hvad og hvorfor
Compose-filen henviser til imaget med versionstagget alene, fx `:1.4.2`, og tilbagerulning hviler på, at
det tag altid peger på det samme image. I dag kan et build-job køres igen på samme tag, eller et tag kan
slettes og sættes igen, og så overskrives versionstagget i GHCR uden at nogen ser det. Build-workflowet
skal kunne nægte at bygge, når versionstagget allerede findes. Opgavebeskrivelsen: fase 2, krav 12.

## Færdig når
- [ ] Med inputtet slået til stopper en kørsel på et release-tag før bygningen med en dansk fejl, hvis versionstagget allerede findes i registryet, og intet pushes.
- [ ] Med inputtet slået fra, eller på en kørsel der ikke er et release-tag `vX.Y.Z`, er adfærden som i dag.
- [ ] Beskeden om et efterladt image siger, med inputtet slået til, at imaget skal slettes i GHCR eller en ny version tagges, og at gen-kørsel afvises.
- [ ] Valideringen i dette repo kræver det nye input og er grøn.
- [ ] README beskriver inputtet, caller-eksemplet slår det til, og afsnittet om oprydning efter en rød kørsel siger, at gen-kørsel afvises, når inputtet er slået til.

## Sådan bygger vi det
**`.github/workflows/docker-publish.yaml`**
- Nyt input `protect_release_tags`, `type: boolean`, `default: false`. Beskrivelse på dansk: nægter at bygge, hvis versionstagget allerede findes; kræver et nyt versionsnummer.
- Nyt trin *Tjek at versionstagget er ledigt* **efter** `Extract Docker metadata` og **før** `Build and push`. Login er sket før metadata, så opslaget kan læse private pakker. Versionen tages fra `steps.meta.outputs.version`, så tjekket bruger præcis den version metadata-action tagger med.
- Trinnet kører kun når `inputs.protect_release_tags` er sand og `github.ref_type == 'tag'`. Den præcise kontrol af `vX.Y.Z` sker i bash med samme regexp som i `deploy-update.yaml`, fordi GitHub-udtryk ikke har regex. Matcher tagget ikke, skrives en linje om at tjekket springes over, og trinnet afsluttes grønt.
- Opslag: `docker buildx imagetools inspect "${IMAGE}:${VERSION}" --format '{{.Manifest.Digest}}'` med `IMAGE` fra `steps.image.outputs.name`. Lykkes opslaget, findes tagget: `::error::` på dansk med image, tag og digest, og besked om at en ny bygning kræver et nyt versionsnummer, exit 1. Fejler opslaget, printes dets output, og bygningen fortsætter.
- `Rapportér efterladt image`: når inputtet er slået til, lyder beskeden: slet imaget i GHCR (inkl. signatur-artefaktet `sha256-<digest>`), eller tag en ny version; gen-kørsel vil blive afvist. Ellers som i dag.
- Kommentar der forklarer hvorfor: compose-filen peger på tagget, ikke digesten.

**`.github/workflows/validate.yaml`**: `protect_release_tags` tilføjes til de faste inputs for `docker-publish.yaml`.

**`README.md`**
- Inputtabellen for `docker-publish.yaml` får rækken.
- Caller-eksemplet: `with:` under `build` bliver en rigtig blok med `protect_release_tags: true` og en kommentar; de øvrige eksempler bliver stående som kommentarer under den.
- *Oprydning efter en rød kørsel*, punktet *Build-jobbet rødt efter push*: med inputtet slået til kan kørslen ikke genstartes, før imaget og dets signatur-artefakt er slettet, eller der tagges en ny version.
- *Inputs og outputs*: én sætning om, at inputtet er slået fra som standard, så eksisterende kaldere er uberørte, og at skabelonen slår det til.

## Hvad vi ikke rører
- Eksisterende inputs, outputs, tagging-regler, signering og øvrige trin i `docker-publish.yaml`.
- `deploy-update.yaml`, `scripts/`, `tests/`.
- Caller-skabelonen i agenter-repoet; README-eksemplet er forlægget.
- Ingen tags, ingen udgivelse.

## Afhænger af
intet

## Beslutninger
- BESLUTTET: Standard `false` — kontrakten udvides kun additivt; eksisterende kaldere på `v1` må ikke ændre adfærd. Skabelonen slår det til.
- BESLUTTET: Et fejlende opslag regnes som "tagget findes ikke", og output printes — ved første bygning af et nyt repo findes pakken slet ikke, og værnet er mod fejl, ikke mod en modstander. Kun et vellykket opslag stopper kørslen.
- BESLUTTET: Tjekket ligger efter metadata-trinnet og bruger dets `version` — så tjek og tags kan aldrig være uenige om versionen.
- BESLUTTET: Ingen undtagelse og intet input til at tvinge en overskrivning — et versionstag der er pushet forkert, rettes med et nyt nummer, som README allerede siger.

## Åbne punkter

## Indvendinger

---

## Developers noter

### Hvad er lavet

Gren `task-0004-protect-release-tags`, tre commits (`db3ebf1`, `28f182f`, `bbc36b1`) plus denne note. Intet pushet, ingen tags. `docs/BOARD.md`, `docs/decisions/log.md`, task-0005 og task-0006 er ikke rørt og ikke taget med i nogen commit.

**Filer**

- `.github/workflows/docker-publish.yaml`
  - Nyt input `protect_release_tags`, `type: boolean`, `default: false`, dansk beskrivelse. Eksisterende inputs, outputs, tagging-regler, signering og øvrige trin er uændrede.
  - Nyt trin *Tjek at versionstagget er ledigt* (`id: protect`) efter `Extract Docker metadata` og før `Build and push`. `if: inputs.protect_release_tags && github.ref_type == 'tag'`. I bash: samme regexp som i `deploy-update.yaml` (`^v[0-9]+\.[0-9]+\.[0-9]+$`) mod `github.ref_name`; matcher tagget ikke, skrives én linje om at tjekket springes over, exit 0. Ellers `docker buildx imagetools inspect "${IMAGE}:${VERSION}" --format '{{.Manifest.Digest}}'` med `IMAGE` fra `steps.image.outputs.name` og `VERSION` fra `steps.meta.outputs.version`. Lykkes opslaget: `::error::` på dansk med image, tag og digest og besked om at en ny bygning kræver et nyt versionsnummer, exit 1 — intet er pushet på det tidspunkt. Fejler opslaget: dets stderr printes indrykket, og trinnet sætter outputtet `protected=true` og afslutter grønt.
  - *Rapportér efterladt image*: læser `steps.protect.outputs.protected`. Er det `true`, lyder beskeden: slet imaget i GHCR (inkl. signatur-artefaktet `sha256-<digest>`, med den faktiske digest indsat), eller tag en ny version; gen-kørsel vil blive afvist. Ellers beskeden som i dag.
  - Kommentarer på dansk med hvorfor: compose-filen peger på tagget, ikke digesten; tjekket bruger metadata-trinnets version; fejlende opslag regnes som ledigt.
- `.github/workflows/validate.yaml`: `protect_release_tags` tilføjet til de faste inputs for `docker-publish.yaml`.
- `README.md`
  - Inputtabellen for `docker-publish.yaml` har fået rækken, og én sætning under tabellen om at inputtet er slået fra som standard, så eksisterende kaldere er uberørte, og at eksemplet slår det til.
  - Caller-eksemplet: `with:` under `build` er nu en rigtig blok med `protect_release_tags: true` og en kommentar; de øvrige eksempler står som kommentarer under den.
  - *Oprydning efter en rød kørsel*, punktet *Build-jobbet rødt efter push*: med inputtet slået til afvises gen-kørslen; den kan først genstartes når imaget og signatur-artefaktet `sha256-<digest>` er slettet, eller der tagges en ny version.

**Færdig når — efterprøvet lokalt**

| Punkt | Resultat |
|---|---|
| Inputtet slået til, release-tag, versionstagget findes → stop før bygning med dansk fejl, intet pushes | Ja. Trinnets run-blok kørt ordret lokalt med en `docker`-stub der svarer med en digest: `::error::Versionstagget …:1.2.3 findes allerede i registryet og peger på sha256:…`, exit 1. Trinnet ligger før `Build and push`, så intet er pushet |
| Inputtet slået fra, eller ikke et release-tag → adfærd som i dag | Ja. `if:` springer trinnet over når inputtet er falsk eller `ref_type` ikke er `tag` (vurderes af GitHub, ikke efterprøvet lokalt). Bash-grenen kørt med `v1.2.3-rc1`, `main` og `1.2.3`: "er ikke et release-tag … springes over", exit 0, stubben kaldes ikke, intet output sættes. `v1.2.3` og `v12.0.7` matcher. Med en stub der fejler (pakken findes ikke): output printes, exit 0, `protected=true`. Eksisterende kaldere: inputtet er `false` som standard |
| Beskeden om efterladt image, med inputtet slået til | Ja. Begge grene af run-blokken kørt lokalt: med `PROTECTED=true` siges slet imaget i GHCR inkl. `sha256-<hex>`, eller tag en ny version, gen-kørsel afvises; uden er beskeden uændret. Se dog *Uklart* om betingelsen |
| Valideringen kræver det nye input og er grøn | Ja. Begge Python-blokke fra `validate.yaml` kørt lokalt mod repoet: `docker-publish.yaml: ok` med `protect_release_tags` blandt inputs, `deploy-update.yaml: ok`, scripttesten ok. `bash -n` på alle 13 `run:`-blokke i de tre workflows: 0 fejl |
| README: inputtet beskrevet, eksemplet slår det til, oprydningsafsnittet nævner afvist gen-kørsel | Ja. Caller-eksemplets YAML parset med pyyaml: `jobs.build.with == {'protect_release_tags': True}`. Inputtabellen i README og workflowets inputs er samme mængde |

Desuden observeret: et uautentificeret kald af den rigtige `docker buildx imagetools inspect` mod GHCR giver 403, og trinnet regner det som "ledigt" og fortsætter, som besluttet. Det betyder også at et mislykket login på runneren gør værnet virkningsløst i stilhed — bortset fra at opslagets output står i loggen. Det følger af beslutningen om fejlende opslag og er ikke ændret.

pyyaml til den lokale kørsel lagt i scratchpad med `pip install --target` og `PYTHONPATH`; `.venv` indeholder stadig kun `ruamel.yaml`.

### Hvad er ikke lavet, og hvorfor

- **Ikke efterprøvet i GitHub Actions**: `if:`-betingelsen med `inputs.protect_release_tags` (boolean) og `github.ref_type`, det rigtige opslag mod GHCR med `GITHUB_TOKEN`-login på runneren, og at `validate.yaml` er grøn i Actions. Kræver push og udgivelse, som er menneskets skridt. Alle run-blokke er kørt lokalt som beskrevet.
- Caller-skabelonen i agenter-repoet er ikke rørt; README-eksemplet er forlægget, som opgaven siger.

### Uklart

- **Betingelsen for den ændrede besked i *Rapportér efterladt image*.** Opgaven siger "når inputtet er slået til". Jeg har bundet beskeden til at tjek-trinnet faktisk værnede om tagget (`steps.protect.outputs.protected == 'true'`, dvs. inputtet slået til **og** ref er et release-tag `vX.Y.Z` **og** opslaget fandt tagget ledigt) frem for til inputtet alene. Grunden: med inputtet slået til, men på `workflow_dispatch` fra en gren eller på `v1.2.3-rc1`, afvises en gen-kørsel ikke, og beskeden "gen-kørsel vil blive afvist" ville være forkert. I alle tilfælde der matcher *Færdig når* (inputtet slået til, release-tag) er beskeden den nye. Skal det i stedet være inputtet alene, er det én linje (`PROTECTED: ${{ inputs.protect_release_tags }}`) og outputtet i tjek-trinnet kan fjernes.
- **"hvis det findes" om signatur-artefaktet.** Når kørslen er rød efter push, er det typisk signeringen der fejlede, og så findes `sha256-<digest>` ofte ikke. Jeg har tilføjet forbeholdet i fejlbeskeden; README siger det uden forbehold som opgaven foreskriver. Sig til hvis beskeden skal følge opgavens ordlyd præcist.
- **Fund til README (ikke rettet, uden for de afsnit opgaven nævner):** afsnittet *Tilbagerulning* siger "Versionstags overskrives aldrig i GHCR, så det forrige image findes stadig" som et faktum. Det holder nu kun med `protect_release_tags` slået til; uden er det en konvention. Architect afgør om sætningen skal pege på inputtet.
