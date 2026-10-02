"""Saet image-feltet paa en eller flere services i en compose-fil, og roer intet andet.

Bruges af .github/workflows/deploy-update.yaml og kan koeres lokalt:

    .venv\\Scripts\\python.exe scripts\\update_compose_image.py <fil> <services> <image:tag>

`<services>` er et servicenavn, eller flere adskilt af komma (`web,worker`).
Mellemrum omkring kommaerne tolereres. Alle services skal pege paa samme
image-navn som det nye - se vaernet nedenfor.

Exit-koder, saa workflowet kan skelne:

    0  mindst ét image-felt blev aendret og filen skrevet
    3  alle angivne services stod allerede paa den oenskede vaerdi; filen
       er ikke roert
    1  fejl: filen, en service eller et image-felt findes ikke, filen kunne
       ikke laeses som YAML, eller en service peger paa et andet image-navn
       end det nye
    2  forkerte argumenter (argparse)

Alt eller intet: alle services kontrolleres foerst, og filen skrives kun hvis
ingen af dem fejler. En halvt opdateret compose-fil paa main ville ellers
udrulle noget, ingen har bedt om.

Vaernet: det nuvaerende image-navn (uden tag og digest) skal vaere lig det nye
image-navn (uden tag). En slaafejl i servicenavnet maatte ellers erstatte fx
databasens image med appens, og et compose-tjek fanger det ikke. Et tilsigtet
skift af image-navn rettes i haanden paa main.

Pr. service skrives én linje til stdout: `<service>: <gammel version> -> <ny
version>` eller `<service>: staar allerede paa <ny version>`. Ved exit 0
skrives til sidst en linje
`changed=<service>,<service>` med de services der blev aendret, i den
raekkefoelge de blev angivet, saa workflowet kan saette dem i commit-beskeden.

Hvorfor ruamel.yaml og ikke en fuld genskrivning: filen laeses og skrives af
Portainer og af mennesker, og den skal se ud som foer, ogsaa i kommentarer,
indrykning og anfoerselstegn. ruamel.yaml bruges derfor til det, den er god
til - at finde den praecise linje og kolonne for `services.<service>.image`
uanset indrykning og dubletter af ordet `image` andre steder - og selve
aendringen laves som en tekstudskiftning paa netop den linje. Resten af
filen roeres ikke, byte for byte. Resultatet laeses ind igen bagefter, saa
en skaev udskiftning aldrig bliver skrevet ud i stilhed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

EXIT_CHANGED = 0
EXIT_ERROR = 1
EXIT_UNCHANGED = 3


def fejl(path: str, besked: str, line: int | None = None) -> int:
    """Skriv en fejl i det format GitHub Actions viser i oversigten."""
    sted = f'file={path}' + (f',line={line}' if line is not None else '')
    print(f'::error {sted}::{besked}', file=sys.stderr)
    return EXIT_ERROR


def parse_services(tekst: str) -> list[str]:
    """Del `web, worker` op i navne. Tomme led (`web,,worker`) ignoreres."""
    return [s.strip() for s in tekst.split(',') if s.strip()]


def image_name(ref: str) -> str:
    """Image-referencen uden tag og digest.

    `host:5000/org/app:1.2@sha256:...` -> `host:5000/org/app`. Kun sidste
    sti-led kan have et tag, saa et kolon i registry-porten roerer vi ikke.
    """
    ref = ref.split('@', 1)[0]
    sti, skille, sidste = ref.rpartition('/')
    if ':' in sidste:
        sidste = sidste.rsplit(':', 1)[0]
    return sti + skille + sidste


def image_version(ref: str) -> str:
    """Det der staar efter image-navnet: tagget, evt. med digest. Hele
    referencen hvis der hverken er tag eller digest, saa loglinjen aldrig
    bliver tom."""
    rest = ref[len(image_name(ref)):].lstrip(':')
    return rest or ref


def find_image_node(doc, service: str):
    """Returner (mapping, (linje, kolonne)) for `services.<service>.image`.

    Linje og kolonne er 0-baserede og peger paa starten af vaerdien - ved en
    citeret skalar paa selve anfoerselstegnet.
    """
    services = doc.get('services') if hasattr(doc, 'get') else None
    if not services or not hasattr(services, 'get'):
        raise KeyError('filen har ingen `services:`-sektion')
    svc = services.get(service)
    if svc is None:
        kendte = ', '.join(sorted(str(k) for k in services)) or '(ingen)'
        raise KeyError(f'servicen `{service}` findes ikke. Kendte services: {kendte}')
    if not hasattr(svc, 'get') or 'image' not in svc:
        raise KeyError(f'servicen `{service}` har intet `image:`-felt. Scriptet tilfoejer ikke '
                       f'feltet - det skal staa i filen i forvejen.')
    if not isinstance(svc['image'], str):
        raise KeyError(f'`services.{service}.image` er ikke en tekstvaerdi')
    return svc, svc.lc.value('image')


def scalar_span(line: str, col: int) -> tuple[int, int, str]:
    """Find hvor skalaren paa `line` slutter, og hvilket anfoerselstegn den bruger.

    Returnerer (start, slut, citat), hvor citat er '', '"' eller "'".
    """
    rest = line[col:]
    if rest[:1] in ('"', "'"):
        q = rest[0]
        i = 1
        while i < len(rest):
            if q == "'" and rest[i] == "'" and rest[i + 1:i + 2] == "'":
                i += 2  # '' er et escaped ' i enkeltciterede skalarer
                continue
            if q == '"' and rest[i] == '\\':
                i += 2
                continue
            if rest[i] == q:
                return col, col + i + 1, q
            i += 1
        raise ValueError('anfoerselstegnet lukkes ikke paa samme linje')
    # Ucitéret: skalaren slutter foer en kommentar (` #`) eller ved linjeslut.
    slut = len(rest.rstrip('\r\n'))
    for i in range(len(rest)):
        if rest[i] == '#' and (i == 0 or rest[i - 1] in ' \t'):
            slut = i
            break
    while slut > 0 and rest[slut - 1] in ' \t':
        slut -= 1
    return col, col + slut, ''


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Saet services.<service>.image paa en eller flere services i en compose-fil '
                    'uden at aendre andet.')
    parser.add_argument('compose_path', help='sti til compose-filen')
    parser.add_argument('services', help='navn paa servicen under services:, eller flere adskilt '
                                         'af komma, fx web,worker')
    parser.add_argument('image', help='ny vaerdi, fx ghcr.io/org/app:1.2.3')
    args = parser.parse_args(argv)

    services = parse_services(args.services)
    if not services:
        parser.error('der skal angives mindst ét servicenavn')
    dubletter = [s for s in dict.fromkeys(services) if services.count(s) > 1]
    if dubletter:
        parser.error(f'servicen `{dubletter[0]}` er angivet mere end én gang')

    path = Path(args.compose_path)
    if not path.is_file():
        return fejl(args.compose_path, f'compose-filen `{args.compose_path}` findes ikke')

    # newline='' bevarer CRLF/LF som de staar, saa en Windows-fil ikke bliver
    # skrevet om til LF bare fordi image-feltet blev rettet.
    with open(path, encoding='utf-8', newline='') as fh:
        tekst = fh.read()
    linjer = tekst.splitlines(keepends=True)

    yaml = YAML()
    try:
        doc = yaml.load(tekst)
    except YAMLError as e:
        return fejl(args.compose_path, f'filen kunne ikke laeses som YAML: {e}')

    nyt_navn = image_name(args.image)

    # Foerste gennemloeb: find og kontrollér alle services uden at skrive.
    # Fejler én, er filen ikke roert - alt eller intet.
    udskiftninger: list[tuple[str, int, int, int, str, str]] = []
    for service in services:
        try:
            svc, (lnr, col) = find_image_node(doc, service)
        except KeyError as e:
            return fejl(args.compose_path, str(e).strip("'"))

        gammel = svc['image']
        gammelt_navn = image_name(gammel)
        if gammelt_navn != nyt_navn:
            return fejl(args.compose_path,
                        f'servicen `{service}` peger paa imaget `{gammelt_navn}`, men der skulle '
                        f'skrives `{nyt_navn}`. Er det en slaafejl i inputtet service? Er skiftet '
                        f'af image-navn tilsigtet, saa ret linjen i haanden paa main foerst.',
                        lnr + 1)

        if gammel == args.image:
            continue

        linje = linjer[lnr]
        try:
            start, slut, citat = scalar_span(linje, col)
        except ValueError as e:
            return fejl(args.compose_path,
                        f'kunne ikke afgraense vaerdien af `image` paa `{service}`: {e}', lnr + 1)

        if linje[start:slut].strip(citat) != gammel:
            # Multilinje-skalar, alias eller noget andet vi ikke genkender. Hellere
            # stoppe end skrive noget halvt.
            return fejl(args.compose_path,
                        f'vaerdien paa linjen (`{linje[start:slut]}`) svarer ikke til den YAML '
                        f'laeste (`{gammel}`). Ret image-feltet til en enkelt linje og proev igen.',
                        lnr + 1)
        udskiftninger.append((service, lnr, start, slut, citat, gammel))

    ny_version = image_version(args.image)
    if not udskiftninger:
        for service in services:
            print(f'{service}: staar allerede paa {ny_version}')
        return EXIT_UNCHANGED

    # Andet gennemloeb: skriv alle linjer i hukommelsen. Hver service har sin
    # egen linje, saa udskiftningerne kan ikke paavirke hinanden.
    for _service, lnr, start, slut, citat, _gammel in udskiftninger:
        linje = linjer[lnr]
        linjer[lnr] = linje[:start] + citat + args.image + citat + linje[slut:]
    ny_tekst = ''.join(linjer)

    # Efterkontrol: den nye fil skal parse, og hvert felt skal have faaet den
    # vaerdi vi bad om. Ellers roerer vi ikke filen.
    try:
        ny_doc = yaml.load(ny_tekst)
    except YAMLError as e:
        return fejl(args.compose_path, f'resultatet kunne ikke laeses tilbage: {e}')
    for service, lnr, *_rest in udskiftninger:
        try:
            faktisk = ny_doc['services'][service]['image']
        except (KeyError, TypeError) as e:
            return fejl(args.compose_path, f'resultatet kunne ikke laeses tilbage: {e}', lnr + 1)
        if faktisk != args.image:
            return fejl(args.compose_path,
                        f'efter udskiftning staar image paa `{service}` paa `{faktisk}`, '
                        f'ikke `{args.image}`', lnr + 1)

    with open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(ny_tekst)

    aendrede = {service: gammel for service, *_rest, gammel in udskiftninger}
    for service in services:
        if service in aendrede:
            print(f'{service}: {image_version(aendrede[service])} -> {ny_version}')
        else:
            print(f'{service}: staar allerede paa {ny_version}')
    print('changed=' + ','.join(s for s in services if s in aendrede))
    return EXIT_CHANGED


if __name__ == '__main__':
    sys.exit(main())
