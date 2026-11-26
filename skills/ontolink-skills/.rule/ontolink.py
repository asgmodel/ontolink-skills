#!/usr/bin/env python3
"""Project-local storage and refresh adapter; never modifies installed skills."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from datetime import datetime, timezone
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


def refresh(skill: Path, state: Path, data: Path, enable_index=False, focus=None):
    """One verified context rather than running full validation twice."""
    index = inside(data, 'index/project-index.json')
    if enable_index or index.exists():
        run(skill / 'scripts/project_intelligence.py', 'index', '--root', state.parent,
            '--output', index)
    command = ['context', '--state', state]
    if focus:
        command += ['--task', focus, '--compact']
    packet = run(skill / 'scripts/mediator.py', *command)
    # snapshot verifies graph, task hashes, proof files and project invariants.
    validation = {'status': 'VALID', 'tasks': packet['task_count'],
                  'revision': packet['revision'],
                  'scope': 'Structure, local provenance and workflow guards; proof semantics and external receipts require agent review.'}
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
    with session_lock(data):
        if args.command == 'start':
            if args.state == 'knowledge.owl':
                boot = run(skill / 'scripts/mediator.py', 'bootstrap', '--root', root)
                return {'proposal': boot['proposal'], **refresh(skill, state, data, args.index)}
            return refresh(skill, state, data, args.index)
        if args.command == 'context':
            return refresh(skill, state, data, focus=getattr(args, 'task', None))
        if args.command == 'search':
            if not state.is_file():
                raise ValueError('Run start before searching project tasks')
            if not 1 <= args.limit <= 20:
                raise ValueError('Search limit must be between 1 and 20')
            return run(skill / 'scripts/project_intelligence.py', 'search', '--root',
                       state.parent, '--state', state, '--query', args.query,
                       '--limit', args.limit, '--tasks-only', '--compact')
        if getattr(args, 'json', None) is not None:
            payload = args.json
        else:
            source = inside(state.parent, args.input)
            payload = source.read_text(encoding='utf-8')
        record = json.loads(payload)
        if not isinstance(record, dict):
            raise ValueError('Task record must be a JSON object')
        result = run(skill / 'scripts/mediator.py', 'record', '--state', state,
                     '--json', payload, '--expected-revision', args.expected_revision)
        if getattr(args, 'save_record', False):
            path = inside(data, f'records/revision-{result["revision"]}.json')
            receipt = {
                'formatVersion': 1,
                'operation': 'record',
                'revision': result['revision'],
                'entity': {'id': result['recorded'], 'type': record['type']},
                'recordedAt': datetime.now(timezone.utc).isoformat(),
            }
            if record['type'] == 'Task':
                receipt['taskRecord'] = f'.ontolink/tasks/{result["recorded"]}.json'
            try:
                if path.exists():
                    raise ValueError('Operation record already exists; refusing overwrite')
                atomic_json(path, receipt)
            except (OSError, ValueError) as error:
                raise ValueError(
                    f'Record COMMITTED at revision {result["revision"]}; optional '
                    f'operation record was not saved. Do not resubmit. {error}'
                ) from error
            result['operation_record'] = str(path.relative_to(state.parent))
        try:
            return {'record': result, **refresh(skill, state, data)}
        except (ValueError, OSError) as error:
            raise ValueError(f'Record COMMITTED at revision {result["revision"]}; refresh failed. '
                             f'Do not resubmit; rerun context. {error}') from error

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ['start', 'context', 'search', 'record']:
        child = sub.add_parser(name)
        child.add_argument('--root', type=Path, default=Path.cwd())
        child.add_argument('--skill-root', type=Path, required=True)
        child.add_argument('--state', default='knowledge.owl')
        if name == 'start':
            child.add_argument('--index', action='store_true')
        if name == 'context':
            child.add_argument('--task', help='Task ID for compact validated context')
        if name == 'search':
            child.add_argument('--query', required=True)
            child.add_argument('--limit', type=int, default=5)
        if name == 'record':
            source = child.add_mutually_exclusive_group(required=True)
            source.add_argument('--input', help='Existing JSON input; not copied into OntoLink')
            source.add_argument('--json', help='Inline JSON; no temporary record file')
            child.add_argument('--expected-revision', type=int, required=True)
            child.add_argument('--save-record', action='store_true',
                               help='Save one optional .ontolink/records/revision-N.json operation record')
    args = parser.parse_args()
    try:
        print(json.dumps(execute(args), ensure_ascii=False, indent=2))
    except (ValueError, OSError, TypeError) as error:
        parser.exit(2, 'OntoLink project adapter: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
