---
name: ontolink-implementation
description: Implementation phase procedure for ontology-mediated OntoLink tasks.
---

# Implementation

Load only this phase and the focused context returned by the [coordinator](../../SKILL.md). Follow the existing `knowledge.owl` state; never bootstrap a second graph.

**Phase:** `build`. **Required outcome kind:** `implementation`.

Change real source code, then build and exercise affected components. Preserve existing contracts and record exact files and results.

Use `mediator.py context --task <id>` to check current dependencies and blockers. Update the existing single task JSON through `record --json` with the observed revision. Attach only relevant source/proof references and the **latest** update. Preserve real evidence and dependencies; mark DONE only after current PASS proof and all prerequisites. Query context again before handing off.
