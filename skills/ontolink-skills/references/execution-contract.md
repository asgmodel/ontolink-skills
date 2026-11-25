# Execution contract

## Sequence and handoffs

| Phase | Skill | Mandatory outcome kind | Next phase |
| --- | --- | --- | --- |
| discover | ontolink-discovery | requirements | design |
| design | ontolink-architecture | contracts | plan |
| plan | ontolink-planning | plan | build |
| build | ontolink-implementation | implementation | verify |
| verify | ontolink-verification | verification | deliver |
| deliver | ontolink-delivery | handoff | monitor |
| monitor | ontolink-monitoring | monitoring | new/reopened work |

The OWL phase individuals supply this sequence and routing. Do not introduce a parallel JSON routing authority. The graph's initial seven tasks are workflow obligations, not evidence of product implementation. Split them into owned subtasks only with explicit outcomes and dependencies; earlier phases must finish before a later task becomes executable. A partial documentation review does not justify passing a runtime verification obligation.

## State ownership

On first project use, automatically run the coordinator bootstrap to create or reuse `knowledge.owl` at the real project root. Preserve an explicitly configured canonical state path and never create a second graph. Installation alone does not execute the bootstrap. Keep the default state at the project root as `knowledge.owl`. Paths in artifacts and proof records are relative to its directory. All referenced files must remain within that directory; symlink escapes and absolute paths are rejected. Keep secrets and private personal data out of graph records, prompts and committed proof logs.

The mediator stores supported triples, applies task/phase guards and atomically updates cooperating writers through a lock and expected revision. Do not clear a lock simply to bypass another writer; investigate a stale lock after establishing the owning process is no longer active. Never edit the state behind an active writer.

Confidence/likelihood records do not contribute to progress. Progress is completed accepted task weight divided by total declared task weight; changing the task set changes the denominator and must be reported. If current bytes differ from a recorded artifact, context validation fails until the revision and its downstream impact are recorded.

## Evidence and change impact

A PASS record requires a local proof file and hashes matching both that proof and its current target artifact. This establishes traceable provenance, not proof that the command ran, the test was meaningful or the claim is true. Review the command, environment, output, acceptance criteria and source revision before recording PASS.

Link dependent artifacts and tasks through `dependsOn`, `usesArtifact` and `derivedFrom`. Changed artifact hashes, reopened tasks and changed requirements/contracts/decisions reopen reachable tasks and stale reachable artifacts. Re-run affected checks before closing work. Closing a blocker only makes work eligible; it does not complete the task.

External deployments, provider integrations and sent communications need actual external receipts and host authorization. A graph field or local screenshot name cannot grant permission or prove an external operation.
