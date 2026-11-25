#!/usr/bin/env python3
"""Install or update OntoLink project copies while preserving project knowledge."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from uuid import uuid4

SOURCE = Path(__file__).resolve().parents[1]


def installed_packages(source, catalog):
    """Validate the coordinator and its seven nested phase directories."""
    found = {}
    for entry in catalog['skills']:
        name = entry['name']
        if Path(name).name != name or not name.startswith('ontolink-'):
            raise ValueError('Invalid catalog skill name')
        folder = source if entry['path'] == '.' else safe_path(source, entry['path'])
        skill = folder / 'SKILL.md'
        if not skill.is_file():
            raise ValueError('Incomplete OntoLink package; missing: ' + name)
        match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', skill.read_text(encoding='utf-8'), re.S)
        identity = re.search(r'^name:\s*([a-z0-9-]+)\s*$', match.group(1), re.M) if match else None
        if not identity or identity.group(1) != name:
            raise ValueError('Unexpected bundled skill identity: ' + name)
        if name in found:
            raise ValueError('Duplicate catalog skill name: ' + name)
        found[name] = folder
    return found


def safe_path(root, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or path == Path('.'):
        raise ValueError('Use a nonempty relative path without ..')
    target = root / path
    for parent in target.parents:
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError('Symlink parent is unsupported: ' + str(parent))
    return target


def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def copy(source, target):
    if source.is_symlink():
        target.symlink_to(os.readlink(source), target_is_directory=source.is_dir())
    elif source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)


def run_json(script, *args):
    result = subprocess.run([sys.executable, str(script), *map(str, args)],
                            capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise ValueError(result.stderr.strip())
    return json.loads(result.stdout)


def setup(project, skills_dir='.agents/skills', state_path='knowledge.owl', source=SOURCE):
    project = Path(project).resolve(strict=True)
    source = Path(source).resolve(strict=True)
    if project == source or project.is_relative_to(source):
        raise ValueError('Use an application project outside the distribution checkout')
    if not project.is_dir():
        raise ValueError('Project must be an existing directory')
    core = source
    rules = source / '.rule'
    catalog = json.loads((source / 'assets/catalog.json').read_text(encoding='utf-8'))
    # Check the whole bundle before creating any project files.
    installed_packages(source, catalog)
    state = safe_path(project, state_path)
    if state.is_symlink():
        raise ValueError('Canonical state cannot be a symlink')
    if state_path != 'knowledge.owl' and not state.is_file():
        raise ValueError('An explicit canonical state must already exist')
    if not state.parent.is_dir():
        raise ValueError('Canonical state directory must exist')
    data = safe_path(state.parent, '.ontolink')
    if data.is_symlink():
        raise ValueError('Generated directory cannot be a symlink')
    data.mkdir(exist_ok=True)
    spec = importlib.util.spec_from_file_location('ontolink_setup_adapter', rules / 'ontolink.py')
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    existing = state.read_bytes() if state.exists() else None
    changes = []
    backup = adapter.inside(data, 'backups/' + uuid4().hex)
    backup.mkdir(parents=True)
    applied = []
    # The wrapper's same lock prevents cooperating record/refresh calls during setup.
    with adapter.session_lock(data):
        for folder in ['records', 'proofs', 'artifacts']:
            adapter.inside(data, folder).mkdir(exist_ok=True)
        if state.with_suffix(state.suffix + '.lock').exists():
            raise ValueError('Canonical state has an active writer lock; retry after it finishes')
        if existing is not None:
            run_json(core / 'scripts/mediator.py', 'validate', '--state', state)
        metadata = adapter.inside(data, 'installation.json')
        previous = json.loads(metadata.read_text(encoding='utf-8')) if metadata.exists() else {}
        if not isinstance(previous, dict):
            raise ValueError('Existing installation metadata must be a JSON object')
        with tempfile.TemporaryDirectory(prefix='setup-', dir=data) as temporary:
            stage = Path(temporary)
            target = safe_path(project, str(Path(skills_dir) / 'ontolink-skills'))
            if target == source or target.is_relative_to(source) or source.is_relative_to(target):
                raise ValueError('Installation must not overwrite its source package')
            incoming = stage / 'ontolink-skills'
            shutil.copytree(source, incoming, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            changes.append((target, incoming))
            # Move prior managed phase copies into the bundle, retaining backups.
            for entry in catalog['skills']:
                if entry['role'] != 'phase':
                    continue
                legacy = safe_path(project, str(Path(skills_dir) / entry['name']))
                identity = legacy / 'SKILL.md'
                if legacy.is_symlink() or not identity.is_file():
                    continue
                text = identity.read_text(encoding='utf-8')
                if re.match(r'\A---\r?\nname: ' + re.escape(entry['name']) + r'\r?\n', text):
                    changes.append((legacy, None))
            for rule in sorted(rules.iterdir()):
                if rule.is_file() and rule.suffix in {'.md', '.py'}:
                    incoming = stage / ('rule-' + rule.name)
                    shutil.copy2(rule, incoming)
                    changes.append((safe_path(project, '.rule/' + rule.name), incoming))
            block = ('<!-- ontolink:start -->\n'
                     'Before project work, read `.rule/ONTOLOGY-FIRST.md`. Resolve the installed\n'
                     '`ontolink-skills` coordinator and run `.rule/ontolink.py start` with its actual\n'
                     '`--skill-root` and the canonical `--state` when configured. Keep generated\n'
                     'OntoLink records, proofs and text under the fixed `.ontolink/` directory.\n'
                     '<!-- ontolink:end -->')
            for name in ['AGENTS.md', 'GEMINI.md']:
                target = safe_path(project, name)
                if target.is_symlink():
                    raise ValueError('Host instruction files cannot be symlinks')
                text = target.read_text(encoding='utf-8') if target.exists() else ''
                begin, end = '<!-- ontolink:start -->', '<!-- ontolink:end -->'
                if begin in text or end in text:
                    if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) > text.index(end):
                        raise ValueError('Malformed managed host block: ' + name)
                    text = text[:text.index(begin)] + block + text[text.index(end) + len(end):]
                elif text.startswith('# OntoLink project instructions\n') and len(text.splitlines()) <= 7:
                    text = '# OntoLink project instructions\n\n' + block + '\n'
                else:
                    text = text.rstrip() + ('\n\n' if text else '') + block + '\n'
                text = text.replace('.ontolinkRule/ONTOLOGY-FIRST.md', '.rule/ONTOLOGY-FIRST.md')
                incoming = stage / name
                incoming.write_text(text, encoding='utf-8')
                changes.append((target, incoming))
            adapter.atomic_json(backup / 'manifest.json', {'paths': [str(target.relative_to(project)) for target, _ in changes]})
            if existing is not None:
                shutil.copy2(state, backup / 'knowledge.owl')
            try:
                for index, (target, incoming) in enumerate(changes):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    old = backup / str(index)
                    had_old = target.exists() or target.is_symlink()
                    if had_old:
                        copy(target, old)
                    applied.append((target, old, had_old))
                    remove(target)
                    if incoming is not None:
                        copy(incoming, target)
                installed = safe_path(project, str(Path(skills_dir) / 'ontolink-skills'))
                if existing is None:
                    run_json(installed / 'scripts/mediator.py', 'bootstrap', '--root', project)
                refreshed = adapter.refresh(installed, state, data)
                if existing is not None and state.read_bytes() != existing:
                    raise ValueError('Canonical state changed during setup; stop and inspect concurrent activity')
                result = {'previousVersion': previous.get('sourceVersion'),
                          'sourceVersion': catalog['version'], 'skillsDirectory': skills_dir,
                          'canonicalState': state_path, 'backup': str(backup.relative_to(state.parent)),
                          'revision': refreshed['context']['revision'],
                          'paths': [str(target.relative_to(project)) for target, _ in changes]}
                adapter.atomic_json(adapter.inside(data, 'installation.json'), result)
                return result
            except Exception:
                for target, old, had_old in reversed(applied):
                    remove(target)
                    if had_old:
                        copy(old, target)
                adapter.inside(data, 'context.json').unlink(missing_ok=True)
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--skills-dir', default='.agents/skills')
    parser.add_argument('--state', default='knowledge.owl')
    args = parser.parse_args()
    try:
        print(json.dumps(setup(args.project, args.skills_dir, args.state), ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, 'OntoLink setup: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
