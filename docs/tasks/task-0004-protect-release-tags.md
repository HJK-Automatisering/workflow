---
nummer: task-0004
titel: Uforanderlige versionstags via protect_release_tags
status: planlagt
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
### Hvad er ikke lavet, og hvorfor
### Uklart
