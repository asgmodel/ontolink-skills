# Execution contract

The ontology defines seven available phases: `discover → design → plan → build → verify → deliver → monitor`. **Not every project needs seven initial tasks.** Startup proposes 1 task for small projects, 3 for medium, 7 for large. More tasks are added only when real scope requires them. Any declared prerequisite must be completed; removing a task does not imply work was performed.

The single active `knowledge.owl` stores the project, compact task projections and unique RDF links. `.ontolink/tasks/<id>.json` is the one current detail file for each task. `taskRecordHash` protects the reference. No new Event nodes, redundant JSON caches or per-revision receipts are created; old events may be archived during safe compaction. Do not overwrite or reset existing state.

For every action, read only the focused task, relevant dependencies and phase skill. Preserve the source project's code and contracts. Record the latest update and verified evidence. Use `--expected-revision` to reject concurrent writes. `DONE` requires current artifact bytes, matching proof hashes, explicit PASS evidence, resolved blockers and completed real dependencies.

External deployments and communications require actual authorization and receipts. A matching hash does not prove the semantic correctness of a test. Never invent successful checks, confidence values, changes or token savings.

When the ontology exceeds the archive threshold, preserve a copy under `.ontolink/archive/` before safe compaction. Continue working in the new `knowledge.owl` without discarding task JSON, required dependencies or evidence. Generated code indices are optional and not canonical task knowledge.
