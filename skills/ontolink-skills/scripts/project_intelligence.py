#!/usr/bin/env python3
"""Optional OntoLink project-intelligence commands.

This CLI does not modify ``knowledge.owl``. It builds a generated index under
``.ontolink/index`` and can enrich the mediator's existing context packet with
ranked code/file hints while preserving the original workflow contract.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from context_compiler import compile_context
from mediator import ONTOLOGY, snapshot
from project_indexer import build_index, default_index_path, load_index, update_index, write_index
from rdf_store import Store
from retrieval import search
from smart_tasks import smart_search_tasks
from task_access import focused_work_packet


def _index(root: Path, output: Path | None, changed: list[str]):
    target = output or default_index_path(root)
    if changed and target.exists():
        data = update_index(root, load_index(target), changed)
    else:
        data = build_index(root)
    write_index(target, data)
    return {'index': str(target), 'records': data['recordCount'], 'incremental': bool(changed)}


def _load_state(state: Path):
    return Store.read(state), Store.read(ONTOLOGY)


def _load_optional_index(root: Path, index_path: Path | None):
    path = index_path or default_index_path(root)
    return (load_index(path), path) if path.exists() else ({'version': 1, 'records': []}, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)

    ix = sub.add_parser('index', help='Build or incrementally refresh the generated project-code index')
    ix.add_argument('--root', type=Path, default=Path.cwd())
    ix.add_argument('--output', type=Path)
    ix.add_argument('--changed', action='append', default=[])

    srch = sub.add_parser('search', help='Search canonical project knowledge plus the generated index')
    srch.add_argument('--root', type=Path, default=Path.cwd())
    srch.add_argument('--state', type=Path, required=True)
    srch.add_argument('--index', type=Path)
    srch.add_argument('--query', required=True)
    srch.add_argument('--limit', type=int, default=10)
    srch.add_argument('--tasks-only', action='store_true')
    srch.add_argument('--compact', action='store_true')

    focus = sub.add_parser('focus', help='Targeted task work context with direct integrity checks')
    focus.add_argument('--state', type=Path, required=True)
    focus.add_argument('--task', required=True)
    focus.add_argument('--budget', type=int, default=2000)
    focus.add_argument('--strict', action='store_true',
                       help='Validate the entire project before returning the focused packet')

    ctx = sub.add_parser('context', help='Extend the legacy mediator packet with ranked project-intelligence hints')
    ctx.add_argument('--root', type=Path, default=Path.cwd())
    ctx.add_argument('--state', type=Path, required=True)
    ctx.add_argument('--index', type=Path)
    ctx.add_argument('--query', required=True)
    ctx.add_argument('--task')
    ctx.add_argument('--limit', type=int, default=10)
    ctx.add_argument('--budget', type=int, default=6000)

    args = parser.parse_args()
    if args.command == 'index':
        result = _index(args.root, args.output, args.changed)
    elif args.command == 'search' and args.tasks_only:
        # Stage 1: Python parses project RDF; the model only receives Top-K IDs.
        # No task JSON, generated source index or static ontology is opened.
        tasks = smart_search_tasks(Store.read(args.state), args.query, args.limit)
        result = {'query': args.query, 'tasks': tasks}
    elif args.command == 'focus':
        # Stage 2/3: read and SHA-check exactly one task JSON, fetch direct
        # dependencies and actionable evidence, and send a focused work packet.
        graph, ontology = _load_state(args.state)
        if args.strict:
            from mediator import validate
            validate(graph, args.state.parent, ontology)
        result = focused_work_packet(graph, ontology, args.state.parent, args.task, args.budget)
        if args.strict:
            result['validation_scope'] = 'full project validation plus focused task'
    else:
        graph, ontology = _load_state(args.state)
        index_data, path = _load_optional_index(args.root, args.index)
        hits = search(graph, index_data, args.query, args.limit)
        if args.command == 'search':
            result = {'index': str(path), 'query': args.query,
                      'hits': [hit.as_dict() for hit in hits]}
        else:
            base = snapshot(graph, ontology, args.state.parent, args.task, args.budget,
                            compact=bool(args.task))
            result = compile_context(base, hits, args.budget)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
