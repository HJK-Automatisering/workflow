"""Saet image-feltet paa en service i en compose-fil, og roer intet andet.

Bruges af .github/workflows/deploy-update.yaml og kan koeres lokalt:

    .venv\\Scripts\\python.exe scripts\\update_compose_image.py <fil> <service> <image:tag>

Exit-koder, saa workflowet kan skelne:

    0  image-feltet blev aendret og filen skrevet
    3  image-feltet stod allerede paa den oenskede vaerdi; filen er ikke roert
    1  fejl: filen, servicen eller image-feltet findes ikke, eller filen
       kunne ikke laeses som YAML
    2  forkerte argumenter (argparse)

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
        description='Saet services.<service>.image i en compose-fil uden at aendre andet.')
    parser.add_argument('compose_path', help='sti til compose-filen')
    parser.add_argument('service', help='navnet paa servicen under services:')
    parser.add_argument('image', help='ny vaerdi, fx ghcr.io/org/app:1.2.3')
    args = parser.parse_args(argv)

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

    try:
        svc, (lnr, col) = find_image_node(doc, args.service)
    except KeyError as e:
        return fejl(args.compose_path, str(e).strip("'"))

    gammel = svc['image']
    if gammel == args.image:
        print(f'services.{args.service}.image staar allerede paa {args.image}')
        return EXIT_UNCHANGED

    linje = linjer[lnr]
    try:
        start, slut, citat = scalar_span(linje, col)
    except ValueError as e:
        return fejl(args.compose_path, f'kunne ikke afgraense vaerdien af `image`: {e}', lnr + 1)

    if linje[start:slut].strip(citat) != gammel:
        # Multilinje-skalar, alias eller noget andet vi ikke genkender. Hellere
        # stoppe end skrive noget halvt.
        return fejl(args.compose_path,
                    f'vaerdien paa linjen (`{linje[start:slut]}`) svarer ikke til den YAML '
                    f'laeste (`{gammel}`). Ret image-feltet til en enkelt linje og proev igen.',
                    lnr + 1)

    linjer[lnr] = linje[:start] + citat + args.image + citat + linje[slut:]
    ny_tekst = ''.join(linjer)

    # Efterkontrol: den nye fil skal parse, og feltet skal have faaet den
    # vaerdi vi bad om. Ellers roerer vi ikke filen.
    try:
        ny_doc = yaml.load(ny_tekst)
        faktisk = ny_doc['services'][args.service]['image']
    except (YAMLError, KeyError, TypeError) as e:
        return fejl(args.compose_path, f'resultatet kunne ikke laeses tilbage: {e}', lnr + 1)
    if faktisk != args.image:
        return fejl(args.compose_path,
                    f'efter udskiftning staar image paa `{faktisk}`, ikke `{args.image}`', lnr + 1)

    with open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(ny_tekst)
    print(f'services.{args.service}.image: {gammel} -> {args.image}')
    return EXIT_CHANGED


if __name__ == '__main__':
    sys.exit(main())
