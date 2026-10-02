# Beslutningslog

Append-only. Nyeste øverst. Én linje pr. beslutning.

**Ejes af `architect`.** Dens tråd er den eneste samtale i modellen, og loggen er det eneste spor af den der overlever tråden. Hver beslutning truffet i en `architect`-tråd skrives ind, med begrundelse, før tråden lukkes.

Her hører også **afvisninger**: et fund der ikke bliver en opgave, skal have sin begrundelse her. Ellers er det et fund der forsvandt.

`Nr.` er nummeret beslutningen hører til — `task-0042`, `test-0003` — eller `—` hvis den gælder projektet som helhed.

| Dato | Nr. | Beslutning | Begrundelse | Rolle |
|---|---|---|---|---|
| 2026-10-02 | task-0004 | Opgaven er bygget; nyt input, nyt trin, to-grenet besked, validering og README | Alle punkter under Færdig når holder ved læsning af diffen; run-blokke og valideringens Python-blokke kørt lokalt | architect |
| 2026-10-02 | task-0004 | Beskeden om efterladt image skifter kun, når tjek-trinnet faktisk værnede, ikke på inputtet alene | Ellers lover den en afvisning, der ikke sker på grene og forhåndstags. Developers forslag, godkendt | architect |
| 2026-10-02 | task-0006 | Fund fra task-0004 lagt i task-0006: README-afsnittet Tilbagerulning siger som faktum, at versionstags aldrig overskrives; det holder kun med inputtet slået til | Én sætning i README; task-0006 rører afsnittene omkring alligevel | architect |
| 2026-10-02 | task-0006 | Værn mod forkert image-navn i deploy-update, også ved én service | En slåfejl i `service` ville ellers erstatte fx databasens image med appens; compose-tjekket fanger det ikke. Prisen er én manuel rettelse ved tilsigtet navneskift. Godkendt af mennesket | architect |
| 2026-10-02 | task-0006 | Flere services i det eksisterende input `service`, adskilt af komma; alt eller intet; delvis idempotens | Nyt input ved siden af ville kræve at `service` stadig sættes, fordi det er påkrævet. Halvt opdateret fil på main afvist | architect |
| 2026-10-02 | task-0005 | Lint bygges efter task-0006 | Begge rører deploy-update.yaml, eksempelfilen og README; lint-testene skal se eksempelfilen med `worker` | architect |
| 2026-10-02 | — | task-0003 udgives ikke som v1.1.1 | Kun README og eksempelfil; README læses fra main, ikke fra et tag. Næste minor-tag samler task-0004 til task-0006 | architect |
| 2026-10-02 | task-0003 | Opgaven er bygget; README og eksempelfil | Alle punkter under Færdig når holder ved læsning af diffen; scripttesten er grøn lokalt | architect |
| 2026-10-02 | task-0005 | To fund fra task-0003 lagt i task-0005: kommentaren i deploy-update.yaml ved sanity-trinnet og kommentaren i .gitignore siger stadig, at Portainer genererer stack.env | Sanity-trinnet erstattes alligevel i task-0005; .gitignore-kommentaren er én linje, der hører med i samme oprydning | architect |
| 2026-10-02 | task-0005 | Lint-jobbet ligger i samme caller-workflow og kører på alle pull requests uden stifilter | Én skabelonfil at vedligeholde; stifilter pr. job kræver en tredjeparts-action. Separat caller-fil afvist. Godkendt af mennesket | architect |
| 2026-10-02 | task-0005 | Ingen literaler under `environment:`; regler `hemmelighed`, ny `env-vaerdi`, og `env-fil` forbyder `env_file` helt | Portainer skriver ikke stack.env for Git-stacks; princippet om ingen værdier i compose-filen består, og en forbindelsesstreng under en neutral nøgle må ikke slippe igennem. Alternativ B afvist. Godkendt af mennesket | architect |
| 2026-10-02 | task-0005 | Lint blokerer udrulningen i deploy-jobbet; mennesket kører scriptet mod de kendte kaldere før `v1` flyttes | Opgavebeskrivelsen siger erstat sanity-trinnet; en app der aldrig har set reglerne må ikke få en rød release uventet | architect |
| 2026-10-02 | task-0005 | Regelnavnet `env-vaerdi` er nyt i forhold til agenternes deploy-kontrakt | Agenter-repoet opdateres af mennesket i en anden tråd; regelnavne deles mellem lint og kontrakt | architect |
| 2026-10-02 | — | Fase 2 delt i task-0004 (protect_release_tags) og task-0005 (compose-lint) | Uafhængige leverancer; opgavebeskrivelsen siger selv, at tag-beskyttelsen kan trækkes ud | architect |
| 2026-10-02 | task-0003 | Fund fra migreringen: Portainer genererer ikke stack.env for Git-stacks; README rettes som egen opgave, workflows urørt | Stackens variabler substitueres i compose-filen; sanity-trinnets tomme stack.env er harmløs og erstattes af lint i task-0005 | architect |
| 2026-10-02 | — | Emnet flere services pr. kald er et reelt behov | ba-bfo-fagligt-ledelsestilsyn kørte to deploy-jobs for ét image ved v0.2.0 | architect |
| 2026-10-02 | task-0001 | Fase 1 bekræftet i drift på ba-bfo-fagligt-ledelsestilsyn: release udrullet via Portainer, rc-tag bygget uden udrulning, gen-kørsel og git revert virker | Menneskets testkørsel efter v1.1.0. Fase 2 kan påbegyndes | architect |
| 2026-10-02 | — | v1.1.0 udgivet og v1 flyttet dertil | Fase 1 er additiv (nyt workflow, nyt output, README); kaldere på @v1 får det uden ændring. Valideringen var grøn før tagget | architect |
| 2026-10-01 | task-0002 | Opgaven er bygget; README, CLAUDE.md og kommentaren ved signeringstrinnet | Alle punkter under Færdig når holder ved læsning mod workflow-filerne; caller-eksemplet er parset og matcher inputs og outputs | architect |
| 2026-10-01 | task-0002 | Jobbet i caller-eksemplet hedder `build`; skabelonens `publish` omdøbes af agenter-tråden | Navnet siger, hvad jobbet gør; projekterne opdateres alligevel for at få deploy-jobbet | architect |
| 2026-10-01 | task-0002 | Fund om bagud CLAUDE.md rettet inden for opgaven, ikke som nyt nummer | Opgaven var i gang og ejede allerede CLAUDE.md-ændringen; udvidet over delelinjen | architect |
| 2026-10-01 | — | Emnet "Udgivelsesprocedure for dette repo" fjernet fra BOARD | Dækket af README-afsnittet "Udgivelse af dette repo" i task-0002 | architect |
| 2026-10-01 | — | Servernavnet fjernet fra docs/prompt-workflow-gitops-v2.md, og den upushede kickoff-commit rettet | Repoet er offentligt; forretningsspecifikke værdier må ikke stå i docs/, og historik kan ikke gøres privat bagefter. Kun lokal historik blev omskrevet. Godkendt af mennesket | architect |
| 2026-10-01 | task-0001 | Opgaven er bygget; de to menneskelige testpunkter efterprøves ved første rigtige release | Ni lokale punkter dokumenteret med kørsler; testkørslen kræver udgivelse og compose-fil i app-repoet og står som emne på BOARD | architect |
| 2026-10-01 | task-0001 | Scriptet finder med ruamel og erstatter tekst på én linje; fuld ruamel-dump afvist | Resten af filen forbliver byte for byte uændret; en dump kan ændre indrykning og linjebredde. Godkendt af mennesket | architect |
| 2026-10-01 | task-0001 | `validate.yaml` udløses også af `scripts/**`, `tests/**` og `requirements.txt` | Scripttesten skal køre, når scriptet ændres. Udvidelse ud over opgaven, godkendt | architect |
| 2026-10-01 | task-0001 | deploy-update logger fast ind på ghcr.io | Eneste registry i brug; udledning af image-navnet er ikke umagen værd nu. Nævnes i README | architect |
| 2026-10-01 | task-0001 | Developer brugte gh-tokenet til ét læsende kald efter signaturens bundle-blob ud over login og manifest-opslag | Certifikatet lå ikke i manifestet (cosign v3 bundle-format). Inden for ånden, uden for ordlyden; rapporteret til mennesket, logget ud bagefter | architect |
| 2026-10-01 | task-0002 | To fund fra task-0001 lagt i task-0002: cosign v3 referrers-format i oprydningsafsnittet, og den løse verifikationsregel i kommentar og README rettes | Dokumentation og kommentarer; hører i README-opgaven, ikke i et nyt nummer | architect |
| 2026-10-01 | task-0001 | Developer må logge ind på GHCR med menneskets lokale gh-token for at læse et signaturcertifikat | Kun lokalt og kun under opgaven; identiteten afgør cosign-reglen, og det skal vides før udgivelse som v1.1.0 | architect |
| 2026-10-01 | task-0001 | `.venv` oprettes i repoet; `requirements.txt` er eneste afhængighedsfil | Repoet får Python-scripts; kontrakten kræver virtuelt miljø til lokale kald. Intet andet Python-tilbehør | architect |
| 2026-10-01 | task-0001 | `requirements.txt`, pip i Dependabot og `.venv` trukket frem fra fase 2 | ruamel.yaml ankommer med deploy-update, så afhængighedsstyringen skal følge med nu | architect |
| 2026-10-01 | task-0001 | Fase 1 testes på ba-bfo-fagligt-ledelsestilsyn, ikke et demo-repo | Mennesket vil have den første rigtige app med. Compose-fil, caller og Portainer-stack i det repo ligger i andre tråde | architect |
| 2026-10-01 | — | GitOps fase 1 delt i task-0001 (workflows) og task-0002 (README) | README kan først skrives, når workflowets form er endelig; to tråde, én afhængighed | architect |
| 2026-10-01 | — | Der bygges kun på tag-push; ingen `on.push.branches` i caller-eksemplet | Fastholder eksisterende skabelon; deploy-commit kan dermed aldrig udløse en bygning, og `paths-ignore` bortfalder | architect |
| 2026-10-01 | — | Kun `GITHUB_TOKEN` til deploy-commit; ingen App-token, ingen secrets | `main` er ubeskyttet i de berørte repos; reserveløsninger dokumenteres kun i README | architect |
| 2026-10-01 | — | Caller-skabelonen i agenter-repoet opdateres af en anden tråd ud fra README | Mennesket håndterer den bro i agenter-tråden; en hook tjekker, at kaldere matcher nyeste skabelon | architect |
