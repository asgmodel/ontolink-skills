#!/usr/bin/env python3
"""Generate a UTF-8 discovery sitemap for public repository documentation."""
import argparse
from pathlib import Path
from urllib.parse import quote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'https://github.com/asgmodel/ontolink-skills'
NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'


def documented_paths(root=ROOT):
    paths = [Path('README.md')]
    paths += sorted(path.relative_to(root) for path in (root / 'docs').glob('*.md'))
    paths += sorted(path.relative_to(root) for path in (root / 'skills').rglob('*.md'))
    return sorted(set(paths), key=lambda path: path.as_posix())


def render(root=ROOT):
    ET.register_namespace('', NS)
    tree = ET.Element('{' + NS + '}urlset')
    locations = [REPOSITORY]
    locations += [REPOSITORY + '/blob/main/' + quote(path.as_posix(), safe='/')
                  for path in documented_paths(root) if path != Path('README.md')]
    # Omit speculative priorities, frequencies and lastmod dates.
    for location in locations:
        url = ET.SubElement(tree, '{' + NS + '}url')
        ET.SubElement(url, '{' + NS + '}loc').text = location
    ET.indent(tree)
    return ET.tostring(tree, encoding='utf-8', xml_declaration=True) + b'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'sitemap.xml'
    expected = render()
    if args.check:
        if not path.exists() or path.read_bytes() != expected:
            parser.exit(1, 'Sitemap is stale; run python scripts/generate_sitemap.py\n')
        print('PASS: sitemap covers all skill entry points, references and documentation')
    else:
        path.write_bytes(expected)
        print(path)


if __name__ == '__main__':
    main()
