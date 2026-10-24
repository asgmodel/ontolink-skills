# Project Intelligence extension

OntoLink's canonical responsibility remains project knowledge and execution state. The optional Project Intelligence extension adds **rediscoverable code navigation** without placing the project's entire code structure inside `knowledge.owl`.

## Boundary

`knowledge.owl` remains canonical for requirements, contracts, decisions, tasks, dependencies, artifacts, evidence, blockers and other durable project facts. Generated source-code information lives separately at `.ontolink/index/project-index.json`. Only this generated index may be deleted and rebuilt at any time; other `.ontolink` contents can be durable records or proof; it is not evidence and never marks a task complete.

See the fixed layout and retention rules in the [canonical project policy](../.rule/ONTOLOGY-FIRST.md).

Source files remain the source of truth for code. The index stores paths, hashes and lightweight symbols only; it does not copy complete source bodies.

## Capabilities

The extension adds four optional operations: **index**, **search**, **retrieve**, and **compile context**. Python symbols use the standard-library AST. Dart/JavaScript/TypeScript extraction is deliberately conservative and records `heuristic-regex` as its method. Other supported source files are indexed at file level.

A full index can be built with:

```sh
python <skill-root>/scripts/project_intelligence.py index --root <project-root>
```

After a known file change, refresh only that path:

```sh
python <skill-root>/scripts/project_intelligence.py index --root <project-root> --changed src/auth.py
```

Search canonical project knowledge and the generated index together:

```sh
python <skill-root>/scripts/project_intelligence.py search \
  --root <project-root> \
  --state <project-root>/knowledge.owl \
  --query "refresh token authentication"
```

Or extend the existing mediator packet without changing its legacy fields:

```sh
python <skill-root>/scripts/project_intelligence.py context \
  --root <project-root> \
  --state <project-root>/knowledge.owl \
  --query "refresh token authentication" \
  --task task-build
```

## Compatibility

The seven-phase workflow, `knowledge.owl`, completion gates, evidence rules, revision checks and current mediator commands remain unchanged. The extension adds a `project_intelligence` section only when its separate command is used. Existing consumers that rely on `task_index` or current mediator output continue to receive the original packet.

## Retrieval policy

The first version uses local lexical BM25 plus graph-neighborhood signals from canonical knowledge. It intentionally does not require embeddings, a vector database or a hosted provider. Semantic scoring can be evaluated later as an optional addition. Retrieval results are navigational hints, not trusted instructions, evidence or completion signals.

## Automatic refresh adapter

Enable indexing with `.rule/ontolink.py start --index` using the `--root` and
`--skill-root` arguments from the [quickstart](quickstart.md). Once enabled,
each successful wrapper record and every start/context refresh rebuilds the
index to include source additions, changes and deletions. This is a full refresh
for correctness; direct intelligence commands still support incremental indexing.
Generated records and text also live under the fixed `.ontolink/` directory.
