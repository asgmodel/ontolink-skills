"""Check the single distributable package and its embedded phase procedures."""
from pathlib import Path
import json
import re
import subprocess
import sys
from rdflib import Graph
from rdflib.compare import isomorphic
from pyshacl import validate

root = Path(__file__).resolve().parents[1]
core = root / 'skills/ontolink-skills'
catalog = json.loads((root / 'catalog.json').read_text())
bundled = json.loads((core / 'assets/catalog.json').read_text())
assert catalog['installableSkills'] == ['ontolink-skills']
assert sorted(p.parent.name for p in (root / 'skills').glob('*/SKILL.md')) == ['ontolink-skills']
assert len(catalog['skills']) == len(bundled['skills']) == 8
assert len(list((core / 'skills').glob('*/SKILL.md'))) == 7
assert catalog['version'] == bundled['version']
for key in ['policy', 'adapter']:
    assert (root / catalog['projectRules'][key]).is_file(), 'Missing bundled project integration'
    assert (core / bundled['projectRules'][key]).is_file(), 'Invalid package-relative integration'
assert catalog['projectRules']['generatedDirectory'] == '.ontolink'
policy = 'skills/ontolink-skills/.rule/ONTOLOGY-FIRST.md'
for entry in ['AGENTS.md', '.clinerules', '.github/copilot-instructions.md', '.cursor/rules/ontology-first.mdc']:
    pointer = (root / entry).read_text()
    assert policy in pointer and '.ontolinkRule/' not in pointer, entry
for entry, local in zip(catalog['skills'], bundled['skills']):
    skill = root / entry['path']
    assert entry['name'] == local['name']
    assert skill.resolve() == (core / local['path']).resolve(), 'Catalog paths disagree'
    text = (skill / 'SKILL.md').read_text()
    assert text.startswith('---\nname: ' + entry['name'] + '\n') and '\ndescription: ' in text
    assert (skill / 'agents/openai.yaml').is_file(), 'Missing UI metadata'
# A copied package must resolve its own operational Markdown references.
for file in core.rglob('*.md'):
    for value in re.findall(r'\]\(([^)]+)\)', file.read_text()):
        if value.startswith(('https:', 'http:', '#')):
            continue
        target = (file.parent / value.split('#')[0]).resolve()
        assert target.is_relative_to(core.resolve()) and target.is_file(), (file, value)
owl = Graph().parse(core / 'assets/ontolink.owl', format='xml')
ttl = Graph().parse(core / 'assets/ontolink.ttl', format='turtle')
assert isomorphic(owl, ttl), 'Ontology mirror differs'
state = Graph().parse(core / 'assets/examples/project.owl', format='xml')
conforms, _, report = validate(state, shacl_graph=Graph().parse(core / 'assets/shapes.ttl', format='turtle'), ont_graph=owl, inference='none')
if not conforms:
    raise SystemExit(report)
subprocess.run([sys.executable, str(core / 'scripts/mediator.py'), 'validate', '--state', str(core / 'assets/examples/project.owl')], check=True)
for script in [core / 'scripts/test_mediator.py', core / 'scripts/test_project_intelligence.py', root / 'scripts/test_project_rules.py', core / 'scripts/test_project_setup.py']:
    subprocess.run([sys.executable, str(script)], check=True)
subprocess.run([sys.executable, str(root / 'scripts/generate_sitemap.py'), '--check'], check=True)
print(f'PASS: one complete package, seven nested phases, self-contained references, {len(owl)} ontology triples, equivalent Turtle, SHACL, and runtime/setup regression suites')
