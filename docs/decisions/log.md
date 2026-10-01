# Beslutningslog

Append-only. Nyeste øverst. Én linje pr. beslutning.

**Ejes af `architect`.** Dens tråd er den eneste samtale i modellen, og loggen er det eneste spor af den der overlever tråden. Hver beslutning truffet i en `architect`-tråd skrives ind, med begrundelse, før tråden lukkes.

Her hører også **afvisninger**: et fund der ikke bliver en opgave, skal have sin begrundelse her. Ellers er det et fund der forsvandt.

`Nr.` er nummeret beslutningen hører til — `task-0042`, `test-0003` — eller `—` hvis den gælder projektet som helhed.

| Dato | Nr. | Beslutning | Begrundelse | Rolle |
|---|---|---|---|---|
| 2026-10-01 | task-0001 | Developer må logge ind på GHCR med menneskets lokale gh-token for at læse et signaturcertifikat | Kun lokalt og kun under opgaven; identiteten afgør cosign-reglen, og det skal vides før udgivelse som v1.1.0 | architect |
| 2026-10-01 | task-0001 | `.venv` oprettes i repoet; `requirements.txt` er eneste afhængighedsfil | Repoet får Python-scripts; kontrakten kræver virtuelt miljø til lokale kald. Intet andet Python-tilbehør | architect |
| 2026-10-01 | task-0001 | `requirements.txt`, pip i Dependabot og `.venv` trukket frem fra fase 2 | ruamel.yaml ankommer med deploy-update, så afhængighedsstyringen skal følge med nu | architect |
| 2026-10-01 | task-0001 | Fase 1 testes på ba-bfo-fagligt-ledelsestilsyn, ikke et demo-repo | Mennesket vil have den første rigtige app med. Compose-fil, caller og Portainer-stack i det repo ligger i andre tråde | architect |
| 2026-10-01 | — | GitOps fase 1 delt i task-0001 (workflows) og task-0002 (README) | README kan først skrives, når workflowets form er endelig; to tråde, én afhængighed | architect |
| 2026-10-01 | — | Der bygges kun på tag-push; ingen `on.push.branches` i caller-eksemplet | Fastholder eksisterende skabelon; deploy-commit kan dermed aldrig udløse en bygning, og `paths-ignore` bortfalder | architect |
| 2026-10-01 | — | Kun `GITHUB_TOKEN` til deploy-commit; ingen App-token, ingen secrets | `main` er ubeskyttet i de berørte repos; reserveløsninger dokumenteres kun i README | architect |
| 2026-10-01 | — | Caller-skabelonen i agenter-repoet opdateres af en anden tråd ud fra README | Mennesket håndterer den bro i agenter-tråden; en hook tjekker, at kaldere matcher nyeste skabelon | architect |
