"""Lint en compose-fil mod reglerne i deploy-kontrakten.

Bruges af .github/workflows/compose-lint.yaml (pull requests) og af
deploy-update.yaml (efter opdateringen af image-feltet, foer commit paa main),
og kan koeres lokalt uden GitHub-kontekst:

    .venv\\Scripts\\python.exe scripts\\compose_lint.py deploy\\docker-compose.yml

Exit-koder:

    0  ingen fejl; advarsler er tilladt
    1  mindst én fejl
    2  forkerte argumenter (argparse)

Raekkefoelge:

    1. Filen laeses som YAML. Kan den ikke det, er det én fejl, og resten
       springes over - reglerne kan ikke tjekkes paa noget der ikke parser.
    2. `docker compose -f <fil> config -q --no-interpolate`. --no-interpolate,
       saa tjekket ikke afhaenger af hvilke variabler der er sat paa den
       maskine der koerer, og ingen stack.env behoeves. Findes docker compose
       ikke (typisk lokalt), springes trinnet over med en advarsel; den fulde
       kontrol sker i GitHub Actions.
    3. Reglerne, pr. service - og for netvaerk paa topniveau.
    4. Undtagelser i topniveau-feltet `x-undtagelser`.

Hver fejl og advarsel skrives paa stderr i det format GitHub Actions viser
som annotation paa filen:

    ::error file=<fil>,line=<n>::[<regel>] <service>: <besked>
    ::warning file=<fil>,line=<n>::[<regel>] <service>: <besked>

Regelnavnet i de kantede parenteser er det samme som i README og i
agenternes deploy-kontrakt, saa fejlen kan rettes uden at laese scriptet.
Fund der ikke hoerer til en regel, bruger `[yaml]`, `[compose]`, `[struktur]`
og `[undtagelse]`.

Undtagelser:

    x-undtagelser:
      - service: web
        regel: bind-mount
        begrundelse: "Leverandoerens image kraever en konfigurationsfil paa denne sti"
        godkendt-af: "Navn Navnesen"
        dato: "2026-10-01"

En gyldig undtagelse goer fejlene for den regel paa den service til
advarsler. Manglende `service`, `godkendt-af` eller `dato`, eller et ukendt
regelnavn, er selv en fejl, og undtagelsen daekker saa intet. En dato aeldre
end et aar giver en advarsel; en undtagelse der ikke rammer nogen fejl, er
doed og giver ogsaa en advarsel. For reglen `eksternt-netvaerk` er `service`
netvaerkets navn, fordi reglen gaelder et netvaerk og ikke en service. Fund
uden service - en committet .env eller stack.env - kan ikke undtages.

Hvorfor ruamel.yaml: den kender linjen for hver noegle og hvert listeelement,
saa fejlen kan pege paa den linje der skal rettes. pyyaml kan ikke det.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.constructor import DuplicateKeyError
from ruamel.yaml.error import YAMLError

EXIT_OK = 0
EXIT_ERROR = 1

# Regelnavnene deles med README og agenternes deploy-kontrakt. Omdoebes et,
# skal det rettes begge steder - og i tests/compose/fejl/<regel>.yml.
REGLER = (
    'build', 'latest', 'privileged', 'docker-sock', 'bind-mount', 'host-adgang',
    'hemmelighed', 'env-vaerdi', 'env-fil', 'restart', 'mem-limit', 'logging',
    'ports', 'container-name', 'eksternt-netvaerk', 'alias',
)

PROXY_NETVAERK = 'nginx-proxy-manager_default'
DOCKER_SOCK = '/var/run/docker.sock'
FLYTBARE_TAGS = ('latest', 'main', 'master', 'stable', 'edge', 'dev', 'nightly', 'lts')
HOST_ADGANG_NOEGLER = ('devices', 'cap_add', 'sysctls', 'security_opt')
HEMMELIG_DELSTRENG = ('PASSWORD', 'PASSWD', 'SECRET', 'TOKEN', 'CREDENTIALS')
HEMMELIG_LED = ('KEY', 'PRIVATE')
ENV_FILNAVNE = ('stack.env', '.env')
UNDTAGELSE_MAKS_ALDER = timedelta(days=365)

# Praecis `${NAVN}` og intet andet. `${NAVN:-x}`, `${NAVN-x}`, `$NAVN` og
# `tekst${NAVN}` falder igennem, saa en vaerdi aldrig kan gemme sig i en
# standardvaerdi.
SUBSTITUTION = re.compile(r'^\$\{[A-Za-z_][A-Za-z0-9_]*\}$')


@dataclass
class Fund:
    regel: str
    emne: str | None   # service eller netvaerk; None for fund paa filniveau
    line: int | None   # 1-baseret; None hvis der ikke er en linje at pege paa
    besked: str
    advarsel: bool = False


def key_line(mapping, key, fallback: int | None = None) -> int | None:
    """1-baseret linje for noeglen `key` i en ruamel-mapping."""
    try:
        return mapping.lc.key(key)[0] + 1
    except (KeyError, AttributeError, TypeError):
        return fallback


def item_line(seq, index: int, fallback: int | None = None) -> int | None:
    """1-baseret linje for element nr. `index` i en ruamel-liste."""
    try:
        return seq.lc.item(index)[0] + 1
    except (KeyError, AttributeError, TypeError, IndexError):
        return fallback


def er_sand(v) -> bool:
    """`true` som YAML-boolean eller som tekst. ruamel laeser YAML 1.2, hvor
    `yes` er en streng - compose selv godtager den, saa det goer vi ogsaa."""
    return v is True or (isinstance(v, str) and v.strip().lower() in ('true', 'yes', 'on'))


def er_substitution(v) -> bool:
    return isinstance(v, str) and SUBSTITUTION.match(v) is not None


def ligner_hemmelighed(noegle: str) -> bool:
    k = noegle.upper()
    if any(s in k for s in HEMMELIG_DELSTRENG):
        return True
    return any(led in HEMMELIG_LED for led in k.split('_'))


def image_tag(ref: str) -> str | None:
    """Tagget i en image-reference, eller None hvis der ikke er et.

    `host:5000/org/app:1.2@sha256:...` -> `1.2`. Kun sidste sti-led kan have
    et tag, saa et kolon i registry-porten taeller ikke.
    """
    ref = ref.split('@', 1)[0]
    sidste = ref.rpartition('/')[2]
    if ':' not in sidste:
        return None
    return sidste.rsplit(':', 1)[1]


def volume_kilde(item) -> tuple[str | None, str | None]:
    """(kilde, type) for et volume i kort eller lang form.

    Kort form `kilde:maal[:tilstand]` giver kilden; `- /data` alene er et
    anonymt volume paa en sti i containeren og har ingen kilde. Lang form
    giver `source` og `type`.
    """
    if isinstance(item, str):
        dele = item.split(':')
        if len(dele) >= 2:
            return dele[0], None
        return None, None
    if isinstance(item, dict):
        kilde = item.get('source')
        typ = item.get('type')
        return (str(kilde) if kilde is not None else None,
                str(typ) if typ is not None else None)
    return None, None


def er_vaertssti(kilde: str) -> bool:
    return kilde.startswith(('/', './', '../'))


def env_poster(env):
    """-> [(noegle, vaerdi eller None, indeks eller None)] for begge former.

    Mapping-form: `NOEGLE: ${NOEGLE}`. Listeform: `- NOEGLE=${NOEGLE}`.
    Indekset er til linjeopslag i listeform; None i mapping-form.
    """
    poster = []
    if isinstance(env, dict):
        for k, v in env.items():
            poster.append((str(k), v, None))
    elif isinstance(env, list):
        for i, item in enumerate(env):
            if not isinstance(item, str):
                poster.append((str(item), None, i))
                continue
            k, sep, v = item.partition('=')
            poster.append((k, v if sep else None, i))
    return poster


def lint_service(navn: str, svc, svc_line: int | None) -> list[Fund]:
    fund: list[Fund] = []

    def fejl(regel: str, besked: str, line: int | None = None) -> None:
        fund.append(Fund(regel, navn, line if line is not None else svc_line, besked))

    # build
    if 'build' in svc:
        fejl('build', 'har `build:`. Imaget bygges og signeres af docker-publish.yaml og '
                      'udrulles som et versionstag - compose-filen peger kun paa et image.',
             key_line(svc, 'build'))

    # latest
    image = svc.get('image')
    if not isinstance(image, str) or not image.strip():
        fejl('latest', 'har intet `image:`-felt. Skriv imaget med et versionstag, fx '
                       '`image: ghcr.io/<org>/<app>:1.2.3`.', key_line(svc, 'image'))
    else:
        tag = image_tag(image)
        line = key_line(svc, 'image')
        if tag is None:
            fejl('latest', f'imaget `{image}` har intet tag og peger dermed paa `latest`, som '
                           f'flytter sig. Skriv et versionstag, fx `:1.2.3`.', line)
        elif tag.lower() in FLYTBARE_TAGS:
            fejl('latest', f'imaget `{image}` har tagget `{tag}`, som flytter sig. Skriv et '
                           f'versionstag, fx `:1.2.3`.', line)
        elif not any(c.isdigit() for c in tag):
            fejl('latest', f'imaget `{image}` har tagget `{tag}` uden et ciffer, saa det kan ikke '
                           f'vaere en version. Skriv et versionstag, fx `:1.2.3`.', line)

    # privileged
    if er_sand(svc.get('privileged')):
        fejl('privileged', 'koerer med `privileged: true`, som giver containeren fuld adgang til '
                           'vaerten. Fjern det.', key_line(svc, 'privileged'))

    # docker-sock og bind-mount. Docker-socketen er ogsaa en bind-mount, men
    # ét volume skal give én fejl, og docker-sock er den praecise.
    volumes = svc.get('volumes')
    if isinstance(volumes, list):
        for i, item in enumerate(volumes):
            line = item_line(volumes, i, svc_line)
            kilde, typ = volume_kilde(item)
            if kilde is not None and kilde.rstrip('/') == DOCKER_SOCK:
                fejl('docker-sock', f'monterer `{DOCKER_SOCK}`, som giver containeren kontrol '
                                    f'over alle containere paa vaerten. Fjern det.', line)
            elif typ == 'bind' or (kilde is not None and er_vaertssti(kilde)):
                fejl('bind-mount', f'monterer stien `{kilde}` fra vaerten. Brug et navngivet '
                                   f'volume, der staar under `volumes:` paa topniveau.', line)

    # host-adgang
    if isinstance(svc.get('network_mode'), str) and svc['network_mode'].strip() == 'host':
        fejl('host-adgang', 'har `network_mode: host`. Al adgang gaar via proxy-netvaerket; '
                            'fjern det.', key_line(svc, 'network_mode'))
    if isinstance(svc.get('pid'), str) and svc['pid'].strip() == 'host':
        fejl('host-adgang', 'har `pid: host`, som giver indsigt i vaertens processer. Fjern det.',
             key_line(svc, 'pid'))
    for noegle in HOST_ADGANG_NOEGLER:
        if noegle in svc:
            fejl('host-adgang', f'har `{noegle}:`, som giver adgang til vaerten ud over det '
                                f'normale. Fjern det, eller skriv en undtagelse.', key_line(svc, noegle))

    # hemmelighed og env-vaerdi: én fejl pr. noegle, hemmelighed vinder.
    env = svc.get('environment')
    for noegle, vaerdi, indeks in env_poster(env):
        if er_substitution(vaerdi):
            continue
        line = item_line(env, indeks, svc_line) if indeks is not None else key_line(env, noegle, svc_line)
        if ligner_hemmelighed(noegle):
            fejl('hemmelighed',
                 f'`{noegle}` ligner en hemmelighed, og vaerdien er ikke praecis `${{NAVN}}`. '
                 f'Skriv `{noegle}=${{{noegle}}}` og saet vaerdien som stackens variabel i '
                 f'Portainer. Standardvaerdier som `${{NAVN:-x}}` er heller ikke tilladt.', line)
        elif vaerdi is None:
            fejl('env-vaerdi',
                 f'`{noegle}` staar uden vaerdi. Skriv `{noegle}=${{{noegle}}}` og saet vaerdien '
                 f'som stackens variabel i Portainer.', line)
        else:
            fejl('env-vaerdi',
                 f'`{noegle}` har en vaerdi skrevet i filen; kun praecis `${{NAVN}}` er tilladt. '
                 f'Skriv `{noegle}=${{{noegle}}}` og saet vaerdien som stackens variabel i '
                 f'Portainer. Standardvaerdier som `${{NAVN:-x}}` er heller ikke tilladt.', line)

    # env-fil (servicedelen; den committede fil tjekkes paa filniveau)
    if 'env_file' in svc:
        fejl('env-fil', 'har `env_file:`. Portainer skriver ingen stack.env for Git-stacks; '
                        'variablerne saettes paa stacken og substitueres ind, hvor der staar '
                        '`${NAVN}`. Fjern `env_file`.', key_line(svc, 'env_file'))

    # restart
    if 'restart' not in svc or svc.get('restart') is None:
        fejl('restart', 'mangler `restart`. Skriv `restart: unless-stopped`, saa containeren kommer '
                        'op igen efter genstart af vaerten.', key_line(svc, 'restart'))
    else:
        r = svc['restart']
        if r is False or (isinstance(r, str) and r.strip().lower() == 'no'):
            fejl('restart', 'har `restart: no`. Skriv `restart: unless-stopped`, saa containeren '
                            'kommer op igen efter genstart af vaerten.', key_line(svc, 'restart'))

    # mem-limit
    har_mem_limit = svc.get('mem_limit') not in (None, '')
    deploy = svc.get('deploy')
    resources = deploy.get('resources') if isinstance(deploy, dict) else None
    limits = resources.get('limits') if isinstance(resources, dict) else None
    har_deploy_limit = isinstance(limits, dict) and limits.get('memory') not in (None, '')
    if not har_mem_limit and not har_deploy_limit:
        fejl('mem-limit', 'mangler en hukommelsesgraense. Skriv `mem_limit: 512m` (eller '
                          '`deploy.resources.limits.memory`), saa en enkelt container ikke kan '
                          'tage hele vaerten.')

    # logging
    logging = svc.get('logging')
    options = logging.get('options') if isinstance(logging, dict) else None
    mangler = [k for k in ('max-size', 'max-file')
               if not (isinstance(options, dict) and options.get(k) not in (None, ''))]
    if mangler:
        line = (key_line(logging, 'options') if isinstance(logging, dict) and 'options' in logging
                else key_line(svc, 'logging'))
        fejl('logging', f'mangler `logging.options.{"` og `logging.options.".join(mangler)}`. Uden '
                        f'dem vokser containerloggen, til disken er fuld. Skriv fx '
                        f'`max-size: "10m"` og `max-file: "3"`.', line)

    # ports
    if 'ports' in svc:
        fejl('ports', 'har `ports:`. Al adgang gaar via Nginx Proxy Manager paa proxy-netvaerket; '
                      'fjern `ports` og saet et alias under `networks`.', key_line(svc, 'ports'))

    # container-name
    if 'container_name' in svc:
        fejl('container-name', 'har `container_name:`, som kolliderer paa tvaers af stacks. Fjern '
                               'det; Docker navngiver containeren efter stack og service.',
             key_line(svc, 'container_name'))

    # alias
    nets = svc.get('networks')
    if isinstance(nets, list):
        for i, net in enumerate(nets):
            if net == PROXY_NETVAERK:
                fejl('alias', f'er paa `{PROXY_NETVAERK}` uden alias. Skriv netvaerket i mapping-form '
                              f'med `aliases:`, saa proxyen kan finde servicen paa et fast navn.',
                     item_line(nets, i, svc_line))
    elif isinstance(nets, dict) and PROXY_NETVAERK in nets:
        spec = nets.get(PROXY_NETVAERK)
        aliases = spec.get('aliases') if isinstance(spec, dict) else None
        if not aliases:
            fejl('alias', f'er paa `{PROXY_NETVAERK}` uden alias. Skriv `aliases:` med mindst et '
                          f'navn, saa proxyen kan finde servicen paa et fast navn.',
                 key_line(nets, PROXY_NETVAERK))

    return fund


def lint_netvaerk(doc) -> list[Fund]:
    fund: list[Fund] = []
    netvaerk = doc.get('networks')
    if not isinstance(netvaerk, dict):
        return fund
    for navn, spec in netvaerk.items():
        if not isinstance(spec, dict):
            continue
        external = spec.get('external')
        # `external: {name: x}` er den gamle form; den taeller ogsaa som ekstern.
        if (er_sand(external) or isinstance(external, dict)) and str(navn) != PROXY_NETVAERK:
            fund.append(Fund('eksternt-netvaerk', str(navn), key_line(netvaerk, navn),
                             f'er et eksternt netvaerk. Kun `{PROXY_NETVAERK}` maa vaere eksternt; '
                             f'alle andre netvaerk hoerer til stacken selv.'))
    return fund


def lint_env_filer(path: Path) -> list[Fund]:
    """Tjek med `git ls-files`, om en stack.env eller .env er committet i det
    repo compose-filen ligger i. Filsystemet duer ikke: en lokal .env ligger
    der med vilje og er ignoreret af git."""
    git = shutil.which('git')
    if git is None:
        return [Fund('env-fil', None, None, 'git findes ikke paa denne maskine; tjekket for en '
                                               'committet stack.env eller .env er sprunget over.',
                     advarsel=True)]
    mappe = str(path.resolve().parent)
    try:
        top = subprocess.run([git, '-C', mappe, 'rev-parse', '--show-toplevel'],
                             capture_output=True, text=True, encoding='utf-8', errors='replace',
                             timeout=30)
        if top.returncode != 0:
            return [Fund('env-fil', None, None, 'compose-filen ligger ikke i et git-repo; tjekket '
                                                   'for en committet stack.env eller .env er '
                                                   'sprunget over.', advarsel=True)]
        rod = top.stdout.strip()
        r = subprocess.run([git, '-C', rod, 'ls-files', '-z'],
                           capture_output=True, text=True, encoding='utf-8', errors='replace',
                           timeout=30)
    except subprocess.TimeoutExpired:
        return [Fund('env-fil', None, None, 'git svarede ikke; tjekket for en committet stack.env '
                                               'eller .env er sprunget over.', advarsel=True)]
    if r.returncode != 0:
        return [Fund('env-fil', None, None, f'`git ls-files` fejlede ({r.stderr.strip()[:200]}); '
                                               f'tjekket for en committet stack.env eller .env er '
                                               f'sprunget over.', advarsel=True)]
    fund = []
    for sti in r.stdout.split('\0'):
        if sti and sti.rsplit('/', 1)[-1] in ENV_FILNAVNE:
            fund.append(Fund('env-fil', None, None,
                             f'`{sti}` er committet i repoet. Variabler og hemmeligheder saettes '
                             f'paa stacken i Portainer og hoerer aldrig i repoet. Fjern filen fra '
                             f'git (`git rm --cached`) og sikr at .gitignore daekker den.'))
    return fund


def compose_tjek(path: Path) -> Fund | None:
    """`docker compose config -q --no-interpolate`. None hvis filen er i orden."""
    docker = shutil.which('docker')
    if docker is None:
        return Fund('compose', None, None, 'docker findes ikke paa denne maskine; compose-tjekket er '
                                               'sprunget over. Det koerer i GitHub Actions.', advarsel=True)
    try:
        version = subprocess.run([docker, 'compose', 'version'], capture_output=True, text=True,
                                 encoding='utf-8', errors='replace', timeout=60)
        if version.returncode != 0:
            return Fund('compose', None, None, 'docker compose findes ikke paa denne maskine; '
                                                   'compose-tjekket er sprunget over. Det koerer i '
                                                   'GitHub Actions.', advarsel=True)
        r = subprocess.run([docker, 'compose', '-f', str(path), 'config', '-q', '--no-interpolate'],
                           capture_output=True, text=True, encoding='utf-8', errors='replace',
                           timeout=120)
    except subprocess.TimeoutExpired:
        return Fund('compose', None, None, 'docker compose svarede ikke inden for tidsgraensen. '
                                               'Koer tjekket igen.')
    if r.returncode == 0:
        return None
    linjer = [l for l in r.stderr.strip().splitlines() if l.strip()]
    aarsag = ' | '.join(linjer[-3:]) if linjer else f'exit {r.returncode}'
    return Fund('compose', None, None, f'docker compose kan ikke laese filen: {aarsag}')


def til_dato(v) -> date | None:
    """`dato` i en undtagelse. ruamel laeser `2026-10-01` som date og
    `"2026-10-01"` som tekst; begge godtages."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        try:
            return date.fromisoformat(v.strip())
        except ValueError:
            return None
    return None


