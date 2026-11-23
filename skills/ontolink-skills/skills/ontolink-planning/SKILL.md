---
name: ontolink-planning
description: Planning phase procedure for ontology-mediated OntoLink tasks.
---

# Planning

Load only this phase and the focused context returned by the [coordinator](../../SKILL.md). Follow the existing `knowledge.owl` state; never bootstrap a second graph.

**Phase:** `plan`. **Required outcome kind:** `plan`.

Split only real work into concise subtasks. Give each task one owner, explicit dependencies, completion criteria and realistic scope.

Use `mediator.py context --task <id>` to check current dependencies and blockers. Update the existing single task JSON through `record --json` with the observed revision. Attach only relevant source/proof references and the **latest** update. Preserve real evidence and dependencies; mark DONE only after current PASS proof and all prerequisites. Query context again before handing off.
