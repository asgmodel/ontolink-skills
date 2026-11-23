---
name: ontolink-monitoring
description: Monitoring phase procedure for ontology-mediated OntoLink tasks.
---

# Monitoring

Load only this phase and the focused context returned by the [coordinator](../../SKILL.md). Follow the existing `knowledge.owl` state; never bootstrap a second graph.

**Phase:** `monitor`. **Required outcome kind:** `monitoring`.

Inspect current health and follow-up risks during active sessions. Do not claim continuous monitoring without an actual automation.

Use `mediator.py context --task <id>` to check current dependencies and blockers. Update the existing single task JSON through `record --json` with the observed revision. Attach only relevant source/proof references and the **latest** update. Preserve real evidence and dependencies; mark DONE only after current PASS proof and all prerequisites. Query context again before handing off.
