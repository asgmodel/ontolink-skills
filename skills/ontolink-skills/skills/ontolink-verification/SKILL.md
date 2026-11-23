---
name: ontolink-verification
description: Verification phase procedure for ontology-mediated OntoLink tasks.
---

# Verification

Load only this phase and the focused context returned by the [coordinator](../../SKILL.md). Follow the existing `knowledge.owl` state; never bootstrap a second graph.

**Phase:** `verify`. **Required outcome kind:** `verification`.

Run relevant tests, inspect failures and confirm artifact/proof hashes. Report unresolved issues rather than issuing unsupported PASS evidence.

Use `mediator.py context --task <id>` to check current dependencies and blockers. Update the existing single task JSON through `record --json` with the observed revision. Attach only relevant source/proof references and the **latest** update. Preserve real evidence and dependencies; mark DONE only after current PASS proof and all prerequisites. Query context again before handing off.