def anvend_undtagelser(doc, fund: list[Fund]) -> list[Fund]:
    """Goer fund daekket af gyldige undtagelser til advarsler, og tilfoejer
    fund for undtagelser der selv er forkerte eller doede."""
    if 'x-undtagelser' not in doc:
        return fund
    undtagelser = doc.get('x-undtagelser')
    top_line = key_line(doc, 'x-undtagelser')
    if not isinstance(undtagelser, list):
        fund.append(Fund('undtagelse', None, top_line,
                         '`x-undtagelser` skal vaere en liste af undtagelser med `service`, `regel`, '
                         '`begrundelse`, `godkendt-af` og `dato`.'))
        return fund

    i_dag = date.today()
    for i, u in enumerate(undtagelser):
        line = item_line(undtagelser, i, top_line)
        if not isinstance(u, dict):
            fund.append(Fund('undtagelse', None, line,
                             'undtagelse nr. %d er ikke en mapping med `service`, `regel`, '
                             '`begrundelse`, `godkendt-af` og `dato`.' % (i + 1)))
            continue

        service = u.get('service')
        regel = u.get('regel')
        godkendt_af = u.get('godkendt-af')
        dato = til_dato(u.get('dato'))
        emne = f'{service}/{regel}' if service is not None and regel is not None else 'nr. %d' % (i + 1)

        gyldig = True
        if not isinstance(service, str) or not service.strip():
            fund.append(Fund('undtagelse', None, line,
                             f'undtagelsen {emne} mangler `service` (servicens navn under `services:`; '
                             f'for `eksternt-netvaerk` netvaerkets navn).'))
            gyldig = False
        if not isinstance(regel, str) or regel not in REGLER:
            fund.append(Fund('undtagelse', None, key_line(u, 'regel', line),
                             f'undtagelsen {emne} har et ukendt regelnavn `{regel}`. Kendte regler: '
                             f'{", ".join(REGLER)}.'))
            gyldig = False
        if not isinstance(godkendt_af, str) or not godkendt_af.strip():
            fund.append(Fund('undtagelse', None, line,
                             f'undtagelsen {emne} mangler `godkendt-af`. En undtagelse skal have et navn '
                             f'paa den der har godkendt den.'))
            gyldig = False
        if dato is None:
            fund.append(Fund('undtagelse', None, key_line(u, 'dato', line),
                             f'undtagelsen {emne} mangler `dato`, eller datoen er ikke paa formen '
                             f'AAAA-MM-DD.'))
            gyldig = False
        if not gyldig:
            continue

        ramt = False
        for f in fund:
            if f.regel == regel and f.emne == service and not f.advarsel:
                f.advarsel = True
                f.besked += f' Undtaget: godkendt af {godkendt_af.strip()} den {dato.isoformat()}.'
                ramt = True
        if not ramt:
            fund.append(Fund('undtagelse', None, line,
                             f'undtagelsen {emne} daekker ingen fejl og kan fjernes.', advarsel=True))
        if i_dag - dato > UNDTAGELSE_MAKS_ALDER:
            fund.append(Fund('undtagelse', None, key_line(u, 'dato', line),
                             f'undtagelsen {emne} er fra {dato.isoformat()} og dermed aeldre end et aar. '
                             f'Afgoer om den stadig gaelder, og saet en ny dato.', advarsel=True))
    return fund


