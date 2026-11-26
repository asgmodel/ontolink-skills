---
name: ontolink-skills
description: Coordinate discovery, architecture, planning, implementation, verification, delivery and monitoring with compact OWL project state and one JSON record per task.
---

# OntoLink coordinator

Use one canonical `knowledge.owl` per target project. Its triples contain the project, active task summaries, unique dependencies and links to task records. Store task-specific details in `.ontolink/tasks/<id>.json`, one task per file; only the latest update is retained. Do not add project JSON or `.ontolink` to this skill repository.

## Start

Resolve the real target root; never initialize inside the skills distribution. Read [project policy](.rule/ONTOLOGY-FIRST.md), then run:

```sh
python <skill-root>/scripts/project_setup.py --project /absolute/project
python <project>/.rule/ontolink.py start --root <project> --skill-root <project>/.agents/skills/ontolink-skills
```

The mediator inspects source footprint and proposes small / medium / large starter workflows. It creates one, three or seven phase tasks, respectively; don't create speculative subtasks. Existing canonical state is validated, not reset.

## Execute

1. Get a focused packet with `mediator.py context --state <project>/knowledge.owl --task <id>`; load only the selected phase skill in `skills/`.
2. Work on the actual code and checks. Keep full logs in their original project files. Refer to only relevant files and concise proof/evidence in the task record.
3. Record a change using `mediator.py record --state ... --json '{"id":"task-discover","type":"Task","lastUpdate":"..."}' --expected-revision N`. Other typed records remain supported, but no new Event nodes are written.
4. Re-query and validate. DONE requires completed dependencies, current artifacts, passing proof, and resolved blockers. Never invent successful checks or externally completed actions.
5. Read [record contract](references/record-contract.md) and the fixed v4 template only before writes; use [execution contract](references/execution-contract.md) only if the workflow requires more detail.

Graph/JSON boundary: `knowledge.owl` contains lightweight identity, links,
dependencies, status and routing; detailed `description` (problem, objective,
scope, approach and testable acceptance criteria) exists only in task JSON.
Search the graph with Python before reading the selected task details.
Do not copy entire ontologies, index history or all phase files into prompts. The JSON record is a SHA-256-linked snapshot; avoid repeating relations between `properties` and `relationships`. Context provides only the active task and a bounded task index.

Seven on-demand skills are `ontolink-discovery`, `ontolink-architecture`, `ontolink-planning`, `ontolink-implementation`, `ontolink-verification`, `ontolink-delivery` and `ontolink-monitoring`. Optional generated source indexing is available using `project_intelligence.py` for large repositories; it is not canonical task knowledge.

Keep existing project state and evidence when upgrading. Preserve user files, approval requirements and revision locks. Missing proof is not completion. 
