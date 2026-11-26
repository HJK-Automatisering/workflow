---
nummer: task-0011
titel: compose-lint: proxyens netværk hedder proxy
status: afsluttet
kilde: interview
oprettet: 2026-11-26
---

# task-0011 — compose-lint: proxyens netværk hedder proxy

## Hvad og hvorfor
Proxyens netværk skifter navn fra `nginx-proxy-manager_default` til `proxy`.
Beslutningen er truffet i `docker-host`:

- Proxyens stak i Portainer skal låses til administratorer. Det kan den ikke i
  dag, fordi `nginx-proxy-manager_default` er oprettet af proxyens stak og
  derfor regnes for en del af den. Låses stakken, kan andre stakke ikke komme
  på netværket.
- Indtil da er proxyens stak delt med de teams, der har stakke bag proxyen, og
  de kan stoppe og ændre den.
- `proxy` er oprettet direkte på værten uden en stak. Det findes allerede, og
  proxyen står på begge netværk.
- Stakkene flytter over til `proxy`. Det gamle netværk lukkes på en dato, der
  ikke er fastsat endnu.

Lint er det første skridt i omdøbningen. Fra udgivelsen er `proxy` det eneste
tilladte navn.

## Færdig når
- [ ] `PROXY_NETVAERK` i `scripts/compose_lint.py` er `proxy`. Et eksternt netværk `proxy` består, og reglen `alias` gælder services på `proxy`.
- [ ] Det gamle navn giver en fejl med regelnavnet `eksternt-netvaerk` for hver linje, hvor det står: nøglen under `networks:` på topniveau og hver services henvisning til netværket. Hver fejl har linjenummeret og siger, at `nginx-proxy-manager_default` skal rettes til `proxy` på netop den linje.
- [ ] Det gamle navn fanges også, når det står som `name:` eller `external.name` på et eksternt netværk med en anden nøgle.
- [ ] Det gamle navn kan ikke undtages. En undtagelse for `eksternt-netvaerk` med `service: nginx-proxy-manager_default` dækker intet, fejlen bliver stående, og beskeden siger, at navnet ikke kan undtages.
- [ ] Alle eksempler i `tests/compose/` bruger `proxy` og bryder kun det, de skal. Et nyt eksempel med det gamle navn og en undtagelse for det dækkes af `validate.yaml`, og valideringen er grøn.
- [ ] README: regeltabellens rækker for `eksternt-netvaerk` og `alias`, punktet under *Undtagelser*, caller-eksemplerne og referencen bruger `proxy`.
- [ ] Scriptet er kørt mod de lokale kloner af app-repoer med `deploy/docker-compose.yml`. Noten siger, hvor mange der fejler på det gamle navn — ikke hvilke, fordi repoet er offentligt.

Efterprøves før udgivelse:

- [ ] `docker-host` har meldt, at et team uden administratorrettigheder kan udrulle en stak på `proxy` i Portainer. Indtil da bliver grenen ikke udgivet, selv om den er bygget.

## Hvad vi ikke rører
- Workflow-filerne `compose-lint.yaml` og `deploy-update.yaml`. Scriptet hentes ved samme SHA.
- Andre netværk, som flere stakke deler, fx `mail-client_default`. De tages for sig.
- `docs/prompt-workflow-gitops-v2.md` og `task-0005`. De er historik.
- Kalderskabelonen og deploy-kontrakten i agenter-repoet. Står det gamle navn der, rettes det i det repo.

## Afhænger af
intet

## Beslutninger
- BESLUTTET: Udgives på `v1` som en bevidst undtagelse, `v1.8.0` med flyt af `v1`. Ikke `v2`. Svar fra mennesket 2026-11-26.
- BESLUTTET: Ingen overgang, hvor det gamle navn kun giver en advarsel. Beslutning i `docker-host`.
- BESLUTTET: Det gamle navn kan ikke undtages i `x-undtagelser`. Svar fra mennesket 2026-11-26.
- BESLUTTET: Ingen ny regel. Fejlen hører under `eksternt-netvaerk`, fordi regelnavnene deles med agenternes deploy-kontrakt.
- BESLUTTET: Udgives først, når Portainer-prøven i `docker-host` er bestået.

## Åbne punkter
intet

## Indvendinger

## Developers noter
<Alt over denne overskrift ejes af architect. Alt under skrives kun af developer.>

Bygget i architects tråd efter menneskets ja, uden for rollerne, fordi developer-skillen ikke var indlæst. Grenen er `task-0011-proxy-network`. Bygget først som task-0010 på en lokal `main`, der var bagud; nummeret var taget på `origin/main` og er skiftet.

**Lavet:**
- `scripts/compose_lint.py`: `PROXY_NETVAERK` er `proxy`, og `GAMMELT_PROXY_NETVAERK` holder det gamle navn. `Fund` har feltet `kan_undtages`, og `daekker` springer fund over, der ikke kan undtages.
- Det gamle navn giver én fejl på `eksternt-netvaerk` pr. linje: nøglen på topniveau (uanset `external`), et `name:` eller `external.name` med det gamle navn under en hvilken som helst nøgle, og hver services henvisning i mapping- og listeform. Services på det gamle navn får ikke også en `alias`-fejl.
- En gyldig undtagelse, der rammer et fund, som ikke kan undtages, giver advarslen "daekker intet, fordi fejlen ikke kan undtages" i stedet for den almindelige om en død undtagelse.
- `tests/compose/`: alle eksempler bruger `proxy`. Nyt eksempel `proxy-gammelt-navn.yml`, hvor de forventede fejllinjer er markeret `# fejl`, og med to undtagelser, der ikke må dække.
- `validate.yaml`: nyt trin 6 i selvtesten af `compose_lint.py`. Det tjekker linjerne, beskeden, at intet blev undtaget, og at der ikke er fejl på andre regler.
- README: regeltabellen, punktet under *Undtagelser* og referencen.

**Efterprøvet lokalt** med `.venv` og Docker (compose v5.1.3): begge scripttests fra `validate.yaml` er grønne.

**Kørt mod lokale kloner af app-repoer:** 15 har `deploy/docker-compose.yml`. Ni er grønne med scriptet på `main` og bliver røde med denne gren, alle ni på det gamle navn. Ingen bruger `proxy` endnu. Én var rød i forvejen af andre grunde. Klonerne kan være bagud for deres `main`.

**Ikke lavet:** Udgivelsen. Den venter på Portainer-prøven i `docker-host` og på menneskets egen test.
