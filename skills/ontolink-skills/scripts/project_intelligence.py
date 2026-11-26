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
    else:
        graph, ontology = _load_state(args.state)
        if args.command == 'search' and args.tasks_only:
            # Read only task nodes from the canonical graph; do not open the code index.
            hits = search(graph, None, args.query, args.limit, only_tasks=True)
            if args.compact:
                result = {'query': args.query, 'tasks': [
                    {'id': hit.id, 'title': graph.one(hit.node, 'urn:ontolink:title'),
                     'status': graph.one(hit.node, 'urn:ontolink:status'),
                     'phase': graph.one(hit.node, 'urn:ontolink:phase').removeprefix('urn:ontolink:')}
                    for hit in hits]}
            else:
                result = {'query': args.query, 'hits': [hit.as_dict() for hit in hits]}
        else:
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