def skriv(path: str, fund: Fund) -> None:
    niveau = 'warning' if fund.advarsel else 'error'
    sted = f'file={path}' + (f',line={fund.line}' if fund.line is not None else '')
    emne = f'{fund.emne}: ' if fund.emne is not None else ''
    print(f'::{niveau} {sted}::[{fund.regel}] {emne}{fund.besked}', file=sys.stderr)


def lint(path: Path) -> list[Fund]:
    with open(path, encoding='utf-8') as fh:
        tekst = fh.read()
    try:
        doc = YAML().load(tekst)
    except (YAMLError, DuplicateKeyError) as e:
        line = getattr(getattr(e, 'problem_mark', None), 'line', None)
        # GitHub viser kun foerste linje af en annotation, saa parserens
        # flerlinjede besked foldes sammen til én.
        return [Fund('yaml', None, line + 1 if line is not None else None,
                     'filen kunne ikke laeses som YAML: ' + ' '.join(str(e).split()))]

    fund: list[Fund] = []
    compose = compose_tjek(path)
    if compose is not None:
        fund.append(compose)

    if not isinstance(doc, dict):
        fund.append(Fund('struktur', None, 1, 'filen er ikke en mapping med `services:` paa topniveau.'))
        return fund
    services = doc.get('services')
    if not isinstance(services, dict) or not services:
        fund.append(Fund('struktur', None, key_line(doc, 'services', 1),
                         'filen har ingen `services:`-sektion med mindst en service.'))
        return fund

    for navn, svc in services.items():
        svc_line = key_line(services, navn)
        if not isinstance(svc, dict):
            fund.append(Fund('struktur', str(navn), svc_line, 'servicen er ikke en mapping.'))
            continue
        fund.extend(lint_service(str(navn), svc, svc_line))

    fund.extend(lint_netvaerk(doc))
    fund.extend(lint_env_filer(path))
    return anvend_undtagelser(doc, fund)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Lint en compose-fil mod reglerne i deploy-kontrakten. Exit 0 uden fejl, '
                    '1 ved fejl, 2 ved forkerte argumenter.')
    parser.add_argument('compose_path', help='sti til compose-filen, fx deploy/docker-compose.yml')
    args = parser.parse_args(argv)

    path = Path(args.compose_path)
    if not path.is_file():
        skriv(args.compose_path, Fund('struktur', None, None,
                                       f'compose-filen `{args.compose_path}` findes ikke.'))
        return EXIT_ERROR

    fund = lint(path)
    fund.sort(key=lambda f: (f.line is None, f.line or 0))
    for f in fund:
        skriv(args.compose_path, f)

    fejl = sum(1 for f in fund if not f.advarsel)
    advarsler = sum(1 for f in fund if f.advarsel)
    if fejl:
        print(f'{args.compose_path}: {fejl} fejl, {advarsler} advarsler')
        return EXIT_ERROR
    print(f'{args.compose_path}: ok ({advarsler} advarsler)')
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
