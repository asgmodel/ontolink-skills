#!/usr/bin/env python3
"""Project-local storage and refresh adapter; never modifies installed skills."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def inside(base: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Use a project-relative path without ..: ' + relative)
    target = base / path
    for candidate in [target, *target.parents]:
        if candidate == base:
            break
        if candidate.is_symlink():
            raise ValueError('Symlink paths are not supported: ' + str(candidate))
    if not target.resolve().is_relative_to(base.resolve()):
        raise ValueError('Path escapes project: ' + relative)
    return target


def atomic_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.ontolink-', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def run(script: Path, *arguments):
    command = [sys.executable, str(script), *map(str, arguments)]
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise ValueError(f'Command failed ({result.returncode}): {command!r}\n{result.stderr.strip()}')
    return json.loads(result.stdout)


@contextmanager
def session_lock(data: Path):
    lock = inside(data, 'session.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


def refresh(skill: Path, state: Path, data: Path, enable_index=False):
    cache = inside(data, 'context.json')
    cache.unlink(missing_ok=True)
    validation = run(skill / 'scripts/mediator.py', 'validate', '--state', state)
    index = inside(data, 'index/project-index.json')
    if enable_index or index.exists():
        run(skill / 'scripts/project_intelligence.py', 'index', '--root', state.parent,
            '--output', index)
    packet = run(skill / 'scripts/mediator.py', 'context', '--state', state)
    atomic_json(cache, packet)
    return {'validation': validation, 'context': packet}


def execute(args):
    root = args.root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Project root must be an existing directory')
    skill = args.skill_root.resolve(strict=True)
    if not (skill / 'scripts/mediator.py').is_file() or not (skill / 'SKILL.md').is_file():
        raise ValueError('Resolve the actual installed ontolink-skills coordinator directory')
    state = inside(root, args.state)
    if args.state != 'knowledge.owl' and not state.is_file():
        raise ValueError('Explicit state must already exist; use the mediator init command deliberately')
    data = inside(state.parent, '.ontolink')
    data.mkdir(exist_ok=True)
    for folder in ['records', 'proofs', 'artifacts']:
        inside(data, folder).mkdir(exist_ok=True)
    with session_lock(data):
        # Never leave a stale successful packet after any failed operation.
        inside(data, 'context.json').unlink(missing_ok=True)
        if args.command == 'start':
            if args.state == 'knowledge.owl':
                run(skill / 'scripts/mediator.py', 'bootstrap', '--root', root)
            return refresh(skill, state, data, args.index)
        if args.command == 'context':
            return refresh(skill, state, data)
        payload = inside(state.parent, args.input)
        if not payload.is_relative_to(data / 'records') or payload.suffix != '.json':
            raise ValueError('Record input must be .ontolink/records/<name>.json beside canonical state')
        # Validate payload syntax before invoking the canonical writer.
        record = json.loads(payload.read_text(encoding='utf-8'))
        if not isinstance(record, dict):
            raise ValueError('Record input must be a JSON object')
        receipt = inside(data, f'records/revision-{args.expected_revision + 1}.receipt.json')
        if receipt.exists():
            raise ValueError('Receipt already exists; query context and reconcile before retrying')
        result = run(skill / 'scripts/mediator.py', 'record', '--state', state,
                     '--input', payload, '--expected-revision', args.expected_revision)
        try:
            atomic_json(receipt, {'input': args.input, 'result': result})
            return {'record': result, **refresh(skill, state, data)}
        except (ValueError, OSError) as error:
            inside(data, 'context.json').unlink(missing_ok=True)
            raise ValueError(f'Record COMMITTED at revision {result["revision"]}; refresh/receipt failed. '
                             f'Do not resubmit; rerun context. {error}') from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ['start', 'context', 'record']:
        child = sub.add_parser(name)
        child.add_argument('--root', type=Path, default=Path.cwd())
        child.add_argument('--skill-root', type=Path, required=True)
        child.add_argument('--state', default='knowledge.owl')
        if name == 'start':
            child.add_argument('--index', action='store_true')
        if name == 'record':
            child.add_argument('--input', required=True)
            child.add_argument('--expected-revision', type=int, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(execute(args), ensure_ascii=False, indent=2))
    except (ValueError, OSError, TypeError) as error:
        parser.exit(2, 'OntoLink project adapter: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
